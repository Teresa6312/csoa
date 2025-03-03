from django.shortcuts import render, redirect
from userManagement.models import CustomUser, Permission, AppMenu
from .util import CustomJSONEncoder, no_permission_redirect, get_object_or_redirect
from .util_model_maint import update_or_create
from django.http import HttpResponseRedirect, HttpResponse
from .models import FileModel
from .forms import ModelDataImportForm
import mimetypes
from django.contrib import messages
import json
from django.conf import settings
from django.core.exceptions import ValidationError
from django.apps import apps
import logging

logger = logging.getLogger("django")


def get_home_view(request):
    template_name = "base/home.html"
    return render(request, template_name)


def get_app_home_view(request, app_name):
    user_app_menu = request.current_page_menu
    for menu in user_app_menu.get("sub_menu", []):
        if menu.get("link", None) is not None:
            link = menu.get("link")
            return HttpResponseRedirect(link)
    mini_app = AppMenu.objects.filter(key=app_name, menu_level=0)
    if mini_app is None or mini_app.count() != 1:
        messages.warning(request, "Application is not found")
        return redirect("app:home")
    return no_permission_redirect(request, "app:home")


def download_file(request, file_id):
    file_instance = get_object_or_redirect(FileModel, id=file_id)
    file_path = file_instance.file.path
    file_name = file_instance.name

    # Detect the content type of the file
    content_type, _ = mimetypes.guess_type(file_path)

    # Serve the file as an HTTP response
    response = HttpResponse(open(file_path, "rb").read(), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


# Only appliable for BaseAuditModel data import view
def model_data_import_view(request):
    template_name = "base/model_data_import.html"
    context = {}
    if request.method == "POST":
        form = ModelDataImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            form = ModelDataImportForm()
            try:

                # Load the JSON data from the uploaded file
                uploaded_data = json.load(uploaded_file)
                app = uploaded_data.get("app")
                model = uploaded_data.get("model")
                data = uploaded_data.get("data")

                model_class = apps.get_model(app, model)
                fields = uploaded_data.get("fields", model_class.selected_fields_info())
                field_list = (
                    model_class.selected_fields_info()
                    if fields is None
                    else model_class.get_selected_fields_info(fields)
                )
                fields = field_list
                # Update or create the model instances from the JSON data
                instance_pks = []
                created_count = 0
                updated_count = 0
                for item in data:
                    instance, created = update_or_create(model_class, item)
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    if instance is not None:
                        instance_pks.append(instance.pk)
                instance_list = model_class.objects.filter(pk__in=instance_pks).values(
                    *fields.keys()
                )
                messages.success(
                    request,
                    f"Data Import Successful. {created_count} records created, {updated_count} records updated.",
                )
                queryset_data = json.dumps(
                    list(instance_list),
                    cls=CustomJSONEncoder,
                )
                context["queryset"] = queryset_data
                context["fields"] = fields
                context["exportCsv"] = True
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON file.")
            except Exception as e:
                logger.exception(f"Error importing model data {e}")
                raise ValidationError(f"Data Import Failed {e}")
        else:
            messages.error(request, f"Invalid form data. {form.errors}")
    form = ModelDataImportForm()
    context["form"] = form
    return render(request, template_name, context)
