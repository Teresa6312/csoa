from django.db.models.signals import post_save, pre_save
from django.db import models
from django.dispatch import receiver
from .models import ModelDictionaryConfigModel, ModelDictionaryItemsConfigModel
from django.db.models.signals import post_migrate
from base.util import get_related_names_for_model, CustomJSONEncoder
import json
import logging
from django.utils import timezone

logger = logging.getLogger("django")


@receiver(pre_save, sender=ModelDictionaryConfigModel)
def model_dictionary_save(sender, instance, **kwargs):
    class_name = instance.get_model_class()
    fk_fields = []
    fk_multi_fields = []
    for field in class_name._meta.get_fields():
        if isinstance(field, models.ForeignKey) or isinstance(
            field, models.OneToOneField
        ):
            related_name = field.remote_field.related_name
            fk_fields.append(
                {
                    "model": field.related_model._meta.label,
                    "field_name": field.name,
                    "related_name": (
                        related_name
                        if related_name is not None
                        else f"{class_name._meta.model_name}_set"
                    ),
                    "label": field.verbose_name,
                }
            )
        elif isinstance(field, models.ManyToManyField):
            related_name = field.remote_field.related_name
            fk_multi_fields.append(
                {
                    "model": field.related_model._meta.label,
                    "field_name": field.name,
                    "related_name": (
                        related_name
                        if related_name is not None
                        else f"{class_name._meta.model_name}_set"
                    ),
                    "label": field.verbose_name,
                }
            )
    fk, rnf = get_related_names_for_model(class_name)
    fk_fields = fk_fields + fk
    fk_multi_fields = fk_multi_fields + rnf
    if len(fk_fields) > 0:
        instance.fk_fields = json.loads(json.dumps(fk_fields, cls=CustomJSONEncoder))
    if len(fk_multi_fields) > 0:
        instance.fk_multi_fields = json.loads(
            json.dumps(fk_multi_fields, cls=CustomJSONEncoder)
        )
    instance.pk_field_name = class_name._meta.pk.name
    instance.model_label = (
        class_name._meta.verbose_name.title()
        if instance.model_label == "model"
        else instance.model_label
    )


@receiver(post_save, sender=ModelDictionaryConfigModel)
def model_dictionary_saved(sender, instance, created, **kwargs):
    class_name = instance.get_model_class()
    if created:
        index = 0
        for field in class_name._meta.fields:
            list_display = True
            fieldsets = True
            if (
                isinstance(field, models.ForeignKey)
                or isinstance(field, models.ManyToManyField)
                or isinstance(field, models.OneToOneField)
            ):
                list_display = False
                fieldsets = False
            new_item = ModelDictionaryItemsConfigModel.objects.create(
                dictionary=instance,
                backend_field_name=field.name,
                add_fieldsets=True,
                edit_fieldsets=True,
                fieldsets=fieldsets,
                field_label=field.verbose_name.title(),
                index=index if field.name != "is_active" else 99,
                list_display=list_display,
            )
            new_item.save()
            index = index + 1


# may use the following to get all the related fields
# @receiver(pre_save, sender=ModelDictionaryConfigModel)
# def model_dictionary_create(sender, instance, **kwargs):
#     his = instance.history.all()
#     # make sure only apply when create
#     if len(his) == 0:
#         class_name = instance.get_model_class()
#         fk_fields = []
#         related_name_fields = []
#         for field in class_name._meta.fields:
#             print(field)
#             if isinstance(field, models.ForeignKey) or isinstance(field, models.ManyToManyField):
#                 print(field)
#                 fk_fields.append(field.name)
#         if len(fk_fields) > 0:
#             instance.fk_fields = ','.join(fk_fields)
#         related_name_fields = get_related_names_for_model(class_name)
#         if len(related_name_fields) > 0:
#             instance.related_name_fields = ','.join(related_name_fields)
#         instance.pk_field_name = class_name._meta.pk.name
#         instance.model_label = class_name._meta.label.title()

# @receiver(post_save, sender=ModelDictionaryConfigModel)
# def model_dictionary_saved(sender, instance, created, **kwargs):
#     class_name = instance.get_model_class()
#     index = 0
#     if created:
#         for field in class_name._meta.fields:
#             list_display = True
#             if isinstance(field, models.ForeignKey) or isinstance(field, models.ManyToManyField):
#                 list_display = False
#             new_item = ModelDictionaryItemsConfigModel.objects.create(dictionary=instance,
#                                                             backend_field_name=field.name,
#                                                             field_label=field.verbose_name.title(),
#                                                             index=index, list_display = list_display)
#             new_item.save()
#             index = index + 1
#         if instance.fk_fields is not None:
#             fk_fields = instance.fk_fields.split(',')
#             for fk in fk_fields:
#                 fk_field = class_name._meta.get_field(fk)
#                 related_model = fk_field.related_model
#                 for related_field in related_model._meta.fields:
#                     new_item = ModelDictionaryItemsConfigModel.objects.create(dictionary=instance,
#                                                                    backend_field_name=f"{fk}__{related_field.name}",
#                                                                    field_label=f"{fk_field.verbose_name}  {related_field.verbose_name}".title(),
#                                                                    index=index, list_display = False)
#                     new_item.save()
#                     index = index + 1
#             related_name_fields = instance.related_name_fields.split(',')
#             for fk in related_name_fields:
#                 related_model_class = get_related_model_class(class_name, fk)
#                 if related_model_class is not None:
#                     # fk_field = related_model_class._meta.get_field(fk)
#                     # related_model = fk_field.related_model
#                     for related_field in related_model_class._meta.fields:
#                         new_item = ModelDictionaryItemsConfigModel.objects.create(dictionary=instance,
#                                                                     backend_field_name=f"{fk}__{related_field.name}",
#                                                                     field_label=f"{fk_field.verbose_name}  {related_field.verbose_name}".title(),
#                                                                     index=index, list_display = False, )
#                         new_item.save()
#                         index = index + 1

# #  if there is some data table structure change, need to check if the model configed in ModelDictionaryConfigModel, if it is configed, need to do some handling
#  for example, what to do if table removed, what to do if add new fields or delete existed fields (FK or not FK), something for the related models configed in ModelDictionaryConfigModel


@receiver(post_migrate)
def execute_after_migrate(sender, **kwargs):
    objects = ModelDictionaryConfigModel.objects.filter(is_active=True)
    # Update the 'updated_at' field for each object
    for obj in objects:
        logger.info(f"update ModelDictionaryConfigModel:'{obj}' after migrate")
        obj.updated_at = timezone.now()
        obj.save()


from django.db.models.signals import pre_save  # Import the pre_save signal
from django.dispatch import receiver  # Import the receiver decorator
from .models import Case, WorkflowInstance, TaskInstance  # Import necessary models
from base import constants  # Import constants
import logging  # Import logging module
from jsonForm.WorkflowExecutor import (
    WorkflowExecutor,
)  # Import the WorkflowExecutor class

logger = logging.getLogger("django")  # Get a logger instance


@receiver(
    pre_save, sender=Case
)  # Decorator to connect the function to the pre_save signal of the Case model
def case_saved(sender, instance, **kwargs):
    """
    Signal handler function that is called before a Case instance is saved.
    This function manages the workflow and task creation/updates based on the Case status.

    Args:
        sender: The model class that sends the signal (Case).
        instance: The Case instance being saved.
        kwargs: Additional keyword arguments.
    """
    form = instance.form  # Get the associated FormTemplate
    wf_executor = WorkflowExecutor()  # Create an instance of the WorkflowExecutor

    if form is None:  # Check if the form is set
        raise ValueError(
            "The 'form' cannot be empty."
        )  # Raise error if form is missing

    # Case was cancelled or only saved as draft
    if instance.status == constants.CASE_CANCELLED:  # If the case is cancelled
        if (
            instance.task_instances.all().count() > 0
        ):  # Check if there are any active task instances
            for task_instance in instance.task_instances.filter(
                is_active=1
            ):  # Iterate through active task instances
                task_instance.is_active = False  # Deactivate the task instance
                task_instance.save()  # Save the changes
        if (
            instance.workflow_instance is not None
        ):  # Check if a workflow instance exists
            workflow_instance = instance.workflow_instance  # Get the workflow instance
            workflow_instance.is_active = False  # Deactivate the workflow instance
            workflow_instance.save()  # Save the changes
    elif not instance.is_submited:  # If the case is saved as a draft
        instance.status = "Draft"  # Set the status to 'Draft'

    # Initial the workflow and task when user submit the form case
    elif (
        instance.is_submited
        and form.workflow is not None
        and instance.workflow_instance is None
    ):  # If the case is submitted, has a workflow, and no workflow instance yet
        workflow_instance = WorkflowInstance.objects.create(
            workflow=form.workflow
        )  # Create a new workflow instance
        instance.workflow_instance = (
            workflow_instance  # Assign the workflow instance to the case
        )
        instance.workflow_name = (
            form.workflow.name
        )  # Set the workflow name for the case
        current_task = wf_executor.get_first_task(
            form.workflow
        )  # Get the first task of the workflow
        next_task = wf_executor.execute(
            instance, current_task
        )  # Execute the workflow from the first task
        if next_task is not None:  # If there is a next task
            instance.status = (
                next_task.name
            )  # Update the case status with the next task name
        else:  # If there is no next task, the workflow is complete
            instance.set_case_completed()  # Mark the case as completed

    # Update workflow and task when user worked on the case
    elif (
        instance.workflow_instance is not None
    ):  # If a workflow instance exists (case is in progress)
        remain_task = instance.task_instances.filter(
            is_active=1
        )  # Get the remaining active task instances
        if remain_task.count() == 0:  # If there are no remaining active tasks
            priority_decision = wf_executor.get_priority_decision(
                instance
            )  # Get the priority decision point
            if (
                priority_decision is not None
                and priority_decision.next_task is not None
            ):  # If a decision point and next task exist
                next_task = wf_executor.execute(
                    instance, priority_decision.next_task
                )  # Execute the workflow from the next task
                if next_task is not None:  # If there is a next task
                    instance.status = next_task.name  # Update the case status
                else:  # If no next task, workflow is complete
                    instance.set_case_completed()  # Mark the case as completed
            else:  # If no decision point or next task, workflow is complete
                instance.set_case_completed()  # Mark the case as completed
