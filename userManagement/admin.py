from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Company,
    Department,
    Team,
    CustomUser,
    AppMenu,
    Permission,
    CustomGroup,
)
from .forms import (
    CustomUserChangeForm,
    CustomUserCreationForm,
    AppMenuUpdateForm,
    PermissionInlineFormset,
    PermissionlineForm,
    CustomGroupForm,
    AppMenuCreateForm,
    AppMenuInlineCreateForm,
    AppMenuInlineUpdateForm,
)
from base.admin import BaseAuditAdmin, default_readonly_fields


class DepartmentInline(admin.TabularInline):
    model = Department
    can_delete = False
    extra = 1
    fields = [
        "short_name",
        "full_name",
        "senior_manager",
        "manager",
        "is_active",
    ]
    verbose_name_plural = "Departments"


class TeamInline(admin.TabularInline):
    model = Team
    can_delete = False
    extra = 1
    fields = ["short_name", "full_name", "manager", "is_active"]
    verbose_name_plural = "Teams"


class UserInline(admin.TabularInline):
    model = CustomUser
    can_delete = False
    extra = 1
    fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "department",
        "position",
    ]
    verbose_name_plural = "Users"


class CompanyAdmin(BaseAuditAdmin):
    inlines = (DepartmentInline,)
    list_display = ["full_name", "short_name", "is_active", "manager"]
    list_filter = ["is_active"]
    search_fields = ["full_name", "short_name"]


admin.site.register(Company, CompanyAdmin)


class DepartmentAdmin(BaseAuditAdmin):
    inlines = (
        TeamInline,
        UserInline,
    )
    list_display = [
        "company",
        "full_name",
        "short_name",
        "is_active",
        "senior_manager",
        "manager",
    ]
    list_filter = ["company", "is_active"]
    search_fields = ["full_name", "short_name"]


admin.site.register(Department, DepartmentAdmin)


class TeamAdmin(BaseAuditAdmin):
    # inlines = (UserInline, )
    list_display = ["department", "full_name", "short_name", "is_active", "manager"]
    list_filter = ["department", "is_active"]
    search_fields = ["full_name", "short_name"]


admin.site.register(Team, TeamAdmin)


class SelectPermissionline(admin.TabularInline):
    model = Permission
    form = PermissionlineForm
    formset = PermissionInlineFormset
    fields = ["existing_permission"]
    extra = 1
    can_delete = False
    verbose_name_plural = "Select Permission"

    def get_formset(self, request, obj=None, **kwargs):
        # Pass the parent instance to the formset
        formset = super().get_formset(request, obj, **kwargs)
        formset.form = self.get_form_with_parent_instance(formset.form, obj)
        return formset

    def get_form_with_parent_instance(self, form_class, parent_instance):
        class FormWithParentInstance(form_class):
            def __init__(self, *args, **kwargs):
                kwargs["parent_instance"] = parent_instance
                super().__init__(*args, **kwargs)

        return FormWithParentInstance

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Get the parent department instance from the request
        if self.parent_model:
            parent_obj_id = self.get_parent_object_id(request)
            if parent_obj_id is not None:
                g = CustomGroup.objects.get(id=parent_obj_id)
                if g.group_type == 1:
                    return qs.filter(role__isnull=True, app__control_type="app")
                if g.group_type in CustomGroup.get_company_group_type():
                    return qs.filter(
                        role__isnull=True,
                        app__control_type__in=["company", "department", "team"],
                    )
                if g.group_type in CustomGroup.get_department_group_type():
                    return qs.filter(
                        role__isnull=True, app__control_type__in=["department", "team"]
                    )
                if g.group_type in CustomGroup.get_team_group_type():
                    return qs.filter(role__isnull=True, app__control_type__in=["team"])
        # Fallback: return an empty queryset if no parent object is found
        return qs.none()

    def get_parent_object_id(self, request):
        # Parse the request path to get the parent object ID
        path_components = request.path.split("/")
        if "change" in path_components:
            parent_obj_id_index = path_components.index("change") - 1
            return path_components[parent_obj_id_index]
        return None


class CustomUserAdmin(UserAdmin, BaseAuditAdmin):

    list_display = [
        "username",
        "company",
        "department",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "is_superuser",
    ]
    search_fields = ["username", "first_name", "last_name", "email"]
    readonly_fields = ("last_login", "date_joined")
    list_filter = ["department", "company", "team"]
    fieldsets = [
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "title",
                    "email",
                    "office_phone",
                    "mobile",
                    "company",
                    "department",
                    "team",
                    "position",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "permissions")},
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined") + default_readonly_fields},
        ),
    ]

    add_fieldsets = (
        (None, {"fields": ("username",)}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "title",
                    "email",
                    "office_phone",
                    "mobile",
                    "company",
                    "department",
                    "team",
                    "position",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "permissions")},
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        """
        Use a custom form for updating instances and the default form for creating new instances.
        """
        if obj:  # If `obj` is not None, we are updating an existing instance
            kwargs["form"] = CustomUserChangeForm
        else:
            kwargs["form"] = CustomUserCreationForm
        return super().get_form(request, obj, **kwargs)


admin.site.register(CustomUser, CustomUserAdmin)


class AppMenuInline(admin.TabularInline):
    model = AppMenu
    can_delete = False
    extra = 1
    verbose_name_plural = "Sub Menu"

    def get_formset(self, request, obj=None, **kwargs):
        if obj:
            if any(child.pk for child in obj.appmenu_set.all()):
                kwargs["form"] = AppMenuInlineUpdateForm
            else:
                kwargs["form"] = AppMenuInlineCreateForm
        else:
            kwargs["form"] = AppMenuInlineCreateForm
        return super().get_formset(request, obj, **kwargs)

    def get_form_with_parent_instance(self, form_class, parent_instance):
        class FormWithParentInstance(form_class):
            def __init__(self, *args, **kwargs):
                kwargs["parent_instance"] = parent_instance
                super().__init__(*args, **kwargs)

        return FormWithParentInstance


class CreateMenuline(admin.TabularInline):
    model = AppMenu
    form = AppMenuInlineCreateForm
    # formset = AppmenulineFormset
    extra = 1
    can_delete = False
    verbose_name_plural = "Create Menu"

    def get_formset(self, request, obj=None, **kwargs):
        # Pass the parent instance to the formset
        formset = super().get_formset(request, obj, **kwargs)
        formset.form = self.get_form_with_parent_instance(formset.form, obj)
        return formset

    def get_form_with_parent_instance(self, form_class, parent_instance):
        class FormWithParentInstance(form_class):
            def __init__(self, *args, **kwargs):
                kwargs["parent_instance"] = parent_instance
                super().__init__(*args, **kwargs)

        return FormWithParentInstance

    def get_parent_object_id(self, request):
        # Parse the request path to get the parent object ID
        path_components = request.path.split("/")
        if "change" in path_components:
            parent_obj_id_index = path_components.index("change") - 1
            return path_components[parent_obj_id_index]
        return None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.none()


class ExistedMenuInline(admin.TabularInline):
    model = AppMenu
    can_delete = True
    extra = 1
    form = AppMenuInlineUpdateForm
    verbose_name_plural = "Existed Menus"


class AppMenuAdmin(BaseAuditAdmin):
    list_display = [
        "application_menu_display",
        "key",
        "label",
        "control_type",
        "link",
        "parent_app_menu",
        "is_active",
        "menu_level",
    ]
    list_filter = ["menu_level", "is_active", "control_type"]
    search_fields = ["key", "label", "link"]
    inlines = (CreateMenuline, ExistedMenuInline)
    readonly_fields = (
        "application_menu_display",
    )  # Make it read-only in the detail view

    def get_form(self, request, obj=None, **kwargs):
        """
        Use a custom form for updating instances and the default form for creating new instances.
        """
        if obj:  # If `obj` is not None, we are updating an existing instance
            kwargs["form"] = AppMenuUpdateForm
        else:
            kwargs["form"] = AppMenuCreateForm
        return super().get_form(request, obj, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # 如果是修改页面
            return ["key"]  # 在修改时将字段设为只读
        else:
            return []  # 在添加时字段可编辑

    def get_inline_instances(self, request, obj=None):
        # Only show inlines if the object already exists (i.e., this is an update)
        if obj is not None:  # obj will be None when creating a new object
            return super().get_inline_instances(request, obj)
        return (
            []
        )  # Return an empty list, which means no inlines will be shown for creation

    @admin.display(description="Application Menu")
    def application_menu_display(self, obj):
        # 'obj' is the model instance
        parent = obj.parent_app_menu
        label = obj.label
        while parent:  # Assuming 0 is the top level menu
            label = (
                "%s[L%s]::%s" % (parent.label, parent.menu_level, label)
                if parent.menu_level != 0
                else "%s::%s" % (parent.label, label)
            )
            parent = parent.parent_app_menu
        return label  # HTML is allowed, but escape if needed (see below)


admin.site.register(AppMenu, AppMenuAdmin)


class AppFilter(admin.SimpleListFilter):
    title = "App"  # The title for the filter
    parameter_name = "app"  # The URL parameter for the filter

    def lookups(self, request, model_admin):
        # Return a list of tuples, each containing the ID and display name
        specific_instances = AppMenu.objects.filter(
            menu_level=0
        )  # Replace with your specific IDs
        return [(instance.id, str(instance)) for instance in specific_instances]

    def queryset(self, request, queryset):
        # Filter the queryset based on the selected value
        if self.value():
            return queryset.filter(app__id=self.value())
        return queryset


class PermissionAdmin(BaseAuditAdmin):
    list_display = ["role", "app", "team", "department", "company"]
    list_filter = ["role", AppFilter, "team", "department", "company"]


admin.site.register(Permission, PermissionAdmin)


class PermissionInline(admin.TabularInline):
    model = Permission
    can_delete = True
    extra = 0  # 不显示额外的空白表单
    max_num = 0  # 禁用添加新项
    fields = ["app", "company", "department", "team"]
    readonly_fields = ("app", "company", "department", "team")
    verbose_name_plural = "Existed Permission"


class CustomGroupAdmin(BaseAuditAdmin):
    list_display = ["name", "group_type", "is_active"]
    list_filter = ["group_type", "is_active"]
    inlines = (
        SelectPermissionline,
        PermissionInline,
    )
    form = CustomGroupForm
    # readonly_fields_for_update = ('group_type', )


admin.site.register(CustomGroup, CustomGroupAdmin)
