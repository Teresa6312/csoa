from django.db.models import OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render, get_object_or_404, redirect
from userManagement.models import AppMenu
from jsonForm.models import FormTemplate, TaskInstance, CaseData, Workflow
from jsonForm.forms import TaskInstanceForm
from jsonForm import util
from .redis import get_redis_data_json, create_redis_key_json, create_redis_key
from .forms import HeaderingForm
from .models import FileModel
from jsonForm.tables import CaseTable, create_dynamic_case_data_table_class, CaseDataFilter, CaseDataTable
from django_tables2 import RequestConfig
from django.db.models import JSONField
from .util import CustomJSONEncoder, extract_datatables_search_builder_parameters
from .util_model import set_context_base, get_audit_history_fields
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.db.models import Q
from functools import reduce
import json

import logging
logger = logging.getLogger('django')

def create_case_view(request, context, app_name,form_code):
	template_name = 'base/app_case_form.html'
	form = context['form']
	if form is None:
		return render(request, template_name, context )
	case_context = util.create_case_view(request, form, context['mini_app'].id)
	if case_context == {}:
		return redirect('app:app_home', app_name)
	else:
		context.update(case_context)
	return render(request, template_name, context )

def edit_case_view(request, context, app_name, form_code, case_id):
	template_name = 'base/app_case_form.html'
	form = context['form']
	case_instance = context['case_instance']
	if case_instance is None:
		return redirect('app:app_home', app_name)
	if not request.user == case_instance.created_by or case_instance.is_submited:
		return redirect('app:app_case_details', app_name = app_name, case_id = case_instance.id)
	case_context = util.edit_case_data_view(request, case_instance, form, context['mini_app'].id)
	if case_context == {}:
		return redirect('app:app_my_cases_index', app_name)
	else:
		context.update(case_context)
	context['edit'] = True
	return render(request, template_name, context )

def get_case_details(request, context, app_name, form_code, case_id):
	template_name = 'base/app_case_details.html'
	case_instance = context['case_instance']
	if case_instance is None:
		return redirect('app:app_home', app_name)
	if case_instance.status =='Draft' and case_instance.created_by == request.user:
		return redirect('app:app_my_cases_edit', app_name, form_code, case_id)
	task_fields = TaskInstance.selected_fields_info() # need to bre replace with a config table to maintains the field list like model dict
	task_fields_names = list(task_fields.keys())
	tasks_queryset = case_instance.task_instances.all().order_by('-updated_at')
	context['task_instances'] = json.dumps(list(tasks_queryset.values(*task_fields_names)), cls=CustomJSONEncoder)
	context['task_fields'] = task_fields
	section_datas = case_instance.case_data_case.all().values('form_section__json_template','section_data').order_by('form_section__index')
	context['section_datas'] =  json.dumps(list(section_datas), cls=CustomJSONEncoder)
	if request.method == 'POST':
		pending_task_forms = [TaskInstanceForm(request.POST, request.FILES,  instance=ti, prefix=f"pending_task_{ti.id}") for ti in tasks_queryset.filter(is_active=True)]
		forms_is_valid = True
		for task_form in pending_task_forms:
			if not task_form.is_valid():
				forms_is_valid = False
		if forms_is_valid:
			for task_form in pending_task_forms:
				task_form.save()
				case_instance.updated_by = request.user
				case_instance.save()
			return redirect('app:app_case_details', app_name, form_code, case_id)
		else:
			context['pending_task_forms'] = pending_task_forms
	else:
		context['pending_task_forms'] = [ TaskInstanceForm(instance=ti, prefix=f"pending_task_{ti.id}") for ti in tasks_queryset.filter(is_active=True)]
# audit history setting
	context['history_data_url'] = f'/api{request.path}/history-filter'
	context['history_fields'] = get_audit_history_fields()
# document settings
	file_fields=FileModel.selected_fields_info() # need to bre replace with a config table to maintains the field list like model dict
	file_fields['task_files__task__name'] = 'Task Name'
	context['file_data_url'] = f'/api{request.path}/documents-filter'
	context['file_fields'] = file_fields
	context['file_root'] = settings.MEDIA_URL
	return render(request, template_name, context)


def get_case_details_history_json(request, app_name, form_code, case_id):
	form = get_object_or_404(FormTemplate, code=form_code)
	model_class = form.get_model_class()
	case_instance = model_class.objects.get(pk=case_id)
	if case_instance is None:
		messages.info("Case Not  Found")
		return JsonResponse()
	data = util.get_case_audit_history(case_instance)
	data_json = json.dumps(data, cls=CustomJSONEncoder)
	records_total = len(data)
	response_data = {
		'recordsTotal': records_total,
		'recordsFiltered': records_total, 
		'data': json.loads(data_json)
	}
	return JsonResponse(response_data)

def get_case_details_documents_json(request, app_name, form_code, case_id):
	form = get_object_or_404(FormTemplate, code=form_code)
	model_class = form.get_model_class()
	case_instance = model_class.objects.get(pk=case_id)
	if case_instance is None:
		return JsonResponse({'message': "Case Not  Found"})
	fields=FileModel.selected_fields_info()
	fields['task_files__task__name'] = 'Task Name'
	data = FileModel.objects.filter(task_files__case_task_instances__id = case_id).order_by('-created_at').values(*fields)
	data_json = json.dumps(list(data), cls=CustomJSONEncoder)
	records_total = len(data)
	response_data = {
		'recordsTotal': records_total,
		'recordsFiltered': records_total, 
		'data': json.loads(data_json)
	}
	return JsonResponse(response_data)

# all the forms linked in one mini_app should using same table to store data
# if the forms use different table to store data, need to create another view
#  need to create search function in UI template for search data
# ongoingList/completedList
def get_my_cases_view(request, context, app_name):
	template_name = 'base/app_my_cases.html'
	mini_app = context['mini_app']
	form = FormTemplate.objects.filter(application=mini_app).order_by('-is_active').first() 
	model_class = form.get_model_class()
	type=request.GET.get('type')
	if type is not None:
		context['type'] = type
	else:
		context['type'] = 'todoList'
	user_permissions = request.user.permissions.filter(app=mini_app)
	if type == 'todoList' or type is None:
		cases = model_class.objects.filter(
			Q(
				form__application=mini_app, 
				is_submited=True, 
				workflow_instance__is_active=True, 
				task_instances__is_active=True,
				task_instances__assign_to__in=user_permissions # assigned cases
			) |
			Q(
				form__application=mini_app,  
				created_by = request.user, 
				is_submited=False # draft cases
			)
			).exclude(status='Cancelled').distinct()
	elif type == 'ongoingList':
		cases = model_class.objects.filter(
			(
				Q(task_instances__assign_to__in=user_permissions) |
				Q(created_by = request.user)
			) & 
			Q(
				form__application=mini_app, 
				is_submited=True, 
				workflow_instance__is_active=True, 
			)
			).exclude(status='Cancelled').distinct()
	elif type == 'completedList':
		cases = model_class.objects.filter(
			(
				Q(task_instances__assign_to__in=user_permissions) |
				Q(created_by = request.user)
			) & 
			Q(
				form__application=mini_app, 
				is_submited=True, 
				workflow_instance__is_active=False, 
			)
			).exclude(status='Cancelled').distinct()
	else:
		cases = None
	if cases is not None:
		cases = CaseTable(cases) # need to create dynamic table for this
		RequestConfig(request, paginate={"per_page": 25}).configure(cases)
	context['cases'] = cases
	return render(request, template_name, context)

# search all forms in the app, rearrange header only shows when a form was search
def get_cases_search_view(request, context, app_name):
	# ----------------------------------------------------------------------------------
	# 1. initialize all the default data
	# ----------------------------------------------------------------------------------
	template_name = 'base/app_cases_search.html'
    # Initialize selected headers
	initial_form_value = request.session.get('initial_form_value', '')
	selected_headers = request.session.get('initial_selected_headers', [])

	mini_app = context['mini_app']
	forms = FormTemplate.objects.filter(application=mini_app)
	queryset = CaseData.objects.filter(case__form__application=mini_app, case__is_submited=True, form_section__index=0).exclude(case__status='Cancelled')
	# Apply additional filters from the request
	case_filter = CaseDataFilter(request.GET, queryset=queryset)
	case_filter.form.fields['form'].queryset = forms
	# ----------------------------------------------------------------------------------
	# 2. if there is any filters: 
	# ----------------------------------------------------------------------------------
	# Check if any filter fields have been filled out
	filters_active = bool(request.GET)  # Check if any GET parameters are present
	if filters_active and case_filter.form.is_valid() and request.GET.get('form', '') != '':
		# ----------------------------------------------------------------------------------
		#  3 get the form, and set up the header selections for "Re-arrange Heading"
		# ----------------------------------------------------------------------------------
		form = get_object_or_404(FormTemplate, pk=request.GET.get('form'))
		headers = get_redis_data_json(f'form_header{form.id}')
		if headers is None:
			data = form.get_key_list
			create_redis_key_json(f'form_header:{form.id}', data)
		headers = get_redis_data_json(f'form_header:{form.id}')
		# ----------------------------------------------------------------------------------
		# 4 need to detect if the form filter was changed, if so selected_headers need to be reset
		# ----------------------------------------------------------------------------------
		if not initial_form_value == '' and not initial_form_value == request.GET.get('form'):
			selected_headers= []
		request.session['initial_form_value'] = request.GET['form']
		
		# ----------------------------------------------------------------------------------
		# 5. if user click "Re-arrange Heading"
		# ----------------------------------------------------------------------------------
		if request.method == 'POST':
			header_form = HeaderingForm(request.POST)
			header_form.fields['headers'].choices = [(a['key'], a['label']) for a in headers if not a['input']=='list']
			if header_form.is_valid():
				# Process header form data
				selected_headers = header_form.cleaned_data['headers']
				request.session['initial_selected_headers'] = selected_headers
		else:
			header_form = HeaderingForm(initial={'headers': selected_headers})
			header_form.fields['headers'].choices = [(a['key'], a['label']) for a in headers if not a['input']=='list']
		context['header_form'] = header_form
		
		# ----------------------------------------------------------------------------------
		# 6. if selected_headers is not empty, need to reset the data table
		# ----------------------------------------------------------------------------------
		if len(selected_headers)>0:
			headers = [ a for a in headers if a['key'] in selected_headers]
			index_set = set([ a['index'] for a in headers if not a['index'] == 0 ])
			annotated_fields = {}
			for i in index_set:
				case_data_subquery = CaseData.objects.filter(
					case=OuterRef('case__id'),  # Refers to the outer Request model's primary key
					form_section__index=i
				).values('section_data')
				annotated_fields[f'section_data_{i}'] = Coalesce(Subquery(case_data_subquery, output_field=JSONField()), Value('{}', output_field=JSONField()))
			queryset = queryset.annotate(**annotated_fields)
			case_filter = CaseDataFilter(request.GET, queryset=queryset)
			case_filter.form.fields['form'].queryset = forms

		DynamicTable = create_dynamic_case_data_table_class(headers)
		cases =  DynamicTable(case_filter.qs)
	else:
		headers=[]
		cases = CaseDataTable(case_filter.qs)
		
	# pagging
	RequestConfig(request, paginate={"per_page": 25}).configure(cases)

	context['forms'] = forms
	context['cases'] = cases
	context['filter'] = case_filter
	context['selected_headers'] = selected_headers
	return render(request, template_name, context)

# CaseData need to be changed, get model class from form for queryset
def get_cases_search_by_form_view(request, context, app_name, form_code):
	template_name = 'base/app_case_list.html'
	# ----------------------------------------------------------------------------------
	# 1. initialize all the default data
	# ----------------------------------------------------------------------------------
	index=request.GET.get('index')
	if index is None:
		index = 0
	mini_app = context['mini_app']
	form =  context['form']
	# ----------------------------------------------------------------------------------
	# 2. set up headers for the table
	# ----------------------------------------------------------------------------------
	fields = CaseData.selected_fields_info()
	headers = get_redis_data_json(f'form_header:{form.id}')
	if headers is None:
		data = form.get_key_list
		create_redis_key_json(f'form_header:{form.id}', data)
	headers = get_redis_data_json(f'form_header:{form.id}')
	for h in headers:
		if h['index']==index:
			fields[f"section_data__{h['key']}"] = h['label']

	context['fields'] = fields
	context['data_url'] = f'/api{request.path}/{mini_app.pk}-{form.id}-{index}-filter' #f'/app-base/{app_name}/{model}/data'
	return render(request, template_name, context)


# # CaseData need to be changed, get model class from form for queryset
# def get_cases_search_by_form_view_data(request, app_name, form_code, app_id, form_id, index):
# 	form = FormTemplate.objects.get(code=form_code, application__key=app_name)
# 	if form is None:
# 		return JsonResponse({"message_type": "error", "message": "Invalid Case Form"})
# 	case_data_class = form.get_section_model_class()
# 	queryset = case_data_class.objects.filter(case__form__application=app_id, case__form= form_id, case__is_submited=True, form_section__index=index).exclude(case__status='Cancelled')
# 	fields = case_data_class.selected_fields_info()
# 	headers = get_redis_data_json(f'form_header:{form_id}')
# 	# to control form template that has more than one section
# 	for h in headers:
# 		if h['index']==index:
# 			fields[f"section_data__{h['key']}"] = h['label']
# 	field_names = list(fields.keys())
	
# 	# 处理排序
# 	order_column = request.GET.get('order[0][column]', None)
# 	order_by = None
# 	if order_column is not None:
# 		order_column_name = field_names[int(order_column)]
# 		order_direction = request.GET.get('order[0][dir]', 'asc')
# 		order_by = order_column_name if order_direction == 'asc' else f"-{order_column_name}"
# 		queryset = queryset.order_by(order_by)

# 	# 处理过滤
# 	search_value = request.GET.get('search[value]', None)
# 	if search_value:
# 		queryset = queryset.filter(field_1__icontains=search_value)  # 你可以根据需要调整

# 	# 处理分页
# 	paginator = Paginator(queryset.values(*field_names), request.GET.get('length', 10))
# 	page_number = int(request.GET.get('start', 0)) // int(request.GET.get('length', 10)) + 1
# 	page = paginator.get_page(page_number)

# 	data = []
# 	for obj in page:
# 		item_data = {field: obj.get(field, '--') for field in field_names}
# 		# item_data['details'] = reverse('app:app_case_details', args=[
# 		# 	obj.get(app_name),
# 		# 	obj.get('case__id', '--')
# 		# ])
# 		# Append to the data list
# 		data.append(item_data)

# 	response = {
# 		"draw": int(request.GET.get('draw', 0)),
# 		"recordsTotal": queryset.count(),
# 		"recordsFiltered": paginator.count,
# 		"data": data
# 	}
# 	return JsonResponse(response)

def get_case_workflow_view(request, context, app_name, form_code, case_id):
	template_name = 'base/app_case_workflow.html'
	workflow_data = get_redis_data_json(f"workflow:{context['form'].workflow.id}")
	if workflow_data is None:
		workflow = get_object_or_404(Workflow, pk=context['form'].workflow.id)
		workflow_data = workflow.get_workflow_data()
		create_redis_key(f'workflow:{workflow.id}', json.dumps(workflow_data, cls=CustomJSONEncoder))
	workflow_data = get_redis_data_json(f"workflow:{context['form'].workflow.id}")
	context['workflow_data'] = workflow_data
	return render(request, template_name, context)

def get_cases_search_by_form_view_data(request, app_name, form_code, app_id, form_id, index):
	all_values = request.POST
	form = FormTemplate.objects.get(code=form_code, application__key=app_name)
	if form is None:
		return JsonResponse({"message_type": "error", "message": "Invalid Case Form"})
	case_data_class = form.get_section_model_class()
	queryset = case_data_class.objects.filter(case__form__application=app_id, case__form= form_id, case__is_submited=True, form_section__index=index).exclude(case__status='Cancelled')
	fields = case_data_class.selected_fields_info()
	headers = get_redis_data_json(f'form_header:{form_id}')
	# to control form template that has more than one section
	search_keys = []
	for h in headers:
		if h['index']==index:
			fields[f"section_data__{h['key']}"] = h['label']
			search_keys.append(f"section_data__{h['key']}")
	field_names = list(fields.keys())

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
	return JsonResponse(response_data, safe=False)