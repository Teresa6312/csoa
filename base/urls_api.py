from .views_case import get_case_details_history_json, get_case_details_documents_json, get_cases_search_by_form_view_data
from .views_model import get_model_details_view_sub_table_json
from jsonForm.views import workflow_data
from django.urls import path
from .decorators import request_decorator

app_name = 'app-api'
# all the url here should match the UI url, the permission control on these api-views will compare with the UI, use the last "/xxx" for addtional filter, must label with filter in the end 
urlpatterns=[
    path('app/<str:app_name>/cases/search/<str:form_code>/<int:app_id>-<int:form_id>-<int:index>-filter', request_decorator(get_cases_search_by_form_view_data), name='app_cases_search_form_Data'), # for searching large data set, match with base:app_cases_search_form
    path('forms/workflow/<uuid:workflow_id>-filter', workflow_data, name='workflow_data'),# match with jsonForm:workflow_view
    path('app/<str:app_name>/cases/search/<str:form_code>/<int:case_id>/history-filter', request_decorator(get_case_details_history_json), name='app_case_details_history'), # app:app_case_details
    path('app/<str:app_name>/cases/search/<str:form_code>/<int:case_id>/documents-filter', request_decorator(get_case_details_documents_json), name='app_case_details_documents'), # app:app_case_details
    path('app/<str:app_name>/model/<str:model>/<str:id>/<str:sub_table_model>&<str:sub_table_field>-filter', request_decorator(get_model_details_view_sub_table_json) , name='app_model_view_details_sub_table'), # app:app_model_view_details
]