from .views import JsonFormListView, form_template_view, get_workflow_view
from django.urls import path

app_name = "forms"

urlpatterns = [
    path("", JsonFormListView.as_view(), name="index"),
    path("view/<int:form_id>-filter", form_template_view, name="view"),
    path("workflow/<uuid:workflow_id>-filter", get_workflow_view, name="workflow_view"),
]
