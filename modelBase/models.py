from django.db import models
from base.models import BaseAuditModel
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
    pending_record = models.ForeignKey(
        PendingRecordModel, blank=True, null=True, on_delete=models.PROTECT
    )

    class Meta:
        abstract = True


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
    flag = models.BooleanField(default=False)
    original_data = models.JSONField(default=dict)

