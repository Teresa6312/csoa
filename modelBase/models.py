from django.db import models
from base.models import BaseAuditModel
from django.apps import apps
from base.validators import get_validator
from base.cache import global_class_cache_decorator
from base.util import get_object_or_redirect
from jsonForm.models import (
    CaseBaseModel,
    CaseDataBaseModel,
    WorkflowInstanceBaseModel,
    TaskInstanceBaseModel,
)
from base.constants import (
    TASK_TYPE_CHOICES,
    TASK_TYPE_AUTO,
    CASE_INITIATED,
    CASE_COMPLETED,
    CASE_CANCELLED,
)
import ast

import uuid


class PendingRecordModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    backend_app_label = models.CharField(max_length=127, blank=True, null=True)
    backend_app_model = models.CharField(max_length=127, blank=True, null=True)
    model_pk = models.PositiveBigIntegerField()
    is_deleted = models.BooleanField(default=False)
    record = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return "%s (%s.%s)" % (
            self.model_pk,
            self.backend_app_label,
            self.backend_app_model,
        )


class DualControlModel(BaseAuditModel):
    id = models.PositiveBigIntegerField(primary_key=True, editable=False)
    pending_record = models.ForeignKey(
        PendingRecordModel, blank=True, null=True, on_delete=models.PROTECT
    )

    class Meta:
        abstract = True


class ModelDictionaryConfigModel(BaseAuditModel):
    code = models.CharField(
        max_length=63, primary_key=True, validators=[get_validator("no_space_str_w_")]
    )
    description = models.CharField(max_length=511)
    backend_app_label = models.CharField(max_length=127)
    backend_app_model = models.CharField(max_length=127)
    model_label = models.CharField(max_length=255, default="model")
    pk_field_name = models.CharField(max_length=63, default="id", blank=True, null=True)
    default_order_by = models.CharField(
        max_length=255,
        default="['id']",
        verbose_name="a list of fields that used for ordering the records in list view",
        blank=True,
        null=True,
    )
    unique_keys = models.CharField(
        max_length=255,
        default="['id']",
        verbose_name="a list of fields that make the record unique",
        blank=True,
        null=True,
    )
    fk_fields = models.JSONField(
        max_length=511,
        verbose_name="Are FK fields in the table or other table with one to one or many to one relationship",
        help_text='format [{"model": "model","field_name": "field_name","label": "label"}] ',
        blank=True,
        null=True,
    )
    fk_multi_fields = models.JSONField(
        max_length=511,
        verbose_name="As FK field in the table or other tables with one to many or manay to many relationship",
        help_text='format [{"model": "model","field_name": "field_name","label": "label"}]',
        blank=True,
        null=True,
    )
    sub_tables = models.JSONField(
        max_length=511,
        verbose_name="related table to create, display, or modify",
        help_text='related table to create, display, or modify format [{"id_filter_name": "id_filter_name", "dictionary_code": "dictionary_code", "label": "label"}] ** id_filter_name should be the field name__id in the sub table model',
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return "%s (%s.%s)" % (
            self.code,
            self.backend_app_label,
            self.backend_app_model,
        )

    def create_model_instance(self, *args, **kwargs):
        if self.backend_app_label and self.backend_app_model:
            model_class = apps.get_model(self.backend_app_label, self.backend_app_model)
            if model_class:
                return model_class.objects.create(*args, **kwargs)
            else:
                raise ValueError(
                    f"Model '{self.backend_app_label}' not found in app '{self.backend_app_model}'"
                )
        else:
            raise ValueError(f"backend_app_label and backend_app_model is required")

    def get_model_class(self):
        if self.backend_app_label is not None and self.backend_app_model is not None:
            try:
                model_class = apps.get_model(
                    self.backend_app_label, self.backend_app_model
                )
                return model_class
            except:
                raise ValueError(
                    f"Not able to find mode {self.backend_app_label}.{self.backend_app_model}"
                )
        else:
            raise ValueError(
                f"backend_app_label and backend_app_model is missing in Form"
            )

    def get_model_class_instance_by_pk(self, pk):
        return self.get_model_class().objects.get(pk)

    def clean(self):
        self.get_model_class()

    def get_list_display(self):
        return (
            ModelDictionaryItemsConfigModel.objects.filter(
                dictionary=self, list_display=True
            )
            .values_list("backend_field_name", "field_label")
            .order_by("index")
        )

    def get_add_fieldsets(self):
        return (
            ModelDictionaryItemsConfigModel.objects.filter(
                dictionary=self, add_fieldsets=True
            )
            .values_list("backend_field_name", "field_label")
            .order_by("index")
        )

    def get_fieldsets(self):
        return (
            ModelDictionaryItemsConfigModel.objects.filter(
                dictionary=self, fieldsets=True
            )
            .values_list("backend_field_name", "field_label")
            .order_by("index")
        )

    def get_edit_fieldsets(self):
        return (
            ModelDictionaryItemsConfigModel.objects.filter(
                dictionary=self, edit_fieldsets=True
            )
            .values_list("backend_field_name", "field_label")
            .order_by("index")
        )

    def get_field_lists(self):
        return {
            "code": self.code,
            "model_label": self.model_label,
            "backend_app_label": self.backend_app_label,
            "backend_app_model": self.backend_app_model,
            "sub_tables": self.sub_tables,
            "pk_field_name": self.pk_field_name,
            "fk_fields": self.fk_fields,
            "unique_keys": (
                ast.literal_eval(self.unique_keys) if self.unique_keys else None
            ),
            "default_order_by": (
                ast.literal_eval(self.default_order_by)
                if self.default_order_by
                else None
            ),
            "fk_multi_fields": self.fk_multi_fields,
            "list_display": {f[0]: f[1] for f in self.get_list_display()},
            "add_fieldsets": {f[0]: f[1] for f in self.get_add_fieldsets()},
            "fieldsets": {f[0]: f[1] for f in self.get_fieldsets()},
            "edit_fieldsets": {f[0]: f[1] for f in self.get_edit_fieldsets()},
        }

    @global_class_cache_decorator(cache_key="model_dict")
    def get_details(cls, code):
        instance = get_object_or_redirect(cls, code=code)
        if instance is None:
            return None
        else:
            return instance.get_field_lists()


# for PK field, index should be always 0
class ModelDictionaryItemsConfigModel(BaseAuditModel):
    dictionary = models.ForeignKey(
        ModelDictionaryConfigModel,
        on_delete=models.PROTECT,
        related_name="dictionary_item_dictionary",
    )
    backend_field_name = models.CharField(max_length=127)
    field_label = models.CharField(max_length=255)
    index = models.PositiveSmallIntegerField(verbose_name="index for field ordering")
    add_fieldsets = models.BooleanField(
        default=False, verbose_name="fields for create records"
    )
    list_display = models.BooleanField(
        default=True, verbose_name="fields for display in list"
    )
    fieldsets = models.BooleanField(
        default=True, verbose_name="fields for display in details"
    )
    edit_fieldsets = models.BooleanField(
        default=False, verbose_name="fields for enable edit"
    )


class WorkflowInstance(WorkflowInstanceBaseModel):
    pass


class TaskInstance(TaskInstanceBaseModel):
    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        related_name="task_instance_workflow_instance",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    pass


class Case(CaseBaseModel):
    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        related_name="case_workflow_instance",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    task_instances = models.ManyToManyField(
        TaskInstance, related_name="case_task_instances"
    )  # should be one to many, but the design buill be better if use ManyToManyField, because TaskInstance is not only use in here

    def set_case_completed(self):
        workflow_instance = self.workflow_instance
        workflow_instance.is_active = 0
        workflow_instance.save()
        self.status = CASE_COMPLETED

    def get_task_instances_model(self):
        return self._meta.get_field("task_instances").related_model

    def get_workflow_instance_model(self):
        return self._meta.get_field("workflow_instance").related_model


class CaseData(CaseDataBaseModel):
    case = models.ForeignKey(
        Case, on_delete=models.PROTECT, related_name="case_data_case"
    )
