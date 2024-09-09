from django.http import JsonResponse
from django.core.exceptions import ValidationError
from userManagement.models import AppMenu
from django.shortcuts import  redirect
from django.contrib import messages
from jsonForm.models import FormTemplate
from functools import wraps
import inspect
import logging
logger = logging.getLogger('django')

def request_decorator(func):
    def wrapper(request, *args, **kwargs):
        try:
            if request.method == 'POST':
                result = func(request, *args, **kwargs)
                return result
            else:
                return JsonResponse({'message_type': 'error', 'message': 'Invalid request method'}, status=400)
        except ValidationError as e:
            field_errors = [{'name': field, 'status': ', '.join(errors)} for field, errors in e.message_dict.items()]
            error_response = {'message_type': 'error', 'message': field_errors}
            return JsonResponse(error_response, status=400)
        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'message_type': 'error', 'message': 'System Error'}, status=500)
    return wrapper


def case_decorator(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        func_name = func.__name__
        func_module = inspect.getmodule(func)
        logger.debug(f'{func_module.__name__}.{func_name}')
        context = {}
        app_name  = kwargs.get('app_name', '')
        form_code  = kwargs.get('form_code', None)
        case_id  = kwargs.get('case_id', None)
        
        mini_app = AppMenu.objects.filter(key=app_name, menu_level=0)
        if mini_app is None or mini_app.count() != 1:
            messages.warning(request, "Application is not found")
            return redirect('app:home')
        context['app_name'] = app_name
        context['mini_app'] = mini_app.first()
        menu = next((m for m in request.menu if m.get('key', '') == app_name), None)
        context['menu'] = menu
        
        if form_code is not None:
            form = FormTemplate.objects.get(code=form_code, application__key=app_name)
            if form is None:
                messages.warning(request, "Form Template is not found")
                return redirect('app:app_home', app_name)
            context['form'] = form
            context['form_code'] = form_code
            if case_id is not None:
                model_class = form.get_model_class()
                case_instance = model_class.objects.get(pk=case_id)
                context['case_instance'] = case_instance
                context['case_id'] = case_id
                if case_instance is None:
                    messages.warning(request, "Case is not found")
                    return redirect('app:app_home', app_name)
        # Call the original function with modified arguments
        result = func(request,context, *args, **kwargs)
        return result
    return wrapper

def model_decorator(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        context = {}
        app_name  = kwargs.get('app_name', '')
        mini_app = AppMenu.objects.filter(key=app_name, menu_level=0)
        if mini_app is None or mini_app.count() != 1:
            messages.warning(request, "Application is not found")
            return redirect('app:home')
        context['mini_app'] = mini_app.first()
        context['app_name'] = app_name
        menu = next((m for m in request.menu if m.get('key', '') == app_name), None)
        context['menu'] = menu
        model  = kwargs.get('model', None)
        if model is not None:
            context['model'] = model
        id  = kwargs.get('id', None)
        if id is not None:
            context['id'] = id
        sub_table_model  = kwargs.get('sub_table_model', None)
        if sub_table_model is not None:
            context['sub_table_model'] = sub_table_model
        sub_table_field  = kwargs.get('sub_table_field', None)
        if sub_table_field is not None:
            context['sub_table_field'] = sub_table_field
        result = func(request, context, *args, **kwargs)
        return result
    return wrapper