from django.db import models
from base.models import BaseAuditModel, FileModel
from userManagement.models import (
    Company,
    Department,
    Team,
    AppMenu,
    Permission,
    CustomUser,
    Team,
    CustomGroup,
)
import json
from jsonschema import validate, ValidationError
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.apps import apps
import uuid
from base.validators import get_validator
from django_jsonform.models.fields import JSONField
from base.cache import global_class_cache_decorator, global_instance_cache_decorator
from django.conf import settings
from base.util import (
    get_object_or_redirect,
    validate_json_with_schema,
    load_schema_from_file,
)

from base.constants import (
    TASK_TYPE_CHOICES,
    TASK_TYPE_AUTO,
    TASK_TYPE_FLOW,
    CASE_INITIATED,
    CASE_COMPLETED,
    JSON_FORM_TEMPLATE_SCHEMA_PATH,
)


# Create your models here.
class FormTemplate(BaseAuditModel):
    code = models.CharField(
        max_length=15, unique=True, validators=[get_validator("no_space_str_w_-")]
    )
    name = models.CharField(max_length=127, unique=True)
    description = models.CharField(max_length=1023)

    owner_company = models.ForeignKey(
        Company,
        related_name="template_owner_department",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    owner_department = models.ForeignKey(
        Department,
        related_name="template_owner_department",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    owner_team = models.ForeignKey(
        Team,
        related_name="template_owner_team",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    application = models.ForeignKey(
        AppMenu,
        related_name="template_application",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    backend_app_label = models.CharField(max_length=63, blank=True, null=True)
    backend_app_model = models.CharField(max_length=63, blank=True, null=True)
    backend_app_section_model = models.CharField(max_length=63, blank=True, null=True)

    workflow = models.ForeignKey(
        "Workflow",
        related_name="template_workflow",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    process_department = models.ForeignKey(
        Department,
        related_name="template_process_department",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    process_team = models.ForeignKey(
        Team,
        related_name="template_process_department",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=False)

    def __str__(self) -> str:
        return "%s (%s)" % (self.name, self.code)

    def clean(self):
        if self.id:
            related_sections = self.form_section_form_template.filter(
                is_active=True, is_publish=True
            )
            existed_keys = set()
            for related_section in related_sections:
                new_keys = set(related_section.json_template.keys())
                common_keys = existed_keys.intersection(new_keys)
                if len(common_keys) > 0:
                    raise ValidationError(
                        f"Input key must be unique in Section: {related_section}, Duplicated key found {common_keys}"
                    )

    def get_absolute_url(self):
        return dict(new=reverse("jsonForm:view", args=[str(self.id)]))

    @property
    def control_type(self):
        if self.application is not None:
            return ("app", "Application")
        if self.owner_team is not None > 0:
            return ("team", "Team")
        if self.owner_department is not None:
            return ("department", "Department")
        if self.owner_company is not None:
            return ("company", "Company")
        return ("global", "Global")

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

    @global_instance_cache_decorator(
        cache_key="form_template_model_class", timeout=settings.CACHE_TIMEOUT_L3
    )
    def get_model_class(self):
        if self.backend_app_label and self.backend_app_model:
            model_class = apps.get_model(self.backend_app_label, self.backend_app_model)
            return model_class
        else:
            raise ValueError(
                f"backend_app_label and backend_app_model is missing in Form"
            )

    @global_instance_cache_decorator(
        cache_key="form_template_section_model_class", timeout=settings.CACHE_TIMEOUT_L3
    )
    def get_section_model_class(self):
        if self.backend_app_label and self.backend_app_section_model:
            model_class = apps.get_model(
                self.backend_app_label, self.backend_app_section_model
            )
            return model_class
        else:
            raise ValueError(
                f"backend_app_label and backend_app_section_model is missing in Form"
            )

    @global_instance_cache_decorator(
        cache_key="form_template_model_instance", timeout=settings.CACHE_TIMEOUT_L3
    )
    def get_model_instance(self, id):
        if self.backend_app_label and self.backend_app_model:
            model_class = apps.get_model(self.backend_app_label, self.backend_app_model)
            if model_class:
                return get_object_or_redirect(model_class, pk=id)
            else:
                raise ValueError(
                    f"Model '{self.backend_app_label}' not found in app '{self.backend_app_model}'"
                )
        else:
            raise ValueError(f"backend_app_label and backend_app_model is required")

    @property
    def get_key_list(self):
        sections = self.form_section_form_template.filter(is_publish=True).order_by(
            "index"
        )
        existed_keys = set()
        headers = []
        for sec in sections:
            new_fields = sec.get_key_list
            if len(existed_keys) > 0:
                new_keys = set(f["key"] for f in new_fields)
                unique_keys_in_new_keys = new_keys - existed_keys
                headers = headers + [
                    a for a in new_fields if a["key"] in unique_keys_in_new_keys
                ]
                existed_keys = existed_keys.union(new_keys)
            else:
                headers = new_fields
                existed_keys = set(f["key"] for f in new_fields)
        return headers

    @global_class_cache_decorator(
        cache_key="form_instance", timeout=settings.CACHE_TIMEOUT_L3
    )
    def get_instance_by_code(cls, code):
        result = get_object_or_redirect(cls, code=code)
        if result is None:
            return None
        else:
            return result

    @global_class_cache_decorator(
        cache_key="form_header", timeout=settings.CACHE_TIMEOUT_L3
    )
    def get_headers_by_code(cls, code):
        form = cls.get_instance_by_code(code)
        if form is not None:
            return form.get_key_list
        else:
            return []


class FormSection(BaseAuditModel):
    index = models.PositiveSmallIntegerField(default=0)
    name = models.CharField(max_length=127)
    description = models.CharField(max_length=1023, blank=True, null=True)
    version = models.PositiveSmallIntegerField(default=0)
    json_template = models.JSONField(
        max_length=1000,
        help_text="JSON template for the form section validate with schema https://www.jsonschemavalidator.net/",
    )
    # json_template = JSONField(schema=load_schema_from_file(JSON_FORM_TEMPLATE_SCHEMA_PATH))
    json_template_schema = models.JSONField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="JSON template schema for the form section",
    )
    template = models.ForeignKey(
        FormTemplate,
        related_name="form_section_form_template",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=False)
    is_publish = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template", "version", "index"],
                name="unique form section version index template",
            ),
            models.UniqueConstraint(
                fields=["template", "version", "name"],
                name="unique form section version name template",
            ),
        ]

    def __str__(self) -> str:
        return "%s (v.%s)" % (self.name, self.version)

    def clean(self):
        super().clean()
        # Check if the json_template field is valid JSON and meets custom requirements
        try:
            # This is redundant, as JSONField already ensures the data is valid JSON.
            if isinstance(self.json_template, dict):
                json_str = json.dumps(self.json_template)
                json.loads(json_str)
            elif isinstance(self.json_template, str):
                json.loads(self.json_template)
            else:
                raise ValidationError("Invalid JSON format.")
            validate_form_section_json(self.json_template)
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format.")

        if self.id:
            related_sections = self.template.form_section_form_template.filter(
                is_active=True, is_publish=True
            ).exclude(id=self.id)
        elif self.template.id:
            related_sections = self.template.form_section_form_template.filter(
                is_active=True, is_publish=True
            )
        else:
            related_sections = []
        for related_section in related_sections:
            existed_keys = set(related_section.json_template.keys())
            new_keys = set(self.json_template.keys())
            common_keys = existed_keys.intersection(new_keys)
            if len(common_keys) > 0:
                raise ValidationError(
                    f"Input key must be unique in {self.template}, Duplicated key found {common_keys}"
                )

    def create_model_instance(self, *args, **kwargs):
        if self.template.backend_app_label and self.template.backend_app_section_model:
            model_class = apps.get_model(
                self.template.backend_app_label, self.template.backend_app_section_model
            )
            if model_class:
                return model_class.objects.create(*args, **kwargs)
            else:
                raise ValueError(
                    f"Model '{self.template.backend_app_label}' not found in app '{self.template.backend_app_section_model}'"
                )
        else:
            raise ValueError(
                f"backend_app_label and backend_app_section_model is required from template"
            )

    @global_instance_cache_decorator(
        cache_key="form_section_template_model_instance",
        timeout=settings.CACHE_TIMEOUT_L3,
    )
    def get_model_instance(self, id):
        if self.template.backend_app_label and self.template.backend_app_section_model:
            model_class = apps.get_model(
                self.template.backend_app_label, self.template.backend_app_section_model
            )
            if model_class:
                return get_object_or_redirect(model_class, pk=id)
            else:
                raise ValueError(
                    f"Model '{self.template.backend_app_label}' not found in app '{self.template.backend_app_section_model}'"
                )
        else:
            raise ValueError(
                f"backend_app_label and backend_app_section_model is required from template"
            )

    @property
    @global_instance_cache_decorator(
        cache_key="form_section_template_json_key_list",
        timeout=settings.CACHE_TIMEOUT_L3,
    )
    def get_key_list(self):
        fields = []
        json_data = self.json_template
        for field in json_data:
            fields.append(
                {
                    "key": field,
                    "label": json_data[field].get("label", field),
                    "input": json_data[field].get("input", ""),
                    "index": self.index,
                }
            )
        return fields


def validate_form_section_json_message(json_value):
    """
    Validate that the input string is a valid JSON format.

    Args:
        value (str): The string to validate.

    Raises:
        ValidationError: If the string is not valid JSON.
    """
    error_message = ""
    for key in json_value:
        has_label = False
        has_input = False
        is_select = False
        is_string = False
        is_decimal = False
        is_list = False
        is_date = False
        is_file = False
        has_option = False
        has_length = False
        has_max_digits = False
        has_decimal_places = False
        has_fields = False
        validator = ""
        format = json_value[key]
        if not isinstance(format, dict):
            error_message = error_message + "%s is not a valid JSON string/n" % (key)
        for fk in format:
            if fk == "label":
                has_label = True
                if format[fk] is None or format[fk] == "":
                    error_message = error_message + '%s has no "label"/n' % (key)
            elif fk == "input":
                has_input = True
                if format[fk] is None or format[fk] == "":
                    error_message = error_message + '%s has no "input"/n' % (key)
                elif format[fk] in ("select", "select_multiple"):
                    is_select = True
                elif format[fk] == "string":
                    is_string = True
                elif format[fk] == "integer":
                    pass
                elif format[fk] == "decimal":
                    is_decimal = True
                elif format[fk] == "list":
                    is_list = True
                elif format[fk] == "date":
                    is_date = True
                elif format[fk] == "file":
                    is_file = True
                else:
                    error_message = (
                        error_message
                        + 'The system only support "select", "select_multiple", "integer", "decimal", "string", "date", "file", and "list" input. "%s" was not supported/n'
                        % (format[fk])
                    )
            elif fk == "choices" or fk == "choices_map":
                has_option = True
                if (
                    format["choices"] == []
                    or format["choices"] == ""
                    or format["choices"] is None
                    or not (
                        isinstance(format["choices"], list)
                        or isinstance(format["choices"], str)
                    )
                ) and (
                    format["choices_map"] == []
                    or format["choices_map"] == ""
                    or format["choices_map"] is None
                    or not (
                        isinstance(format["choices_map"], list)
                        or isinstance(format["choices_map"], str)
                    )
                ):
                    error_message = (
                        error_message
                        + '%s has no "choices" or "choices_map" /n' % (key)
                    )
            elif fk == "length":
                has_length = True
                if not isinstance(format[fk], int):
                    error_message = error_message + "The length of %s must be int/n" % (
                        key
                    )
            elif fk == "max_digits":
                has_max_digits = True
                if not isinstance(format[fk], int):
                    error_message = (
                        error_message + "The max_digits of %s must be int/n" % (key)
                    )
            elif fk == "decimal_places":
                has_decimal_places = True
                if not isinstance(format[fk], int):
                    error_message = (
                        error_message + "The decimal_places of %s must be int/n" % (key)
                    )
            elif fk == "validator":
                validator = format[fk]
            elif fk == "fields":
                has_fields = True
                if not isinstance(format[fk], dict):
                    error_message = (
                        error_message + "The fields of %s must be dict/n" % (key)
                    )
                else:
                    error_message = error_message + validate_form_section_json_message(
                        format[fk]
                    )

        if not has_label:
            error_message = error_message + '%s has no "label"/n' % (key)
        if not has_input:
            error_message = error_message + '%s has no "input"/n' % (key)

        if is_select and not has_option:
            error_message = (
                error_message + '%s has "select" input but no "choices"/n' % (key)
            )
        if not is_select and has_option:
            error_message = (
                error_message + '%s has "choices" but not "select" input/n' % (key)
            )
        if not is_string and has_length:
            error_message = (
                error_message + '%s has "length" but not "string" input/n' % (key)
            )
        if is_string and not has_length:
            error_message = (
                error_message + '%s has "string" input but not "length"/n' % (key)
            )
        if is_decimal and not (has_max_digits and has_decimal_places):
            error_message = (
                error_message
                + '%s has "decimal" input but has no "max_digits or decimal_places"/n'
                % (key)
            )
        if not is_decimal and (has_max_digits or has_decimal_places):
            error_message = (
                error_message
                + '%s has "max_digits or decimal_places" but not "decimal" input/n'
                % (key)
            )
        if is_list and not has_fields:
            error_message = (
                error_message + '%s has "list" input but has no "fields"/n' % (key)
            )
        if not is_list and has_fields:
            error_message = error_message + '%s has "fields" but not "list" input/n' % (
                key
            )
        if (
            validator
            not in ("validate_today_and_before", "validate_today_and_after", "")
            and is_date
        ):
            error_message = (
                error_message
                + 'The validator of %s must be "today_and_before" or "today_and_after" /n'
                % (key)
            )
        elif validator:
            get_validator(validator)
    return error_message


def validate_form_section_json(value):
    try:
        schema = load_schema_from_file(JSON_FORM_TEMPLATE_SCHEMA_PATH)
        if schema is None:
            raise ValidationError(
                "Error with loading schema file %s" % (JSON_FORM_TEMPLATE_SCHEMA_PATH)
            )
    except Exception as e:
        raise ValidationError(
            "Error with loading schema file %s" % (JSON_FORM_TEMPLATE_SCHEMA_PATH)
        )
    try:
        if value is not None:
            error_message_1 = validate_json_with_schema(value, schema)
            error_message_2 = validate_form_section_json_message(value)
        else:
            raise ValidationError("Enter a valid JSON string.")
        if error_message_1 != "" or error_message_2 != "":
            raise ValidationError("%s | %s" % (error_message_1, error_message_2))
    except json.JSONDecodeError:
        raise ValidationError("Enter a valid JSON string.")


class Workflow(BaseAuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(max_length=511, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_workflow_data(self):
        tasks = self.task_workflow.all().order_by("index")
        tasks_data = [
            {
                "id": str(task.id),
                "name": task.name,
                "description": task.description,
                "assign_to": [
                    {
                        "app": p.app.label if p.app is not None else None,
                        "role": p.role.name if p.role is not None else None,
                        "company": (
                            p.company.full_name if p.company is not None else None
                        ),
                        "department": (
                            p.department.full_name if p.department is not None else None
                        ),
                        "team": p.team.full_name if p.team is not None else None,
                    }
                    for p in task.assign_to.all()
                ],
                "assign_to_role": (
                    task.assign_to_role.name
                    if task.assign_to_role is not None
                    else None
                ),
                "decision_points": [
                    {
                        "id": str(dp.id),
                        "name": dp.decision,
                        "next_task_id": str(dp.next_task_id),
                        "priority": dp.priority,
                    }
                    for dp in task.decision_points_task.all().order_by("priority")
                ],
            }
            for task in tasks
        ]

        data = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "tasks": tasks_data,
        }
        return data

    @global_class_cache_decorator(
        cache_key="workflow_data", timeout=settings.CACHE_TIMEOUT_L3
    )
    def get_data_by_id(cls, id):
        result = get_object_or_redirect(cls, pk=id)
        if result is None:
            return None
        return result.get_workflow_data()


class Task(BaseAuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow, related_name="task_workflow", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=511, blank=True, null=True)
    assign_to = models.ManyToManyField(
        Permission, related_name="task_assign_to", blank=True
    )
    assign_to_role = models.ForeignKey(
        CustomGroup,
        related_name="task_assign_to_role",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    assign_to_user = models.ForeignKey(
        CustomUser,
        related_name="task_assign_to_user",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="not in used",
    )
    index = models.PositiveSmallIntegerField(
        default=1, help_text="task order index start from 0, others default to 1"
    )
    task_type = models.CharField(
        max_length=31, choices=TASK_TYPE_CHOICES, default=TASK_TYPE_FLOW
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "name"], name="unique task workflow task name"
            ),
            models.UniqueConstraint(
                fields=["workflow", "index"], name="unique task workflow task index"
            ),
        ]

    def __str__(self):
        return f"[{self.workflow}({self.index})] {self.name}"

    def clean(self):  # 在model的clean方法中调用验证器
        if self.index == 0 and self.task_type == "Manual":
            raise ValidationError(
                f"Manual Craete Task should not be the first task in the workflow"
            )


class DecisionPoint(BaseAuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task, related_name="decision_points_task", on_delete=models.CASCADE
    )
    decision = models.CharField(max_length=255)
    next_task = models.ForeignKey(
        Task,
        related_name="decision_points_next_task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    priority = models.PositiveSmallIntegerField(
        default=1,
        help_text="decision priority to determine the next task, 1 is the first priority. It is usefull if the task was assigned to multiple decision makers, if one rejected the case, and the whold case should be cancelled, then reject should be the highest priority",
    )
    condition = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON-encoded string representing the condition for this decision point. Find the condition format in the  folder.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "decision"], name="unique  decision point task&decision"
            ),
            models.UniqueConstraint(
                fields=["task", "priority"], name="unique decision point task&priority"
            ),
        ]

    def __str__(self):
        return f"[{self.task.workflow}] {self.task.name} - {self.decision} ({self.priority})"


class WorkflowInstanceBaseModel(BaseAuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow,
        related_name="%(app_label)s_%(class)s_workflow",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(default=True)  # if the workflow instance is active

    class Meta:
        abstract = True


class TaskInstanceBaseModel(BaseAuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task, related_name="%(app_label)s_%(class)s_task", on_delete=models.CASCADE
    )
    assign_to = models.ForeignKey(
        Permission,
        related_name="%(app_label)s_%(class)s_assign_to",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )  # assign_to can be null for auto task
    assign_to_user = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_assign_to_user",
        blank=True,
        null=True,
    )
    decision_point = models.ForeignKey(
        DecisionPoint,
        related_name="%(app_label)s_%(class)s_decision_point",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    comment = models.CharField(max_length=511, blank=True, null=True)
    files = models.ManyToManyField(
        FileModel, related_name="%(app_label)s_%(class)s_files", blank=True
    )

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created_by",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_updated_by",
        blank=True,
        null=True,
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    created_by_name = models.CharField(max_length=300, blank=True, null=True)
    updated_by_name = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ["created_at"]

    @classmethod
    def selected_fields_info(cls):
        fields = [
            "id",
            "task__workflow__name",
            "task__name",
            "assign_to__role__name",
            "assign_to__company__full_name",
            "assign_to__department__full_name",
            "assign_to__team__full_name",
            "assign_to_user__username",
            "decision_point__decision",
            "comment",
            "created_at",
            "updated_at",
            "updated_by_name",
            "is_active",
        ]  # List of fields you want to include
        field_info = TaskInstance.get_selected_fields_info(fields)
        return field_info

    def clean(self):  # 在model的clean方法中调用验证器
        if not self.assign_to and self.task.task_type != constants.TASK_TYPE_AUTO:
            raise ValidationError(
                f"assign_to is required for task type {self.task.task_type}"
            )
        if self.is_active == False and self.decision_point is None:
            raise ValidationError(f"Inactive task should have decision point")

    def save(self, *args, **kwargs):
        if self.created_by is not None and self.created_by_name is None:
            self.created_by_name = "%s %s" % (
                self.created_by.first_name,
                self.created_by.last_name,
            )
        # Update the updated_by_name field if updated_by is provided
        if self.updated_by is not None:
            self.updated_by_name = "%s %s" % (
                self.updated_by.first_name,
                self.updated_by.last_name,
            )
        super().save(*args, **kwargs)


class CaseBaseModel(BaseAuditModel):
    form = models.ForeignKey(
        FormTemplate,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_form",
    )
    is_submited = models.BooleanField(default=False)
    case_team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_team",
        blank=True,
        null=True,
    )
    case_department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_department",
        blank=True,
        null=True,
    )

    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created_by",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_updated_by",
        blank=True,
        null=True,
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    case_team_name = models.CharField(max_length=127, blank=True, null=True)
    case_department_name = models.CharField(max_length=127, blank=True, null=True)
    # case_company_name = models.CharField(max_length=127, blank=True, null=True)
    form_code = models.CharField(max_length=15, blank=True, null=True)
    form_name = models.CharField(max_length=127, blank=True, null=True)
    workflow_name = models.CharField(max_length=255, blank=True, null=True)
    created_by_name = models.CharField(max_length=300, blank=True, null=True)
    updated_by_name = models.CharField(max_length=300, blank=True, null=True)

    # Draft/Initial -> task name -> Compleled/Cancelled
    status = models.CharField(max_length=255, default=CASE_INITIATED)

    class Meta:
        abstract = True

    @classmethod
    def selected_fields_info(cls):
        fields = [
            "id",
            "form_code",
            "form_name",
            "is_submited",
            "case_department_name",
            "case_team_name",
            "created_by_name",
            "updated_by_name",
            "created_at",
            "updated_at",
            "status",
        ]  # List of fields you want to include
        field_info = Case.get_selected_fields_info(fields)
        return field_info

    def get_case_data_in_json(self):
        sections = self.case_data_case.all()
        data = {}
        for instance in sections:
            try:
                # Safely load JSON data.  Handles cases where the JSONField might be None or contain invalid JSON
                instance_data = instance.section_data
                if instance_data is None:
                    continue  # Skip if the JSONField is None
                if isinstance(
                    instance_data, str
                ):  # Check if it's a string (older Django versions might store JSON as strings)
                    instance_data = json.loads(instance_data)
                if isinstance(
                    instance_data, dict
                ):  # Make sure it's a dictionary before merging
                    data.update(instance_data)
                else:
                    raise ValidationError(
                        f"Warning: JSONField data for instance {instance.pk} is not a dictionary. Skipping."
                    )
            except (json.JSONDecodeError, AttributeError) as e:
                raise ValidationError(
                    f"Error processing JSONField for instance {instance.pk}: {e}"
                )
        return data

    def save(self, *args, **kwargs):
        # Set the default values for the name fields if they are not provided
        if self.form is not None and self.form_name is None:
            self.form_name = self.form.name
        if self.form is not None and self.form_code is None:
            self.form_code = self.form.code
        if self.case_team is not None and self.case_team_name is None:
            self.case_team_name = self.case_team.full_name
        if self.case_department is not None and self.case_department_name is None:
            self.case_department_name = self.case_department.full_name
        if self.created_by is not None and self.created_by_name is None:
            self.created_by_name = "%s %s" % (
                self.created_by.first_name,
                self.created_by.last_name,
            )
        # Update the updated_by_name field if updated_by is provided
        if self.updated_by is not None:
            self.updated_by_name = "%s %s" % (
                self.updated_by.first_name,
                self.updated_by.last_name,
            )
        super().save(*args, **kwargs)


class CaseDataBaseModel(BaseAuditModel):
    form_section = models.ForeignKey(
        FormSection,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_form_section",
    )
    section_data = models.JSONField(
        default=dict
    )  # set validation after save if the data lenght was changed after save, data maybe trancated

    form_section_name = models.CharField(max_length=127, blank=True, null=True)

    class Meta:
        abstract = True

    @classmethod
    def selected_fields_info(cls):
        fields = [
            "case__id",
            "case__status",
            "case__form_name",
            "form_section_name",
            "case__created_by_name",
            "case__updated_by_name",
            "case__created_at",
            "case__updated_at",
        ]  # List of fields you want to include
        field_info = CaseData.get_selected_fields_info(fields)
        return field_info

    def save(self, *args, **kwargs):
        if kwargs.get("created", False):
            if self.form_section is not None:
                self.form_section_name = self.form_section.name
        super().save(*args, **kwargs)


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
