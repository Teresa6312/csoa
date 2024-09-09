import json
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

logger = logging.getLogger('django')

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime)):
            return obj.strftime('%m/%d/%Y %H:%M:%S')
        if isinstance(obj, (date)):
            return obj.strftime('%m/%d/%Y')
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, Promise):
            return str(obj) 
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