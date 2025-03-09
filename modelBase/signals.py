
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
