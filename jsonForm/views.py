from django.shortcuts import render
from django.views.generic import TemplateView
from .models import FormTemplate, Workflow, Task
from .forms import CaseForm
from base.util import get_object_or_redirect
from .util import create_case_view, edit_case_data_view
import json
from base.util import CustomJSONEncoder


class JsonFormListView(TemplateView):
    template_name = "jsonForm/form_list.html"

    def get(self, request):
        forms = FormTemplate.objects.filter(is_active=True)
        return render(
            request, self.template_name, {"title": "Case Forms", "forms": forms}
        )


def form_create_case_view(request, form_id):
    template_name = "jsonForm/form.html"
    form = get_object_or_redirect(FormTemplate, id=form_id)
    case_form = CaseForm()
    case_form.fields["created_by"].initial = request.user
    case_form.fields["case_team"].initial = request.user.team.first()
    context = create_case_view(request, form)
    return render(request, template_name, context)


def form_template_view(request, form_id):
    template_name = "jsonForm/form.html"
    form = get_object_or_redirect(FormTemplate, id=form_id)
    case_form = CaseForm()
    case_form.fields["created_by"].initial = request.user
    case_form.fields["case_team"].initial = request.user.team.first()
    context = create_case_view(request, form)
    context["view"] = True
    form_template = form.form_section_form_template.all().values()
    form_template_data = json.dumps(list(form_template), cls=CustomJSONEncoder)
    context["form_template"] = json.loads(form_template_data)
    return render(request, template_name, context)


def form_edit_case_data_view(request, case_id, form_id):
    template_name = "jsonForm/form.html"
    form = get_object_or_redirect(FormTemplate, id=form_id)
    case = get_object_or_redirect(
        form.get_model_class(), id=case_id, form=form, is_submited=True
    )
    context = edit_case_data_view(request, case, form)
    return render(request, template_name, context)


def get_workflow_view(request, workflow_id):
    template_name = "jsonForm/workflow.html"
    workflow_data = workflow_data = Workflow.get_data_by_id(workflow_id)
    context = {}
    context["workflow_data"] = workflow_data
    context["datatables"] = False
    return render(request, template_name, context)
