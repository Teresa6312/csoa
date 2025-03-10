from django.urls import path
from . import views
from . import views_case
from . import views_model
from .decorators import case_decorator, model_decorator, model_unit_decorator

app_name = "app"
urlpatterns = [
    path("", views.get_home_view, name="home"),
    path(
        "admin-maintenance/model-data-import",
        views.model_data_import_view,
        name="maintenance",
    ),
    path("app/<str:app_name>/home", views.get_app_home_view, name="app_home"),
    path(
        "app/<str:app_name>/forms/add/<str:form_code>",
        case_decorator(views_case.create_case_view),
        name="app_forms",
    ),
    path(
        "app/<str:app_name>/my-cases",
        case_decorator(views_case.get_my_cases_view),
        name="app_my_cases_index",
    ),
    path(
        "app/<str:app_name>/my-cases/<str:form_code>/edit/<int:case_id>-filter",
        case_decorator(views_case.edit_case_view),
        name="app_my_cases_edit",
    ),
    path(
        "app/<str:app_name>/cases/workflow/<str:form_code>/<int:case_id>-filter",
        case_decorator(views_case.get_case_workflow_view),
        name="app_case_workflow",
    ),
    # path('app/<str:app_name>/cases/search', case_decorator(views_case.get_cases_search_view), name='app_cases_search'),
    path(
        "app/<str:app_name>/cases/search/<str:form_code>",
        case_decorator(views_case.get_cases_search_by_form_view),
        name="app_cases_search_form",
    ),
    path(
        "app/<str:app_name>/cases/<str:form_code>/details/<int:case_id>-filter",
        case_decorator(views_case.get_case_details),
        name="app_case_details",
    ),
    path(
        "app/<str:app_name>/cases/<str:form_code>/details/<str:display_type>/<int:case_id>-filter",
        case_decorator(views_case.get_case_details),
        name="app_case_details_in_list",
    ),
    path(
        "app/<str:app_name>/model/<str:model>",
        model_decorator(views_model.get_model_view),
        name="app_model_view",
    ),
    path(
        "app/<str:app_name>/model/<str:model>/details/<str:id>-filter",
        model_decorator(views_model.get_model_details_view),
        name="app_model_view_details",
    ),
    path(
        "app/<str:app_name>/model-unit/<str:department>/<str:team>/<str:model>",
        model_unit_decorator(views_model.get_model_view),
        name="app_model_unit_view",
    ),
    path(
        "app/<str:app_name>/model-unit/<str:department>/<str:team>/<str:model>/<str:id>-filter",
        model_unit_decorator(views_model.get_model_details_view),
        name="app_model_unit_view_details",
    ),
]
