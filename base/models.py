from django.db import models
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError
from django.apps import apps
from .util import get_related_names_for_model
from .redis import get_redis_data_json, create_redis_key_json, delete_redis_key
from .validators import get_validator
import uuid

def validate_dictionary_code(value):
    if '_active' in value:
        raise ValidationError('The dictionary_code should not contains "_active".')
    
class BaseAuditModel(models.Model):
    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True

    @property
    def created_at(self):
        return self.history.last().history_date if self.history.exists() else None

    @property
    def created_by(self):
        return self.history.last().history_user if self.history.exists() else None

    @property
    def updated_at(self):
        return self.history.first().history_date if self.history.exists() else None

    @property
    def updated_by(self):
        return self.history.first().history_user if self.history.exists() else None
    
    @classmethod
    def get_selected_fields_info(cls, fields):
        selected_info = {}        
        for field in fields:
            # Handle normal fields and foreign key fields
            try:
                verbose_name = ''
                if '__' in field:  # Handle ForeignKey fields
                    field_parts = field.split('__')
                    related_model = None
                    for index in range(len(field_parts)):
                        related_field = cls._meta.get_field(field_parts[index]) if related_model is None else related_model._meta.get_field(field_parts[index])
                        if isinstance(related_field, models.ForeignKey):
                            related_model = related_field.related_model
                            verbose_name = verbose_name + ' ' + related_field.verbose_name
                        else:
                            verbose_name = verbose_name + ' ' +  related_field.name
                else:
                    verbose_name = cls._meta.get_field(field).verbose_name
                selected_info[field] = verbose_name.capitalize()
            except models.FieldDoesNotExist:
                pass
        return selected_info

    @classmethod
    def selected_fields_info(cls):
        return {
            field.name: field.verbose_name for field in cls._meta.fields
        }

class DualControlModel(BaseAuditModel):
    id = models.PositiveBigIntegerField(primary_key=True, editable=False)
    pending_record = models.ForeignKey('PendingRecordModel',blank=True, null=True, on_delete=models.PROTECT)
    class Meta:
        abstract = True
class DictionaryModel(BaseAuditModel):
    code = models.CharField(max_length=63, primary_key=True, validators=[validate_dictionary_code,get_validator('no_space_str_w_-')])
    description = models.CharField(unique=True, max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '%s (%s)'%(self.code, self.description)

class DictionaryItemModel(BaseAuditModel):
    dictionary = models.ForeignKey(DictionaryModel, on_delete=models.PROTECT, related_name='dictionary_item_dictionary')
    value = models.CharField(max_length=255)
    code = models.CharField(max_length=63, null=True, blank=True)
    category = models.CharField(max_length=63, null=True, blank=True)
    sub_category = models.ForeignKey(DictionaryModel, on_delete=models.PROTECT, related_name='dictionary_item_sub_category', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '%s - %s'%(self.dictionary, self.value)
    
    @classmethod
    def selected_fields_info(cls):
        fields = ['id', 'dictionary__code', 'dictionary__description', 'value', 'code', 'category', 'is_active']  # List of fields you want to include
        field_info = DictionaryItemModel.get_selected_fields_info(fields)
        return field_info
    
class FileModel(BaseAuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='documents/')
    name = models.CharField(max_length=127)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    
    def __str__(self):
        return self.name
    
class PendingRecordModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    backend_app_label = models.CharField(max_length=127, blank=True, null= True)
    backend_app_model = models.CharField(max_length=127, blank=True, null= True)
    model_pk = models.PositiveBigIntegerField()
    is_deleted = models.BooleanField(default=False)
    record = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

class ModelDictionaryConfigModel(BaseAuditModel):
    code = models.CharField(max_length=63, primary_key=True, validators=[get_validator('no_space_str_w_-')])
    description = models.CharField(max_length=511)
    backend_app_label = models.CharField(max_length=127)
    backend_app_model = models.CharField(max_length=127)
    model_label = models.CharField(max_length=255, default="model")
    pk_field_name = models.CharField(max_length=63, default='id', blank=True, null= True)
    fk_fields = models.JSONField(max_length=511, verbose_name="Are FK fields in the table or other table with one to one or many to one relationship", help_text='format [{"model": "model","field_name": "field_name","label": "label"}] ', blank=True, null= True) 
    fk_multi_fields = models.JSONField(max_length=511, verbose_name="As FK field in the table or other tables with one to many or manay to many relationship", help_text='format [{"model": "model","field_name": "field_name","label": "label"}]', blank=True, null= True)
    sub_tables = models.JSONField(max_length=511, verbose_name="related table to create, display, or modify", help_text='related table to create, display, or modify format [{"id_filter_name": "id_filter_name", "dictionary_code": "dictionary_code", "label": "label"}] ** id_filter_name should be the field name__id in the sub table model', blank=True, null= True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return "%s (%s.%s)"%(self.code, self.backend_app_label, self.backend_app_model)
    
    def create_model_instance(self, *args, **kwargs):
        if self.backend_app_label and self.backend_app_model:
            model_class = apps.get_model(self.backend_app_label, self.backend_app_model)
            if model_class:
                return model_class.objects.create(*args, **kwargs)
            else:
                raise ValueError(f"Model '{self.backend_app_label}' not found in app '{self.backend_app_model}'")
        else:
            raise ValueError(f"backend_app_label and backend_app_model is required")
    
    def get_model_class(self):
        if self.backend_app_label is not None and self.backend_app_model is not None :
            try:
                model_class = apps.get_model(self.backend_app_label, self.backend_app_model)
                return model_class
            except:
                raise ValueError(f"Not able to find mode {self.backend_app_label}.{self.backend_app_model}")
        else:
            raise ValueError(f"backend_app_label and backend_app_model is missing in Form")
    
    def get_model_class_instance_by_pk(self, pk):
        return self.get_model_class().objects.get(pk)

    def clean(self):
        self.get_model_class()
    
    def get_list_display(self):
        return ModelDictionaryItemsConfigModel.objects.filter(dictionary = self, list_display=True).values_list('backend_field_name', 'field_label').order_by('index')
    
    def get_add_fieldsets(self):
        return ModelDictionaryItemsConfigModel.objects.filter(dictionary = self, add_fieldsets=True).values_list('backend_field_name', 'field_label').order_by('index')
    
    def get_fieldsets(self):
        return ModelDictionaryItemsConfigModel.objects.filter(dictionary = self, fieldsets=True).values_list('backend_field_name', 'field_label').order_by('index')

    def get_edit_fieldsets(self):
        return ModelDictionaryItemsConfigModel.objects.filter(dictionary = self, edit_fieldsets=True).values_list('backend_field_name', 'field_label').order_by('index')

    def get_field_lists(self):
        return {
            'code': self.code,
            'model_label': self.model_label,
            'backend_app_label': self.backend_app_label,
            'backend_app_model': self.backend_app_model,
            'sub_tables': self.sub_tables,
            'pk_field_name': self.pk_field_name,
            'list_display': {f[0]: f[1] for f in self.get_list_display()},
            'add_fieldsets': {f[0]: f[1] for f in self.get_add_fieldsets()},
            'fieldsets': {f[0]: f[1] for f in self.get_fieldsets()},
            'edit_fieldsets': {f[0]: f[1] for f in self.get_edit_fieldsets()}
        }

    @classmethod
    def get_details(cls, code):
        data = get_redis_data_json(f"model_dict__{code}")
        if data is None:
            instance = ModelDictionaryConfigModel.objects.get(code=code)
            if instance is None or instance.is_active == False:
                delete_redis_key(f"model_dict__{code}")
                return None
            else: 
                create_redis_key_json(f"model_dict__{code}", instance.get_field_lists())
                data = get_redis_data_json(f"model_dict__{code}")
        return data

# for PK field, index should be always 0
class ModelDictionaryItemsConfigModel(BaseAuditModel):
    dictionary = models.ForeignKey(ModelDictionaryConfigModel, on_delete=models.PROTECT, related_name='dictionary_item_dictionary')
    backend_field_name = models.CharField(max_length=127)
    field_label = models.CharField(max_length=255)
    index = models.PositiveSmallIntegerField(verbose_name="index for field ordering")
    add_fieldsets = models.BooleanField(default=False, verbose_name="fields for create records")
    list_display = models.BooleanField(default=True, verbose_name="fields for display in list")
    fieldsets = models.BooleanField(default=True, verbose_name="fields for display in details")
    edit_fieldsets = models.BooleanField(default=False, verbose_name="fields for enable edit")
