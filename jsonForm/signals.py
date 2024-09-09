from django.db.models.signals import post_save, post_delete, pre_save, pre_delete
from django.dispatch import receiver
from .models import Workflow, Task, DecisionPoint, Case, WorkflowInstance, TaskInstance, Permission, FormSection, FormTemplate
from base.redis import create_redis_key_json, delete_redis_key
import uuid
import logging
logger = logging.getLogger('django')

@receiver(post_save, sender=Workflow)
def workflow_saved(sender, instance, created, **kwargs):
    instance.get_workflow_data()

@receiver([post_save], sender=Task)
def task_saved(sender, instance, created, **kwargs):
    if instance.workflow is not None:
        instance.workflow.get_workflow_data()

@receiver(post_delete, sender=Task)
def task_deleted(sender, instance, **kwargs):
    if instance.workflow is not None:
        instance.workflow.get_workflow_data()

@receiver([post_save], sender=DecisionPoint)
def decisionpoint_saved(sender, instance, created, **kwargs):
    if instance.task is not None and instance.task.workflow is not None:
        instance.task.workflow.get_workflow_data()

@receiver(post_delete, sender=DecisionPoint)
def decisionpoint_deleted(sender, instance, **kwargs):
    if instance.task is not None and instance.task.workflow is not None:
        instance.task.workflow.get_workflow_data()

@receiver(pre_delete, sender=Workflow)
def workflow_before_delete_handle(sender, instance, **kwargs):
    delete_redis_key(f'workflow:{instance.id}')

@receiver(post_save, sender=FormTemplate)
def form_saved(sender, instance, created, **kwargs):
    data = instance.get_key_list
    create_redis_key_json(f'form_header:{instance.id}', data)

@receiver([post_save], sender=FormSection)
def section_saved(sender, instance, created, **kwargs):
    data = instance.template.get_key_list
    create_redis_key_json(f'form_header:{instance.template.id}', data)

@receiver(post_delete, sender=FormSection)
def section_deleted(sender, instance, **kwargs):
    data = instance.template.get_key_list
    create_redis_key_json(f'form_header:{instance.template.id}', data)

@receiver([pre_delete], sender=FormTemplate)
def form_before_delete_handle(sender, instance, **kwargs):
    delete_redis_key(f'form_header:{instance.id}')

@receiver(pre_save, sender=Case)
def case_saved(sender, instance, **kwargs):
    form = instance.form
    if form is None:
        raise ValueError("The 'form' cannot be empty.")
    if form.workflow is None:
        raise ValueError("The 'workflow' on form '{form}' cannot be empty.")

    # Case was cancelled or only save as draft  
    if  instance.status == 'Cancelled':
        if instance.task_instances.all().count() > 0:
            for task_instance in instance.task_instances.filter(is_active = 1):
                task_instance.is_active = 0
                task_instance.save()
        if instance.workflow_instance is not None:
            workflow_instance = instance.workflow_instance
            workflow_instance.is_active = 0
            workflow_instance.save()
    elif not instance.is_submited:
        instance.status = 'Draft'
    # initial the workflow and task when user submit the form case
    elif instance.is_submited and form.workflow is not None and instance.workflow_instance is None:
        wf_instance = WorkflowInstance.objects.create(id = uuid.uuid4(), workflow = form.workflow)
        instance.workflow_instance = wf_instance
        first_task = form.workflow.task_workflow.filter(index=0).first()
        if first_task is None:
            raise ValueError(f"The 'initial task' from workflow '{form.workflow}' is not able to find")
        instance.status = first_task.name
        pers = []
        if first_task.assign_to_role is not None:
            per = Permission.get_assign_to_role(form.application,first_task.assign_to_role,instance)
            if per is not None:
                pers.append(per)
        elif first_task.assign_to is not None:
            pers =  first_task.assign_to.all()
        if len(pers) == 0:
            raise ValueError(f"No user group was found to assign the task ({first_task.assign_to_role} or {first_task.assign_to})")
        logger.debug(pers)
        for per in pers:
            if first_task.assign_to_role is not None and first_task.assign_to_role.name == 'Case Owner':
                task_instance = TaskInstance.objects.create(id = uuid.uuid4(), task = first_task, assign_to = per, workflow_instance = wf_instance, assign_to_user=instance.created_by)
            else:
                task_instance = TaskInstance.objects.create(id = uuid.uuid4(), task = first_task, assign_to = per, workflow_instance = wf_instance)
            task_instance.save()
            instance.task_instances.add(task_instance)
    # update workflow and task when user worked on the case
    elif instance.workflow_instance is not None:
        wf_instance = WorkflowInstance.objects.create(id = uuid.uuid4(), workflow = form.workflow)
        remain_task = instance.task_instances.filter(is_active = 1)
        if remain_task.count() == 0:
            priority_decision = instance.task_instances.filter(task__name = instance.status).order_by('-updated_at').first() # IF THERE IS MULTIPLE TASK IN ONE SHOT, THERE IS AN ISSUE WITH THIS
            if priority_decision is not None and priority_decision.decision_point is not None and priority_decision.decision_point.next_task is not None:
                next_task = priority_decision.decision_point.next_task
                instance.status = next_task.name
                pers = []
                if next_task.assign_to_role is not None:
                    per = Permission.get_assign_to_role(form.application,next_task.assign_to_role,instance)
                    if per is not None:
                       pers.append(per)
                elif next_task.assign_to is not None:
                    pers =  next_task.assign_to.all()
                if len(pers) == 0:
                    raise ValueError(f"No user group was found to assign the task ({next_task.assign_to_role} or {next_task.assign_to})")
                logger.debug(pers)
                for per in pers:
                    if next_task.assign_to_role is not None and next_task.assign_to_role.name == 'Case Owner':
                        task_instance = TaskInstance.objects.create(id = uuid.uuid4(), task = next_task, assign_to = per, workflow_instance = wf_instance, assign_to_user=instance.created_by)
                    else:
                        task_instance = TaskInstance.objects.create(id = uuid.uuid4(), task = next_task, assign_to = per, workflow_instance = wf_instance)
                    task_instance.save()
                    logger.debug(task_instance)
                    instance.task_instances.add(task_instance)
            else:
                workflow_instance = instance.workflow_instance
                workflow_instance.is_active = 0
                workflow_instance.save()
                instance.status = 'Completed'