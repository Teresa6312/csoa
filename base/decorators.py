from django.http import JsonResponse
from django.core.exceptions import ValidationError
from modelBase.models import ModelDictionaryConfigModel
from userManagement.models import AppMenu
from .util_model import get_dictionary
from .util import get_model_class, get_object_or_redirect
from django.shortcuts import redirect
from django.contrib import messages
from jsonForm.models import FormTemplate
from functools import wraps
from django.http import HttpResponseRedirect

import inspect
import logging

logger = logging.getLogger("django")


def request_decorator(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        func_name = func.__name__
        func_module = inspect.getmodule(func)
        logger.debug(f"{func_module.__name__}.{func_name}")
        try:
            if request.method == "POST":
                result = func(request, *args, **kwargs)
                return result
            else:
                return JsonResponse(
                    {"message_type": "error", "message": "Invalid request method"},
                    status=400,
                )
        except ValidationError as e:
            field_errors = [
                {"name": field, "status": ", ".join(errors)}
                for field, errors in e.message_dict.items()
            ]
            return JsonResponse(
                {"message_type": "error", "message": field_errors}, status=400
            )
        except Exception as e:
            logger.error(str(e))
            return JsonResponse(
                {"message_type": "error", "message": "System Error"}, status=500
            )

    return wrapper


def case_decorator(func):
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
        # Call the original function with modified arguments
        result = func(request, context, *args, **kwargs)
        return result

    return wrapper


def model_decorator(func):
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
    message = None
    mini_app = AppMenu.get_app_instance_by_key(app_name)
    if mini_app is None:
        message = "Application is not found"
    else:
        context["mini_app"] = mini_app
    return message, context


# cases pages may not have form
def __setup_case_form(request, context, form_code, case_id):
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
            # if case_instance is None:
            #     message = f"Case ({case_id}) is not found"
    return message, context


# model pages must has model
def __setup_model(request, context, model, id):
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
