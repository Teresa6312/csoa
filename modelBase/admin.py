from django.contrib import admin
from base.admin import BaseAuditAdmin
from .models import ModelDictionaryConfigModel, ModelDictionaryItemsConfigModel


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
    verbose_name_plural = "Dictionary Iteam"


class ModelDictionaryConfigAdmin(BaseAuditAdmin):
    inlines = (ModelDictionaryItemsConfigInline,)
    list_display = [
        "code",
        "backend_app_label",
        "backend_app_model",
        "model_label",
        "is_active",
    ]
    list_filter = ["is_active"]
    search_fields = ["code", "description"]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # 如果是修改页面
            return ["code"]  # 在修改时将字段设为只读
        else:
            return []  # 在添加时字段可编辑


admin.site.register(ModelDictionaryConfigModel, ModelDictionaryConfigAdmin)


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


admin.site.register(ModelDictionaryItemsConfigModel, ModelDictionaryItemsConfigAdmin)

# class ModelDictionaryItemsConfigModelAdmin(BaseAuditAdmin):
#     list_display = ['dictionary','backend_field_name', 'field_label']
#     # search_fields = ['code', 'description']
# admin.site.register(ModelDictionaryItemsConfigModel, ModelDictionaryItemsConfigModelAdmin)
