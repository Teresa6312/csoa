from django.urls import path
from .views import edit_case

app_name = "modelBase"

urlpatterns = [
    path("edit/case/<int:case_id>-filter", edit_case, name="edit_case"),
]
