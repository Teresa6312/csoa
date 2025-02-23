import json
from jsonschema import validate, ValidationError
import uuid
from datetime import date, datetime
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.files import File
import mimetypes
from django.contrib import messages
from django.db.models import Func
from decimal import Decimal
from django.apps import apps
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.utils.functional import Promise  # Import the Promise class for from django.utils.translation import gettext_lazy as _ values
import re
import logging
from django.db.models import Q
from django.shortcuts import redirect
from django.http import JsonResponse
import mimetypes
from django.http import HttpResponseRedirect
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from functools import reduce
from django.core.paginator import Paginator
from django.http import Http404
from .cache import global_cache_decorator
from django.conf import settings
# from django.core.serializers.json import DjangoJSONEncoder as CustomJSONEncoder # for datetime serialization

logger = logging.getLogger('django')

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime)):
            return obj.strftime('%m/%d/%Y %H:%M:%S')
        if isinstance(obj, (date)):
            return obj.strftime('%m/%d/%Y')
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, bool):  # Check for standard booleans This one doesn't work for some reason
            return 'Yes' if obj else 'No'
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, Promise):
            return str(obj)
        if obj is None:
            return ''
        return super().default(obj)
    
def save_form_data_to_json(form):
    if form.is_valid():
        data = form.cleaned_data
        json_data = json.dumps(data, cls=CustomJSONEncoder)
        # Save `json_data` to your database or another storage system
        return json_data
    else:
        return None
    
# Convert 'MM/DD/YYYY' to 'YYYY-MM-DD'
def convert_date_format(date_str):
    if date_str:
        # Parse the date from 'MM/DD/YYYY' format
        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
        # Convert to 'YYYY-MM-DD' format
        return date_obj.strftime('%Y-%m-%d')
    return None

def to_camel_case(string):
    if string is None or not isinstance(string, str):
        return ''
    words = string.split()
    # If there's only one word, just return it in lowercase
    if len(words) == 1:
        return words[0].lower()
    # Convert the first word to lowercase, and capitalize the subsequent words
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

def send_email(request, subject, to_email_address, content, attachments=[]):
    try:
        email = EmailMessage(subject, content, settings.DEFAULT_FROM_EMAIL, to_email_address)
        for a in attachments:
            if a.get('path', None) is not None and a.get('name', None) is not None:
                path = a.get('path')
                file_name = a.get('name')
                # For large attachments, consider using streaming to avoid loading the entire file into memory:
                with open(f'{path}/{file_name}', 'rb') as f:
                    mime_type, _ = mimetypes.guess_type(file_name)
                    file_obj = File(f)
                    # application/octet-stream: This is a generic MIME type that is used as a fallback when the actual MIME type cannot be determined. It's safe to use for binary files when the specific MIME type is unknown.
                    email.attach(file_name, file_obj.read(), mime_type or 'application/octet-stream')
            else:
                messages.error(request, ('No file found!'))
        email.send()
    except Exception as e:
        logger.error(e)
        messages.error(request, ('System error!'))

# Create a custom function to cast the UUID to a string. Different database may has a little different
class UUIDToString(Func):
    function = 'CAST'
    template = "%(function)s(%(expressions)s AS TEXT)"  # Use TEXT for SQLite

    def __init__(self, expression, **extra):
        super().__init__(expression, **extra)

def get_related_names_for_model(model_class):
    fk_fields = []
    related_name_fields = []
    # Iterate through all models in the project
    for model in apps.get_models():
        # Iterate over all fields in the model
        for field in model._meta.get_fields():
            # Check if the field is a relation (ForeignKey, ManyToManyField, OneToOneField) 
            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                # Check if the field's related model is the given model class
                if field.remote_field.model == model_class:
                    related_name = field.remote_field.related_name
                    if related_name is not None:
                        if related_name !='+' and isinstance(field, (ForeignKey, ManyToManyField)):
                            related_name_fields.append(
                                {
                                "model": model._meta.label,
                                "field_name": field.name,
                                "related_name": related_name,
                                "label": field.verbose_name
                                }
                            )
                        elif related_name !='+' and isinstance(field, OneToOneField):
                            fk_fields.append(
                                {
                                "model": model._meta.label,
                                "field_name": field.name,
                                "related_name": related_name,
                                "label": field.verbose_name
                                }
                            )
                    else:
                        if isinstance(field, (ForeignKey, ManyToManyField)):
                            related_name_fields.append(
                                {
                                "model": model._meta.label,
                                "field_name": field.name,
                                "related_name": f"{model._meta.model_name}_set",
                                "label": field.verbose_name
                                }
                            )
                        else:
                            fk_fields.append(
                                {
                                "model": model._meta.label,
                                "field_name": field.name,
                                "related_name": f"{model._meta.model_name}_set",
                                "label": field.verbose_name
                                }
                                )
    return fk_fields, related_name_fields

def get_related_model_class(model_class, related_name):
    # Iterate over all fields in the model
    for field in model_class._meta.get_fields():
        # Check if the field has a related name that matches the given related_name
        if hasattr(field, 'related_name') and field.related_name == related_name:
            # Return the related model class
            return field.related_model
    # Return None if no matching related_name is found
    return None

def get_related_model_related_names(model_class, relate_model_class):
    # Iterate over all fields in the model
    related_names = []
    for field in model_class._meta.get_fields():
        # Check if the field has a related name that matches the given related_name
        if field.related_model == relate_model_class:
            # Return the related model class
            if hasattr(field, 'related_name'):
                related_names.append(field.related_name)
            elif hasattr(field, 'related_query_name'):
                related_names.append(field.related_query_name)
    # Return None if no matching related_name is found
    return related_names

#  in used for datatables.js search
def extract_datatables_search_panes_parameters(post_data):
    regex = re.compile(r'searchPanes\[(.*?)\]\[(.*?)\]')
    extracted_params = {}
    for key, value in post_data.items():
        match = regex.search(key)
        if match:
            field = match.group(1)
            index = int(match.group(2))
            if field not in extracted_params:
                extracted_params[field] = {}
            if index not in extracted_params[field]:
                extracted_params[field][index] = []
            extracted_params[field][index].append(value)
    return extracted_params

#  in used for datatables.js search
def extract_datatables_search_builder_parameters(post_data, search_builder_logic):
    field_name = post_data.get('searchBuilder[criteria][0][origData]', None)
    i = 0 
    q_objects = Q()  # Initialize an empty Q object
    while field_name is not None:
        operator = post_data.get(f'searchBuilder[criteria][{i}][condition]', None)
        value = post_data.get(f'searchBuilder[criteria][{i}][value1]', '')
        value2 = post_data.get(f'searchBuilder[criteria][{i}][value2]', '')
        data_type = post_data.get(f'searchBuilder[criteria][{i}][type]', '')
        logger.debug(f'field_name:{field_name};condition:{operator};value1:{value};value2:{value2};data_type:{data_type}')
        # Dynamically build the query lookup
        if operator == '!null':
            q_objects &= Q(**{f'{field_name}__isnull': False})
        elif operator == 'null':
            q_objects &= Q(**{f'{field_name}__isnull': True})
        elif operator == '!=':
            q_objects &= ~Q(**{f'{field_name}': value})
        elif operator == '=':
            q_objects &= Q(**{f'{field_name}': value})
        elif operator == '!contains' and data_type in ['string']:
            q_objects &= ~Q(**{f'{field_name}__icontains': value})
        elif operator == 'contains' and data_type in ['string']:
            q_objects &= Q(**{f'{field_name}__icontains': value})
        elif operator == '!starts' and data_type in ['string']:
            q_objects &= ~Q(**{f'{field_name}__startswith': value})
        elif operator == 'starts' and data_type in ['string']:
            q_objects &= Q(**{f'{field_name}__startswith': value})
        elif operator == '!ends' and data_type in ['string']:
            q_objects &= ~Q(**{f'{field_name}__endswith': value})
        elif operator == 'ends' and data_type in ['string']:
            q_objects &= Q(**{f'{field_name}__endswith': value})
        elif operator == '>=' and data_type in ['num']:
            q_objects &= Q(**{f'{field_name}__gte': value})
        elif operator == '>' and data_type in ['num']:
            q_objects &= Q(**{f'{field_name}__gt': value})
        elif operator == '<' and data_type in ['num']:
            q_objects &= Q(**{f'{field_name}__lt': value})
        elif operator == '<=' and data_type in ['num']:
            q_objects &= Q(**{f'{field_name}__lte': value})
        elif operator == '!between' and data_type in ['num']:
            q_objects &= ~Q(**{f'{field_name}__gte': value}) & Q(**{f'{field_name}__lte': value2})
        elif operator == 'between' and data_type in ['num']:
            q_objects &= Q(**{f'{field_name}__gte': value}) & Q(**{f'{field_name}__lte': value2})

        i = i + 1
        field_name = post_data.get(f'searchBuilder[criteria][{i}][origData]', None)

    return q_objects

def set_datatables_response(request, queryset, fields: list,search_keys: list):
    draw = int(request.POST.get('draw', 1))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))

    search_value = request.POST.get('search[value]', None)
    search_builder_logic = request.POST.get('searchBuilder[logic]', None)

    # 处理过滤
    if search_value:
        conditions = reduce(lambda x, y: x | Q(**{f'{y}__icontains': search_value}), search_keys, Q())
        queryset = queryset.filter(conditions)
    if search_builder_logic is not None:
        q_objects = extract_datatables_search_builder_parameters(request.POST, search_builder_logic)
        queryset = queryset.filter(q_objects)
    
    # 处理排序
    order_column = request.POST.get('order[0][column]', None)
    order_by = None
    if order_column is not None:
        order_column_name = fields[int(order_column)]
        order_direction = request.POST.get('order[0][dir]', 'asc')
        order_by = order_column_name if order_direction == 'asc' else f"-{order_column_name}"
        queryset = queryset.order_by(order_by)

    logger.debug(queryset.query)
    
    # 处理分页
    paginator = Paginator(queryset.values(*fields), request.POST.get('length', 10))
    page_number = start // length + 1
    page = paginator.get_page(page_number)

    data = json.dumps(list(page), cls=CustomJSONEncoder)

    return {
        "recordsTotal": queryset.count(),
        "recordsFiltered": paginator.count,
        'data': json.loads(data),
    }



def no_permission_redirect(request, path=None, message=None):
    if message is None and request.path.startswith('/api'):
        return JsonResponse({"message_type": "error", "message": "No Permission", "data": []}, status=403)
    elif message is None:
        message = f"You do not have permission to view this page({request.path})."
    messages.error(request, f"{message}")
    if path is not None:
        return redirect(path)
    referer = request.META.get('HTTP_REFERER')  # Previous URL (if exists)
    if referer:
        return HttpResponseRedirect(referer)
    else:
        return redirect('app:home')
    
def get_model_class(backend_app_label, backend_app_model):
    if backend_app_label and backend_app_model:
        model_class = apps.get_model(backend_app_label, backend_app_model)
        return model_class
    else:
        raise ValueError(f"backend_app_label and backend_app_model is missing in Form")
    
def get_object_or_redirect(model, *args, message="Data object not found.", **kwargs):
    try:
        return get_object_or_404(model, *args, **kwargs)
    except Http404 as e:
        logger.error(e)
        raise ValueError(message)
    except Exception as e:
        logger.error(e)
        raise ValueError("System Error")

def method_model_to_dict(model_object):
    # Using model_to_dict and json.dumps
    workflow_dict = model_to_dict(model_object)
    return json.dumps(workflow_dict)

def get_menu_key_in_list(sub_menu: list, parent_key=None):
    result = []
    for menu in sub_menu:
        key = f"{parent_key}__{menu.get('key')}"  if parent_key is not None else menu.get('key')
        result.append(key)
        new_sub_menu = menu.get('sub_menu', [])
        if len(menu.get('sub_menu', []))>0:
            result += get_menu_key_in_list(new_sub_menu, key)
    return result

import json
from django.conf import settings

# def load_form_config():
#     config_path = settings.BASE_DIR / 'reference' / 'form_template.json'
#     with open(config_path, 'r', encoding='utf-8') as f:
#         return json.load(f)

def validate_form_data(form_data, config):
    errors = {}
    
    # 字段级验证
    for field_id, field_config in config['fields'].items():
        value = form_data.get(field_id)
        
        # 必填验证
        if field_config.get('required') and not value:
            errors[field_id] = "此字段为必填项"
            
        # 类型验证
        if field_config['type'] == 'number' and not value.isdigit():
            errors[field_id] = "必须为有效数字"
            
    # 跨字段验证
    for rule in config.get('validation_rules', {}).values():
        if rule['type'] == 'range':
            source_value = form_data.get(rule['depends_on'])
            target_value = form_data.get(rule['target'])
            min_val = rule['rules'][source_value]['min']
            max_val = rule['rules'][source_value]['max']
            
            if not (min_val <= float(target_value) <= max_val):
                errors[rule['target']] = f"有效范围：{min_val}-{max_val}"
    
    return errors


def load_schema_from_file(schema_file_path):
    """Loads a JSON schema from a file.

    Args:
        schema_file_path: The path to the JSON schema file.

    Returns:
        The JSON schema as a Python dictionary, or None if an error occurs.
    """
    try:
        path = "%s%s" % (settings.BASE_DIR, schema_file_path)  # Add encoding for potential issues
        logger.debug(f"loading schema: {path}")
        with open(path, 'r', encoding='utf-8') as f:  # Add encoding for potential issues
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"Error loading schema: {e}")
        logger.error(f"Error loading schema: {e}")
        return None

def validate_json_with_schema(json_data, schema):
    """Validates a JSON object against a JSON schema.

    Args:
        json_data: The JSON object to validate (as a Python dictionary).
        schema: The JSON schema (as a Python dictionary).

    Returns:
        None if the JSON is valid.
        A string containing the validation error message if invalid.
    """
    try:
        validate(instance=json_data, schema=schema)
        return ''  # JSON is valid
    except ValidationError as e:
        return e.message  # Return the validation error message

@global_cache_decorator(cache_key="normalized_url", timeout = settings.CACHE_TIMEOUT_L3)
def normalized_url(path):
    path = path.lower() if path is not None else ''
    new_path = ''
    if path.startswith('/api'):
        path = path.replace('/api', '')
    if path.endswith('-filter'):
        path_split = path.split("/")
        for p in path_split:
            if not p.endswith('-filter') and p != '':
                new_path = f'{new_path}/{p}'

    if new_path == '':
        new_path = path
    return new_path