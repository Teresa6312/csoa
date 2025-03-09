from django.http import JsonResponse
from base.models import ModelDictionaryConfigModel
from userManagement.models import AppMenu
from .util_model import get_dictionary
from .util import get_model_class, get_object_or_redirect
from django.shortcuts import redirect
from django.contrib import messages
from jsonForm.models import FormTemplate
from functools import wraps
from django.http import HttpResponseRedirect
from . import constants

import inspect
import logging

logger = logging.getLogger("django")


def request_decorator(func):
    """
    Decorator to handle POST requests and log function calls.

    Args:
        func (function): The function to be decorated.

    Returns:
        function: The wrapped function.

    Database Operations:
        None
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        func_name = func.__name__
        func_module = inspect.getmodule(func)
        logger.debug(f"{func_module.__name__}.{func_name}")
        if request.method == "POST":
            result = func(request, *args, **kwargs)
            return result
        else:
            return JsonResponse(
                {"message_type": "error", "message": "Invalid request method"},
                status=400,
            )
    return wrapper


def case_decorator(func):
    """
    Decorator to set up context for case-related views and handle permissions.

    Args:
        func (function): The function to be decorated.

    Returns:
        function: The wrapped function.

    Database Operations:
        - Read: AppMenu, FormTemplate, case_instance (various models)
        - Conditional: Redirect based on permissions and context setup

    Tables Used:
        - AppMenu
        - FormTemplate
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        func_name = func.__name__
        func_module = inspect.getmodule(func)
        logger.debug(f"{func_module.__name__}.{func_name}")

        context = {}
        for key in kwargs.keys():
            if kwargs.get(key, None) is not None:
                context[key] = kwargs.get(key)

        app_name = kwargs.get("app_name", "")
        message, context = __setup_app(request, context, app_name)
        form_code = kwargs.get("form_code", None)
        case_id = kwargs.get("case_id", None)
        if message is None:
            message, context = __setup_case_form(request, context, form_code, case_id)
            if message is None:
                case_instance = context.get("case_instance", None)
                mini_app = context.get("mini_app", None)
                if mini_app is not None and case_instance is not None:
                    if not __verify_case_permission(request, mini_app, case_instance):
                        message = "Permission Denied"
            home_page = True
        else:
            home_page = False
        if message is not None:
            referer = request.META.get("HTTP_REFERER")  # Previous URL (if exists)
            if message is not None:
                if request.path.startswith("/api"):
                    return JsonResponse(
                        {"message_type": "error", "message": message, "data": []},
                        status=404,
                    )
                messages.warning(request, message)
                if referer:
                    return HttpResponseRedirect(referer)
                else:
                    if home_page:
                        redirect("app:home")
                    else:
                        return redirect("app:app_home", app_name)
        result = func(request, context, *args, **kwargs)
        return result

    return wrapper


def model_decorator(func):
    """
    Decorator to set up context for model-related views.

    Args:
        func (function): The function to be decorated.

    Returns:
        function: The wrapped function.

    Database Operations:
        - Read: AppMenu, ModelDictionaryConfigModel, model_instance (various models)
        - Conditional: Redirect based on context setup

    Tables Used:
        - AppMenu
        - ModelDictionaryConfigModel
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        func_name = func.__name__
        func_module = inspect.getmodule(func)
        logger.debug(f"{func_module.__name__}.{func_name}")

        context = {}
        for key in kwargs.keys():
            if kwargs.get(key, None) is not None:
                context[key] = kwargs.get(key)

        app_name = kwargs.get("app_name", "")
        message, context = __setup_app(request, context, app_name)
        model = kwargs.get("model", None)
        id = kwargs.get("id", None)
        if message is None:
            message, context = __setup_model(request, context, model, id)
            home_page = True
        else:
            home_page = False
        if message is not None:
            referer = request.META.get("HTTP_REFERER")  # Previous URL (if exists)
            if message is not None:
                if request.path.startswith("/api"):
                    return JsonResponse(
                        {"message_type": "error", "message": message, "data": []},
                        status=404,
                    )
                messages.warning(request, message)
                if referer:
                    return HttpResponseRedirect(referer)
                else:
                    if home_page:
                        redirect("app:home")
                    else:
                        return redirect("app:app_home", app_name)
        result = func(request, context, *args, **kwargs)
        return result

    return wrapper


def model_unit_decorator(func):
    """
    Decorator to set up context for unit-related views.

    Args:
        func (function): The function to be decorated.

    Returns:
        function: The wrapped function.

    Database Operations:
        - Read: AppMenu, ModelDictionaryConfigModel, department, team
        - Conditional: Redirect based on context setup

    Tables Used:
        - AppMenu
        - ModelDictionaryConfigModel
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        func_name = func.__name__
        func_module = inspect.getmodule(func)
        logger.debug(f"{func_module.__name__}.{func_name}")

        context = {}
        for key in kwargs.keys():
            if kwargs.get(key, None) is not None:
                context[key] = kwargs.get(key)

        app_name = kwargs.get("app_name", "")
        message, context = __setup_app(request, context, app_name)
        model = kwargs.get("model", None)
        department = kwargs.get("department", "")
        team = kwargs.get("team", "")
        if message is None:
            message, context = __setup_model(request, context, model)
            home_page = True
            if message is None:
                message, context = __setup_unit(request, context, department, team)
        else:
            home_page = False

        if message is not None:
            referer = request.META.get("HTTP_REFERER")  # Previous URL (if exists)
            if message is not None:
                if request.path.startswith("/api"):
                    return JsonResponse(
                        {"message_type": "error", "message": message, "data": []},
                        status=404,
                    )
                messages.warning(request, message)
                if referer:
                    return HttpResponseRedirect(referer)
                else:
                    if home_page:
                        redirect("app:home")
                    else:
                        return redirect("app:app_home", app_name)
        result = func(request, context, *args, **kwargs)
        return result

    return wrapper


def __setup_app(request, context, app_name):
    """
    Set up the application context.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): The context dictionary to be modified.
        app_name (str): The application name.

    Returns:
        tuple: A tuple containing a message (str) and the modified context (dict).

    Database Operations:
        - Read: AppMenu

    Tables Used:
        - AppMenu
    """
    message = None
    mini_app = AppMenu.get_app_instance_by_key(app_name)
    if mini_app is None:
        message = "Application is not found"
    else:
        context["mini_app"] = mini_app
    return message, context


# cases pages may not have form
def __setup_case_form(request, context, form_code, case_id):
    """
    Set up the case form context.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): The context dictionary to be modified.
        form_code (str): The form code.
        case_id (int): The case ID.

    Returns:
        tuple: A tuple containing a message (str) and the modified context (dict).

    Database Operations:
        - Read: FormTemplate, case_instance (various models)

    Tables Used:
        - FormTemplate
    """
    message = None
    if form_code is not None:
        form = FormTemplate.get_instance_by_code(form_code)
        mini_app = context["mini_app"]
        if form is None or mini_app is None or (form.application != mini_app):
            message = f"Form Template ({context['app_name']}-{form_code}) is not found"
        else:
            context["form"] = form
        if form is not None and case_id is not None:
            model_class = get_model_class(
                form.backend_app_label, form.backend_app_model
            )
            case_instance = get_object_or_redirect(model_class, pk=case_id)
            context["case_instance"] = case_instance
    return message, context


def __verify_case_permission(request, mini_app, case_instance):
    """
    Verify case permissions for the user.

    Args:
        request (HttpRequest): The HTTP request object.
        mini_app (AppMenu): The mini application instance.
        case_instance (Model): The case instance.

    Returns:
        bool: True if the user has permission, False otherwise.

    Database Operations:
        - Read: case_instance (various models)

    Tables Used:
        - Various models depending on the case instance
    """
    user_info = (
        request.session["user_info"]
        if "user_info" in request.session
        else request.user.get_user_info()
    )
    if user_info.get("is_superuser", False):
        return True
    if case_instance.status == constants.CASE_CANCELLED:
        return False
    if case_instance.created_by == request.user:
        return True

    role_unit = request.current_page_menu.get("role_unit", [])
    role_unit_ids = [r.get("permission_role__id") for r in role_unit]

    if (
        case_instance.status != constants.CASE_COMPLETED
        and case_instance.task_instance is not None
        and len(role_unit_ids) > 0
        and case_instance.task_instances.filter(
            assign_to__id__in=role_unit_ids
        ).exists()
    ):
        return True

    role_company_ids = [r.get("permission_role__company__id") for r in role_unit]
    role_department_ids = [r.get("permission_role__department__id") for r in role_unit]
    role_team_ids = [r.get("permission_role__team__id") for r in role_unit]
    if len(role_unit) == 0:
        return False
    elif (
        mini_app.control_type == "company"
        and case_instance.case_department.company.id in role_company_ids
    ):
        return True
    elif mini_app.control_type == "department":
        if case_instance.case_department.id in role_department_ids:
            return True
        else:
            parent_id_list = [
                r.get("permission_role__company__id")
                for r in role_unit
                if r.get("permission_role__department__id") is None
                and r.get("permission_role__company__id") is not None
            ]
            if case_instance.department.company.id in parent_id_list:
                return True
            else:
                return False
    elif mini_app.control_type == "team":
        if case_instance.case_team.id in role_team_ids:
            return True
        else:
            parent_id_list = [
                r.get("permission_role__department__id")
                for r in role_unit
                if r.get("permission_role__team__id") is None
                and r.get("permission_role__department__id") is not None
            ]
            grandparent_id_list = [
                r.get("permission_role__company__id")
                for r in role_unit
                if r.get("permission_role__team__id") is None
                and r.get("permission_role__department__id") is None
                and r.get("permission_role__company__id") is not None
            ]
            if case_instance.case_team.department.id in parent_id_list:
                return True
            elif case_instance.case_team.department.company.id in grandparent_id_list:
                return True
            else:
                return False
    elif mini_app.control_type == "app":  # app level permission
        return True
    return False


# model pages must has model
def __setup_model(request, context, model, id):
    """
    Set up the model context.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): The context dictionary to be modified.
        model (str): The model name.
        id (int): The model instance ID.

    Returns:
        tuple: A tuple containing a message (str) and the modified context (dict).

    Database Operations:
        - Read: ModelDictionaryConfigModel, model_instance (various models)

    Tables Used:
        - ModelDictionaryConfigModel
    """
    model_class = None
    model_details = None
    message = None
    if model is not None:
        model_details = ModelDictionaryConfigModel.get_details(model)
        if model_details is not None:
            model_class = get_model_class(
                model_details.get("backend_app_label", ""),
                model_details.get("backend_app_model", ""),
            )
            if model_class is not None and id is not None:
                model_instance = get_object_or_redirect(model_class, pk=id)
                context["model_instance"] = model_instance
                context["model_details"] = model_details

    # model pages must has model
    if model_class is None and message is None:
        message = "Page is not found"
    elif message is None:
        context["model_details"] = model_details
        context["model_class"] = model_class
    return message, context


# Unit Control pages must have department
def __setup_unit(request, context, department, team):
    """
    Set up the unit context.

    Args:
        request (HttpRequest): The HTTP request object.
        context (dict): The context dictionary to be modified.
        department (str): The department name.
        team (str): The team name.

    Returns:
        tuple: A tuple containing a message (str) and the modified context (dict).

    Database Operations:
        - Read: department, team (from dictionaries)

    Tables Used:
        - None (uses dictionaries)
    """
    message = None
    dept_list = get_dictionary("department_list_active")
    dept = next((m for m in dept_list if m.get("short_name", None) == department), None)
    if dept is None:
        message = "Department is not found"
    if team != "" and team.lower() != "all":
        team_list = get_dictionary("team_list_active")
        team = next((m for m in team_list if m.get("short_name", None) == team), None)
        if team is None:
            message = "Team is not found"
    else:
        # team may use for filter for all Unit Control pages, so need to reset
        context["team"] = None
    return message, context
