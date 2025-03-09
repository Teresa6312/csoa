from django.db.models import OuterRef, Subquery, Value
from django.db.models.functions import Coalesce, Cast
from django.db.models import TextField
from django.shortcuts import render, redirect
from jsonForm.models import FormTemplate, Workflow
from userManagement.models import AppMenu
from jsonForm.forms import create_dynamic_task_instance_form
from jsonForm import util as formUtil
from .models import FileModel

# from jsonForm.tables import create_dynamic_case_table_class, create_dynamic_case_data_table_class, create_dynamic_case_data_filter
# from django_tables2 import RequestConfig
from django.db.models import JSONField
from .util import (
    CustomJSONEncoder,
    set_datatables_response,
    no_permission_redirect,
    get_model_class,
    get_object_or_redirect,
)
from .util_model import get_audit_history_fields, get_select_choices
from .util_files import download_file
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.db.models import Q
from functools import reduce
from django.urls import reverse

from base.constants import TASK_TYPE_AUTO

import json

import logging

logger = logging.getLogger("django")


def create_case_view(request, context, app_name, form_code):
    """
    View to create a new case.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): Context data for the view.
        app_name (str): The name of the application.
        form_code (str): The code of the form.

    Returns:
        HttpResponse: Renders the case creation form or redirects to the app home.

    Database Operations:
        - Read: FormTemplate
        - Create: Case instance

    Tables Used:
        - FormTemplate (Read)
    """
    template_name = "base/app_case_form.html"
    form = context["form"]
    if form is None:
        return render(request, template_name, context)
    case_context = formUtil.create_case_view(request, form, context["mini_app"].id)
    if case_context == {}:
        return redirect("app:app_home", app_name)
    else:
        context.update(case_context)
    form_template = form.form_section_form_template.all().values()
    form_template_data = json.dumps(list(form_template), cls=CustomJSONEncoder)
    context["form_template"] = json.loads(form_template_data)
    return render(request, template_name, context)


def edit_case_view(request, context, app_name, form_code, case_id):
    """
    View to edit an existing case.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): Context data for the view.
        app_name (str): The name of the application.
        form_code (str): The code of the form.
        case_id (int): The ID of the case to be edited.

    Returns:
        HttpResponse: Renders the case edit form or redirects to the app home.

    Database Operations:
        - Read: Case instance
        - Update: Case data

    Tables Used:
        - Case instance (Read, Update)
    """
    template_name = "base/app_case_form.html"
    form = context["form"]
    case_instance = context["case_instance"]
    mini_app = context["mini_app"]
    if case_instance is None:
        return redirect("app:app_home", app_name)
    workflow_edit_status = [
        v[0] for v in get_select_choices("dict_workflow_edit_status_active")
    ]
    if not (
        request.user == case_instance.created_by
        and case_instance.status in workflow_edit_status
    ):
        messages.warning(
            request,
            f"only the user who created the case can EDIT the case with status in {workflow_edit_status} (Case ID: {case_id}, Case: Status {case_instance.status})",
        )
        return redirect("app:app_home", app_name)
    case_context = formUtil.edit_case_data_view(
        request, case_instance, form, mini_app.id
    )
    if case_context == {}:
        return redirect("app:app_my_cases_index", app_name)
    else:
        context.update(case_context)
    context["edit"] = True
    context["datatables"] = False
    form_template = form.form_section_form_template.all().values()
    form_template_data = json.dumps(list(form_template), cls=CustomJSONEncoder)
    context["form_template"] = json.loads(form_template_data)
    return render(request, template_name, context)


def get_case_details(request, context, app_name, form_code, case_id, display_type="block"):
    """
    View to get details of a specific case.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): Context data for the view.
        app_name (str): The name of the application.
        form_code (str): The code of the form.
        case_id (int): The ID of the case.

    Returns:
        HttpResponse: Renders the case details page.

    Database Operations:
        - Read: Case instance, TaskInstance, FileModel

    Tables Used:
        - Case instance (Read)
        - TaskInstance (Read)
        - FileModel (Read)
    """
    template_name = "base/app_case_details.html"
    case_instance = context["case_instance"]
    mini_app = context["mini_app"]
    if case_instance is None:
        return redirect("app:app_home", app_name)

    # set up the case form section details

    if display_type == "list":
        section_datas_fields = {'id': 'ID'}
        template_fields = case_instance.case_data_case.first().form_section.get_fields
        for key in template_fields.keys():
            section_datas_fields["section_data__" + key] = template_fields.get(key)
        section_datas_list = list(case_instance.case_data_case.all().values(*section_datas_fields))
        context["section_datas_list"] = section_datas_list
        context["section_datas_fields"] = section_datas_fields
    else:
        section_datas = (
            case_instance.case_data_case.all()
            .values("form_section__json_template", "section_data")
            .order_by("form_section__index")
        )
        context["section_datas"] = json.dumps(list(section_datas), cls=CustomJSONEncoder)

    # set up the task list data
    TaskInstance = case_instance.get_task_instances_model()
    task_fields = (
        TaskInstance.selected_fields_info()
    )  # need to be replace with a config table to maintains the field list like model dict
    task_fields_names = list(task_fields.keys())
    context["task_fields"] = task_fields

    if case_instance.workflow_instance is not None:
        if request.user.is_superuser:
            tasks_queryset = (
                case_instance.workflow_instance.task_instance_workflow_instance.all()
            )
        else:
            tasks_queryset = (
                case_instance.workflow_instance.task_instance_workflow_instance.exclude(
                    task__task_type=TASK_TYPE_AUTO
                )
            )
        context["task_instances"] = json.dumps(
            list(
                tasks_queryset.values(*task_fields_names).order_by(
                    "-created_at", "-updated_at"
                )
            ),
            cls=CustomJSONEncoder,
        )
    else:
        context["task_instances"] = []

    # set up the task instance form for the case details page
    role_unit = request.current_page_menu.get("role_unit", [])
    role_unit_ids = [r.get("permission_role__id") for r in role_unit]
    TaskInstanceForm = create_dynamic_task_instance_form(TaskInstance)

    if case_instance.workflow_instance is not None and request.method == "POST":
        case_lock = case_instance.get_lock()
        if case_lock is not None:
            messages.warning(
                request,
                f"Case #{case_instance.id} is locked by user {case_lock}, please try again after one minute.",
            )
            return redirect("app:app_case_details", app_name, form_code, case_id)
        else:
            case_instance.set_lock(request)
        pending_task_forms = [
            TaskInstanceForm(
                request.POST,
                request.FILES,
                request=request,
                instance=ti,
                prefix=f"pending_task_{ti.id}",
            )
            for ti in tasks_queryset.filter(
                Q(is_active=True)
                & (
                    Q(assign_to__id__in=role_unit_ids)
                    | Q(is_active=request.user.is_superuser)
                )
            )
        ]
        forms_is_valid = True
        for task_form in pending_task_forms:
            task_form.pre_clean_validation(mini_app, case_instance)
            if not task_form.is_valid():
                forms_is_valid = False
        if forms_is_valid:
            for task_form in pending_task_forms:
                task_form.save()
                case_instance.updated_by = request.user
                try:
                    case_instance.save()
                except Exception as e:
                    for t in pending_task_forms:
                        task = TaskInstance.objects.get(id=t.instance.id)
                        task.is_active = True
                        task.save()
                        logger.debug(e)
                        messages.error(request, e)
                    raise Exception(e)
            case_instance.remove_lock()
            return redirect("app:app_case_details", app_name, form_code, case_id)
        else:
            context["pending_task_forms"] = pending_task_forms
    elif case_instance.workflow_instance is not None:
        context["pending_task_forms"] = [
            TaskInstanceForm(
                request=request, instance=ti, prefix=f"pending_task_{ti.id}"
            )
            for ti in tasks_queryset.filter(
                Q(is_active=True)
                & (
                    Q(assign_to__id__in=role_unit_ids)
                    | Q(is_active=request.user.is_superuser)
                )
            )
        ]

    # audit history setting
    context["history_data_url"] = reverse(
        "api:app_case_details_history", args=[app_name, form_code, case_id]
    )
    context["history_fields"] = get_audit_history_fields()

    # document settings
    file_fields = (
        FileModel.selected_fields_info()
    )  # need to be replace with a config table to maintains the field list like model dict
    related_name = "%s_%s_files" % (
        TaskInstance._meta.app_label.lower(),
        TaskInstance._meta.model_name,
    )
    file_fields["%s__task__name" % related_name] = "Task Name"
    context["file_data_url"] = reverse(
        "api:app_case_details_documents", args=[app_name, form_code, case_id]
    )
    context["file_download_url"] = reverse(
        "api:app_case_details_file_download", args=[app_name, form_code, case_id, "0"]
    )
    context["file_fields"] = file_fields
    context["file_root"] = settings.MEDIA_URL
    return render(request, template_name, context)


def get_my_cases_view(request, context, app_name):
    """
    View to get the list of cases assigned to the current user.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): Context data for the view.
        app_name (str): The name of the application.

    Returns:
        HttpResponse: Renders the user's cases list.

    Database Operations:
        - Read: AppMenu, model_class

    Tables Used:
        - AppMenu (Read)
        - model_class (Read)

    Addtional Information:
        # all the forms linked in one mini_app should using same table to store data
        # if the forms use different table to store data, need to create another view
        # need to create search function in UI template for search data
        # ongoingList/completedList

    """
    type = request.GET.get("type")
    permission_list = request.permission_list
    if type is None:
        type = "todoList"
    context["type"] = type

    show_list = False
    permission__details = False
    permission__edit = False

    if type is None:
        type = "todoList"
    context["type"] = type

    for perm in permission_list:
        if perm == type:
            show_list = True
        elif perm == f"{type}__details":
            permission__details = True
        elif perm == f"{type}__edit":
            permission__edit = True

    if not show_list:
        return no_permission_redirect(
            request, None, f"No permission to {type}-{show_list}"
        )

    template_name = "base/app_my_cases.html"
    form = AppMenu.get_app_form_by_key(app_name)
    model_class = form.get_model_class()

    context["fields"] = model_class.selected_fields_info()
    context["id_key"] = "id"
    context["other_key"] = "form_code"
    context["permission__details"] = permission__details
    context["permission__edit"] = permission__edit
    context["data_url"] = reverse("api:app_my_cases_data", args=[app_name, type])
    context["details_url"] = reverse("app:app_case_details", args=[app_name, 0, 1])
    context["edit_url"] = reverse("app:app_my_cases_edit", args=[app_name, 0, 1])
    return render(request, template_name, context)


def get_cases_search_by_form_view(request, context, app_name, form_code):
    """
    View to search cases by form.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): Context data for the view.
        app_name (str): The name of the application.
        form_code (str): The code of the form.

    Returns:
        HttpResponse: Renders the case search results.

    Database Operations:
        - Read: FormTemplate, data_class

    Tables Used:
        - FormTemplate (Read)
        - data_class (Read)
    
     Addtional Information:
       - FormTemplate (Read): The model that contains information about forms.
       - data_class (Read): The model that contains information about cases.
    """
    template_name = "base/app_case_list.html"
    # ----------------------------------------------------------------------------------
    # 1. initialize all the default data
    # ----------------------------------------------------------------------------------
    index = request.GET.get("index")
    if index is None:
        index = 0
    mini_app = context["mini_app"]
    form = context["form"]
    data_class = get_model_class(form.backend_app_label, form.backend_app_section_model)
    # ----------------------------------------------------------------------------------
    # 2. set up headers for the table
    # ----------------------------------------------------------------------------------
    fields = data_class.selected_fields_info()
    headers = FormTemplate.get_headers_by_code(form_code)
    for h in headers:
        if h["index"] == index:
            fields[f"section_data__{h['key']}"] = h["label"]

    context["fields"] = fields
    context["data_url"] = reverse(
        "api:app_cases_search_form_Data",
        args=[app_name, form_code, mini_app.id, form.id, index],
    )
    context["id_key"] = "case__id"
    context["details_url"] = reverse(
        "app:app_case_details", args=[app_name, form_code, 0]
    )
    return render(request, template_name, context)


def get_case_workflow_view(request, context, app_name, form_code, case_id):
    """
    View to get the workflow details of a specific case.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): Context data for the view.
        app_name (str): The name of the application.
        form_code (str): The code of the form.
        case_id (int): The ID of the case.

    Returns:
        HttpResponse: Renders the workflow details page.

    Database Operations:
        - Read: Workflow

    Tables Used:
        - Workflow (Read)
    """
    template_name = "jsonForm/workflow.html"
    workflow_data = Workflow.get_data_by_id(context["form"].workflow.id)
    context["workflow_data"] = workflow_data
    return render(request, template_name, context)
