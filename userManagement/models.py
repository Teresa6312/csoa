from django.db import models
from base.models import BaseAuditModel
from django.contrib.auth.models import AbstractUser, Group
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from base.redis import create_redis_key, create_redis_key_queryset, create_redis_key_json, get_redis_data_json
from django.core.validators import MaxValueValidator
from django.db.models import Q
from base.validators import get_validator

TITLE_CHOICE = (
('Mr.', 'Mr.'),
('Ms.', 'Miss'),
('Mrs.', 'Mrs.'),
('Mx.', 'Mx.'),
)

# APP_CHOICE = ( (a['key'], a['label']) for a in APP_LIST )

CONTROL_TYPE_CHOICE = (
    ('app', 'App'),
    ('company', 'Company'),
    ('department', 'Department'),
    ('team', 'Team')
)

GROUP_TYPE_CHOICE = (
    (1, '[App Name] role'),
    (2, 'Normal Team role'),
    (3, 'Normal Department role'),
    (4, 'Normal Company role'),
    (5, 'Team Manager role'),
    (6, 'Department Manager role'),
    (7, 'Company Manager role'),
    (8, 'Department Senior role'),
    (9, 'App Team role'),
    (10, 'App Department role'),
    (12, 'App Company role')
)

class Company(BaseAuditModel):
    short_name = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=127, unique=True)
    manager = models.ForeignKey('CustomUser', on_delete=models.PROTECT, related_name='company_manager', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '%s (%s)'%(self.full_name, self.short_name)

    @classmethod
    def company_list(cls):
        company = Company.objects.all()
        create_redis_key_queryset('company_list', company)
        return company

    @classmethod
    def company_list_active(cls):
        company = Company.objects.filter(is_active=True)
        create_redis_key_queryset('company_list_active', company)
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
    
    @classmethod
    def department_list(cls):
        department = Department.objects.all()
        create_redis_key_queryset('department_list', department)
        return department

    @classmethod
    def department_list_active(cls):
        department = Department.objects.filter(is_active=True)
        create_redis_key_queryset('department_list_active', department)
        return department
    
class Team(BaseAuditModel):
    short_name = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=127, unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='team_department')
    manager = models.ForeignKey('CustomUser', on_delete=models.PROTECT, related_name='team_manager', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '%s (%s)'%(self.full_name, self.short_name)
    
    @classmethod
    def team_list(cls):
        team = Team.objects.all()
        create_redis_key_queryset('team_list', team)
        return team
        
    @classmethod
    def team_list_active(cls):
        team = Team.objects.filter(is_active=True)
        create_redis_key_queryset('team_list_active', team)
        return team

# {'key': 'jsonForm', 'label': 'Request Form', 'icon': 'fa fa-file-text', 'link':'jsonForm:index', 'type':'team'},

class AppMenu(BaseAuditModel):
    key = models.CharField(max_length=31, validators=[get_validator('no_space_str_w_-')])
    label = models.CharField(max_length=63)
    icon = models.CharField(max_length=31, blank=True, null=True)
    link = models.CharField(max_length=63, blank=True, null=True)
    control_type = models.CharField(max_length=31, choices=CONTROL_TYPE_CHOICE, blank=True, null=True
                                    , help_text="If control type is empty, which means this is a menu/functions under the sub app")
    parent_app_menu = models.ForeignKey('AppMenu', on_delete=models.CASCADE, blank=True, null=True)
    menu_level = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(5)])
    is_active = models.BooleanField(default=False)
    diango_view = models.CharField(max_length=127, blank=True, null=True)
    data_control = models.BooleanField(default=False) 
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['key', 'label', 'link', 'menu_level', 'parent_app_menu'], name='unique App menu')
        ]

    def __str__(self) -> str:
        if self.menu_level == 0 :
            return '[Active:%s][App Control Level:%s] %s'%(self.is_active, self.control_type, self.label)
        else:
            return '[Active:%s]-[Level:%s]-[%s]-%s'%(self.is_active, self.menu_level,self.parent_app_menu,self.label)

    def save(self, *args, **kwargs):
        if (self.control_type is not None and self.menu_level != 0 )or  (self.control_type is  None and self.menu_level == 0 ):
            raise ValidationError(
                '"menu_level" is only appliable for the menu/function under a sub app',
                code='invalid_input'
            )
        if AppMenu.objects.filter(label = self.label, control_type = None, menu_level=0).count()>0:
            raise ValidationError(
                '"label" for sub app must be unique',
                code='invalid_input'
            )            
        super().save(*args, **kwargs)

    @classmethod
    def build_menu_tree(cls, menu_items):
        menu_dict = {}
        for item in menu_items:
            menu_dict[item.id] = {
                'key': item.key,
                'label': item.label,
                'link': item.link,
                'icon': item.icon,
                'subMenu': [],
                'menu_level': item.menu_level,
                'diango_view': item.diango_view,
                'data_control': item.data_control
            }
        menu_tree = []
        for item in menu_items:
            if item.parent_app_menu is not None and menu_dict.get(item.parent_app_menu.id, None) is not None:
                parent = menu_dict.get(item.parent_app_menu.id)
                parent['subMenu'].append(menu_dict[item.id])
            else:
                menu_tree.append(menu_dict[item.id])
        return menu_tree
    
    @classmethod
    def build_menu_tree_redis(cls):
        menu_items = AppMenu.objects.filter(is_active = True).order_by('menu_level')
        menus = AppMenu.build_menu_tree(menu_items)
        for m in menus:
            create_redis_key_json('menu_list_active_%s'%m['key'],  m)

    @classmethod
    def build_app_list_active_redis(cls):
        app = AppMenu.objects.filter(is_active = True, menu_level = 0)
        create_redis_key_queryset('app_list_active', app)

# Built-in roles
# Admin (Django Built-in)
# Case Creator (will not be used to assign permission, only in used on workflow task assignment)
# User Admin (ID Admin for OSD and RSD)
# Company Manager
# Department Senior Manager
# Department Manager
# Team Manager


class CustomGroup(Group, BaseAuditModel):
    group_type = models.PositiveSmallIntegerField(choices=GROUP_TYPE_CHOICE, blank=True, null=True, help_text='''
                                                  If group type is empty, which means this is a basic group and not a role for assigning to business user\n
                                                    # [App Name] role only apply for specific application, so apps.count = 1, and this role is applicatable to which team/department/company that the user has permission to
                                                    # Normal [team/department/company] role is applicable for selected application, and this role is applicatable to which team/department/company that the user belongs to
                                                    # [team/department/company] manager role is applicable for selected application, and this role is applicatable to which team/department/company that the user belongs to
                                                    # team/department/company] role is applicable for selected application, and this role is applicatable to which team/department/company that the user has permission to
                                                  ''')
    is_active = models.BooleanField(default=True)
    menus = models.ManyToManyField(AppMenu, related_name='group_menus', blank=True)
    class Meta:
        verbose_name = 'group'
        verbose_name_plural = 'groups'

    def __str__(self) -> str:
        return '[%s] %s'%(self.group_type, self.name)
    @classmethod
    def get_team_group_type(cls):
        return [2,5,9]
    @classmethod
    def get_department_group_type(cls):
        return [3,6,10,8]
    @classmethod
    def get_company_group_type(cls):
        return [4,7,12]
    @classmethod
    def get_belongs_group_type(cls):
        return [2,3,4,5,6,7,8]
    @classmethod
    def get_perms_group_type(cls):
        return [9,10, 12]
    @classmethod
    def get_team_belongs_group_type(cls):
        return [2,5]
    @classmethod
    def get_department_belongs_group_type(cls):
        return [3,6,8]
    @classmethod
    def get_company_belongs_group_type(cls):
        return [4,7]
    @classmethod
    def get_manager_group_type(cls):
        return [5,6,7,8]

# company/department/team is for data control, not access control, like KYC and CMT, data owns by different depertment or teams
# if other company/department/team need to see the data or edit the data, he/she should have the data permission which is controled by Permission
# Page access is controled by Role
# APP defines the app data belongs to which company/department/team (some data may not have data control, some data required data control, etc.)
# if there is no data access control required, use [APP] control type in AppMenu

class Permission(BaseAuditModel):
    role = models.ForeignKey(CustomGroup, on_delete=models.CASCADE,related_name='permission_role', blank=True, null=True)
    app = models.ForeignKey(AppMenu, on_delete=models.CASCADE,related_name='permission_app')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=True, null=True,related_name='permission_team')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, blank=True, null=True,related_name='permission_department')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, blank=True, null=True,related_name='permission_company')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['role', 'app', 'team', 'department', 'company'], name='unique permisson')
        ]
        
    def __str__(self) -> str:
        return '[%s][app:%s][company:%s][department:%s][team:%s]'%(self.role, self.app, self.company, self.department, self.team)

    def save(self, *args, **kwargs):
        if self.role is not None and self.role.group_type is None:
            raise ValidationError(
                'The group you select is a basic group. Only the group with "group_type" is used to assign to the user',
                code='invalid_role'
            )
        super().save(*args, **kwargs)
    
    @property
    def department_list(self):
        if self.team is not None:
            return [self.department, self.team.department]
        else:
            return [self.department,]
    @property
    def company_list(self):
        if self.department is not None:
            return [self.company, self.department.company]
        else:
            return [self.company,]

    @classmethod
    def selected_fields_info(cls):
        fields = ['app__label', 'role__name', 'company__full_name', 'department__full_name', 'team__full_name']  # List of fields you want to include
        field_info = Permission.get_selected_fields_info(fields)
        return field_info

    @classmethod
    def get_assign_to_role(cls, app, role, case):
        filter = Q(app = app, role=role)
        if role.name == 'Case Owner':
            filter = Q(app = app, user_permissions=case.created_by, role__menus__key=f'createCase{case.form.code}')
        elif app.control_type != 'app' and role.group_type in CustomGroup.get_team_group_type():
            filter &= Q(team = case.case_team)
        elif app.control_type != 'app' and role.group_type in CustomGroup.get_department_group_type():
            filter &= Q(team__isnull = True, department= case.case_department)
        elif app.control_type != 'app' and role.group_type in CustomGroup.get_company_group_type():
            filter &= Q(team__isnull = True, department__isnull = True, company = case.case_department.company)
        else:
            filter &= Q(team__isnull = True, department__isnull = True, company__isnull=True)
        return Permission.objects.filter(filter).first()

    @property
    def get_perm_user_department(self, user):
        if self.app.control_type != 'app':
            return self.department
        else:
            return user.department
    @property
    def get_perm_user_company(self, user):
        if self.app.control_type != 'app':
            return self.company
        else:
            return user.company
class CustomUser(AbstractUser, BaseAuditModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT,related_name='user_company', blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT,related_name='user_department', blank=True, null=True)
    team = models.ManyToManyField(Team, related_name='user_team', blank=True)
    position = models.CharField(max_length=63, blank=True, null=True)
    office_phone = models.CharField(validators=[get_validator('phone_regex')],max_length=15, blank=True, null=True, help_text= 'Format:"000-000-0000"')
    mobile = models.CharField(validators=[get_validator('phone_regex')],max_length=15, blank=True, null=True, help_text= 'Format:"000-000-0000"')
    title = models.CharField(max_length=15, choices=TITLE_CHOICE, blank=True, null=True)
    permissions = models.ManyToManyField(Permission, related_name='user_permissions', blank=True)
    groups = models.ManyToManyField(
        CustomGroup,
        verbose_name='roles',
        blank=True,
        help_text= 'The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='groups',
        related_query_name='user',
    )

    def __str__(self) -> str:
        return '%s %s %s (%s)'%(self.title, self.first_name, self.last_name, self.username)
    
    def get_user_roles(self):
        self.permissions.all().values('role').distinct()

    def get_user_menu_permissions(self):
        menus = get_redis_data_json(f'user_menu:{self.username}')
        if menus is None:
            value = AppMenu.objects.filter(
                group_menus__permission_role__user_permissions=self
            ).distinct()
            menu_all = AppMenu.build_menu_tree(value)
            create_redis_key_json(f'user_menu:{self.username}',  [m for m in menu_all if m.get('menu_level', '') == 0])
            menus = get_redis_data_json(f'user_menu:{self.username}')
        return menus
    @classmethod
    def selected_fields_info(cls):
        fields = ['id','username', 'first_name', 'last_name', 'title', 'email', 'office_phone', 'mobile', 'company__full_name','department__full_name', 'position', 'last_login', 'date_joined' ]  # List of fields you want to include
        field_info = CustomUser.get_selected_fields_info(fields)
        return field_info
    