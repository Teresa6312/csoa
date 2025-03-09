from django import template
from django.urls import reverse
from urllib.parse import urlencode
from django.conf import settings
from base.models import FileModel
from base.util import get_url_fomat

register = template.Library()

@register.simple_tag
def admin_app_url(app_label):
    return reverse('admin:app_list', kwargs={'app_label': app_label})

@register.filter
def startswith(value, arg):
    return value.startswith(arg)

@register.filter
def endswith(value, arg):
    return value.endswith(arg)

# @register.simple_tag
# def add_query_params(url, **kwargs):
#     from urllib.parse import urlencode
#     query_string = urlencode(kwargs)
#     return f"{url}?{query_string}"

@register.simple_tag
def add_query_params(url, **kwargs):
    query_string = urlencode(kwargs)
    return f"{url}?{query_string}"

@register.simple_tag
def get_url(url_name, **kwargs):
    url_format = get_url_fomat(url_name)
    url = url_format.format(**kwargs)
    return f"{url}"

# @register.simple_tag
# def get_json_key_value(json_str, key, default=''):
#     values = ''
#     try:
#         data_dict = json.loads(json_str)
#         values = data_dict.get(key, default)
#     except json.JSONDecodeError:
#         return default
#     return values

# @register.simple_tag
# def get_field_label(instance, field_name):
#     return instance._meta.get_field(field_name).verbose_name

# @register.simple_tag
# def get_field_value(instance, field_name):
#     return getattr(instance, field_name)

# @register.simple_tag
# def initi_file_field(file_id, **kwargs):
#     file = FileModel.objects.filter(id=file_id)
#     if file is None:
#         return "No file found"
#     else:
#         file = file.first()
#         # file_url = f"{settings.MEDIA_URL}/{file.file}"
#         # file_field = f'<a href="{file_url}" download>{file.name}</a>'
#         return file.name