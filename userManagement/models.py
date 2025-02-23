from django.db import models
from base.models import BaseAuditModel
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db.models import Q
from base.validators import get_validator
from django.core.cache import cache
from base.cache import global_class_cache_decorator, global_instance_cache_decorator
from base.util import normalized_url
from base import constants
from django.conf import settings

import json
from base.util import CustomJSONEncoder


TITLE_CHOICE = (
('Mr.', 'Mr.'),
('Ms.', 'Ms.'),
('Mrs.', 'Mrs.'),
('Mx.', 'Mx.'),
)

CONTROL_TYPE_CHOICE = (
    ('app', 'App'),
    ('company', 'Company'),
    ('department', 'Department'),
    ('team', 'Team')
)

class Company(BaseAuditModel):
    short_name = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=127, unique=True)
    manager = models.ForeignKey('CustomUser', on_delete=models.PROTECT, related_name='company_manager', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '%s (%s)'%(self.full_name, self.short_name)

    @global_class_cache_decorator(cache_key='company_list', timeout=settings.CACHE_TIMEOUT_L3)
    def get_list(cls):
        company = cls.objects.all()
        return company
    
    @global_class_cache_decorator (cache_key='company_list_active', timeout=settings.CACHE_TIMEOUT_L3)
    def get_active_list(cls):
        company = cls.objects.filter(is_active=True)
        return company
    
class Department(BaseAuditModel):
    short_name = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=127, unique=True)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='department_company')
    manager = models.ForeignKey('CustomUser', on_delete=models.PROTECT, related_name='department_manager', blank=True, null=True)
    senior_manager = models.ForeignKey('CustomUser', on_delete=models.PROTECT, related_name='department_senior_manager', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '%s (%s)'%(self.full_name, self.short_name)
    
    @global_class_cache_decorator(cache_key='department_list', timeout=settings.CACHE_TIMEOUT_L3)
    def get_list(cls):
        department = Department.objects.all()
        return department

    @global_class_cache_decorator(cache_key='department_list_active', timeout=settings.CACHE_TIMEOUT_L3)
    def get_active_list(cls):
        department = Department.objects.filter(is_active=True)
        return department
    
class Team(BaseAuditModel):
    short_name = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=127, unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='team_department')
    manager = models.ForeignKey('CustomUser', on_delete=models.PROTECT, related_name='team_manager', blank=True, null=True)
    first_support = models.ForeignKey('CustomUser', on_delete=models.PROTECT, related_name='team_first_support', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '%s (%s)'%(self.full_name, self.short_name)
    
    @global_class_cache_decorator(cache_key='team_list', timeout=settings.CACHE_TIMEOUT_L3)
    def get_list(cls):
        team = cls.objects.all()
        return team
    
    @global_class_cache_decorator(cache_key='team_list_active', timeout=settings.CACHE_TIMEOUT_L3)
    def get_active_list(cls):
        team = cls.objects.filter(is_active=True)
        return team
    
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     if self.manager is not None and (self.manager.team.count()==0 or self.manager.team.filter(id=self.id) is None):
    #         user  = CustomUser.objects.get(id=self.manager.id)
    #         user.team.add(self)
    #         user.save()
    #     if self.first_support is not None and (self.first_support.team.count()==0 or self.first_support.team.filter(id=self.id) is None):
    #         user  = CustomUser.objects.get(id=self.first_support.id)
    #         user.team.add(self)
    #         user.save()


# {'key': 'jsonForm', 'label': 'Request Form', 'icon': 'fa fa-file-text', 'link':'jsonForm:index', 'type':'team'},
class AppMenu(BaseAuditModel):
    """
    Represents a menu item or function within the application.  This model defines
    the structure and behavior of the application's navigation menu.
    """

    key = models.CharField(max_length=31, validators=[get_validator('no_space_str_w_')],
                            help_text="Unique identifier for the menu item (no spaces or special characters except '_').")
    label = models.CharField(max_length=63, help_text="Display label for the menu item.")
    icon = models.CharField(max_length=31, blank=True, null=True, help_text="Icon class or name for the menu item.")
    link = models.CharField(max_length=255, blank=True, null=True, help_text="URL or link associated with the menu item.")
    control_type = models.CharField(max_length=31, choices=CONTROL_TYPE_CHOICE, blank=True, null=True,
                                    help_text="Type of control (e.g., 'App', 'Department', 'Team'). If empty, this is not a top-level menu/app.")
    parent_app_menu = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, help_text="Parent menu item. Null for top-level menus.") # Changed 'AppMenu' to 'self'
    menu_level = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(5)], help_text="Menu level (0 for top-level, 1 for first sub-level, etc.). Max 5 levels.")
    is_active = models.BooleanField(default=False, help_text="Whether the menu item is active and visible.")
    diango_view = models.CharField(max_length=127, blank=True, null=True, help_text="Name of the Django view to call (if applicable).") # this field is not used for now, but will be used to store the django view name better debug and maintenance
    unit_control = models.BooleanField(default=False, help_text="Whether unit (department/team) control is enforced for this menu item.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['key', 'label', 'link', 'menu_level', 'parent_app_menu'], name='unique App menu'),
            models.UniqueConstraint(fields=['key', 'menu_level', 'parent_app_menu'], name='unique App menu key')
        ]

    def __str__(self) -> str:
        if self.menu_level == 0:
            return f"[Active:{self.is_active}][App Control Level:{self.control_type or 'N/A'}] {self.label}" # Improved string representation
        else:
            return f"[Active:{self.is_active}]-[Level:{self.menu_level}]-[{self.parent_app_menu}]-{self.label}"

    def save(self, *args, **kwargs):
        """
        Validates and saves the AppMenu instance.
        Ensures that menu_level and control_type are used consistently.
        """
        if (self.control_type is not None and self.menu_level != 0) or (self.control_type is None and self.menu_level == 0):
            raise ValidationError(
                '"control_type" must be defined for top-level menus (menu_level=0) and should be None for sub-menus (menu_level > 0).',
                code='invalid_input'
            )
        if self.menu_level == 0 and AppMenu.objects.filter(label=self.label, control_type=None, menu_level=0).exists():
            raise ValidationError(
                '"label" for top-level menus must be unique.',
                code='invalid_input'
            )
        super().save(*args, **kwargs)

    @classmethod
    def build_menu_tree(cls, menu_items, user=None):
        """
        Builds a nested menu tree structure from a queryset of AppMenu objects.
        Handles user permissions and unit control.
        """
        menu_items = menu_items.prefetch_related('group_menus__permission_role') # Optimize query
        menu_dict = {}

        for item in menu_items:
            if user:
                role_unit = list(item.group_menus.filter(is_active=True, permission_role__user_permissions=user).values(
                    'id', 'name', 'group_type', 'permission_role__id', 'permission_role__app__key',
                    'permission_role__company__short_name', 'permission_role__department__short_name',
                    'permission_role__team__short_name'
                ).distinct())
            else:
                role_unit = list(item.group_menus.filter(is_active=True).values(
                    'id', 'name', 'group_type', 'permission_role__id', 'permission_role__app__key',
                    'permission_role__company__short_name', 'permission_role__department__short_name',
                    'permission_role__team__short_name'
                ).distinct())

            new_role = []
            link = item.link.lower() if item.link else '' # Simplified conditional
            for p in role_unit:
                p_app = (p.get('permission_role__app__key') or '').lower() # Simplified conditional
                if item.unit_control:
                    department = (p.get('group_menus__permission_role__department__short_name') or '').lower()
                    team = (p.get('group_menus__permission_role__team__short_name') or '').lower()
                    if f'/{p_app}/' in link and (f'/{department}/{team}/' in link or f'/{department}/all/' in link):
                        new_role.append(p)
                elif f'/{p_app}/' in link:
                    new_role.append(p)

            if item.unit_control and not new_role: # More Pythonic check
                menu_dict[item.id] = None # Remove if no roles
            else:
                menu_dict[item.id] = {
                    'id': item.id,
                    'key': item.key,
                    'label': item.label,
                    'link': item.link,
                    'icon': item.icon,
                    'sub_menu': [],
                    'menu_level': item.menu_level,
                    'parent_app_menu__id': item.parent_app_menu_id if item.parent_app_menu else None, # Accessing id directly.
                    'parent_app_menu__key': item.parent_app_menu.key if item.parent_app_menu else None, # Accessing id directly.
                    'unit_control': item.unit_control,
                    'role_unit': new_role
                }

        for item in menu_items:
            if item.parent_app_menu and menu_dict.get(item.parent_app_menu_id) and menu_dict.get(item.id): # Combined and more efficient condition
                menu_dict[item.parent_app_menu_id]['sub_menu'].append(menu_dict[item.id])

        return menu_dict

    @global_class_cache_decorator(cache_key='menu_tree_active', timeout=settings.CACHE_TIMEOUT_L3)
    def get_menu_tree(cls):
        """
        Retrieves the active menu tree structure from the database and caches it.
        """
        menu_items = cls.objects.filter(is_active = True).order_by('menu_level')
        menu_dict = cls.build_menu_tree(menu_items)
        return [ v for k, v in menu_dict.items()]

    @global_class_cache_decorator(cache_key='menu_tree_active', timeout=settings.CACHE_TIMEOUT_L3)
    def get_menu_tree_by_id_key(cls, menu_id, menu_key):
        """
        Retrieves a specific menu item from the active menu tree based on its ID and key.

        Args:
            menu_id: The ID of the menu item.
            menu_key: The key of the menu item.

        Returns:
            The menu item dictionary if found, otherwise None.  Returns None if menu_id or menu_key does not match.
        """
        menu_list = cls.get_menu_tree()  # Get the entire menu tree (cached)
        return next((m for m in menu_list if m.get('id') == menu_id and m.get('key') == menu_key), None) # Corrected to m.get('id')


    @global_class_cache_decorator(cache_key='app_tree_active', timeout=settings.CACHE_TIMEOUT_L3)
    def get_app_tree(cls):
        """
        Retrieves the top-level app menu items (menu_level = 0) from the active menu tree.

        Returns:
            A list of top-level app menu item dictionaries.
        """
        app = [a for a in cls.get_menu_tree() if a.get('menu_level') == 0]
        return app

    @global_class_cache_decorator(cache_key='app_instance', timeout=settings.CACHE_TIMEOUT_L3)
    def get_app_instance_by_key(cls, app_name):
        """
        Retrieves a specific top-level app menu instance based on its key.

        Args:
            app_name: The key of the app menu instance.

        Returns:
            The AppMenu object if found, otherwise None.
        """
        try:
            app = cls.objects.get(key=app_name, menu_level=0, is_active=True) # Use .get() directly, more efficient.
            return app
        except cls.DoesNotExist:
            return None


    @global_class_cache_decorator(cache_key='app_form', timeout=settings.CACHE_TIMEOUT_L3)
    def get_app_form_by_id(cls, app_id):
        """
        Retrieves the first associated form (TemplateApplication) for a given app by its ID.

        Args:
            app_id: The ID of the app.

        Returns:
            The first associated TemplateApplication object if found, otherwise None.
        """
        try:
            app = cls.objects.get(id=app_id, menu_level=0, is_active=True)
        except cls.DoesNotExist:
            return None

        forms = app.template_application.all()
        return forms.first() if forms.exists() else None # More concise way to return None if no forms


    @global_class_cache_decorator(cache_key='app_form', timeout=settings.CACHE_TIMEOUT_L3)
    def get_app_form_by_key(cls, app_name):
        """
        Retrieves the first associated form (TemplateApplication) for a given app by its key.

        Args:
            app_name: The key of the app.

        Returns:
            The first associated TemplateApplication object if found, otherwise None.
        """
        try:
            app = cls.objects.get(key=app_name, menu_level=0, is_active=True)
        except cls.DoesNotExist:
            return None

        forms = app.template_application.all()
        return forms.first() if forms.exists() else None # More concise way to return None if no forms

    @global_class_cache_decorator(cache_key='menu_permission_roles_by_url', timeout=settings.CACHE_TIMEOUT_L3)
    def get_permission_roles_by_url(cls,url,department=None, team=None):
        link = normalized_url(url)
        if link == '':
            return []
        queryset = cls.objects.filter(link=link, group_menus__is_active=True)
        queryset.prefetch_related('group_menus__permission_role') # Optimize queryset with prefetch_related

        if Team is not None:
            queryset = queryset.filter(group_menus__permission_role__team=team)
        if department is not None:
            queryset = queryset.filter(group_menus__permission_role__department=department)
        
        return queryset.values('''
            group_menus__id, group_menus__name, group_menus__group_type, group_menus__permission_role__id, group_menus__permission_role__app__key,
            group_menus__permission_role__company__short_name, group_menus__permission_role__department__short_name,
            group_menus__permission_role__team__short_name
        ''').distinct()

    @global_class_cache_decorator(cache_key='menu_permission_users_by_url', timeout=settings.CACHE_TIMEOUT_L3)
    def get_permission_users_by_url(cls,url,department=None, team=None):
        link = normalized_url(url)
        if link == '':
            return []
        queryset = cls.objects.filter(link=link, group_menus__is_active=True, is_active=True) # Ensure the menu is active (_
        queryset.prefetch_related('group_menus__permission_role') # Optimize queryset with prefetch_related

        if Team is not None:
            queryset = queryset.filter(group_menus__permission_role__team=team)
        if department is not None:
            queryset = queryset.filter(group_menus__permission_role__department=department)
            
        return queryset.values('''
            group_menus__permission_role__user_permissions__email, group_menus__permission_role__user_permissions__first_name, group_menus__permission_role__user_permissions__last_name
        ''').annotate(
            email=F('group_menus__permission_role__user_permissions__email'),
            first_name=F('group_menus__permission_role__user_permissions__first_name'),
            last_name=F('group_menus__permission_role__user_permissions__last_name')
        ).distinct()

# Built-in roles
# Admin (Django Built-in)
# Case Creator (will not be used to assign permission, only in used on workflow task assignment)
# User Admin (ID Admin for OSD and RSD)
# Company Manager
# Department Senior Manager
# Department Manager
# Team Manager

class CustomGroup(Group, BaseAuditModel):  # Assuming BaseAuditModel is defined elsewhere
    """
    Custom group model extending Django's built-in Group model.  This model represents roles
    within the application and manages permissions and menu access.
    """
    group_type = models.PositiveSmallIntegerField(choices=constants.GROUP_TYPE_CHOICE, blank=True, null=True, help_text='''
        If group type is empty, which means this is a basic group and not a role for assigning to business user

        # [App Name] role only apply for specific application, so apps.count = 1, and this role is applicatable to which team/department/company that the user has permission to
        # Normal [team/department/company] role is applicable for selected application, and this role is applicatable to which team/department/company that the user belongs to
        # [team/department/company] manager role is applicable for selected application, and this role is applicatable to which team/department/company that the user belongs to
        # team/department/company] role is applicable for selected application, and this role is applicatable to which team/department/company that the user has permission to
    ''')  # Clarify the different group types in the help text
    is_active = models.BooleanField(default=True)  # Whether the group/role is active
    menus = models.ManyToManyField(AppMenu, related_name='group_menus', blank=True)  # Menus associated with this role

    class Meta:
        verbose_name = 'group'  # Consistent naming
        verbose_name_plural = 'groups'

    def __str__(self):
        """
        String representation of the CustomGroup object.
        """
        return f'[{self.group_type}]{self.name}'  # Use the name field from the built-in Group model

    # No other methods are defined in this class.  Usually, permission assignment
    # and other role-related logic would be implemented here or in related models/managers.

    # Example of a method you might add (permission management is usually handled through Django's built-in mechanisms):
    # def assign_permissions(self, permissions):
    #     """Assigns a list of permissions to this group."""
    #     # ... your logic to assign permissions ...

    @global_instance_cache_decorator(cache_key='group_active_user_list', timeout=settings.CACHE_TIMEOUT_L3)
    def get_active_users(self):
        """Gets a list of users associated with this group."""
        return self.user_set.filter(is_active=True) # Use the built-in user_set attribute

    @classmethod
    def get_team_group_type(cls):
        return constants.ROLE_TEAM_GROUP_TYPE
    @classmethod
    def get_department_group_type(cls):
        return constants.ROLE_DEPARTMENT_GROUP_TYPE
    @classmethod
    def get_company_group_type(cls):
        return constants.ROLE_COMPANY_GROUP_TYPE
    @classmethod
    def get_belongs_group_type(cls):
        return constants.ROLE_BELONGS_GROUP_TYPE
    @classmethod
    def get_perms_group_type(cls):
        return constants.ROLE_PERMS_GROUP_TYPE
    @classmethod
    def get_team_belongs_group_type(cls):
        return constants.ROLE_TEAM_BELONGS_GROUP_TYPE
    @classmethod
    def get_department_belongs_group_type(cls):
        return constants.ROLE_DEPARTMENT_BELONGS_GROUP_TYPE
    @classmethod
    def get_company_belongs_group_type(cls):
        return constants.ROLE_COMPANY_BELONGS_GROUP_TYPE
    @classmethod
    def get_manager_group_type(cls):
        return constants.ROLE_MANAGER_GROUP_TYPE


# company/department/team is for data control, not access control, like KYC and CMT, data owns by different depertment or teams
# if other company/department/team need to see the data or edit the data, he/she should have the data permission which is controled by Permission
# Page access is controled by Role
# APP defines the app data belongs to which company/department/team (some data may not have data control, some data required data control, etc.)
# if there is no data access control required, use [APP] control type in AppMenu
class Permission(BaseAuditModel):  # Assuming BaseAuditModel is defined elsewhere
    """
    Represents a permission granting access to data within a specific app, optionally scoped
    by company, department, and team.  Permissions are associated with roles (CustomGroups).
    """
    role = models.ForeignKey(CustomGroup, on_delete=models.CASCADE, related_name='permission_role', blank=True, null=True)  # Role that this permission is granted to
    app = models.ForeignKey(AppMenu, on_delete=models.CASCADE, related_name='permission_app')  # App that this permission applies to
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=True, null=True, related_name='permission_team')  # Team scope for the permission (optional)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, blank=True, null=True, related_name='permission_department')  # Department scope for the permission (optional)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, blank=True, null=True, related_name='permission_company')  # Company scope for the permission (optional)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['role', 'app', 'team', 'department', 'company'], name='unique permisson')  # Ensure unique permissions
        ]

    def __str__(self) -> str:
        """
        String representation of the Permission object.
        """
        return f'[{self.role}][app:{self.app}][company:{self.company}][department:{self.department}][team:{self.team}]'

    def save(self, *args, **kwargs):
        """
        Custom save method to enforce business rules.  Ensures that only roles with a `group_type`
        (i.e., not basic groups) can be used for permissions.
        """
        if self.role is not None and self.role.group_type is None:
            raise ValidationError(
                'The group you select is a basic group. Only the group with "group_type" is used to assign to the user',
                code='invalid_role'
            )
        super().save(*args, **kwargs)

    @property
    def department_list(self):
        """
        Returns a list of departments associated with this permission.  Includes both the directly
        associated department and the department of the associated team (if any).
        """
        return [self.department, self.team.department] if self.team is not None else [self.department]

    @property
    def company_list(self):
        """
        Returns a list of companies associated with this permission. Includes both the directly
        associated company and the company of the associated department (if any).
        """
        return [self.company, self.department.company] if self.department is not None else [self.company]


    @classmethod
    def selected_fields_info(cls):
        """
        Returns information about selected permission fields.

        Returns:
            Field information (currently hardcoded).
        """
        fields = ['app__label', 'role__name', 'company__full_name', 'department__full_name', 'team__full_name']
        field_info = Permission.get_selected_fields_info(fields) 
        return field_info

    @classmethod
    def get_assign_to_role(cls, app, role, case):
        """
        Retrieves a specific permission based on the app, role, and case details.  This function seems to implement
        complex logic to determine the appropriate permission based on the role type and app control type.

        Args:
            app: The AppMenu object.
            role: The CustomGroup object.
            case: The case object (details about the case).

        Returns:
            A Permission object or None if no matching permission is found.
        """
        filter = Q(app=app, role=role)
        if role.name == constants.ROLE_CASE_OWNER:  
            filter = Q(app=app, user_permissions=case.created_by, role__menus__key=f'createCase{case.form.code}') 
        elif app.control_type != 'app' and role.group_type in CustomGroup.get_team_group_type(): 
            filter &= Q(team=case.case_team)  # Filter by case team
        elif app.control_type != 'app' and role.group_type in CustomGroup.get_department_group_type(): 
            filter &= Q(team__isnull=True, department=case.case_department)  # Filter by case department
        elif app.control_type != 'app' and role.group_type in CustomGroup.get_company_group_type(): 
            filter &= Q(team__isnull=True, department__isnull=True, company=case.case_department.company)  # Filter by case company
        else:
            filter &= Q(team__isnull=True, department__isnull=True, company__isnull=True)  # No data control

        return Permission.objects.filter(filter).first()

    @property
    def get_perm_user_department(self, user):
        """
        Gets the department associated with the permission, considering the app's control type.

        Args:
            user: The user object.

        Returns:
            The department object.
        """
        return self.department if self.app.control_type != 'app' else user.department

    @property
    def get_perm_user_company(self, user):
        """
        Gets the company associated with the permission, considering the app's control type.

        Args:
            user: The user object.

        Returns:
            The company object.
        """
        return self.company if self.app.control_type != 'app' else user.company

class CustomUser(AbstractUser, BaseAuditModel):  
    """
    Custom user model extending Django's AbstractUser.
    """
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='user_company', blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='user_department', blank=True, null=True)
    team = models.ManyToManyField(Team, related_name='user_team', blank=True)
    position = models.CharField(max_length=63, blank=True, null=True)
    office_phone = models.CharField(validators=[get_validator('phone_regex')], max_length=15, blank=True, null=True, help_text='Format:"000-000-0000"')
    mobile = models.CharField(validators=[get_validator('phone_regex')], max_length=15, blank=True, null=True, help_text='Format:"000-000-0000"')
    title = models.CharField(max_length=15, choices=TITLE_CHOICE, blank=True, null=True) 
    permissions = models.ManyToManyField(Permission, related_name='user_permissions', blank=True)
    groups = models.ManyToManyField(
        CustomGroup,  # Use your custom group model
        verbose_name='roles',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='groups',
        related_query_name='user',
    )

    def __str__(self) -> str:
        """
        String representation of the CustomUser object.
        """
        return f'{self.title} {self.first_name} {self.last_name} ({self.username})' if self.title else f'{self.first_name} {self.last_name} ({self.username})'

    @global_instance_cache_decorator(cache_key='user_menu_tree', timeout=settings.CACHE_TIMEOUT_L2)
    def get_user_menu_tree(self):
        """
        Retrieves the menu tree structure for this user, filtered by their permissions.

        Returns:
            A list representing the user's menu tree.  Returns an empty list if no menu items are found.
        """
        menu_items = AppMenu.objects.filter(
            group_menus__permission_role__user_permissions=self,
            is_active=True
        ).distinct().order_by('menu_level')
        menu_dict = AppMenu.build_menu_tree(menu_items, self) # Use AppMenu's build_menu_tree method
        return [v for k, v in menu_dict.items() if v is not None] # Filter out None values


    @global_instance_cache_decorator(cache_key='user_app_tree', timeout=settings.CACHE_TIMEOUT_L2)
    def get_user_app_tree(self):
        """
        Retrieves the top-level app menu items (menu_level=0) for this user.

        Returns:
            A tuple containing:
                - A list of top-level app menu items.
                - The full menu tree (redundant, consider removing).
        """
        menu = self.get_user_menu_tree() 
        app = [a for a in menu if a.get('menu_level') == 0]
        return app


    @classmethod
    def selected_fields_info(cls):
        """
        Returns information about selected user fields.  (It appears the implementation of this function is duplicated from another class, consider refactoring).

        Returns:
            Field information (currently just a hardcoded list).
        """
        fields = ['id', 'username', 'first_name', 'last_name', 'title', 'email', 'office_phone', 'mobile', 'company__full_name', 'department__full_name', 'position', 'last_login', 'date_joined', 'is_active', 'is_superuser', 'is_staff']
        field_info = CustomUser.get_selected_fields_info(fields)
        return field_info

    @global_class_cache_decorator(cache_key='user_list', timeout=settings.CACHE_TIMEOUT_L3)
    def get_list(cls):
        """
        Retrieves a list of all users.

        Returns:
            A queryset of all CustomUser objects.
        """
        users = cls.objects.all()
        return users

    @global_class_cache_decorator(cache_key='user_list_active', timeout=settings.CACHE_TIMEOUT_L3)
    def get_active_list(cls):
        """
        Retrieves a list of all active users.

        Returns:
            A queryset of all active CustomUser objects.
        """
        users = cls.objects.filter(is_active=True)
        return users

    @global_class_cache_decorator(cache_key='user_info')
    def get_user_info(cls, id):
        """Retrieves detailed information about the user."""
        fields = cls.selected_fields_info()
        user_info = cls.objects.filter(id=id).values(*fields)
        user_info = list(user_info)[0]
        return  json.loads(json.dumps(user_info, cls=CustomJSONEncoder))
