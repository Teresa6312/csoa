from userManagement.models import Company, Department, Team, CustomUser
from .models import DictionaryModel, DictionaryItemModel
from django.core.cache import cache
from .cache import global_cache_decorator
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.conf import settings
from django.db.models import F, Q
from .util import get_app_list, get_model_list


@global_cache_decorator(
    cache_key="global_select_choices", timeout=settings.CACHE_TIMEOUT_L3
)
def get_select_choices(key):
    data = get_dictionary(key)
    if key in [
        "department_list_active",
        "department_list",
        "team_list_active",
        "team_list",
        "company_list_active",
        "company_list",
    ]:
        result = [(i.get("full_name"), i.get("full_name")) for i in data]
    elif key in ["user_list_active", "user_list"]:
        result = [
            (
                "%s %s (%s)"
                % (i.get("first_name"), i.get("last_name"), i.get("username")),
                "%s %s (%s)"
                % (i.get("first_name"), i.get("last_name"), i.get("username")),
            )
            for i in data
        ]
    else:
        result = []
        for i in data:
            if isinstance(i, dict) and i.get("value") is not None:
                result.append((i.get("value"), i.get("value")))
            else:
                result.append((i, i))
    result.sort(key=lambda x: x[1])
    result.insert(0, ("", "---Select---"))
    return result


@global_cache_decorator(
    cache_key="global_select_choices_ids", timeout=settings.CACHE_TIMEOUT_L3
)
def get_select_choices_ids(key):
    data = get_dictionary(key)
    if key in [
        "department_list_active",
        "department_list",
        "team_list_active",
        "team_list",
        "company_list_active",
        "company_list",
    ]:
        result = [(i.get("id"), i.get("full_name")) for i in data]
    elif key in ["user_list_active", "user_list"]:
        result = [
            (
                i.get("id"),
                "%s %s (%s)"
                % (i.get("first_name"), i.get("last_name"), i.get("username")),
            )
            for i in data
        ]
    else:
        result = [(i.get("id"), i.get("value")) for i in data]
    result.sort(key=lambda x: x[1])
    result.insert(0, ("", "---Select---"))
    return result


@global_cache_decorator(cache_key="global_dict", timeout=settings.CACHE_TIMEOUT_L3)
def get_dictionary(key):
    data = None
    if key == "department_list_active":
        data = Department.get_active_list()
    elif key == "department_list":
        data = Department.get_list()
    elif key == "team_list_active":
        data = Team.get_active_list()
    elif key == "team_list":
        data = Team.get_list()
    elif key == "company_list_active":
        data = Company.get_active_list()
    elif key == "company_list":
        data = Company.get_list()
    elif key == "user_list_active":
        data = CustomUser.get_active_list()
    elif key == "user_list":
        data = CustomUser.get_list()
    elif key == "app_list":
        data = get_app_list()
    elif key == "model_list":
        data = get_model_list()
    elif key.startswith("dict_"):
        if key.endswith("_active"):
            data = DictionaryModel.get_dictionary_active_items_by_code(
                code=key.replace("dict_", "").replace("_active", "")
            )
        else:
            data = DictionaryModel.get_dictionary_items_by_code(
                code=key.replace("dict_", "")
            )
    if data is not None:
        data = list(data.values()) if not isinstance(data, list) else data
    else:
        []
    return data


@global_cache_decorator(
    cache_key="global_dictionary_item_map", timeout=settings.CACHE_TIMEOUT_L3
)
def get_dictionary_item_map(key):
    data = None
    if key == "company_department_map_active":
        data = (
            Company.objects.filter(is_active=True, department_company__is_active=True)
            .values(
                "short_name",
                "full_name",
                "department_company__short_name",
                "department_company__full_name",
            )
            .annotate(
                **{
                    "company_short_name": F("short_name"),
                    "company_full_name": F("full_name"),
                    "department_short_name": F("department_company__short_name"),
                    "department_full_name": F("department_company__full_name"),
                }
            )
        )
    elif key == "company_department_map":
        data = (
            Company.objects.all()
            .values(
                "short_name",
                "full_name",
                "department_company__short_name",
                "department_company__full_name",
            )
            .annotate(
                **{
                    "company_short_name": F("short_name"),
                    "company_full_name": F("full_name"),
                    "department_short_name": F("department_company__short_name"),
                    "department_full_name": F("department_company__full_name"),
                }
            )
        )
    elif key == "company_department_team_map_active":
        data = (
            Department.objects.filter(
                Q(is_active=True)
                & Q(company__is_active=True)
                & (Q(team_department__is_active=True) | Q(team_department__isnull=True))
            )
            .values(
                "short_name",
                "full_name",
                "company__short_name",
                "company__full_name",
                "team_department__short_name",
                "team_department__full_name",
            )
            .annotate(
                **{
                    "company_short_name": F("company__short_name"),
                    "company_full_name": F("company__full_name"),
                    "department_short_name": F("short_name"),
                    "department_full_name": F("full_name"),
                    "team_short_name": F("team_department__short_name"),
                    "team_full_name": F("team_department__full_name"),
                }
            )
        )
    elif key == "company_department_team_map":
        data = (
            Department.objects.all()
            .values(
                "short_name",
                "full_name",
                "company__short_name",
                "company__full_name",
                "team_department__short_name",
                "team_department__full_name",
            )
            .annotate(
                **{
                    "company_short_name": F("company__short_name"),
                    "company_full_name": F("company__full_name"),
                    "department_short_name": F("short_name"),
                    "department_full_name": F("full_name"),
                    "team_short_name": F("team_department__short_name"),
                    "team_full_name": F("team_department__full_name"),
                }
            )
        )
    elif key == "department_team_map_active":
        data = (
            Department.objects.filter(
                Q(is_active=True)
                & Q(company__is_active=True)
                & (Q(team_department__is_active=True) | Q(team_department__isnull=True))
            )
            .values(
                "short_name",
                "full_name",
                "team_department__short_name",
                "team_department__full_name",
            )
            .annotate(
                **{
                    "department_short_name": F("short_name"),
                    "department_full_name": F("full_name"),
                    "team_short_name": F("team_department__short_name"),
                    "team_full_name": F("team_department__full_name"),
                }
            )
        )
    elif key == "department_team_map":
        data = (
            Department.objects.all()
            .values(
                "short_name",
                "full_name",
                "team_department__short_name",
                "team_department__full_name",
            )
            .annotate(
                **{
                    "department_short_name": F("short_name"),
                    "department_full_name": F("full_name"),
                    "team_short_name": F("team_department__short_name"),
                    "team_full_name": F("team_department__full_name"),
                }
            )
        )
    elif key.startswith("dict_"):
        if key.endswith("_active"):
            data = DictionaryItemModel.get_active_dictionary_item_map_by_code(
                code=key.replace("dict_", "").replace("_active", "")
            )
        else:
            data = DictionaryItemModel.get_dictionary_item_map_by_code(
                code=key.replace("dict_", "")
            )
    if data is not None:
        data = list(data)
    else:
        []
    return data


@global_cache_decorator(
    cache_key="global_select_choices_from_map", timeout=settings.CACHE_TIMEOUT_L3
)
def get_select_choices_from_map(map_name, map_field_key, map_field_value=None):
    data = get_dictionary_item_map(map_name)
    if data is not None and len(data) > 0:
        if map_field_value is None:
            result = [
                (i.get(map_field_key), i.get(map_field_key))
                for i in data
                if i.get(map_field_key) is not None
            ]
        else:
            result = [
                (i.get(map_field_key), i.get(map_field_value))
                for i in data
                if i.get(map_field_key) is not None
                and i.get(map_field_value) is not None
            ]
        result = list(set(result))
        result.sort(key=lambda x: x[1])
        result.insert(0, ("", "---Select---"))
    else:
        result = []
    return result


def get_audit_history_fields():
    return {
        "object": "Object",
        "change_time": "Changed Time",
        "change_type": "Changed Type",
        "change_by": "Changed By",
        "changes": "Changes",
    }


@global_cache_decorator(cache_key="audit_data_map")
def get_audit_field_map(class_name):
    data_map = {}
    field_map = {}
    for field in class_name._meta.fields:
        field_map[field.name] = field.verbose_name
        if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
            key = None
            if field.related_model == Department:
                key = "department_list"
            elif field.related_model == Company:
                key = "company_list"
            elif field.related_model == Team:
                key = "team_list"
            elif field.related_model == CustomUser:
                key = "user_list"
            if key is not None:
                values = get_dictionary(key)
            else:
                values = field.related_model.objects.all().values()
            if values is not None:
                data_map[field.name] = {}
                for v in values:
                    if v.get("id", None) is not None:
                        field_value = None
                        if v.get("name", None) is not None:
                            field_value = v.get("name")
                        elif v.get("full_name", None) is not None:
                            field_value = v.get("full_name")
                        elif v.get("username", None) is not None:
                            field_value = v.get("username")
                        elif v.get("code", None) is not None:
                            field_value = v.get("code")
                        elif v.get("key", None) is not None:
                            field_value = v.get("key")
                        data_map[field.name][f"{v.get('id')}"] = (
                            field_value if field_value is not None else v.get("id")
                        )
    return data_map, field_map


def get_audit_history(history, type: str, class_name=None):
    # prepare data map for the FK fields, get data from redis
    # can add more data into redis for mapping
    data_map, field_map = (
        get_audit_field_map(class_name) if class_name is not None else {}
    )
    model_fields = set()
    history_changes = []
    if data_map is not None:
        model_fields = data_map.keys()
    #   start to process the audit data
    for record in history:
        # Determine the type of change
        if record.history_type == "+":
            change_type = "Created"
        elif record.history_type == "-":
            change_type = "Deleted"
        elif record.history_type == "~":
            change_type = "Changed"
        else:
            change_type = "Unknown"
        changes = ""
        if record.prev_record:
            delta = record.diff_against(record.prev_record)
            for change in delta.changes:
                if data_map is not None and change.field in model_fields:
                    change_old = data_map[change.field].get(str(change.old), "None")
                    change_new = data_map[change.field].get(str(change.new), "None")
                else:
                    change_old = change.old
                    change_new = change.new
                field_label = field_map.get(change.field, change.field)
                changes = (
                    changes
                    + f"<strong>[{field_label}]</strong>:{change_old} → {change_new} <br/>"
                )
        if changes != "" or change_type != "Changed":
            history_changes.append(
                {
                    "change_type": change_type,
                    "object": f"{type}-{record.id}",
                    "changes": changes,
                    "change_by": record.history_user.username,
                    "change_time": record.history_date,
                }
            )
    return history_changes


def get_audit_history_by_instance(instance, type: str, class_name=None):
    history = instance.history.all()
    history_changes = get_audit_history(history, type, class_name)
    return history_changes
