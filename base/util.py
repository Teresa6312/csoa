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
from django.utils.functional import Promise
import re
import logging
from django.db.models import Q
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from functools import reduce
from django.core.paginator import Paginator
from .cache import global_cache_decorator
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver
import re

logger = logging.getLogger("django")

class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle specific data types.

    Args:
        obj (any): The object to encode.

    Returns:
        str: The JSON-encoded string.

    Database Operations:
        None
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%m/%d/%Y %H:%M:%S")
        if isinstance(obj, date):
            return obj.strftime("%m/%d/%Y")
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, bool):
            return "Yes" if obj else "No"
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, Promise):
            return str(obj)
        if obj is None:
            return ""
        return super().default(obj)

def save_form_data_to_json(form):
    """
    Save form data to JSON format.

    Args:
        form (Form): The form instance.

    Returns:
        str: JSON string of form data if valid, otherwise None.

    Database Operations:
        None
    """
    if form.is_valid():
        data = form.cleaned_data
        json_data = json.dumps(data, cls=CustomJSONEncoder)
        # Save `json_data` to your database or another storage system
        return json_data
    else:
        return None


# Convert 'MM/DD/YYYY' to 'YYYY-MM-DD'
def convert_date_format(date_str):
    """
    Convert date format from 'MM/DD/YYYY' to 'YYYY-MM-DD'.

    Args:
        date_str (str): Date string in 'MM/DD/YYYY' format.

    Returns:
        str: Date string in 'YYYY-MM-DD' format.

    Database Operations:
        None
    """
    if date_str:
        # Parse the date from 'MM/DD/YYYY' format
        date_obj = datetime.strptime(date_str, "%m/%d/%Y")
        # Convert to 'YYYY-MM-DD' format
        return date_obj.strftime("%Y-%m-%d")
    return None


def to_camel_case(string):
    """
    Convert a string to camel case.

    Args:
        string (str): The input string.

    Returns:
        str: The camel case string.

    Database Operations:
        None
    """
    if string is None or not isinstance(string, str):
        return ""
    words = string.split()
    # If there's only one word, just return it in lowercase
    if len(words) == 1:
        return words[0].lower()
    # Convert the first word to lowercase, and capitalize the subsequent words
    return words[0].lower() + "".join(word.capitalize() for word in words[1:])

def send_email(request, subject, to_email_address, content, attachments=[]):
    """
    Send an email with optional attachments.

    Args:
        request (HttpRequest): The HTTP request object.
        subject (str): The email subject.
        to_email_address (list): List of recipient email addresses.
        content (str): The email content.
        attachments (list): List of attachments.

    Returns:
        None

    Database Operations:
        None
    """
    try:
        email = EmailMessage(
            subject, content, settings.DEFAULT_FROM_EMAIL, to_email_address
        )
        for a in attachments:
            if a.get("path", None) is not None and a.get("name", None) is not None:
                path = a.get("path")
                file_name = a.get("name")
                # For large attachments, consider using streaming to avoid loading the entire file into memory:
                with open(f"{path}/{file_name}", "rb") as f:
                    mime_type, _ = mimetypes.guess_type(file_name)
                    file_obj = File(f)
                    # application/octet-stream: This is a generic MIME type that is used as a fallback when the actual MIME type cannot be determined. It's safe to use for binary files when the specific MIME type is unknown.
                    email.attach(
                        file_name,
                        file_obj.read(),
                        mime_type or "application/octet-stream",
                    )
            else:
                messages.error(request, ("No file found!"))
        email.send()
    except Exception as e:
        rqa = f"Error sending email: {e}"
        logger.exception(e)
        raise Exception(rqa)

class UUIDToString(Func):
    """
    Custom function to cast UUID to string.

    Args:
        expression (Expression): The expression to cast.

    Returns:
        str: The casted string.

    Database Operations:
        None
    """
    function = "CAST"
    template = "%(function)s(%(expressions)s AS TEXT)"

    def __init__(self, expression, **extra):
        super().__init__(expression, **extra)

def get_related_names_for_model(model_class):
    """
    Get related names for a model class.

    Args:
        model_class (Model): The model class.

    Returns:
        tuple: A tuple containing lists of foreign key fields and related name fields.

    Database Operations:
        Read: Various models
    """
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
                        if related_name != "+" and isinstance(
                            field, (ForeignKey, ManyToManyField)
                        ):
                            related_name_fields.append(
                                {
                                    "model": model._meta.label,
                                    "field_name": field.name,
                                    "related_name": related_name,
                                    "label": field.verbose_name,
                                }
                            )
                        elif related_name != "+" and isinstance(field, OneToOneField):
                            fk_fields.append(
                                {
                                    "model": model._meta.label,
                                    "field_name": field.name,
                                    "related_name": related_name,
                                    "label": field.verbose_name,
                                }
                            )
                    else:
                        if isinstance(field, (ForeignKey, ManyToManyField)):
                            related_name_fields.append(
                                {
                                    "model": model._meta.label,
                                    "field_name": field.name,
                                    "related_name": f"{model._meta.model_name}_set",
                                    "label": field.verbose_name,
                                }
                            )
                        else:
                            fk_fields.append(
                                {
                                    "model": model._meta.label,
                                    "field_name": field.name,
                                    "related_name": f"{model._meta.model_name}_set",
                                    "label": field.verbose_name,
                                }
                            )
    return fk_fields, related_name_fields

def get_related_model_class(model_class, related_name):
    """
    Get the related model class for a given related name.

    Args:
        model_class (Model): The model class.
        related_name (str): The related name.

    Returns:
        Model: The related model class.

    Database Operations:
        None
    """
    for field in model_class._meta.get_fields():
        # Check if the field has a related name that matches the given related_name
        if hasattr(field, "related_name") and field.related_name == related_name:
            # Return the related model class
            return field.related_model
    # Return None if no matching related_name is found
    return None

def get_related_model_related_names(model_class, relate_model_class):
    """
    Get related names for a related model class.

    Args:
        model_class (Model): The model class.
        relate_model_class (Model): The related model class.

    Returns:
        list: List of related names.

    Database Operations:
        None
    """
    related_names = []
    for field in model_class._meta.get_fields():
        # Check if the field has a related name that matches the given related_name
        if field.related_model == relate_model_class:
            # Return the related model class
            if hasattr(field, "related_name"):
                related_names.append(field.related_name)
            elif hasattr(field, "related_query_name"):
                related_names.append(field.related_query_name)
    # Return None if no matching related_name is found
    return related_names

def extract_datatables_search_panes_parameters(post_data):
    """
    Extract search panes parameters from DataTables post data.

    Args:
        post_data (QueryDict): The post data.

    Returns:
        dict: Extracted parameters.

    Database Operations:
        None
    """
    regex = re.compile(r"searchPanes\[(.*?)\]\[(.*?)\]")
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

def extract_datatables_search_builder_parameters(post_data, search_builder_logic):
    """
    Extract search builder parameters from DataTables post data.

    Args:
        post_data (QueryDict): The post data.
        search_builder_logic (str): The search builder logic.

    Returns:
        Q: The Q object representing the search conditions.

    Database Operations:
        None
    """
    field_name = post_data.get("searchBuilder[criteria][0][origData]", None)
    i = 0
    q_objects = Q()  # Initialize an empty Q object
    while field_name is not None:
        operator = post_data.get(f"searchBuilder[criteria][{i}][condition]", None)
        value = post_data.get(f"searchBuilder[criteria][{i}][value1]", "")
        value2 = post_data.get(f"searchBuilder[criteria][{i}][value2]", "")
        data_type = post_data.get(f"searchBuilder[criteria][{i}][type]", "")
        logger.debug(
            f"field_name:{field_name};condition:{operator};value1:{value};value2:{value2};data_type:{data_type}"
        )
        # Dynamically build the query lookup
        if operator == "!null":
            q_objects &= Q(**{f"{field_name}__isnull": False})
        elif operator == "null":
            q_objects &= Q(**{f"{field_name}__isnull": True})
        elif operator == "!=":
            q_objects &= ~Q(**{f"{field_name}": value})
        elif operator == "=":
            q_objects &= Q(**{f"{field_name}": value})
        elif operator == "!contains" and data_type in ["string"]:
            q_objects &= ~Q(**{f"{field_name}__icontains": value})
        elif operator == "contains" and data_type in ["string"]:
            q_objects &= Q(**{f"{field_name}__icontains": value})
        elif operator == "!starts" and data_type in ["string"]:
            q_objects &= ~Q(**{f"{field_name}__startswith": value})
        elif operator == "starts" and data_type in ["string"]:
            q_objects &= Q(**{f"{field_name}__startswith": value})
        elif operator == "!ends" and data_type in ["string"]:
            q_objects &= ~Q(**{f"{field_name}__endswith": value})
        elif operator == "ends" and data_type in ["string"]:
            q_objects &= Q(**{f"{field_name}__endswith": value})
        elif operator == ">=" and data_type in ["num"]:
            q_objects &= Q(**{f"{field_name}__gte": value})
        elif operator == ">" and data_type in ["num"]:
            q_objects &= Q(**{f"{field_name}__gt": value})
        elif operator == "<" and data_type in ["num"]:
            q_objects &= Q(**{f"{field_name}__lt": value})
        elif operator == "<=" and data_type in ["num"]:
            q_objects &= Q(**{f"{field_name}__lte": value})
        elif operator == "!between" and data_type in ["num"]:
            q_objects &= ~Q(**{f"{field_name}__gte": value}) & Q(
                **{f"{field_name}__lte": value2}
            )
        elif operator == "between" and data_type in ["num"]:
            q_objects &= Q(**{f"{field_name}__gte": value}) & Q(
                **{f"{field_name}__lte": value2}
            )

        i = i + 1
        field_name = post_data.get(f"searchBuilder[criteria][{i}][origData]", None)

    return q_objects

def set_datatables_response(request, queryset, fields: list, search_keys: list):
    """
    Set the response for DataTables.

    Args:
        request (HttpRequest): The HTTP request object.
        queryset (QuerySet): The queryset to paginate.
        fields (list): List of fields to include in the response.
        search_keys (list): List of fields to search.

    Returns:
        dict: The response data.

    Database Operations:
        Read: Various models
    """
    draw = int(request.POST.get("draw", 1))
    start = int(request.POST.get("start", 0))
    length = int(request.POST.get("length", 10))

    search_value = request.POST.get("search[value]", None)
    search_builder_logic = request.POST.get("searchBuilder[logic]", None)

    # 处理过滤
    if search_value:
        conditions = reduce(
            lambda x, y: x | Q(**{f"{y}__icontains": search_value}), search_keys, Q()
        )
        queryset = queryset.filter(conditions)
    if search_builder_logic is not None:
        q_objects = extract_datatables_search_builder_parameters(
            request.POST, search_builder_logic
        )
        queryset = queryset.filter(q_objects)

    # 处理排序
    order_column = request.POST.get("order[0][column]", None)
    order_by = None
    if order_column is not None:
        order_column_name = fields[int(order_column)]
        order_direction = request.POST.get("order[0][dir]", "asc")
        order_by = (
            order_column_name if order_direction == "asc" else f"-{order_column_name}"
        )
        queryset = queryset.order_by(order_by)

    logger.debug(queryset.query)

    # 处理分页
    paginator = Paginator(queryset.values(*fields), request.POST.get("length", 10))
    page_number = start // length + 1
    page = paginator.get_page(page_number)

    data = json.dumps(list(page), cls=CustomJSONEncoder)

    return {
        "recordsTotal": queryset.count(),
        "recordsFiltered": paginator.count,
        "data": json.loads(data),
    }

def no_permission_redirect(request, path=None, message=None):
    """
    Redirect to a specified path or the home page if the user has no permission.

    Args:
        request (HttpRequest): The HTTP request object.
        path (str): The path to redirect to.
        message (str): The error message.

    Returns:
        HttpResponse: The redirect response.

    Database Operations:
        None
    """
    if message is None and request.path.startswith("/api"):
        return JsonResponse(
            {"message_type": "error", "message": "No Permission", "data": []},
            status=403,
        )
    elif message is None:
        message = f"You do not have permission to view this page({request.path})."
    messages.error(request, f"{message}")
    if path is not None:
        return redirect(path)
    referer = request.META.get("HTTP_REFERER")  # Previous URL (if exists)
    if referer:
        return HttpResponseRedirect(referer)
    else:
        return redirect("app:home")

def get_model_class(backend_app_label, backend_app_model):
    """
    Get the model class for a given app label and model name.

    Args:
        backend_app_label (str): The app label.
        backend_app_model (str): The model name.

    Returns:
        Model: The model class.

    Database Operations:
        None
    """
    if backend_app_label and backend_app_model:
        model_class = apps.get_model(backend_app_label, backend_app_model)
        return model_class
    else:
        raise ValueError(f"backend_app_label and backend_app_model is missing in Form")

def get_object_or_redirect(model, *args, message="Data object not found.", **kwargs):
    """
    Get an object or raise a 404 error with a custom message.

    Args:
        model (Model): The model class.
        message (str): The error message.

    Returns:
        Model: The model instance.

    Database Operations:
        Read: Various models
    """
    try:
        return get_object_or_404(model, *args, **kwargs)
    except Http404 as e:
        logger.error(e)
        raise ValueError(message)
    except Exception as e:
        logger.error(e)
        raise ValueError("System Error")


# model_to_dict Only applicable to the data has no ManyToManyField with other data
def model_to_json_dump(model_object, timezone=None, request=None):
    """
    Convert a model instance to JSON format.

    Args:
        model_object (Model): The model instance.
        timezone (timezone): The timezone.
        request (HttpRequest): The HTTP request object.

    Returns:
        str: JSON string of the model instance.

    Database Operations:
        None
    """
    model_dict = model_to_dict(
        model_object, fields=[field.name for field in model_object._meta.fields]
    )
    return json.dumps(
        model_dict, cls=CustomJSONEncoder, timezone=timezone, request=request
    )

def get_menu_key_in_list(sub_menu: list, parent_key=None):
    """
    Get menu keys in a list.

    Args:
        sub_menu (list): The sub-menu list.
        parent_key (str): The parent key.

    Returns:
        list: List of menu keys.

    Database Operations:
        None
    """
    result = []
    for menu in sub_menu:
        key = (
            f"{parent_key}__{menu.get('key')}"
            if parent_key is not None
            else menu.get("key")
        )
        result.append(key)
        new_sub_menu = menu.get("sub_menu", [])
        if len(menu.get("sub_menu", [])) > 0:
            result += get_menu_key_in_list(new_sub_menu, key)
    return result

def validate_form_data(form_data, config):
    """
    Validate form data against a configuration.

    Args:
        form_data (dict): The form data.
        config (dict): The configuration.

    Returns:
        dict: Dictionary of validation errors.

    Database Operations:
        None
    """
    errors = {}

    # 字段级验证
    for field_id, field_config in config["fields"].items():
        value = form_data.get(field_id)

        # 必填验证
        if field_config.get("required") and not value:
            errors[field_id] = "This field is required"

        # 类型验证
        if field_config["type"] == "number" and not value.isdigit():
            errors[field_id] = "this field must be a number"

    # 跨字段验证
    for rule in config.get("validation_rules", {}).values():
        if rule["type"] == "range":
            source_value = form_data.get(rule["depends_on"])
            target_value = form_data.get(rule["target"])
            min_val = rule["rules"][source_value]["min"]
            max_val = rule["rules"][source_value]["max"]

            if not (min_val <= float(target_value) <= max_val):
                errors[rule["target"]] = (
                    f"value must be in the range：{min_val}-{max_val}"
                )

    return errors

def load_schema_from_file(schema_file_path):
    """
    Load a JSON schema from a file.

    Args:
        schema_file_path (str): The path to the JSON schema file.

    Returns:
        dict: The JSON schema as a Python dictionary, or None if an error occurs.

    Database Operations:
        None
    """
    try:
        path = "%s%s" % (
            settings.BASE_DIR,
            schema_file_path,
        )  # Add encoding for potential issues
        logger.debug(f"loading schema: {path}")
        with open(
            path, "r", encoding="utf-8"
        ) as f:  # Add encoding for potential issues
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"Error loading schema: {e}")
        logger.error(f"Error loading schema: {e}")
        return None

def validate_json_with_schema(json_data, schema):
    """
    Validate a JSON object against a JSON schema.

    Args:
        json_data (dict): The JSON object to validate.
        schema (dict): The JSON schema.

    Returns:
        str: None if the JSON is valid, otherwise the validation error message.

    Database Operations:
        None
    """
    try:
        validate(instance=json_data, schema=schema)
        return ""
    except ValidationError as e:
        return e.message

@global_cache_decorator(cache_key="normalized_url", timeout=settings.CACHE_TIMEOUT_L3)
def normalized_url(path):
    """
    Normalize a URL path.

    Args:
        path (str): The URL path.

    Returns:
        str: The normalized URL path.

    Database Operations:
        None
    """
    path = path.lower() if path is not None else ""
    new_path = ""
    if path.startswith("/api"):
        path = path.replace("/api", "")
    if path.endswith("-filter"):
        path_split = path.split("/")
        for p in path_split:
            if not p.endswith("-filter") and p != "":
                new_path = f"{new_path}/{p}"

    if new_path == "":
        new_path = path
    return new_path

@global_cache_decorator(cache_key="csoa_app_list", timeout=settings.CACHE_TIMEOUT_L3)
def get_app_list():
    """
    Get the list of installed apps.

    Returns:
        list: List of installed apps.

    Database Operations:
        None
    """
    installed_apps = apps.get_models()
    app_list = set()
    for app in installed_apps:
        app_list.add(app._meta.app_label)
    return list(app_list)

@global_cache_decorator(cache_key="csoa_model_list", timeout=settings.CACHE_TIMEOUT_L3)
def get_model_list():
    """
    Get the list of models in installed apps.

    Returns:
        list: List of model names.

    Database Operations:
        None
    """
    installed_apps = settings.INSTALLED_APPS
    model_list = set()
    for app in installed_apps:
        models = apps.get_models(app)  # Get models for each app
        for model in models:
            model_list.add(model.__name__)  # Append model name to the list
    return list(model_list)

def find_url_pattern(resolver, target_namespace, target_name, current_namespace=''):
    """Recursively search for URL pattern with matching namespace and name"""
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            # Handle nested namespaces
            resolver_namespace = pattern.namespace or ''
            new_namespace = (
                f"{current_namespace}:{resolver_namespace}"
                if current_namespace
                else resolver_namespace
            )
            
            # Recursively search in nested patterns
            found = find_url_pattern(
                pattern, 
                target_namespace,
                target_name,
                new_namespace.strip(':')
            )
            if found:
                return found
        elif isinstance(pattern, URLPattern):
            # Match both namespace and pattern name
            if current_namespace == target_namespace and pattern.name == target_name:
                return pattern
    return None

def get_url_fomat(url_name):
    # Split namespace components and final name
    parts = url_name.split(':')
    if len(parts) == 1:
        namespace = ''
        name = parts[0]
    else:
        namespace = ':'.join(parts[:-1])
        name = parts[-1]
    
    # Get root URL resolver
    resolver = get_resolver()
    
    # Find matching pattern
    pattern = find_url_pattern(resolver, namespace, name)
    
    if not pattern:
        raise ValueError(f"URL pattern '{url_name}' not found")
    
    # Get raw URL pattern string
    raw_pattern = pattern.pattern._route
    
    # Convert Django path syntax to named parameters
    formatted_pattern = re.sub(
        r'<([^:]+:)?(\w+)>',  # Matches <converter:param> or <param>
        r'{\2}',              # Keep only parameter name
        raw_pattern
    )
    
    return f'/{formatted_pattern}'