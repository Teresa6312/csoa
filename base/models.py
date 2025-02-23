from django.db import models
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError
from django.apps import apps
from .cache import global_class_cache_decorator
from .util import get_object_or_redirect
from .validators import get_validator
import uuid
from django.db.models import F, Q
from django.conf import settings


def validate_dictionary_code(value):
    if "_active" in value:
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
            verbose_name = ""
            if "__" in field:  # Handle ForeignKey fields
                field_parts = field.split("__")
                related_model = None
                for index in range(len(field_parts)):
                    related_field = (
                        cls._meta.get_field(field_parts[index])
                        if related_model is None
                        else related_model._meta.get_field(field_parts[index])
                    )
                    if isinstance(related_field, models.ForeignKey):
                        related_model = related_field.related_model
                        verbose_name = verbose_name + " " + related_field.verbose_name
                    else:
                        verbose_name = verbose_name + " " + related_field.name
            else:
                verbose_name = cls._meta.get_field(field).verbose_name
            selected_info[field] = verbose_name.capitalize()
        return selected_info

    @classmethod
    def selected_fields_info(cls):
        return {field.name: field.verbose_name for field in cls._meta.fields}

    @classmethod
    def has_file_field(cls):
        return False


class DictionaryModel(BaseAuditModel):
    code = models.CharField(
        max_length=63,
        primary_key=True,
        validators=[validate_dictionary_code, get_validator("no_space_str_w_-")],
    )
    description = models.CharField(unique=True, max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return "%s (%s)" % (self.code, self.description)

    @global_class_cache_decorator(
        cache_key="dictionary", timeout=settings.CACHE_TIMEOUT_L3
    )
    def get_dictionary_items_by_code(cls, code):
        instance = get_object_or_redirect(cls, code=code)
        if instance is None:
            return []
        else:
            return instance.dictionary_item_dictionary.all()

    @global_class_cache_decorator(
        cache_key="dictionary_active", timeout=settings.CACHE_TIMEOUT_L3
    )
    def get_dictionary_active_items_by_code(cls, code):
        instance = get_object_or_redirect(cls, code=code, is_active=True)
        if instance is None:
            return []
        else:
            return instance.dictionary_item_dictionary.filter(is_active=True)


class DictionaryItemModel(BaseAuditModel):
    dictionary = models.ForeignKey(
        DictionaryModel,
        on_delete=models.PROTECT,
        related_name="dictionary_item_dictionary",
    )
    value = models.CharField(max_length=255)
    code = models.CharField(max_length=63, null=True, blank=True)
    category = models.CharField(max_length=63, null=True, blank=True)
    sub_category = models.ForeignKey(
        DictionaryModel,
        on_delete=models.PROTECT,
        related_name="dictionary_item_sub_category",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return "%s - %s" % (self.dictionary, self.value)

    @classmethod
    def selected_fields_info(cls):
        fields = [
            "id",
            "dictionary__code",
            "dictionary__description",
            "value",
            "code",
            "category",
            "is_active",
        ]  # List of fields you want to include
        field_info = DictionaryItemModel.get_selected_fields_info(fields)
        return field_info

    @global_class_cache_decorator(
        cache_key="dictionary_item_map_active_by_code",
        timeout=settings.CACHE_TIMEOUT_L3,
    )
    def get_active_dictionary_item_map_by_code(cls, code):
        queryset = cls.objects.filter(
            dictionary=code,
            is_active=True,
            dictionary__is_active=True,
        )
        dic_query_name = "sub_category"
        dic_item_query_name = "sub_category__dictionary_item_dictionary"
        sub_set = queryset.filter(
            **{
                "%s__is_active" % dic_query_name: True,
                "%s__is_active" % dic_item_query_name: True,
            }
        )
        annotated_fields = {}
        fields = ["code", "value"]
        index = 1
        while sub_set.exists():
            queryset = sub_set
            annotated_fields["L%s__code" % index] = F("%s__code" % dic_item_query_name)
            annotated_fields["L%s__value" % index] = F(
                "%s__value" % dic_item_query_name
            )
            fields.append("L%s__code" % index)
            fields.append("L%s__value" % index)
            dic_query_name = (
                "sub_category__dictionary_item_dictionary__" + dic_query_name
            )
            dic_item_query_name = (
                "sub_category__dictionary_item_dictionary__sub_category__dictionary_item_dictionary"
                + dic_item_query_name
            )
            sub_set = sub_set.filter(
                **{
                    "%s__is_active" % dic_query_name: True,
                    "%s__is_active" % dic_item_query_name: True,
                }
            )
            index += 1
        return queryset.annotate(**annotated_fields).values(*fields)

    # @global_class_cache_decorator(cache_key='dictionary_item_map_by_code', timeout=settings.CACHE_TIMEOUT_L3)
    @classmethod
    def get_dictionary_item_map_by_code(cls, code):
        queryset = cls.objects.filter(dictionary=code)
        dic_item_query_name = "sub_category__dictionary_item_dictionary"
        queryset = queryset.prefetch_related(
            dic_item_query_name + "__" + dic_item_query_name
        )  # Optimize query
        sub_set = queryset.filter(**{"%s__isnull" % dic_item_query_name: False})
        annotated_fields = {"L0_code": F("code"), "L0_value": F("value")}
        index = 1
        while sub_set.exists() and index < 5:
            queryset = queryset.prefetch_related(dic_item_query_name)  # Optimize query
            queryset = queryset.prefetch_related(
                dic_item_query_name + "__sub_category"
            )  # Optimize query
            annotated_fields["L%s_code" % index] = F("%s__code" % dic_item_query_name)
            annotated_fields["L%s_value" % index] = F("%s__value" % dic_item_query_name)
            dic_item_query_name = (
                "sub_category__dictionary_item_dictionary__" + dic_item_query_name
            )
            sub_set = sub_set.filter(**{"%s__isnull" % dic_item_query_name: False})
            index += 1
        return queryset.annotate(**annotated_fields).values(*annotated_fields)


class FileModel(BaseAuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to="documents/")
    name = models.CharField(max_length=127)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.CharField(default="System", max_length=150)

    def __str__(self):
        return self.name

    @classmethod
    def selected_fields_info(cls):
        fields = [
            "id",
            "name",
            "created_at",
            "created_by",
        ]  # List of fields you want to include
        field_info = FileModel.get_selected_fields_info(fields)
        return field_info


class ModelDictionaryConfigModel(BaseAuditModel):
    code = models.CharField(
        max_length=63, primary_key=True, validators=[get_validator("no_space_str_w_")]
    )
    description = models.CharField(max_length=511)
    backend_app_label = models.CharField(max_length=127)
    backend_app_model = models.CharField(max_length=127)
    model_label = models.CharField(max_length=255, default="model")
    # model_type = models.CharField(max_length=63, choices=MODEL_TYPE_CHOICE, default='t')
    json_form = models.ForeignKey(
        "jsonForm.FormTemplate", on_delete=models.CASCADE, blank=True, null=True
    )
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
