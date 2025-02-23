from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, AppMenu, Permission, CustomGroup, Team
from django.contrib.auth.models import Permission as DjangoPermission
from base.util_model import get_select_choices_ids, get_dictionary
from base.util import to_camel_case
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.db.models import Q
from base.validators import get_validator

class CustomUserCreationForm(UserCreationForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(role__isnull=False),
        required=False,
        widget=forms.CheckboxSelectMultiple,  # You can use different widgets like `SelectMultiple`
        label="Select New Permission")
    class Meta():
        model = CustomUser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['office_phone'].validators = [get_validator('phone_regex')]
        self.fields['office_phone'].widget.attrs['placeholder'] = '000-000-0000'
        self.fields['mobile'].validators = [get_validator('phone_regex')]
        self.fields['mobile'].widget.attrs['placeholder'] = '000-000-0000'
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        self.fields['permissions'].queryset =  Permission.objects.filter(role__isnull=False)

    def save(self, commit=True, *args, **kwargs):
        user = super(CustomUserCreationForm, self).save(commit=False, *args, **kwargs)
        user.first_name = user.first_name.title()
        user.last_name = user.last_name.title()
        user.email = user.email.lower()
        default_password = 'defaultpassword123'  # Set your default password here
        user.set_password(default_password)
        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(role__isnull=False),
        required=False,
        widget=forms.CheckboxSelectMultiple,  # You can use different widgets like `SelectMultiple`
        label="Select Permission")
    class Meta:
        model = CustomUser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['office_phone'].validators = [get_validator('phone_regex')]
        self.fields['office_phone'].widget.attrs['placeholder'] = '000-000-0000'
        self.fields['mobile'].validators = [get_validator('phone_regex')]
        self.fields['mobile'].widget.attrs['placeholder'] = '000-000-0000'
        if self.instance:
            user = CustomUser.objects.get(id = self.instance.id)
            self.fields['username'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['readonly'] = True if user.email else False
            if self.instance.department is not None:
                self.fields['team'].queryset = Team.objects.filter(department=self.instance.department)
            self.fields['permissions'].queryset = Permission.objects.filter(
                    Q(role__isnull=False) &
                    (
                        ~Q(role__group_type__in = CustomGroup.get_perms_group_type()) |
                        Q(
                            role__group_type__in = CustomGroup.get_team_belongs_group_type(),
                            team__in = user.team.all()
                        ) |
                        Q(
                            role__group_type__in = CustomGroup.get_department_belongs_group_type(),
                            department = user.department
                        ) | 
                        Q(
                            role__group_type__in = CustomGroup.get_company_belongs_group_type(),
                            company = user.company
                        )
                    )
                ).order_by('app')
    def clean(self):
        super().clean()
        if self.cleaned_data['permissions']:
            for perm in self.cleaned_data['permissions']:
                g = perm.role
                if perm.role is None:
                    raise ValidationError(
                                f"'{perm}' permission has no role"
                            )                    
                if g.group_type in CustomGroup.get_team_belongs_group_type() and perm.team not in self.instance.team.all():
                    raise ValidationError(
                                f"'{perm}' permission is only applicable for users in '{perm.team}' team(s)"
                            )
                if g.group_type in CustomGroup.get_department_belongs_group_type() and perm.department != self.instance.department:
                    raise ValidationError(
                                f"'{perm}' permission is only applicable for users in '{perm.department}' department"
                            )
                if g.group_type in CustomGroup.get_company_belongs_group_type() and perm.company != self.instance.company:
                    raise ValidationError(
                                f"'{perm}' permission is only applicable for users in '{perm.company}' company"
                            )

    def save(self, commit=True, *args, **kwargs):
        user = super(CustomUserChangeForm, self).save(commit=False, *args, **kwargs)
        user.first_name = user.first_name.title()
        user.last_name = user.last_name.title()
        user.email = user.email.lower()
        if commit:
            user.save()
        return user

class AppMenuCreateForm(forms.ModelForm):
    class Meta:
        model = AppMenu
        fields = ['label', 'icon', 'control_type']

    def save(self, commit=True):
        instance = super().save(commit=False)
        label = self.cleaned_data.get('label', None)
        instance.key = to_camel_case(label)
        instance.link = f'/app/{instance.key}/home'
        if commit:
            instance.save()
        return instance
class AppMenuInlineUpdateForm(forms.ModelForm):
    class Meta:
        model = AppMenu
        fields = ['key', 'label','link', 'icon', 'is_active', 'menu_level']

    def __init__(self, *args, **kwargs):
        # Get the parent object ( instance)
        self.parent_instance = kwargs.pop('parent_instance', None)
        super().__init__(*args, **kwargs)
        if self.parent_instance is not None and self.parent_instance.pk is not None and self.parent_instance.menu_level is not None:
            self.fields['menu_level'].initial = self.parent_instance.menu_level + 1

class AppMenuInlineCreateForm(forms.ModelForm):
    is_form = forms.BooleanField(required=False, help_text="If yes, it will auto create 'form' related menus")
    is_my_cases = forms.BooleanField(required=False,help_text="If yes, it will auto create 'My Cases' related menus")
    is_search_cases = forms.BooleanField(required=False,help_text="If yes, it will auto create 'Search Cases' related menus")
    has_my_case_list = forms.BooleanField(required=False,help_text="If yes, it will auto create 'Todo list','On Going list', and 'Completed List'")
    has_cases_search_menus = forms.BooleanField(required=False,help_text="If yes, it will auto case search list")
    class Meta:
        model = AppMenu
        fields = ['label', 'icon', 'menu_level']

    def __init__(self, *args, **kwargs):
        self.parent_instance = kwargs.pop('parent_instance', None)
        super().__init__(*args, **kwargs)
        if self.parent_instance is not None and self.parent_instance.pk is not None and self.parent_instance.menu_level is not None:
            self.fields['menu_level'].initial = self.parent_instance.menu_level + 1

    def save(self, commit=True, *args, **kwargs):
        instance = super(AppMenuInlineCreateForm, self).save(commit=False, *args, **kwargs)
        label = self.cleaned_data.get('label', None)
        instance.key = to_camel_case(label)

        is_form = self.cleaned_data.get('is_form', False)
        is_my_cases = self.cleaned_data.get('is_my_cases', False)
        is_search_cases = self.cleaned_data.get('is_search_cases', False)
        has_my_case_list = self.cleaned_data.get('has_my_case_list', False)
        has_cases_search_menus = self.cleaned_data.get('has_cases_search_menus', False)

        if is_form:
            pass
        elif is_search_cases:
            instance.link = f'/app/{self.parent_instance.key}/cases/search'
        elif is_my_cases:
            instance.key = 'my_cases'
            instance.link = f'/app/{self.parent_instance.key}/my-cases'

        if commit:
            instance.save()

        if has_my_case_list and is_my_cases:
            AppMenu.objects.create(
                menu_level = instance.menu_level + 1,
                key = 'todoList',
                label = 'To-do List',
                link= f'/app/{self.parent_instance.key}/my-cases/todoList',
                parent_app_menu = instance,
                is_active = True
            )
            AppMenu.objects.create(
                menu_level = instance.menu_level + 1,
                key = 'ongoingList',
                label = 'Ongoing List',
                link= f'/app/{self.parent_instance.key}/my-cases/ongoingList',
                parent_app_menu = instance,
                is_active = True
            )
            AppMenu.objects.create(
                menu_level = instance.menu_level + 1,
                key = 'completedList',
                label = 'Completed List',
                link= f'/app/{self.parent_instance.key}/my-cases/completedList',
                parent_app_menu = instance,
                is_active = True
            )
        if has_cases_search_menus:
            pass
        return instance
class AppMenuUpdateForm(forms.ModelForm):
    companys = forms.MultipleChoiceField(required=False, help_text="Only use when 'Control Type' select 'Company'", choices=[])
    departments = forms.MultipleChoiceField(required=False, help_text="Only use when 'Control Type' select 'Department'", choices=[])
    teams = forms.MultipleChoiceField(required=False, help_text="Only use when 'Control Type' select 'Team'", choices=[])

    class Meta:
        model = AppMenu
        fields = '__all__' 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically set choices for the field
        self.fields['companys'].choices = get_select_choices_ids('company_list_active')
        self.fields['departments'].choices = get_select_choices_ids('department_list_active')
        self.fields['teams'].choices = get_select_choices_ids('team_list_active')

        self.fields['companys'].initial = [ p['company'] for p in Permission.objects.filter(app_id = self.instance.id).distinct().values('company')]
        self.fields['departments'].initial = [ p['department']  for p in Permission.objects.filter(app_id = self.instance.id).distinct().values('department')]
        self.fields['teams'].initial = [p['team'] for p in Permission.objects.filter(app_id = self.instance.id).distinct().values('team')]
        
        if self.instance and self.instance.pk and self.instance.menu_level == 0:
            self.fields['parent_app_menu'].widget.attrs['readonly']=True
            self.fields['parent_app_menu'].queryset =  AppMenu.objects.filter(menu_level = -1)

    def save(self, *args, **kwargs):
        instance = super(AppMenuUpdateForm, self).save(*args, **kwargs)
        companys = self.cleaned_data.get('companys', None)
        departments = self.cleaned_data.get('departments', None)
        teams = self.cleaned_data.get('teams', None)
        instance_id = self.instance.id

        # Check if the instance ID is set
        if instance_id is not None:
            system_department = get_dictionary('department_list_active')
            system_team = get_dictionary('team_list_active')

            linked_department = { '%s'%i['id'] : i['department_id'] for i in system_team}
            linked_company = { '%s'%i['id'] : i['company_id'] for i in system_department}
        
            if companys and self.cleaned_data['control_type'] == 'company':
                
                existed = Permission.objects.filter(app_id = instance_id).distinct().values('company')
                for e in existed:
                    if e['company'] not in  companys:
                        Permission.objects.filter(app_id = instance_id, company_id = e['company']).delete()
                for c in companys:
                    if Permission.objects.filter(app_id = instance_id, company_id = c).count() == 0:
                        Permission.objects.create(app_id = instance_id, company_id = c)

            if departments and self.cleaned_data['control_type'] == 'department':
                existed = Permission.objects.filter(app_id = instance_id).distinct().values('department')
                for e in existed:
                    if e['department'] not in  departments:
                        Permission.objects.filter(app_id = instance_id, department_id = e['department'] ).delete()
                for c in departments:
                    if Permission.objects.filter(app_id = instance_id, department_id = c).count() == 0:
                        Permission.objects.create(app_id = instance_id, department_id = c, company_id = linked_company.get(str(c)))

            if teams and self.cleaned_data['control_type'] == 'team':
                existed = Permission.objects.filter(app_id = instance_id).distinct().values('team')
                for e in existed:
                    if e['team'] not in  teams:
                        Permission.objects.filter(app_id = instance_id, team_id = e['team'] ).delete()
                for c in teams:
                    if Permission.objects.filter(app_id = instance_id, team_id = c).count() == 0:
                        linked_department_id = linked_department.get(str(c))
                        Permission.objects.create(app_id = instance_id, team_id = c, department_id=linked_department_id, company_id = linked_company.get(str(linked_department_id)))
            if self.cleaned_data['control_type'] == 'app':
                existed = Permission.objects.filter(app_id = instance_id)
                if existed.count() == 0:
                    Permission.objects.create(app_id = instance_id)
        return instance
class PermissionlineForm(forms.ModelForm):
    existing_permission = forms.ModelChoiceField(queryset=Permission.objects.filter(role=0), required=False, label="Select Existing Permission"
                                                 , help_text="""If the group is Department level role, you can ignore the 'Team' in permission. It will only use Department and Company from the permission
                                                 If the group is Company level role, you can ignore the 'Department' and 'Team' in permission. It will only use Company from the permission""")

    class Meta:
        model = Permission
        fields = ['existing_permission']

    def __init__(self, *args, **kwargs):
        # Get the parent object ( instance)
        self.parent_instance = kwargs.pop('parent_instance', None)
        super().__init__(*args, **kwargs)

        if self.parent_instance:
            # Modify the queryset of the existing_team field based on the parent instance
            if self.parent_instance.id is not None:
                g = CustomGroup.objects.get(id = self.parent_instance.id)
                filter = Q()
                if g.group_type == 1:
                    filter = Q(role__isnull=True, app__control_type='app')
                elif g.group_type in CustomGroup.get_team_group_type() :
                    filter = Q(role__isnull=True, app__control_type__in=['team'])
                elif g.group_type in CustomGroup.get_department_group_type():
                    filter = Q(role__isnull=True, app__control_type__in=['department', 'team'])
                elif g.group_type in CustomGroup.get_company_group_type():
                    filter = Q(role__isnull=True, app__control_type__in=['company', 'department', 'team'])
                if g.group_type in CustomGroup.get_manager_group_type():
                    filter = filter | Q(role__isnull=True, app__control_type='app')
                self.fields['existing_permission'].queryset = Permission.objects.filter(filter)
    def save(self, commit=True):
        instance = super().save(commit=False)
        g = CustomGroup.objects.get(id = self.parent_instance.id)
        if self.cleaned_data['existing_permission']:
            instance = self.cleaned_data['existing_permission']
            company = None
            department = None
            team =  None
            if g.group_type in CustomGroup.get_team_group_type() :
                company = instance.company
                department = instance.department
                team =  instance.team
            elif g.group_type in CustomGroup.get_department_group_type():
                company = instance.company
                department = instance.department
            elif g.group_type in CustomGroup.get_company_group_type():
                company =  instance.company
            new_obj = Permission(
                role=self.parent_instance,
                app=instance.app,
                company=company,
                department=department,
                team=team
            )
            if commit:
                new_obj.save()
            return new_obj
        else:
            return super().save(commit=commit)
    
class PermissionInlineFormset(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        # Use existing team if selected
        if form.cleaned_data.get('existing_permission'):
            form.instance = form.cleaned_data['existing_permission']
        return super().save_new(form, commit=commit)
    
class CustomGroupForm(forms.ModelForm):
    class Meta:
        model = CustomGroup
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Reset the queryset for the ManyToManyField
        self.fields['permissions'].widget = forms.CheckboxSelectMultiple()
        self.fields['menus'].widget = forms.CheckboxSelectMultiple()
        if self.instance.id:
            apps = self.instance.permission_role.all().values('app').distinct()
            menu0 = AppMenu.objects.filter(is_active=True, menu_level=0, id__in=apps).values('id')
            menu1 = AppMenu.objects.filter(is_active=True, menu_level=1, parent_app_menu__in=menu0).values('id')
            menu2 = AppMenu.objects.filter(is_active=True, menu_level=2, parent_app_menu__in=menu1).values('id')
            menu3 = AppMenu.objects.filter(is_active=True, menu_level=3, parent_app_menu__in=menu2).values('id')
            menu4 = AppMenu.objects.filter(is_active=True, menu_level=4, parent_app_menu__in=menu3).values('id')
            menu5 = AppMenu.objects.filter(is_active=True, menu_level=5, parent_app_menu__in=menu4).values('id')
            menu_ids = menu0.union(menu1).union(menu2).union(menu3).union(menu4).union(menu5)
            self.fields['menus'].queryset = AppMenu.objects.filter(is_active=True,id__in=menu_ids).order_by('menu_level', 'parent_app_menu')
            if self.instance.name == 'User Admin' or self.instance.group_type is None or self.instance.group_type == 1:
                self.fields['permissions'].queryset = DjangoPermission.objects.all()  # 可选，设置权限的查询集