from django.contrib import admin
from .models import FormSection, FormTemplate, Workflow, Task, DecisionPoint, WorkflowInstance, TaskInstance, Case, CaseData
from base.admin import BaseAuditAdmin, default_readonly_fields
from userManagement.models import AppMenu
from .forms import FormTemplateForm, FormSectionInlineFormSet, TaskForm, TaskInlineFormSet


class FormSectionInline(admin.StackedInline):
	model = FormSection
	# form = FormSectionForm  # Use the custom form
	formset = FormSectionInlineFormSet  # Attach the custom formset
	can_delete = False
	extra = 1
	verbose_name_plural = 'Sections'

class FormTemplateAdmin(BaseAuditAdmin):
	inlines = (FormSectionInline, )
	form = FormTemplateForm

	list_display = ['code', 'name', 'description','owner_company', 'owner_department', 'owner_team', 'application', 'process_department', 'process_team', 'is_active']
	list_filter = ['owner_company', 'owner_department', 'owner_team', 'application', 'process_department', 'process_team', 'is_active']
	search_fields = ['code', 'name', 'description']

	# class Media:
	# 	js = ('django_jsonform/django-jsonform.js',)
	# 	css = {'all': ('django_jsonform/django-jsonform.css',)}
admin.site.register(FormTemplate, FormTemplateAdmin)

class FormSectionAdmin(BaseAuditAdmin):
	# form = FormSectionForm
	readonly_fields_for_update = ('json_template', 'version', 'template', 'is_publish', 'index')

	list_display = ['index', 'name', 'description','version', 'template', 'is_active', 'is_publish']
	list_filter = ['is_publish', 'is_active']
	search_fields = ['name', 'description', 'json_template']


	def get_readonly_fields(self, request, obj=None):
		if obj:  # This is the case when editing an existing object
			if obj.is_publish:
				return self.readonly_fields + default_readonly_fields + self.readonly_fields_for_update
			else:
				return self.readonly_fields + default_readonly_fields
		else:  # This is the case when adding a new object
			return self.readonly_fields + default_readonly_fields

admin.site.register(FormSection, FormSectionAdmin)


class TaskInline(admin.StackedInline):
	model = Task
	form = TaskForm
	formset = TaskInlineFormSet
	can_delete = False
	extra = 1
	verbose_name_plural = 'Tasks'
	
class WorkflowAdmin(BaseAuditAdmin):
	inlines = (TaskInline, )
	search_fields = ['id', 'name', 'description']
	list_display = [ 'name', 'description', 'is_active']
	list_filter = ['is_active']
admin.site.register(Workflow, WorkflowAdmin)

class DecisionPointInline(admin.StackedInline):
	model = DecisionPoint
	can_delete = False
	extra = 1
	verbose_name_plural = 'Decision Points'
	fk_name='task'
	
class TaskAdmin(BaseAuditAdmin):
	search_fields = ['id', 'name', 'description']
	list_display = [ 'name','workflow', 'description']
	list_filter = ['workflow']
	form = TaskForm
	inlines = (DecisionPointInline, )

admin.site.register(Task, TaskAdmin)

class CaseDataInline(admin.StackedInline):
    model = CaseData
    can_delete = False
    extra = 1
    verbose_name_plural = 'Case Data'

class CaseAdmin(BaseAuditAdmin):
	inlines = (CaseDataInline, )
	list_display = ['id', 'form', 'status', 'is_submited','created_by', 'created_at']
	list_filter = ['status', 'is_submited']
admin.site.register(Case, CaseAdmin)

class CaseDataAdmin(BaseAuditAdmin):
	list_display = ['id', 'case','form_section']
admin.site.register(CaseData, CaseDataAdmin)

class TaskInstanceAdmin(BaseAuditAdmin):
	def case_id(self, obj):
		case = obj.case_task_instances.first()
		return case.id
	search_fields = ['id', 'comment']
	list_filter = ['decision_point', 'task']
	list_display = ['id', 'workflow_instance', 'task', 'assign_to','assign_to_user', 'decision_point', 'comment', 'updated_at','is_active']
	ordering = ['-updated_at']
	list_per_page = 20  # Number of records to display per page
admin.site.register(TaskInstance, TaskInstanceAdmin)

class WorkflowInstanceAdmin(BaseAuditAdmin):
    list_display = ['id', 'workflow', 'is_active']
admin.site.register(WorkflowInstance, WorkflowInstanceAdmin)


# from .models import  CaseData
# from .forms import CaseDataForm
# class CaseDataAdmin(BaseAuditAdmin):
# 	form = CaseDataForm
# 	list_display = ['id', 'case','form_section']
# 	class Media:
# 		js = ('django_jsonform/django-jsonform.js',)
# 		css = {'all': ('django_jsonform/django-jsonform.css',)}
# admin.site.register(CaseData, CaseDataAdmin)

