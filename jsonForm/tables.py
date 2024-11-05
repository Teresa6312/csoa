import django_tables2 as tables
from jsonForm.models import Case, CaseData, FormTemplate
from django.urls import reverse
from django.utils.html import format_html
from django_tables2.utils import A
import django_filters
from base.util_model import get_select_choices_ids

class CaseTable(tables.Table):
    details = tables.LinkColumn('app:app_case_details', text='Details',  verbose_name='Details', args=[A('form__application__key'),A('form__code'),A('id')], orderable=False, empty_values=())
    # edit = tables.LinkColumn('app:app_my_cases_edit', text='Edit',  verbose_name='Edit', args=[A('form__application__key'), A('id'), A('form__code')], orderable=False, empty_values=())
    class Meta:
        model = Case
        template_name = "django_tables2/bootstrap.html"
        fields = ("id", "form", "is_submited","case_department", "case_team", "created_by", "updated_by", "created_at", "updated_at", "status", "details")

def create_dynamic_case_table_class(class_name, column_headers=None, default_fields=None, show_details=False, show_edit=False):
    """
    Create a dynamic table class based on column_headers.

    :param column_headers: List of dictionaries with keys 'key' and 'label'
    :return: A dynamically created table class
    """
    # Dynamically create the Meta class
    class DynamicTableMeta:
        model = class_name
        template_name = "django_tables2/bootstrap.html"
        if default_fields is None:
            fields = ["id", "form", "case_department", "case_team", "created_by", "updated_by", "created_at", "updated_at", "status"]  # Initialize fields as an empty list
        else:
            fields = default_fields

    # Dynamically create the Table class
    attrs = {
        'Meta': DynamicTableMeta,
        'id': tables.Column(verbose_name='Case ID'),
        'form': tables.Column(verbose_name='Case Form'),
        'case_department': tables.Column(verbose_name='Case Form Section'),
        'case_team': tables.Column(verbose_name='Case Form Section Description'),
        'created_by': tables.Column(verbose_name='Case Created By'),
        'created_at': tables.Column(verbose_name='Case Updated By'),
        'updated_by': tables.Column(verbose_name='Case Created At'),
        'updated_at': tables.Column(verbose_name='Case Updated At'),
        'status': tables.Column(verbose_name='Case Status')
        }
    if show_details:
        attrs['details'] = tables.LinkColumn('app:app_case_details', text='Details',  verbose_name='Details', args=[A('form__application__key'),A('form__code'),A('id')], orderable=False, empty_values=())
    if show_edit:
        attrs['edit'] = tables.LinkColumn('app:app_my_cases_edit', text='Edit',  verbose_name='Edit', args=[A('form__application__key'), A('form__code'), A('id')], orderable=False, empty_values=())
    # Create the dynamic table class
    DynamicTable = type('DynamicTable', (tables.Table,), attrs)
    return DynamicTable

class CaseFilter(django_filters.FilterSet):
    form = django_filters.ModelChoiceFilter(field_name='form', queryset=FormTemplate.objects.all(), required=True)
    case_data = django_filters.CharFilter(field_name='case_data_case__section_data', lookup_expr='icontains')
    case_team = django_filters.ChoiceFilter(choices= get_select_choices_ids('team_list'), field_name='case_team')
    case_department = django_filters.ChoiceFilter(choices= get_select_choices_ids('department_list'), field_name='case_department')
    created_at_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_at_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Case
        fields = ["form", "case_data","case_department","case_team", 'created_at_after', 'created_at_before']


def create_dynamic_case_data_filter(data_class):
    class CaseDataFilter(django_filters.FilterSet):
        form = django_filters.ModelChoiceFilter(field_name='case__form', queryset=FormTemplate.objects.all())
        case_data = django_filters.CharFilter(field_name='section_data', lookup_expr='icontains')
        case_status = django_filters.CharFilter(field_name='case__status', lookup_expr='icontains')
        case_team = django_filters.ChoiceFilter(choices= get_select_choices_ids('team_list'), field_name='case__case_team')
        case_department = django_filters.ChoiceFilter(choices= get_select_choices_ids('department_list'), field_name='case__case_department')
        created_at_after = django_filters.DateFilter(field_name='case__created_at', lookup_expr='gte')
        created_at_before = django_filters.DateFilter(field_name='case__created_at', lookup_expr='lte')
    
        class Meta:
            model = data_class
            fields = ["form", "case_status","case_data","case_department","case_team", 'created_at_after', 'created_at_before',]

    return CaseDataFilter


def create_dynamic_case_data_table_class(class_name, column_headers, default_fields=None, show_details=False):
    """
    Create a dynamic table class based on column_headers.

    :param column_headers: List of dictionaries with keys 'key' and 'label'
    :return: A dynamically created table class
    """
    # Dynamically create the Meta class
    class DynamicTableMeta:
        model = class_name
        template_name = "django_tables2/bootstrap.html"
        if default_fields is None:
            fields = ['case__id', 'case__form', 'form_section__name', 'form_section__description', 'case__created_by__username', 'case__updated_by__username', 'case__created_at', 'case__updated_at', 'case__status']  # Initialize fields as an empty list
        else:
            fields = default_fields

    # Dynamically create the Table class
    attrs = {
        'Meta': DynamicTableMeta,
        'case__id': tables.Column(verbose_name='Case ID'),
        'case__form': tables.Column(verbose_name='Case Form'),
        'form_section__name': tables.Column(verbose_name='Case Form Section'),
        'form_section__description': tables.Column(verbose_name='Case Form Section Description'),
        'case__created_by__username': tables.Column(verbose_name='Case Created By'),
        'case__updated_by__username': tables.Column(verbose_name='Case Updated By'),
        'case__created_at': tables.Column(verbose_name='Case Created At'),
        'case__updated_at': tables.Column(verbose_name='Case Updated At'),
        'case__status': tables.Column(verbose_name='Case Status'),
        }
    if column_headers is not None and len(column_headers) != 0:
        # Add columns to the table class
        for column in column_headers:
            if not column['input'] == 'list':
                field_name = f"section_data__{column['key'] }" if column['index'] == 0 else f"section_data_{column['index']}__{column['key'] }"
                label = column.get('label', field_name)
                attrs[field_name] = tables.Column(accessor=field_name, verbose_name=label)
                DynamicTableMeta.fields.append(field_name)  # Add the field to the Meta.fields list
    if show_details:
        attrs['details'] = tables.LinkColumn('app:app_case_details', text='Details',  verbose_name='Details', args=[A('case__form__application__key'), A('case__form__code'), A('case__id')], orderable=False, empty_values=())
    # attrs['edit'] = tables.LinkColumn('app:app_my_cases_edit', text='Edit',  verbose_name='Edit', args=[A('case__form__application__key'), A('case__id'), A('case__form__code')], orderable=False, empty_values=())
    # Create the dynamic table class
    DynamicTable = type('DynamicTable', (tables.Table,), attrs)
    return DynamicTable

class CaseDataTable(tables.Table):
    case = tables.Column(verbose_name='Case ID'),
    case__form = tables.Column(verbose_name='Case Form')
    form_section__name = tables.Column(verbose_name='Case Form Section')
    form_section__description = tables.Column(verbose_name='Case Form Section Description')
    case__created_by__username = tables.Column(verbose_name='Case Created By')
    case__updated_by__username = tables.Column(verbose_name='Case Updated By')
    case__created_at = tables.Column(verbose_name='Case Created At')
    case__updated_at = tables.Column(verbose_name='Case Updated At')
    case__status = tables.Column(verbose_name='Case Status')
    link_column = tables.LinkColumn('app:app_case_details', text='Details',  verbose_name='Details', args=[A('case__form__application__key'), A('case__form__code'), A('case__id')], orderable=False, empty_values=())

    class Meta:
        model = CaseData
        template_name = "django_tables2/bootstrap.html"
        fields = ("case__id", "case__form", "form_section__name", "form_section__description", "case__created_by__username", "case__updated_by__username", "case__created_at", "case__updated_at", "case__status", "link_column")
