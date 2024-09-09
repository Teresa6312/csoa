from django import forms
import json
from django.forms import formset_factory
from base.util_model import get_select_choices
from base.util import convert_date_format
from base.util_model import get_file_by_pk
from base.validators import get_validator
from base.forms import MultipleFileField
from userManagement.models import CustomUser, Team, AppMenu, Permission, Department
from .models import FormTemplate, Workflow, Task, TaskInstance, DecisionPoint, Case
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.db.models import Q
from base.util_model import handle_uploaded_file
class CaseForm(forms.Form):
	created_by = forms.ModelChoiceField(queryset=CustomUser.objects.filter(is_active=True), required=True, label='Initial By')
	case_team = forms.ModelChoiceField(queryset=Team.objects.filter(is_active=True),  required=False, label='Initial By Team')
	case_department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True),  required=False, label='Initial By Department')

	def create_case_form(app_id,user,*args, **kwargs):
		case_form =  CaseForm(*args, **kwargs)
		if app_id is not None and not hasattr(case_form, 'cleaned_data'):
			app = AppMenu.objects.get(id=app_id)
			if app.control_type=='team':
				case_form.fields['case_department'].widget=forms.HiddenInput()
				case_form.fields['case_team'].queryset = Team.objects.filter(Q(permission_team__app = app_id) | Q(user_team__id =user.id)).distinct()
				case_form.fields['case_team'].initial = user.team.first()
				case_form.fields['case_team'].required = True
			else:
				case_form.fields['case_team'].widget=forms.HiddenInput()
				case_form.fields['case_department'].queryset = Department.objects.filter(Q(permission_department__app = app_id) | Q(user_department__id=user.id)).distinct()
				case_form.fields['case_department'].initial = user.department
				case_form.fields['case_department'].required = True
			case_form.fields['created_by'].queryset =  CustomUser.objects.filter(Q(permissions__app = app_id) | Q(id=user.id)).distinct()
			case_form.fields['created_by'].initial = user
		return case_form

def create_dynamic_form_section(json_str, form_section_id=None, instance=None):
	if isinstance(json_str, str):
		field_definitions = json.loads(json_str)
	else:
		field_definitions = json_str
	if isinstance(instance, str):
		instance = json.loads(instance)
	class DynamicFormSection(forms.Form):
		nested_formsets = {}
		nested_formset_fields = {}
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			
			if form_section_id is not None:
				self.fields['form_section_id'] = forms.IntegerField(
					initial=form_section_id,
					widget=forms.HiddenInput()
				)
				self.prefix = f'form_section_id_{form_section_id}'
			for field_name, field_props in field_definitions.items():
				field_type = field_props.get('input')
				field_label = field_props.get('label', field_name)
				field_length = field_props.get('length', None)
				field_required = field_props.get('required', False)
				field_placeholder = field_props.get('placeholder', '')
				field_default = field_props.get('default', None)
				field_hidden = field_props.get('hidden', False)
				field_max_digits = field_props.get('max_digits', 10)
				field_decimal_places = field_props.get('decimal_places', 2)
				field_choices = field_props.get('choices', [])
				field_validator = field_props.get('validator', None)
				field_helptext = field_props.get('helptext', None)
				validators = []
				if field_validator:
					validator = get_validator(field_validator)
					if validator is not None:
						validators.append(validator)
				if isinstance(field_choices, str):
					field_choices = get_select_choices(field_choices)
				elif isinstance(field_choices, list):
					new_field_choices = []
					for f in field_choices:
						new_field_choices.append((f,f))
					field_choices = new_field_choices
				else:
					field_choices = []
				if field_type == 'string':
					if field_length < 200:
						self.fields[field_name] = forms.CharField(
							label=field_label,
							max_length=field_length,
							help_text=field_helptext,
							required=field_required,
							initial=field_default,
							validators=validators,
							widget=forms.TextInput(attrs={'placeholder': field_placeholder})
						)
					else:
						self.fields[field_name] = forms.CharField(
							label=field_label,
							max_length=field_length,
							help_text=field_helptext,
							required=field_required,
							initial=field_default,
							validators=validators,
							widget=forms.Textarea(attrs={'placeholder': field_placeholder})
						)
				elif field_type == 'select':
					self.fields[field_name] = forms.ChoiceField(
						label=field_label,
						required=field_required,
						help_text=field_helptext,
						choices=field_choices,
						validators=validators,
						initial=field_default
					)
				elif field_type == 'select_multiple':
					self.fields[field_name] = forms.MultipleChoiceField(
						label=field_label,
						required=field_required,
						help_text=field_helptext,
						choices=field_choices,
						validators=validators,
						initial=field_default
					)
				elif field_type == 'integer':
					self.fields[field_name] = forms.IntegerField(
						label=field_label,
						required=field_required,
						help_text=field_helptext,
						initial=field_default,
						validators=validators,
						widget=forms.NumberInput(attrs={'placeholder': field_placeholder})
					)
				elif field_type == 'decimal':
					self.fields[field_name] = forms.DecimalField(
						label=field_label,
						required=field_required,
						help_text=field_helptext,
						initial=field_default,
						max_digits=field_max_digits,
						decimal_places=field_decimal_places,
						validators=validators,
						widget=forms.NumberInput(attrs={'placeholder': field_placeholder, 'step': '0.01'})
					)
				elif field_type == 'date':
					self.fields[field_name] = forms.DateField(
						label=field_label,
						required=field_required,
						help_text=field_helptext,
						initial=convert_date_format(field_props.get('default', '')),
						validators=validators,
						widget=forms.DateInput(attrs={'placeholder': field_placeholder, 'type': 'date'}) #
					)
				elif field_type == 'list':
					nested_formset_class = create_dynamic_form_section_formset(field_props['fields'], field_required)
					self.nested_formsets[field_name] = nested_formset_class(prefix=field_name)
					self.nested_formset_fields[field_name] = {
						'fields': field_props['fields'],
						'label' : field_label,
						'required': field_required
					}
				elif field_type == 'file':
					# still not able to handle if user select multiple files and save form as draft, when user eidt the case, the files data are not able to display if there is more than one files
					if field_props.get('multiple', False):
						self.fields[field_name] = MultipleFileField(
							label=field_label,
							help_text=field_helptext,
							required=field_required
						)
					else:
						self.fields[field_name] = forms.FileField(
							label=field_label,
							help_text=field_helptext,
							required=field_required
						)
				if field_hidden:
					self.fields[field_name].widget = forms.HiddenInput()

			for field_name, field in self.fields.items():
				if field.required:
					field.label = f"{field.label} *" if field.label else '*'
					
			# Populate initial data if instance is provided
			if instance:
				for field_name in self.fields:
					if field_name in instance.keys() and not field_name == 'form_section_id':
						if isinstance(self.fields[field_name], forms.DateField):
							self.fields[field_name].initial = convert_date_format(instance.get(field_name, None))
						elif isinstance(self.fields[field_name], MultipleFileField) or isinstance(self.fields[field_name], forms.FileField):
							files =  instance.get(field_name, None)
							if files is not None and isinstance(files, list):
								self.fields[field_name].initial = [get_file_by_pk(file).file for file in files if get_file_by_pk(file) is not None]
							elif files is not None and isinstance(files, str):
								self.fields[field_name].initial = get_file_by_pk(files).file  if get_file_by_pk(files) is not None else None
						else:
							self.fields[field_name].initial = instance.get(field_name, None)
				for formset_name, formset_class in self.nested_formsets.items():
					if formset_name in instance:
						initial_data = instance.get(formset_name, None)
						if initial_data is not None and not len(initial_data) == 0:
							nested_formset_class = create_dynamic_form_section_formset(self.nested_formset_fields[formset_name]['fields'], field_required)
							self.nested_formsets[formset_name] = nested_formset_class(prefix=formset_name, initial=initial_data)
	return DynamicFormSection

def create_dynamic_form_section_formset(fields, field_required=False, instance=None):
	DynamicFormSection = create_dynamic_form_section(fields, instance=instance)

	DynamicFormSectionFormSet = formset_factory(
		DynamicFormSection,
		# formset=DynamicFormSectionFormSet,
		extra=1 if field_required and instance is None else 0,
		can_delete=True
	)
	return DynamicFormSectionFormSet

class FormTemplateForm(forms.ModelForm):
	class Meta:
		model = FormTemplate
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		# Get the parent object ( instance)
		self.parent_instance = kwargs.pop('parent_instance', None)
		super().__init__(*args, **kwargs)
		queryset =  AppMenu.objects.filter(menu_level = 0)
		if self.instance and self.instance.pk and self.instance.application is not None:
			queryset = AppMenu.objects.filter(Q(menu_level = 0) | Q(pk=self.instance.application.pk))
		else:
			queryset =  AppMenu.objects.filter(menu_level = 0)
		self.fields['application'].queryset =  queryset

		if self.instance and self.instance.pk and self.instance.workflow is not None:
			queryset = Workflow.objects.filter(Q(is_active = True) | Q(pk=self.instance.workflow.pk))
		else:
			queryset =  Workflow.objects.filter(is_active=True)
		self.fields['workflow'].queryset =  queryset

	def save(self, commit=True):
		instance = super().save(commit=False)
		if instance.backend_app_label is None or instance.backend_app_model is None or instance.backend_app_section_model is None:
			instance.backend_app_label = 'jsonForm'
			instance.backend_app_model = 'Case'
			instance.backend_app_section_model = 'CaseData'

		new_link_app = False
		if instance.pk:
			old_instance = FormTemplate.objects.get(pk=instance.pk)
			if old_instance.application is None and instance.application is not None:
				new_link_app = True
		elif instance.application is not None:
			new_link_app = True

		if commit:
			instance.save()

		if new_link_app:
			search = AppMenu.objects.create(
					menu_level = 1,
					key = f'search{instance.code}',
					label = f'Search {instance.name}',
					link = f'/app/{instance.application.key}/cases/search/{instance.code}',
					parent_app_menu = instance.application,
					is_active = False
				)
			search.save()
			my_cases_menu = AppMenu.objects.filter(parent_app_menu=instance.application, key='my-cases').first()
			if my_cases_menu is not None: 
				new_form = AppMenu.objects.create(
						menu_level = 2,
						key = f'createCase{instance.code}',
						label = f'Create {instance.name}',
						icon = 'fa fa-plus',
						link =  f'/app/{instance.application.key}/forms/add/{instance.code}',
						parent_app_menu = my_cases_menu,
						is_active = False
					)
				new_form.save()
		return instance

class FormSectionInlineFormSet(BaseInlineFormSet):
	def clean(self):
		super().clean()
		# Collect all cleaned form data
		sections = []
		for form in self.forms:
			if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
				sections.append(form.cleaned_data)
		
		# Perform cross-validation between FormSection instances
		if len(sections) > 1:
			for i, section in enumerate(sections):
				if section.get('is_active', False) and section.get('is_publish', False):
					existed_keys = set(section.get('json_template', {}).keys())
					for other_section in sections[i+1:]:
						if other_section.get('is_active', False)  and section.get('is_publish', False):
							new_keys = set(other_section.get('json_template', {}).keys())
							common_keys = existed_keys.intersection(new_keys)
							# Ensure no two sections have the same input key name
							if len(common_keys) > 0 :
								raise ValidationError(
											f"Input key must be unique in Sections:{section.get('name')} and {other_section.get('name')}, Duplicated key found {common_keys}"
										)
							else:
								existed_keys = existed_keys.union(new_keys)

class TaskForm(forms.ModelForm):
	class Meta:
		model = Task
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['assign_to'].queryset =  Permission.objects.filter(role__isnull=False).order_by('app')

	def clean(self):
		super().clean()
		if self.is_valid and self.cleaned_data and not self.cleaned_data.get('DELETE', False):
			data = self.cleaned_data
			if len(data.get('assign_to', [])) == 0 and data.get('assign_to_role', None) is None:
				raise ValidationError(
							"Neither 'assign to' nor 'assign to role' field contains value"
						)
			if len(data.get('assign_to', [])) != 0 and data.get('assign_to_role', None) is not None:
				raise ValidationError(
							"Either 'assign to' or 'assign to role' field should contain value"
						)
			
class TaskInlineFormSet(BaseInlineFormSet):
	def clean(self):
		super().clean()
		# Collect all cleaned form data
		for form in self.forms:
			if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
				data = form.cleaned_data
				if len(data.get('assign_to', [])) == 0 and data.get('assign_to_role', None) is None:
					raise ValidationError(
								"Neither 'assign to' nor 'assign to role' field contains value"
							)
				if len(data.get('assign_to', [])) != 0 and data.get('assign_to_role', None) is not None:
					raise ValidationError(
								"Either 'assign to' or 'assign to role' field should contain value"
							)
				
class TaskInstanceForm(forms.ModelForm):
	task_str = forms.CharField(label='Task')
	assign_to_str = forms.CharField(label='Assign to')
	add_files= MultipleFileField( label='Files', required=False )
	class Meta:
		model = TaskInstance
		fields = ['task_str', 'assign_to_str', 'assign_to_user', 'decision_point', 'comment', 'add_files']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.instance.id:
			task = TaskInstance.objects.get(id = self.instance.id)
			self.fields['task_str'].initial = task.task
			assign_to = task.assign_to
			text = ''
			if assign_to.team is not None:
				text = f'{assign_to.team.full_name}'
			elif assign_to.department is not None:
				text = f'{assign_to.department.full_name}'
				# self.fields['assign_to_user'].queryset = CustomUser.objects.filter(department=assign_to.department, is_active=True)
			elif assign_to.company is not None:
				text = f'{assign_to.company.full_name}'
			text = f'{assign_to.role.name}({text})'
			self.fields['assign_to_str'].initial = text
			self.fields['task_str'].widget.attrs['readonly'] = True
			self.fields['assign_to_str'].widget.attrs['readonly'] = True
			self.fields['assign_to_user'].required = True
			self.fields['assign_to_user'].queryset = CustomUser.objects.filter(permissions=assign_to, is_active=True)
			self.fields['decision_point'].required = True
			self.fields['decision_point'].queryset = DecisionPoint.objects.filter(task=task.task)
	def save(self, commit=True):
		instance = super().save(commit=False)
		uploaded_files = self.cleaned_data.get('add_files')
		if uploaded_files:
			file_list = handle_uploaded_file(None,uploaded_files)
			for f in file_list:
				instance.files.add(f)
		instance.is_active = False
		return super().save(commit=commit)
