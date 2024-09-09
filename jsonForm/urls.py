from .views import JsonFormListView, form_create_case_view, workflow_data,workflow_view, form_edit_case_data_view
from django.urls import include, path

app_name = 'jsonForm'

urlpatterns=[
    path('', JsonFormListView.as_view(), name='index'),
    path('new_case/<int:form_id>', form_create_case_view, name='new_case'),
    path('edit_case/<int:case_id>/<int:form_id>', form_edit_case_data_view, name='edit_cas'),
    # path('workflow/<uuid:workflow_id>/data/', workflow_data, name='workflow_data'),
    path('workflow/<uuid:workflow_id>/', workflow_view, name='workflow_view'),
]