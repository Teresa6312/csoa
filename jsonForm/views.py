from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView
from .models import FormTemplate, Workflow, Task
from .forms import create_dynamic_form_section, create_dynamic_form_section_formset, CaseForm
import json
from base.util import CustomJSONEncoder
from django.http import JsonResponse
from base.redis import get_redis_data_json, create_redis_key
from .util import create_case_view, edit_case_data_view
class JsonFormListView(TemplateView):
    template_name = 'jsonForm/form_list.html'
    def get(self, request):
        forms=FormTemplate.objects.filter(
            is_active = True
            )
        return render(request, self.template_name, {'title': 'Case Forms', 'forms': forms})
    
def form_create_case_view(request, form_id):
    template_name = 'jsonForm/form.html'
    form = get_object_or_404(FormTemplate, id=form_id)
    case_form =  CaseForm()
    case_form.fields['created_by'].initial = request.user
    case_form.fields['case_team'].initial = request.user.team.first()
    context = create_case_view(request, form)
    return render(request, template_name, context)

def form_edit_case_data_view(request, case_id, form_id):
    template_name = 'jsonForm/form.html'
    form = get_object_or_404(FormTemplate, id=form_id)
    case = get_object_or_404(form.get_model_class(), id=case_id, form = form, is_submited=True)
    context = edit_case_data_view(request, case, form)
    return render(request, template_name, context)

def workflow_data(request, workflow_id):
    try:
        workflow = Workflow.objects.get(id=workflow_id)
    except Workflow.DoesNotExist:
        return JsonResponse({'message_type': 'error', 'message': 'Workflow does not exist'})
    data = get_redis_data_json(f'workflow:{workflow.id}')
    if data is None:
        data = workflow.get_workflow_data()
        create_redis_key(f'workflow:{workflow.id}', json.dumps(data))
    return JsonResponse(data)

def workflow_view(request, workflow_id):
    return render(request, 'jsonForm/workflow.html', {'workflow_id': workflow_id})