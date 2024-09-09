from userManagement.models import Company, Department, Team, CustomUser, AppMenu
from jsonForm.models import FormTemplate
from .models import DictionaryItemModel, FileModel
from .redis import get_redis_data_json, create_redis_key_queryset
from django.utils.text import get_valid_filename
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db import models
import logging
logger = logging.getLogger('django')

def get_select_choices(key):
    data = get_dictionary(key)
    if key in ['department_list_active', 'department_list', 'team_list_active', 'team_list', 'company_list_active', 'company_list']:
        result = [(i.get('full_name'), i.get('full_name')) for i in data]
    elif  key in ['user_list_active','user_list']:
        result = [('%s %s (%s)'%(i.get('first_name'),i.get('last_name'), i.get('username')), '%s %s (%s)'%(i.get('first_name'),i.get('last_name'), i.get('username'))) for i in data]
    else:
        result = [(i.get('value'), i.get('value')) for i in data]
    return result

def get_select_choices_ids(key):
    data = get_dictionary(key)
    if key in ['department_list_active', 'department_list', 'team_list_active', 'team_list', 'company_list_active', 'company_list']:
        result = [(i.get('id'), i.get('full_name')) for i in data]
    elif  key in ['user_list_active','user_list']:
        result = [(i.get('id'), '%s %s (%s)'%(i.get('first_name'),i.get('last_name'), i.get('username'))) for i in data]
    else:
        result = [(i.get('id'), i.get('value')) for i in data]
    return result

def get_dictionary(key):
    data = get_redis_data_json(key)
    if data is None:
        if key == 'department_list_active':
            data = Department.objects.filter(is_active=True)
        elif key == 'department_list':
            data = Department.objects.all()
        elif key == 'team_list_active':
            data = Team.objects.filter(is_active=True)
        elif key == 'team_list':
            data = Team.objects.all()
        elif key == 'company_list_active':
            data = Company.objects.filter(is_active=True)
        elif key == 'company_list':
            data = Company.objects.all()
        elif key == 'user_list_active':
            data = CustomUser.objects.filter(is_active=True)
        elif key == 'user_list':
            data = CustomUser.objects.all()
        elif key.startswith('dict_') :
            if key.endswith('_active'):
                data = DictionaryItemModel.objects.filter(is_active=True, dictionary=key.replace('dict_', '').replace('_active', ''))
            else:
                data = DictionaryItemModel.objects.filter(dictionary=key.replace('dict_', ''))
        # data = json.dumps(list(data.values()))
        create_redis_key_queryset(key, data)
        return get_redis_data_json(key)
    return data

def handle_uploaded_file(request, file):
    try:
        if isinstance(file, list):
            file_list = []
            for f in file:
                safe_filename = get_valid_filename(f.name)
                file_instance = FileModel.objects.create(name=safe_filename, file=f)
                file_list.append(file_instance.pk)
            if len(file_list) == 1:
                return file_list[0]
            else:
                return file_list
        else:
            safe_filename = get_valid_filename(file.name)
            file_instance = FileModel.objects.create(name=safe_filename, file=file)
            return file_instance.pk
    except Exception as e:
        logger.error(e)
        messages.error(request, ('Not able to save file!'))

def get_file_by_pk(pk):
    return FileModel.objects.get(pk=pk)

def get_audit_history_fields():
    return {
        'object': 'Object',
        'change_time': 'Changed Time',
        'change_type': 'Changed Type',
        'change_by': 'Changed By',
        'changes': 'Changes'
    }

def get_audit_history(history, type:str, class_name=None):
# prepare data map for the FK fields, get data from redis
# can add more data into redis for mapping
    data_map = {}
    if class_name is not None:
        for field in class_name._meta.get_fields():
            if isinstance(field, models.ForeignKey):
                redis_key = ''
                if field.related_model == Department:
                    redis_key = 'department_list'
                if field.related_model == Company:
                    redis_key = 'department_list'
                if field.related_model == Team:
                    redis_key = 'department_list'
                if field.related_model == CustomUser:
                    redis_key = 'user_list'
                if redis_key != '':
                    values = get_redis_data_json(redis_key)
                    if values is not None:
                        for v in values:
                            if v.get('id', None) is not None:
                                if v.get('name', None) is not None:
                                    data_map[field.name] = {v.get('id', None): v.get('name', None)}
                                elif v.get('full_name', None) is not None:
                                    data_map[field.name] = {v.get('id', None): v.get('full_name', None)}
                                elif v.get('username', None) is not None:
                                    data_map[field.name] = {v.get('id', None): v.get('username', None)}
                                elif v.get('code', None) is not None:
                                    data_map[field.name] = {v.get('id', None): v.get('code', None)}
                                elif v.get('key', None) is not None:
                                    data_map[field.name] = {v.get('id', None): v.get('key', None)}
    model_fields = set()
    history_changes = []
    if data_map is not None:
        model_fields=data_map.keys()
#   start to process the audit data
    for record in history:
        # Determine the type of change
        if record.history_type == '+':
            change_type = 'Created'
        elif record.history_type == '-':
            change_type = 'Deleted'
        elif record.history_type == '~':
            change_type = 'Changed'
        else:
            change_type = 'Unknown'
        changes = ''
        if record.prev_record:
            delta = record.diff_against(record.prev_record)
            for change in delta.changes:
                if data_map is not None and change.field in model_fields:
                    change_old = data_map[change.field].get(str(change.old), 'None')
                    change_new = data_map[change.field].get(str(change.new), 'None')
                else:
                    change_old = change.old
                    change_new = change.new
                changes = changes + f"<strong>[{change.field}]</strong>:{change_old} → {change_new} <br/>"
        if changes != '' or change_type != 'Changed':
            history_changes.append({
                'change_type': change_type,
                'object': f'{type}-{record.id}',
                'changes': changes,
                'change_by': record.history_user.username,
                'change_time': record.history_date
            })
    return history_changes


def get_audit_history_by_instance(instance, type:str, class_name=None):
    history = instance.history.all()
    history_changes = get_audit_history(history, type)
    return history_changes

def set_context_base(request, app_name, form_code=None, case_id=None):
    context = {}
    mini_app = AppMenu.objects.filter(key=app_name, menu_level=0)
    if mini_app is None or mini_app.count() != 1:
        messages.warning(request, "Application is not found")
        return redirect('app:home')
    else:
        mini_app = mini_app.first()
    context['mini_app'] = mini_app
    menu = next((m for m in request.menu if m.get('key', '') == app_name), None)
    context['menu'] = menu
    if form_code is not None:
        form = FormTemplate.objects.get(code=form_code, application__key=app_name)
        if form is None:
            messages.warning(request, "Form Template is not found")
            return redirect('app:app_home', app_name)
        context['form'] = form
        if case_id is not None:
            model_class = form.get_model_class()
            case_instance = model_class.objects.get(pk=case_id)
            context['case_instance'] = case_instance
            if case_instance is None:
                messages.warning(request, "Case is not found")
                return redirect('app:app_home', app_name)
    return context
