from django.db.models import OuterRef, Subquery, Value
from django.db.models.functions import Coalesce, Cast
from django.db.models import TextField
from django.shortcuts import render, redirect
from jsonForm.models import FormTemplate, TaskInstance, Workflow
from userManagement.models import AppMenu
from jsonForm.forms import TaskInstanceForm
from jsonForm import util as formUtil
from .forms import HeaderingForm
from .models import FileModel
from jsonForm.tables import create_dynamic_case_table_class, create_dynamic_case_data_table_class, create_dynamic_case_data_filter
from django_tables2 import RequestConfig
from django.db.models import JSONField
from .util import CustomJSONEncoder, set_datatables_response, no_permission_redirect, get_model_class, get_object_or_redirect
from .util_model import get_audit_history_fields, get_select_choices
from .util_files import download_file
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.db.models import Q
from functools import reduce
from django.urls import reverse
from .decorators import case_decorator
import json

import logging
logger = logging.getLogger('django')

def create_case_view(request, context, app_name, form_code):
	template_name = 'base/app_case_form.html'
	form = context['form']
	if form is None:
		return render(request, template_name, context )
	case_context = formUtil.create_case_view(request, form, context['mini_app'].id)
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
	workflow_edit_status = [v[0] for v in get_select_choices('dict_workflow_edit_status_active')]
	if not(request.user == case_instance.created_by and case_instance.status in workflow_edit_status): 
		messages.warning(request, f'only the user who created the case can EDIT the case with status in {workflow_edit_status} (Case ID: {case_id}, Case: Status {case_instance.status})')
		return redirect('app:app_home', app_name)
	case_context = formUtil.edit_case_data_view(request, case_instance, form, context['mini_app'].id)
	if case_context == {}:
		return redirect('app:app_my_cases_index', app_name)
	else:
		context.update(case_context)
	context['edit'] = True
	context['datatables'] =  False
	return render(request, template_name, context )

def get_case_details(request, context, app_name, form_code, case_id):
	
	template_name = 'base/app_case_details.html'
	case_instance = context['case_instance']
	if case_instance is None:
		return redirect('app:app_home', app_name)
	task_fields = TaskInstance.selected_fields_info() # need to bre replace with a config table to maintains the field list like model dict
	task_fields_names = list(task_fields.keys())
	tasks_queryset = case_instance.task_instances.all().order_by('-updated_at')
	context['task_instances'] = json.dumps(list(tasks_queryset.values(*task_fields_names)), cls=CustomJSONEncoder)
	context['task_fields'] = task_fields
	section_datas = case_instance.case_data_case.all().values('form_section__json_template','section_data').order_by('form_section__index')
	context['section_datas'] =  json.dumps(list(section_datas), cls=CustomJSONEncoder)

	# role_unit includes the permissions (userManagement.CustomGroup) that the user has in this page
	role_unit = request.current_page_menu.get('role_unit', [])
	role_unit_ids = [ r.get('permission_role__id') for r in role_unit ]

	if request.method == 'POST':
		pending_task_forms = [
			TaskInstanceForm(request.POST, request.FILES, request=request, instance=ti, prefix=f"pending_task_{ti.id}") 
			for ti in tasks_queryset.filter(Q(is_active=True)&(Q(assign_to__id__in=role_unit_ids)|Q(is_active=request.user.is_superuser)))
			]
		forms_is_valid = True
		for task_form in pending_task_forms:
			if not task_form.is_valid():
				forms_is_valid = False
		if forms_is_valid:
			for task_form in pending_task_forms:
				task_form.save()			
				case_instance.updated_by = request.user
				try:
					case_instance.save()
				except Exception as e:
					for t in pending_task_forms:
						task = TaskInstance.objects.get(id = t.instance.id)
						task.is_active = True
						task.save()
						logger.error(e)
						messages.error(request, e)
			return redirect('app:app_case_details', app_name, form_code, case_id)
		else:
			context['pending_task_forms'] = pending_task_forms
	else:
		context['pending_task_forms'] = [ 
			TaskInstanceForm(request=request, instance=ti, prefix=f"pending_task_{ti.id}") 
			for ti in tasks_queryset.filter(Q(is_active=True)&(Q(assign_to__id__in=role_unit_ids)|Q(is_active=request.user.is_superuser)))
			]
# audit history setting
# path('app/<str:app_name>/cases/search/<str:form_code>/details/history/<int:case_id>##', request_decorator(get_case_details_history_json), name='app_case_details_history'), # app:app_case_details
	context['history_data_url'] = reverse('api:app_case_details_history', args=[
			app_name,
			form_code,
			case_id
		])
	context['history_fields'] = get_audit_history_fields()
# document settings
	file_fields=FileModel.selected_fields_info() # need to bre replace with a config table to maintains the field list like model dict
	file_fields['task_files__task__name'] = 'Task Name'

# path('app/<str:app_name>/cases/search/<str:form_code>/details/documents/<int:case_id>##', request_decorator(get_case_details_documents_json), name='app_case_details_documents'), # app:app_case_details
	context['file_data_url'] = reverse('api:app_case_details_documents', args=[
			app_name,
			form_code,
			case_id
		])
# path('app/<str:app_name>/cases/<str:form_code>/file-download/<int:case_id>-filter/<str:file_id>-filter', get_case_details_file_download_view, name='app_case_details_file_download'), # app:app_case_details
	context['file_download_url'] = reverse('api:app_case_details_file_download', args=[
			app_name,
			form_code,
			case_id,
			'0'
		])
	context['file_fields'] = file_fields
	context['file_root'] = settings.MEDIA_URL
	return render(request, template_name, context)

def get_case_details_history_json(request, app_name, form_code, case_id):
	try:
		form = FormTemplate.get_instance_by_code(form_code)
		model_class = get_model_class(form.backend_app_label, form.backend_app_model)
		case_instance = model_class.objects.get(pk=case_id)
	except Exception as e:
		logger.error(e)
		return JsonResponse({'message': "Case Not  Found"}, status=404)
	data = formUtil.get_case_audit_history(case_instance)
	data_json = json.dumps(data, cls=CustomJSONEncoder)
	records_total = len(data)
	response_data = {
		'recordsTotal': records_total,
		'recordsFiltered': records_total, 
		'data': json.loads(data_json)
	}
	return JsonResponse(response_data, safe=True)

def get_case_details_documents_json(request, app_name, form_code, case_id):
	try:
		form = FormTemplate.get_instance_by_code(form_code)
		model_class = get_model_class(form.backend_app_label, form.backend_app_model)
		case_instance = model_class.objects.get(pk=case_id)
	except Exception as e:
		logger.error(e)
		return JsonResponse({'message': "Case Not  Found"}, status=404)
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
	return JsonResponse(response_data, safe=True)

# all the forms linked in one mini_app should using same table to store data
# if the forms use different table to store data, need to create another view
# need to create search function in UI template for search data
# ongoingList/completedList
def get_my_cases_view(request, context, app_name):
	type=request.GET.get('type')
	permission_list = request.permission_list
	if type is None:
		type = 'todoList'
	context['type'] = type

	show_list = False
	permission__details = False
	permission__edit = False

	if type is None:
		type = 'todoList'
	context['type'] = type
	
	for perm in permission_list:
		if perm == type:
			show_list=True
		elif perm == f"{type}__details":
			permission__details = True
		elif perm == f"{type}__edit":
			permission__edit = True

	if not show_list:
		return no_permission_redirect(request, None, f"No permission to {type}-{show_list}")


	template_name = 'base/app_my_cases.html'
	form = AppMenu.get_app_form_by_key(app_name)
	model_class = form.get_model_class()

	context['fields'] = model_class.selected_fields_info()
	context['id_key'] = "id"
	context['other_key'] = "form__code"
	context['permission__details'] = permission__details
	context['permission__edit'] = permission__edit
	context['data_url'] = reverse('api:app_my_cases_data', args=[
			app_name,
			type
		])
	context['details_url'] = reverse('app:app_case_details', args=[
			app_name,
			0,
			1
		])
	context['edit_url'] = reverse('app:app_my_cases_edit', args=[
			app_name,
			0,
			1
		])
	return render(request, template_name, context)

def get_my_cases_view_data(request, app_name, type):

	form = AppMenu.get_app_form_by_key(app_name)
	model_class = form.get_model_class()
	fields = model_class.selected_fields_info()

	user_permissions = request.user.permissions.filter(app__key=app_name)
	if type == 'todoList':
		cases = model_class.objects.filter(
			Q(
				form__application__key=app_name, 
				is_submited=True, 
				workflow_instance__is_active=True, 
				task_instances__is_active=True,
				task_instances__assign_to__in=user_permissions # assigned cases
			) |
			Q(
				form__application__key=app_name,  
				created_by = request.user, 
				is_submited=False # draft cases
			)
			).exclude(status='Cancelled').distinct().order_by('-updated_by')
	elif type == 'ongoingList':
		cases = model_class.objects.filter(
			(
				Q(task_instances__assign_to__in=user_permissions) |
				Q(created_by = request.user)
			) & 
			Q(
				form__application__key=app_name, 
				is_submited=True, 
				workflow_instance__is_active=True, 
			)
			).exclude(status='Cancelled').distinct().order_by('-updated_by')
	elif type == 'completedList':
		cases = model_class.objects.filter(
			(
				Q(task_instances__assign_to__in=user_permissions) |
				Q(created_by = request.user)
			) & 
			Q(
				form__application__key=app_name, 
				is_submited=True, 
				workflow_instance__is_active=False, 
			)
			).exclude(status='Cancelled').distinct().order_by('-updated_by')
	else:
		return JsonResponse({"message": "Page not Found"}, status=404)
	field_keys = list(fields.keys())
	response_data = set_datatables_response(request, cases, field_keys, field_keys)
	return JsonResponse(response_data, safe=True)

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
	case_data_class = forms.first().get_section_model_class()
	queryset = case_data_class.objects.filter(case__form__application=mini_app, case__is_submited=True, form_section__index=0).exclude(case__status='Cancelled')
	# Apply additional filters from the request
	CaseDataFilter = create_dynamic_case_data_filter(case_data_class)
	case_filter = CaseDataFilter(request.GET, queryset=queryset)
	case_filter.form.fields['form'].queryset = forms
	# ----------------------------------------------------------------------------------
	# 2. if there is any filters: 
	# ----------------------------------------------------------------------------------
	# Check if any filter fields have been filled out
	filters_active = bool(request.GET)  # Check if any GET parameters are present
	headers=[]
	if filters_active and case_filter.form.is_valid() and request.GET.get('form', '') != '':
		# ----------------------------------------------------------------------------------
		#  3 get the form, and set up the header selections for "Re-arrange Heading"
		# ----------------------------------------------------------------------------------
		form = get_object_or_redirect(FormTemplate, pk=request.GET.get('form'))
		headers =FormTemplate.get_headers_by_code(form.code) 
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
				case_data_subquery = case_data_class.objects.filter(
					case=OuterRef('case__id'),  # Refers to the outer Request model's primary key
					form_section__index=i
				).values('section_data')
				annotated_fields[f'section_data_{i}'] = Coalesce(Subquery(case_data_subquery, output_field=JSONField()), Value('{}', output_field=JSONField()))
			queryset = queryset.annotate(**annotated_fields)
			case_filter = CaseDataFilter(request.GET, queryset=queryset)
			case_filter.form.fields['form'].queryset = forms
		# DynamicTable = create_dynamic_case_data_table_class(case_data_class, headers)
		# cases =  DynamicTable(case_filter.qs)
	DynamicTable = create_dynamic_case_data_table_class(case_data_class, headers, show_details=True)
	cases = DynamicTable(case_filter.qs)
		
	# pagging
	RequestConfig(request, paginate={"per_page": 25}).configure(cases)

	context['forms'] = forms
	context['cases'] = cases
	context['filter'] = case_filter
	context['selected_headers'] = selected_headers
	context['django_tables2'] = True
	context['datatables'] = False
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
	data_class = get_model_class(form.backend_app_label, form.backend_app_section_model)
	# ----------------------------------------------------------------------------------
	# 2. set up headers for the table
	# ----------------------------------------------------------------------------------
	fields = data_class.selected_fields_info()
	headers = FormTemplate.get_headers_by_code(form_code)
	for h in headers:
		if h['index']==index:
			fields[f"section_data__{h['key']}"] = h['label']

	context['fields'] = fields
	context['data_url'] = reverse('api:app_cases_search_form_Data', args=[
			app_name,
			form_code,
			mini_app.id,
			form.id,
			index
		])
	context['id_key'] = "case__id"
	context['details_url'] = reverse('app:app_case_details', args=[
			app_name,
			form_code,
			0
		])
	return render(request, template_name, context)


def get_case_workflow_view(request, context, app_name, form_code, case_id):
	template_name = 'jsonForm/workflow.html'
	workflow_data = Workflow.get_data_by_id(context['form'].workflow.id)
	context['workflow_data'] = workflow_data
	return render(request, template_name, context)

@case_decorator
def get_cases_search_by_form_view_data(request,context, app_name, form_code, app_id, form_id, index):
	form = context['form']
	case_data_class = get_model_class(form.backend_app_label, form.backend_app_section_model)
	queryset = case_data_class.objects.filter(case__form__application=app_id, case__form= form_id, case__is_submited=True, form_section__index=index).exclude(case__status='Cancelled')
	fields = case_data_class.selected_fields_info()
	headers = FormTemplate.get_headers_by_code(form_code)
	# to control form template that has more than one section
	search_keys = []
	for h in headers:
		if h['index']==index:
			fields[f"section_data__{h['key']}"] = h['label']
			search_keys.append(f"section_data__{h['key']}")
	field_names = list(fields.keys())
	response_data = set_datatables_response(request, queryset, field_names, search_keys)
	return JsonResponse(response_data, safe=True)

@case_decorator
def get_case_details_file_download_view(request, context, app_name, form_code, case_id ,file_id):
	case_instance = context['case_instance']
	if case_instance is None:
		return redirect('app:app_home', app_name)
	data = case_instance.case_data_case.annotate(
				section_data_str=Cast('section_data', TextField())
			).filter(section_data_str__icontains=file_id)
	if data is None or data.count()==0:
		data = case_instance.task_instances.filter(files__id=file_id)
	if data is not None and  data.count()>0 :
		file = FileModel.objects.filter(id=file_id)
		if file.count()==1:
			return download_file(request, file.first())
	return HttpResponse("The requested file was not found on the server", status=404)