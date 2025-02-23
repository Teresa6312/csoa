from django.http import HttpResponse
import mimetypes
from .models import FileModel
from django import forms
from base.forms import MultipleFileField
from django.utils.text import get_valid_filename
from django.contrib import messages
from .util import get_object_or_redirect
import datetime
from django.core.files.base import ContentFile
import copy
import logging
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.conf import settings
import os
import uuid

from django.core.files import File

logger = logging.getLogger('django')


def handle_temp_file(file):
    """
    Generates a temporary file path and writes the file's content to it.
    """
    temp_upload_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    if not os.path.exists(temp_upload_dir):
        os.makedirs(temp_upload_dir)

    safe_filename = get_valid_filename(file.name)
    temp_path = os.path.join(temp_upload_dir, safe_filename)

    with open(temp_path, 'wb+') as destination:  # Open in binary write mode
        for chunk in file.chunks():  # Write file in chunks
            destination.write(chunk)
    return {'name': safe_filename, 'path': temp_path, 'original_name': file.name}

# def handle_uploaded_file(request, file, format='json'):
#     app_name = request.level_1_menu.get('key', '') if hasattr(request, 'level_1_menu') else ''
#     if app_name == '':
#         app_name = request.path.split("/")[1]
#     if app_name == '':
#         app_name = 'others'
#     now = datetime.datetime.now()
#     file_path = "%s/%s/%s"%(app_name, now.year, now.month)
#     if isinstance(file, list):
#         file_list = []
#         for f in file:
#             file_instance = handle_single_file(request, f, file_path, format)
#             file_list.append(file_instance)
#     else:
#         file_instance = handle_single_file(request, f, file_path, format)
#         file_list = [file_instance]
#     return file_list


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

def handle_single_file(request, file, file_path, format='json'):
    file_instance = None
    if isinstance(file, dict):
        """
        Saves a file from a given path to FileModel, storing it in a different location.
        Args:
            file: A dictionary containing path.
            request: The Django request object.
            file_path: The path where you want to save the new file.
        """
        try:
            with open(file['file_path'], 'rb') as file_obj:
                new_file_content = b""  # Initialize an empty bytes object
                for chunk in file_obj.chunks():  # Iterate over file chunks
                    new_file_content += chunk  # Append each chunk to the new content
                new_file = ContentFile(new_file_content, name="%s/%s"%(file_path, file['name']))
                # Create FileModel instance
                file_instance = FileModel.objects.create(
                    name=file['name'],
                    file=new_file,
                    created_by=request.user.username,
                )
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file['original_name']}")
            log.error(f"File not found: {file['path']}")
        except Exception as e:
            raise Exception(f"An error occurred: {e}")
            log.error(f"An error occurred: {e}")
    elif isinstance(file, (InMemoryUploadedFile, TemporaryUploadedFile)):
        new_file_content = b""  # Initialize an empty bytes object
        for chunk in file.chunks():  # Iterate over file chunks
            new_file_content += chunk  # Append each chunk to the new content
        # Create a new ContentFile with the modified content    
        new_file = ContentFile(new_file_content, name="%s/%s"%(file_path, file.name))
        safe_filename = get_valid_filename(file.name)
        file_instance = FileModel.objects.create(name=safe_filename, file=new_file, created_by = request.user.username)
    else:
        raise ValueError("Invalid file type provided.")
        log.error(f"Invalid file type provided.: {type(file)}")
    if format=='json' and file_instance is not None:
        return {'id': str(file_instance.pk), 'name': file.name}
    else:
        return file_instance

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
    previous_files = request.session.get('uploaded_files') if hasattr(request.session, 'uploaded_files')  else None
    for field_name, field in form.fields.items():
        if isinstance(field, forms.FileField) or isinstance(field, MultipleFileField):
            input_name = f'{form.prefix}-{field_name}' if form.prefix is not None else field_name
            clear_files = request.POST.get(f'{input_name}-clear')
            old_files = field.initial if previous_files is None else previous_files.get(field_name)
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