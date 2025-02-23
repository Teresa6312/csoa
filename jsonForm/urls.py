from .views import JsonFormListView, form_template_view, get_workflow_view
from django.urls import path

app_name = "forms"

urlpatterns = [
    path("", JsonFormListView.as_view(), name="index"),
    path("view/<int:form_id>-filter", form_template_view, name="view"),
    # path('new_case/<int:form_id>', form_create_case_view, name='new_case'),
    # path('edit_case/<int:case_id>/<int:form_id>', form_edit_case_data_view, name='edit_cas'),
    # path('workflow/<uuid:workflow_id>/data/', workflow_data, name='workflow_data'),
    path("workflow/<uuid:workflow_id>-filter", get_workflow_view, name="workflow_view"),
]
