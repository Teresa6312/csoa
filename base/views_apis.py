from .util_model import get_select_choices, get_dictionary, get_dictionary_item_map
from .util import CustomJSONEncoder
import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status  # For HTTP status codes
from rest_framework.decorators import api_view
from .decorators import case_decorator
from django.db.models import Q
from .util import (
    CustomJSONEncoder,
    set_datatables_response,
    no_permission_redirect,
    get_model_class,
    get_object_or_redirect,
)
from jsonForm.models import FormTemplate, Workflow
from .models import FileModel
from jsonForm import util as formUtil
from django.db.models.functions import Coalesce, Cast
from django.db.models import TextField
from userManagement.models import AppMenu
from .util_files import download_file

import logging

logger = logging.getLogger("django")


@api_view(["GET"])  # Specify the HTTP methods this view handles
def get_dictionary_view(request, type, key):
    if type == "select":
        data = get_select_choices(key)
    elif type == "select_ids":
        data = get_select_choices_ids(key)
    elif type == "dictionary":
        data = get_dictionary(key)
    elif type == "map":
        data = get_dictionary_item_map(key)
    else:
        data = []
    dictionary_data = json.dumps(data, cls=CustomJSONEncoder)
    return Response({"data": json.loads(dictionary_data)})


@api_view(["POST"])
def get_my_cases_view_data(request, app_name, type):
    form = AppMenu.get_app_form_by_key(app_name)
    model_class = form.get_model_class()
    fields = model_class.selected_fields_info()

    user_permissions = request.user.permissions.filter(app__key=app_name)
    if type == "todoList":
        cases = (
            model_class.objects.filter(
                Q(
                    form__application__key=app_name,
                    is_submited=True,
                    workflow_instance__is_active=True,
                    task_instances__is_active=True,
                    task_instances__assign_to__in=user_permissions,  # assigned cases
                )
                | Q(
                    form__application__key=app_name,
                    created_by=request.user,
                    is_submited=False,  # draft cases
                )
            )
            .exclude(status="Cancelled")
            .distinct()
            .order_by("-updated_by")
        )
    elif type == "ongoingList":
        cases = (
            model_class.objects.filter(
                (
                    Q(task_instances__assign_to__in=user_permissions)
                    | Q(created_by=request.user)
                )
                & Q(
                    form__application__key=app_name,
                    is_submited=True,
                    workflow_instance__is_active=True,
                )
            )
            .exclude(status="Cancelled")
            .distinct()
            .order_by("-updated_by")
        )
    elif type == "completedList":
        cases = (
            model_class.objects.filter(
                (
                    Q(task_instances__assign_to__in=user_permissions)
                    | Q(created_by=request.user)
                )
                & Q(
                    form__application__key=app_name,
                    is_submited=True,
                    workflow_instance__is_active=False,
                )
            )
            .exclude(status="Cancelled")
            .distinct()
            .order_by("-updated_by")
        )
    else:
        return JsonResponse({"message": "Page not Found"}, status=404)
    field_keys = list(fields.keys())
    response_data = set_datatables_response(request, cases, field_keys, field_keys)
    return Response(response_data)  # JsonResponse(response_data, safe=True)


@api_view(["POST"])
@case_decorator
def get_cases_search_by_form_view_data(
    request, context, app_name, form_code, app_id, form_id, index
):
    form = context["form"]
    case_data_class = get_model_class(
        form.backend_app_label, form.backend_app_section_model
    )
    queryset = case_data_class.objects.filter(
        case__form__application=app_id,
        case__form=form_id,
        case__is_submited=True,
        form_section__index=index,
    ).exclude(case__status="Cancelled")
    fields = case_data_class.selected_fields_info()
    headers = FormTemplate.get_headers_by_code(form_code)
    # to control form template that has more than one section
    search_keys = []
    for h in headers:
        if h["index"] == index:
            fields[f"section_data__{h['key']}"] = h["label"]
            search_keys.append(f"section_data__{h['key']}")
    field_names = list(fields.keys())
    response_data = set_datatables_response(request, queryset, field_names, search_keys)
    # return JsonResponse(response_data, safe=True)
    return Response(response_data)


@api_view(["GET"])
@case_decorator
def get_case_details_file_download_view(
    request, context, app_name, form_code, case_id, file_id
):
    case_instance = context["case_instance"]
    if case_instance is None:
        return redirect("app:app_home", app_name)
    data = case_instance.case_data_case.annotate(
        section_data_str=Cast("section_data", TextField())
    ).filter(section_data_str__icontains=file_id)
    if data is None or data.count() == 0:
        data = case_instance.workflow_instance.task_instance_workflow_instance.filter(
            files__id=file_id
        )
    if data is not None and data.count() > 0:
        file = FileModel.objects.filter(id=file_id)
        if file.count() == 1:
            return download_file(request, file.first())
    # return HttpResponse("The requested file was not found on the server", status=404)
    return Response(
        {
            "message": "The requested file was not found on the server",
            "message_type": "error",
        }
    )


@api_view(["POST"])
@case_decorator
def get_case_details_history_json(request, context, app_name, form_code, case_id):
    form = context["form"]
    case_instance = context["case_instance"]
    data = formUtil.get_case_audit_history(case_instance)
    data_json = json.dumps(data, cls=CustomJSONEncoder)
    records_total = len(data)
    response_data = {
        "recordsTotal": records_total,
        "recordsFiltered": records_total,
        "data": json.loads(data_json),
    }
    return Response(response_data)
    # return JsonResponse(response_data, safe=True)


@api_view(["POST"])
@case_decorator
def get_case_details_documents_json(request, context, app_name, form_code, case_id):
    form = context["form"]
    case_instance = context["case_instance"]
    fields = FileModel.selected_fields_info()

    if case_instance.workflow_instance is not None:
        task_ids = case_instance.workflow_instance.task_instance_workflow_instance.all().values(
            "id"
        )
        TaskInstance = case_instance.get_task_instances_model()
        related_name = "%s_%s_files" % (
            TaskInstance._meta.app_label.lower(),
            TaskInstance._meta.model_name,
        )
        fields["%s__task__name" % related_name] = "Task Name"
        data = (
            FileModel.objects.filter(Q(**{f"{related_name}__in": task_ids}))
            .order_by("-created_at")
            .values(*fields)
        )
        data_json = json.dumps(list(data), cls=CustomJSONEncoder)
        records_total = len(data)
    else:
        data_json = "{}"
        records_total = 0
    response_data = {
        "recordsTotal": records_total,
        "recordsFiltered": records_total,
        "data": json.loads(data_json),
    }
    return Response(response_data)
    # return JsonResponse(response_data, safe=True)
