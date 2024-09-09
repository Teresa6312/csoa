from django.apps import apps
from .util_model import get_dictionary, set_context_base
from .util import CustomJSONEncoder
from django.shortcuts import render,get_object_or_404
from userManagement.models import AppMenu
from .redis import get_redis_data_json, create_redis_key_json
from django.http import HttpResponseServerError
from django.contrib import messages
from django.http import JsonResponse
import json
from .models import ModelDictionaryConfigModel

import logging
logger = logging.getLogger('django')

def get_model_view(request, context, app_name, model):
    template_name = 'base/app_model_list.html'
    model_details = ModelDictionaryConfigModel.get_details(model)
    model_class = None
    try:
        if model_details is not None:
            model_class = apps.get_model( model_details.get('backend_app_label', ''),  model_details.get('backend_app_model', ''))
    except Exception as e:
        messages.error(request,"System Error")
        return render(request, template_name, context)
    if model_class is not None:
        fields = model_details.get('list_display', {})
        queryset= model_class.objects.all().values(*fields)
        context['fields'] = fields
        context['queryset'] = json.dumps(list(queryset), cls=CustomJSONEncoder)
        context['urls'] = {}
        # context['draw'] = int(request.GET.get('draw', 0))
        context['recordsTotal'] = queryset.count()
        context['idKey'] = model_details.get('pk_field_name', 'id')
        context['title'] =  model_details.get('model_label', '')
    else:
        messages.warning(request, "No related data found")
    return render(request, template_name, context)

def get_model_details_view(request,context, app_name, model, id):
    template_name = 'base/app_model_details.html'
    model_details = ModelDictionaryConfigModel.get_details(model)
    model_class = None
    try:
        if model_details is not None:
            model_class = apps.get_model( model_details.get('backend_app_label', ''),  model_details.get('backend_app_model', ''))
    except Exception as e:
        messages.error(request,"System Error")
        return render(request, template_name, context)
    if model_class is not None:
        context['title'] =  model_details.get('model_label', '')
        fields = model_details.get('fieldsets', {})
        record = model_class.objects.filter(pk=id).values(*fields)
        if record is not None:
            record_data = json.dumps(list(record), cls=CustomJSONEncoder)
            context['fields'] = fields
            context['record'] = json.loads(record_data)[0]
        sub_tables = model_details.get('sub_tables', [])
        temp = []
        if sub_tables is not None and len(sub_tables) != 0:
            for tab in sub_tables:
                tab_code = tab.get('dictionary_code', None)
                if tab_code is not None:
                    details = ModelDictionaryConfigModel.get_details(tab_code)
                    tab['fields'] = details.get('fieldsets', {})
                    temp.append(tab)
        context['sub_tables'] = temp
        context['model_details'] = model_details
    else:
        messages.info(request, "No related data found")
    return render(request, template_name, context)

def get_model_details_view_sub_table_json(request, app_name, model, id, sub_table_model, sub_table_field):
    model_details = ModelDictionaryConfigModel.get_details(sub_table_model)
    model_class = None
    try:
        if model_details is not None:
            model_class = apps.get_model( model_details.get('backend_app_label', ''),  model_details.get('backend_app_model', ''))
    except Exception as e:
        logger.error(e)
        return JsonResponse({'message_type': 'error','message': "Data Not Found"})
    if model_class is None:
        return JsonResponse({'message_type': 'warning','message': "Data Not  Found"})
    fields = model_details.get('fieldsets', {})
    filter = {sub_table_field:id}
    record = model_class.objects.filter(**filter).values(*fields)
    if record is not None:
        record_data = json.dumps(list(record), cls=CustomJSONEncoder)
        records_total = len(record_data)
        response_data = {
            'recordsTotal': records_total,
            'recordsFiltered': records_total, 
            'data': json.loads(record_data)
        }
    return JsonResponse(response_data)
