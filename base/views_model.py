from django.apps import apps
from django.shortcuts import render
from .util import CustomJSONEncoder
from django.contrib import messages
from django.http import JsonResponse
import json
from modelBase.models import ModelDictionaryConfigModel
from functools import reduce
from django.db.models import Q
from .util import CustomJSONEncoder, extract_datatables_search_builder_parameters
from .util_files import download_file
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from base.models import FileModel
from .decorators import model_decorator

import logging
logger = logging.getLogger('django')

def get_model_view(request, context, app_name, model, department=None, team=None):
    template_name = 'base/app_model_list.html'
    model_details = context['model_details']

    fields = model_details.get('list_display', {})
    context['subtitle'] =  model_details.get('model_label', '')

    context['fields'] = fields
    context['data_url'] = reverse('api:app_model_view_data', args=[
            app_name,
            model
        ])
    context['id_key'] = "id"
    context['details_url'] = reverse('app:app_model_view_details', args=[
            app_name,
            model,
            0
        ])
    return render(request, template_name, context)

@model_decorator
def get_model_view_data(request, context, app_name, model):
    model_details = context['model_details']
    model_class = context['model_class']

    fields = model_details.get('list_display', {})
    search_keys = fields.keys()
    field_names = list(fields.keys())

    queryset= model_class.objects.all().values(*fields)

    draw = int(request.POST.get('draw', 1))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))
    search_value = request.POST.get('search[value]', None)

    search_builder_logic = request.POST.get('searchBuilder[logic]', None)
    logger.debug(search_builder_logic)

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
        order_column_name = field_names[int(order_column)]
        order_direction = request.POST.get('order[0][dir]', 'asc')
        order_by = order_column_name if order_direction == 'asc' else f"-{order_column_name}"
        queryset = queryset.order_by(order_by)

    logger.debug(queryset.query)
    
    # 处理分页
    paginator = Paginator(queryset.values(*field_names), request.POST.get('length', 10))
    page_number = start // length + 1
    page = paginator.get_page(page_number)

    data = json.dumps(list(page), cls=CustomJSONEncoder)
    response_data = {
        "recordsTotal": queryset.count(),
        "recordsFiltered": paginator.count,
        'data': json.loads(data),
        # 'options': filter_kwargs
    }
    return JsonResponse(response_data, safe=True)

def get_model_details_view(request,context, app_name, model, id, department=None, team=None):
    template_name = 'base/app_model_details.html'
    model_details = context['model_details']
    model_class = context['model_class']
    context['subtitle'] =  model_details.get('model_label', '')
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
                tab['fields'] = details.get('list_display', {})
                temp.append(tab)
    context['sub_tables'] = temp
    return render(request, template_name, context)

@model_decorator
def get_model_details_view_sub_table_json(request, context, app_name, model, id, sub_table_model, sub_table_field):
    model_details = ModelDictionaryConfigModel.get_details(sub_table_model)
    model_class = None
    try:
        if model_details is not None:
            model_class = apps.get_model( model_details.get('backend_app_label', ''),  model_details.get('backend_app_model', ''))
    except Exception as e:
        logger.error(e)
        return JsonResponse({'message_type': 'error','message': "Data Not Found"}, status=404)
    if model_class is None:
        return JsonResponse({'message_type': 'warning','message': "Data Not  Found"}, status=404)
    fields = model_details.get('list_display', {})
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
    return JsonResponse(response_data, safe=True)

@model_decorator
def get_model_details_file_download_view(request,context, app_name, model, id, sub_table_field ,file_id):
    model_details = context['model_details']
    sub_tables = model_details.get('sub_tables', [])
    id_filter_name = None 
    for sub in sub_tables:
        if sub.get('model', '') == 'base.FileModel' and sub.get('id_filter_name', '') == sub_table_field:
            id_filter_name = sub.get('id_filter_name', '')
            break
    if id_filter_name is not None:
        file = FileModel.objects.filter(Q(id=file_id)&Q(**{sub_table_field:id}))
        if file.count()==1:
            return download_file(request, file.first())
    return HttpResponse("The requested file was not found on the server", status=404)

