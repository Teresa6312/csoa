from django.db import models
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError
from django.apps import apps
from .cache import global_class_cache_decorator
from .util import get_object_or_redirect
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
        return selected_info

    @classmethod
    def selected_fields_info(cls):
        return {
            field.name: field.verbose_name for field in cls._meta.fields
        }
    
    @classmethod
    def has_file_field(cls):
        return False
class DictionaryModel(BaseAuditModel):
    code = models.CharField(max_length=63, primary_key=True, validators=[validate_dictionary_code,get_validator('no_space_str_w_-')])
    description = models.CharField(unique=True, max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '%s (%s)'%(self.code, self.description)
    
    @global_class_cache_decorator(cache_key='dictionary', timeout=1800)
    def get_dictionary_items_by_code(cls, code):
        instance = get_object_or_redirect(cls, code=code)
        if instance is None:
            return []
        else:
            return instance.dictionary_item_dictionary.all()
        
    @global_class_cache_decorator(cache_key='dictionary_active', timeout=1800)
    def get_dictionary_active_items_by_code(cls, code):
        instance = get_object_or_redirect(cls, code=code, is_active=True)
        if instance is None:
            return []
        else:
            return instance.dictionary_item_dictionary.filter(is_active=True)

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
    created_by = models.CharField(default='System', max_length=150)
    
    def __str__(self):
        return self.name

    @classmethod
    def selected_fields_info(cls):
        fields = ['id', 'name', 'created_at', 'created_by']  # List of fields you want to include
        field_info = FileModel.get_selected_fields_info(fields)
        return field_info
    