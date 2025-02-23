from . import views_case
from . import views_model
from . import views_apis
# from jsonForm.views import workflow_data
from django.urls import path
from .decorators import request_decorator

app_name = 'api'
# all the url here should match the UI url, the permission control on these api-views will compare with the UI, use the last "/xxx" for addtional filter, must label with filter in the end 
urlpatterns=[
    path('global/dictionary/<str:type>/<str:key>-filter', views_apis.get_dictionary_view, name='global_dictionary_view'), # global:global_dictionary_view
    # path('forms/workflow/<uuid:workflow_id>-filter', workflow_data, name='workflow_data'),# match with jsonForm:workflow_view
    # for case
    path('app/<str:app_name>/my-cases/<str:type>',  views_apis.get_my_cases_view_data, name='app_my_cases_data'),
    path('app/<str:app_name>/cases/search/<str:form_code>/<int:app_id>-<int:form_id>-<int:index>-filter', views_apis.get_cases_search_by_form_view_data, name='app_cases_search_form_Data'), # for searching large data set, match with base:app_cases_search_form
    path('app/<str:app_name>/cases/<str:form_code>/details/history/<int:case_id>-filter', views_apis.get_case_details_history_json, name='app_case_details_history'), # app:app_case_details
    path('app/<str:app_name>/cases/<str:form_code>/details/documents/<int:case_id>-filter', views_apis.get_case_details_documents_json, name='app_case_details_documents'), # app:app_case_details
    path('app/<str:app_name>/cases/<str:form_code>/file-download/<int:case_id>-filter/<str:file_id>-filter', views_apis.get_case_details_file_download_view, name='app_case_details_file_download'), # app:app_case_details


    path('app/<str:app_name>/model/<str:model>/details/<str:sub_table_model>/<str:sub_table_field>-filter/<str:id>-filter', request_decorator(views_model.get_model_details_view_sub_table_json) , name='app_model_view_details_sub_table'), # app:app_model_view_details
    path('app/<str:app_name>/model-unit/<str:department>/<str:team>/<str:model>/details/<str:sub_table_model>/<str:sub_table_field>-filter/<str:id>-filter', request_decorator(views_model.get_model_details_view_sub_table_json) , name='app_model_unit_view_details_sub_table'), # app:app_model_unit_view_details
    path('app/<str:app_name>/model/<str:model>', request_decorator(views_model.get_model_view_data) , name='app_model_view_data'), # match with app_model_view
    path('app/<str:app_name>/model/<str:model>/file-download/<str:sub_table_field>-filter/<str:file_id>-filter/<str:id>-filter', views_model.get_model_details_file_download_view, name='app_model_view_details_file_download'),    

]
