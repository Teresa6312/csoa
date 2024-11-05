from django.http import HttpResponse
import mimetypes
from .models import FileModel
from django import forms
from base.forms import MultipleFileField
from django.utils.text import get_valid_filename
from django.contrib import messages
from .util import get_object_or_redirect

import logging
logger = logging.getLogger('django')

def handle_uploaded_file(request, file, format='json'):
    if isinstance(file, list):
        file_list = []
        for f in file:
            safe_filename = get_valid_filename(f.name)
            file_instance = FileModel.objects.create(name=safe_filename, file=f, created_by = request.user.username)
            file_list.append(file_instance)
    else:
        safe_filename = get_valid_filename(file.name)
        file_instance = FileModel.objects.create(name=safe_filename, file=file)
        file_list = [file_instance]
    if format=='json':
        return [ {'id': str(f.pk), 'name': f.name} for f in file_list]
    else:
        return file_list

def get_file_by_pk(pk):
    instanct = get_object_or_redirect(FileModel, pk=pk)
    if instanct is not None:
        return instanct.file
    else:
        return None

def download_file_by_id(request, file_id):
    file_instance = get_object_or_redirect(FileModel, id=file_id)
    return download_file(request, file_instance)

def download_file(request, file_instance):
    file_path = file_instance.file.path
    file_name = file_instance.name
    # Detect the content type of the file
    content_type, _ = mimetypes.guess_type(file_path)
    # Serve the file as an HTTP response
    response = HttpResponse(open(file_path, 'rb').read(), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    return response

    
def process_formset_files(request, formset):
    for field_name, field in formset.fields.items():
        if isinstance(field, forms.FileField) or isinstance(field, MultipleFileField):
            input_name = f'{formset.prefix}-{field_name}' if formset.prefix is not None else field_name
            clear_files = request.POST.get(f'{input_name}-clear')
            old_files = field.initial
            uploaded_files = request.FILES.getlist(input_name)
            # handle any file uploaded
            if uploaded_files is not None and len(uploaded_files)>0:
                file_list = handle_uploaded_file(request,uploaded_files)
            # handle new form or existed form with file field clear
            elif old_files is None or ( clear_files is not None and clear_files == 'on' ):
                file_list = None
            # handle existed form with existed data
            else:
                file_list = old_files
            formset.cleaned_data[field_name] = file_list
    return formset

def process_form_files(request, form):
    for field_name, field in form.fields.items():
        if isinstance(field, forms.FileField) or isinstance(field, MultipleFileField):
            input_name = f'{form.prefix}-{field_name}' if form.prefix is not None else field_name
            clear_files = request.POST.get(f'{input_name}-clear')
            old_files = field.initial
            uploaded_files = request.FILES.getlist(input_name)
            # handle  any file uploaded
            if uploaded_files is not None and len(uploaded_files)>0:
                file_list = handle_uploaded_file(request,uploaded_files)
            # handle new form or existed form with file field clear
            elif old_files is None or ( clear_files is not None and clear_files == 'on' ):
                file_list = None
            # handle existed form with existed data
            else:
                file_list = old_files
            form.cleaned_data[field_name] = file_list
    return form