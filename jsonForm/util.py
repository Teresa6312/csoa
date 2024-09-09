import json
from .forms import create_dynamic_form_section, create_dynamic_form_section_formset, CaseForm
from base.util import CustomJSONEncoder
from base.util_model import handle_uploaded_file, get_audit_history, get_audit_history_by_instance
from .models import FormTemplate, TaskInstance
from userManagement.models import Team, CustomUser, AppMenu
from django import forms
from base.forms import MultipleFileField
from django.contrib import messages
import logging
logger = logging.getLogger('django')

from django.db.models import Q

def create_case_view(request, form: FormTemplate, app_id=None):
    sections = form.form_section_form_template.filter(is_active=True, is_publish=True)
    section_forms = []
    section_forms_data = {}
    section_forms_is_valid = True
    section_formsets_valid = True
    case_team = None
    case_department = None
    case_form = CaseForm.create_case_form(app_id, request.user, prefix='case_form')
    case_form_is_valid = True
    
    for s in sections:
        section_formsets_data = {}
        form_data = None
        DynamicFormSection = create_dynamic_form_section (s.json_template, s.id)
        if request.method == 'POST':
            case_form = CaseForm.create_case_form(app_id, request.user, request.POST,request.FILES, prefix='case_form')
            if not case_form.is_valid():
                case_form_is_valid = False
            else:
                case_team = case_form.cleaned_data.get('case_team', None)
                case_department = case_form.cleaned_data.get('case_department', None)

            section_form = DynamicFormSection(request.POST, request.FILES, prefix=f'form_section_id_{s.id}')
            if section_form.is_valid():
                # Process the files
                section_form = process_form_files(request, section_form, s.id)
                form_data =  section_form.cleaned_data
            else:
                section_forms_is_valid = False
            for field_name in DynamicFormSection.nested_formset_fields:
                DynamicFormSectionFormSet = create_dynamic_form_section_formset(DynamicFormSection.nested_formset_fields[field_name]['fields'])
                nested_formset = DynamicFormSectionFormSet(request.POST, request.FILES, prefix=field_name)
                field_data = []
                if not nested_formset.is_valid():
                    section_formsets_valid = False
                else:
                    for formset in nested_formset:
                        if formset.cleaned_data and not formset.cleaned_data.get('DELETE', False):
                            formset = process_formset_files(request, formset, field_name)
                            field_data.append(formset.cleaned_data)
                    if len(field_data) > 0:
                        section_formsets_data[field_name] = field_data
                    elif DynamicFormSection.nested_formset_fields[field_name]['required']:
                        section_formsets_valid = False

                section_form.nested_formsets[field_name] = nested_formset
            if form_data is not None:
                for a in section_formsets_data:
                    form_data[a] = section_formsets_data[a]
                section_forms_data[str(s.id)] = form_data
            section_forms.append(section_form)
        else:
            section_forms.append(DynamicFormSection)
    
    if request.method == 'POST' and section_forms_is_valid and section_formsets_valid and case_form_is_valid:
        instance = form.create_model_instance(form=form)
        instance.created_by = request.user
        instance.updated_by = request.user
        if request.POST.get('action') == 'draft':
            instance.is_submited = False
            instance.status = 'Draft'
        if (case_team is not None):
            instance.case_team = case_team
            team = Team.objects.get(pk=case_team)
            case_department = team.department
        instance.case_department = case_department
        instance.save()
        try:
            for section in sections:
                section_data = json.dumps(section_forms_data.get(str(section.id)), cls=CustomJSONEncoder)
                section_instance = section.create_model_instance(case = instance, form_section=section, section_data=json.loads(section_data))
                section_instance.save()
        except Exception as e:
            messages.error(request, f"System error")
            logger.error(e)
            for section_datas in instance.case_data_case.all():
                section_datas.delete()
            instance.delete()
            return {'form': form, 'section_forms': section_forms, 'case_form': case_form, 'error': e}
        if request.POST.get('action') == 'submit':
            instance.is_submited = True
        instance.save()
        messages.info(request, f"Case [{instance.id}] {instance.status}")
        return {}
    elif request.method == 'POST':
        messages.warning(request, f"Initial data valid {case_form_is_valid}; Main form valid {section_forms_is_valid}; sub form valid: {section_formsets_valid}")
    return  {'form': form, 'section_forms': section_forms, 'case_form': case_form}

def edit_case_data_view(request, case, form:FormTemplate, app_id=None):
    section_datas = case.case_data_case.all()
    section_forms = []
    section_forms_data = {}
    section_forms_is_valid = True
    section_formsets_valid = True
    case_form_is_valid = True
    case_team = case.case_team
    case_department = case.case_department

    if request.method == 'POST':
        if request.POST.get('action') == 'draft':
            case.is_submited = False
        elif request.POST.get('action') == 'submit':
            case.is_submited = True
        elif request.POST.get('action') == 'cancel':
            case.status = 'Cancelled'
            case.save()
            messages.info(request, f"Case [{case.id}] {case.status}")
            return {}

    case_form =  CaseForm.create_case_form(app_id, request.user ,prefix='case_form')
    for sd in section_datas:
        section_formsets_data = {}
        form_data = None
        DynamicFormSection = create_dynamic_form_section (sd.form_section.json_template, sd.form_section.id, sd.section_data)
        if request.method == 'POST':
            case_form = CaseForm.create_case_form(app_id, request.user,request.POST, request.FILES, prefix='case_form')
            if not case_form.is_valid():
                case_form_is_valid = False
            else:
                case_team = case_form.cleaned_data.get('case_team', None)
                case_department = case_form.cleaned_data.get('case_department', None)

            section_form = DynamicFormSection(request.POST, request.FILES, prefix=f'form_section_id_{sd.form_section.id}')
            if section_form.is_valid():
                # Process the files
                section_form = process_form_files(request, section_form, sd.form_section.id)
                form_data =  section_form.cleaned_data
            else:
                section_forms_is_valid = False
            for field_name in DynamicFormSection.nested_formset_fields:
                DynamicFormSectionFormSet = create_dynamic_form_section_formset(DynamicFormSection.nested_formset_fields[field_name]['fields'])
                nested_formset = DynamicFormSectionFormSet(request.POST, request.FILES, prefix=field_name)
                field_data = []
                if not nested_formset.is_valid():
                    section_formsets_valid = False
                else:
                    for formset in nested_formset:
                        if formset.cleaned_data and not formset.cleaned_data.get('DELETE', False):
                            formset = process_formset_files(request, formset, field_name)
                            logger.debug(formset)
                            field_data.append(formset.cleaned_data)
                    if len(field_data) > 0:
                        section_formsets_data[field_name] = field_data
                    elif DynamicFormSection.nested_formset_fields[field_name]['required']:
                        section_formsets_valid = False
                section_form.nested_formsets[field_name] = nested_formset
            if form_data is not None:                 
                for a in section_formsets_data:
                    form_data[a] = section_formsets_data[a]
                section_forms_data[str(sd.form_section.id)] = form_data
            section_forms.append(section_form)
        else:
            section_forms.append(DynamicFormSection)

    if request.method == 'POST' and section_forms_is_valid and section_formsets_valid and case_form_is_valid:                  
        case.updated_by = request.user    
        if (case_team is not None):
            case.case_team = case_team
            team = Team.objects.get(pk=case_team)
            case_department = team.department
        case.case_department = case_department
        case.save()
        try:
            for section in section_datas:
                section_data = json.dumps(section_forms_data.get(str(section.form_section.id)), cls=CustomJSONEncoder) 
                section.section_data = json.loads(section_data)
                section.save()
        except Exception as e:
            logger.error(e)
            messages.error(request, f"System error")
            return {'form': form, 'section_forms': section_forms, 'case_form': case_form, 'error': e}
        messages.info(request, f"Case [{case.id}] {case.status}")
        return {}
    return  {'form': form, 'section_forms': section_forms, 'case_form': case_form}


def get_case_audit_history(case_instance):
    case_class = case_instance.form.get_model_class()
    history_changes = get_audit_history_by_instance(case_instance, 'Case', case_class)
    case_data_ids = case_instance.case_data_case.all().values('id')
    case_data_class = case_instance.form.get_section_model_class()
    case_data_history = get_audit_history(case_data_class.history.filter(id__in=case_data_ids), 'Data', case_data_class)
    history_changes.extend(case_data_history)
    task_instance_ids = case_instance.task_instances.all()
    task_instance_history = get_audit_history(TaskInstance.history.filter(id__in=task_instance_ids), 'Task', TaskInstance)
    history_changes.extend(task_instance_history)
    return history_changes

# def process_formset_files(request, formset, form_field: str):
#     for i in range(len(formset)):
#         form = formset[i]
#         for field_name, field in form.fields.items():
#             if isinstance(field, forms.FileField) or isinstance(field, MultipleFileField):
#                 input_name = f'{form_field}-{i}-{field_name}'
#                 uploaded_files = request.FILES.getlist(input_name)
#                 file_list = handle_uploaded_file(request,uploaded_files)
#                 formset.cleaned_data[i][field_name] = file_list
#     logger.debug(formset)
#     return formset

def process_formset_files(request, formset, form_field: str):
    i=0
    for field_name, field in formset.fields.items():
        logger.debug(f'{field_name}--{field}')
        if isinstance(field, forms.FileField) or isinstance(field, MultipleFileField):
            input_name = f'{form_field}-{i}-{field_name}'
            uploaded_files = request.FILES.getlist(input_name)
            file_list = handle_uploaded_file(request,uploaded_files)
            formset.cleaned_data[field_name] = file_list
            i=i+1
    return formset

def process_form_files(request, form, form_section_id):
    for field_name, field in form.fields.items():
        if isinstance(field, forms.FileField) or isinstance(field, MultipleFileField):
            input_name = f'form_section_id_{form_section_id}-{field_name}'
            uploaded_files = request.FILES.getlist(input_name)
            file_list = handle_uploaded_file(request,uploaded_files)
            form.cleaned_data[field_name] = file_list
    return form
