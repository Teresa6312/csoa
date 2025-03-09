
from django.shortcuts import get_object_or_404, render
from .models import Case
from .forms import IdForm
from django.contrib import messages

def edit_case(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    case_data = case.case_data_case.all()
    if not case_data.exists():
        return render(request, 'case_data_list_edit.html', {
            'case': case,
            'case_data': [],
            'form': None,
        })

    fields = {'flag': '','id': 'ID'}
    template_fields = case_data.first().form_section.get_fields
    for key in template_fields.keys():
        fields["section_data__" + key] = template_fields.get(key)

    ids_list = [id.id for id in case_data]
    if request.method == 'POST':
        form = IdForm(ids_list, request.POST)
        if form.is_valid():
            case_data_ids = form.cleaned_data.get('ids')
            # case_data_ids = ast.literal_eval(case_data_ids)
            for cd in case_data:
                cd.flag = True if str(cd.id) in case_data_ids else False
                cd.save()
        else:
            messages.error(request, form.errors.as_text())
        case_data = case.case_data_case.all()
        queryset = list(case_data.values(*fields))
        return render(request, 'modelBase/case_data_list_edit.html', {
            'case_instance': case,
            'form': form,
            'fields': fields,
            'queryset': queryset,
        })
    else:
        queryset = list(case_data.values(*fields))
        form = IdForm(ids_list)
        return render(request, 'modelBase/case_data_list_edit.html', {
            'case_instance': case,
            'flag_form': form,
            'fields': fields,
            'queryset': queryset,
        })