from simple_history.admin import SimpleHistoryAdmin
from django.contrib import admin
from django.db import models
from django import forms
from .models import (
    DictionaryModel,
    DictionaryItemModel,
    FileModel,
    ModelDictionaryConfigModel,
    ModelDictionaryItemsConfigModel,
)

default_readonly_fields = (
    "created_by",
    "created_at",
    "updated_by",
    "updated_at",
)


class BaseAuditAdmin(SimpleHistoryAdmin):

    def created_at(self, obj):
        return obj.created_at

    def created_by(self, obj):
        return obj.created_by

    def updated_at(self, obj):
        return obj.updated_at

    def updated_by(self, obj):
        return obj.updated_by

    def get_readonly_fields(self, request, obj=None):
        if obj:
            if hasattr(self, "readonly_fields_for_update"):
                return (
                    self.readonly_fields
                    + default_readonly_fields
                    + self.readonly_fields_for_update
                )
            else:
                return self.readonly_fields + default_readonly_fields
        else:
            return default_readonly_fields

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if isinstance(db_field, models.CharField) and db_field.max_length > 50:
            kwargs["widget"] = forms.Textarea(attrs={"rows": 3})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class DictionaryItemInline(admin.TabularInline):
    model = DictionaryItemModel
    can_delete = False
    extra = 1
    fields = ["value", "code", "category", "sub_category", "is_active"]
    verbose_name_plural = "Dictionary Items"
    fk_name = "dictionary"


class DictionaryAdmin(BaseAuditAdmin):
    inlines = (DictionaryItemInline,)
    list_display = ["code", "description", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "description"]

    def get_readonly_fields(self, request, obj=None):
        return ["code"] if obj else []


class ModelDictionaryItemsConfigInline(admin.TabularInline):
    model = ModelDictionaryItemsConfigModel
    can_delete = False
    extra = 1
    fields = [
        "backend_field_name",
        "field_label",
        "index",
        "add_fieldsets",
        "list_display",
        "fieldsets",
        "edit_fieldsets",
    ]
    verbose_name_plural = "Dictionary Items"


class ModelDictionaryConfigAdmin(BaseAuditAdmin):
    inlines = (ModelDictionaryItemsConfigInline,)
    list_display = [
        "code",
        "backend_app_label",
        "backend_app_model",
        "json_form",
        "model_label",
        "is_active",
    ]
    list_filter = ["is_active"]
    search_fields = ["code", "description"]

    def get_readonly_fields(self, request, obj=None):
        return ["code"] if obj else []


class ModelDictionaryItemsConfigAdmin(BaseAuditAdmin):
    list_display = [
        "dictionary",
        "backend_field_name",
        "field_label",
        "index",
        "add_fieldsets",
        "list_display",
        "fieldsets",
        "edit_fieldsets",
    ]
    search_fields = ["backend_field_name", "field_label"]


admin.site.register(ModelDictionaryConfigModel, ModelDictionaryConfigAdmin)
admin.site.register(ModelDictionaryItemsConfigModel, ModelDictionaryItemsConfigAdmin)
admin.site.register(DictionaryModel, DictionaryAdmin)
admin.site.register(FileModel)
