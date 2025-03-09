from django.shortcuts import render, redirect
from userManagement.models import CustomUser, Permission, AppMenu
from .util import CustomJSONEncoder, no_permission_redirect, get_object_or_redirect
from .util_model_maint import bluk_update_or_create, get_field_keyset
from django.http import HttpResponseRedirect, HttpResponse
from .models import FileModel
from .forms import ModelDataImportForm
from django.db import transaction
import mimetypes
from django.contrib import messages
import json
from django.conf import settings
from django.core.exceptions import ValidationError
from django.apps import apps
import logging

logger = logging.getLogger("django")


def get_home_view(request):
    """
        View to render the home page.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponse: Renders the home page.

        Database Operations:
            - None

        Tables Used:
            - None

        Addtional Information:
            # This is the main entry point for the application.
    """
    template_name = "base/home.html"
    return render(request, template_name)


def get_app_home_view(request, app_name):
    """
        View to render the application home page based on the app_name.

        Args:
            request (HttpRequest): The HTTP request object.
            app_name (str): The name of the application.

        Returns:
            HttpResponseRedirect: Redirects to the application's home page.

        Database Operations:
            - Read: AppMenu

        Tables Used:
            - AppMenu (Read)

        Addtional Information:
None            None
    """
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
    """
        View to handle file download.

        Args:
            request (HttpRequest): The HTTP request object.
            file_id (int): The ID of the file to be downloaded.

        Returns:
            HttpResponse: Serves the file as an HTTP response.

        Database Operations:
            - Read: FileModel

        Tables Used:
            - FileModel (Read)

        Addtional Information:
            # Detects the content type of the file and serves it as an HTTP response.
    """
    file_instance = get_object_or_redirect(FileModel, id=file_id)
    file_path = file_instance.file.path
    file_name = file_instance.name

    # Detect the content type of the file
    content_type, _ = mimetypes.guess_type(file_path)

    # Serve the file as an HTTP response
    response = HttpResponse(open(file_path, "rb").read(), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response

def model_data_import_view(request):
    """
        View to handle data import for class create with BaseAuditModel.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponse: Renders the data import page.

        Database Operations:
            - Read: model_class
            - Create/Update: model_class

        Tables Used:
            - model_class (Read, Create/Update)

        Addtional Information:
            # Only applicable for BaseAuditModel data import view.
    """
    template_name = "base/model_data_import.html"
    context = {}
    if request.method == "POST":
        form = ModelDataImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            form = ModelDataImportForm()
            with transaction.atomic():
                try:
                    # Load the JSON data from the uploaded file
                    uploaded_data = json.load(uploaded_file)
                    app = uploaded_data.get("app")
                    model = uploaded_data.get("model")
                    data = uploaded_data.get("data")

                    model_class = apps.get_model(app, model)

                    fields = get_field_keyset(data, None)
                    field_list = sorted(list(fields))
                    field_list.insert(0, "id")
                    fields = model_class.get_selected_fields_info(field_list)

                    instance_pks, created_count, updated_count = bluk_update_or_create(model_class, data)

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
                    transaction.rollback(True)
                    raise ValidationError("Invalid JSON file.")
                except Exception as e:
                    transaction.rollback(True)
                    logger.exception(f"Error importing model data {e}")
                    raise ValidationError(f"Data Import Failed {e}")
        else:
            messages.error(request, f"Invalid form data. {form.errors}")
    form = ModelDataImportForm()
    context["form"] = form
    return render(request, template_name, context)
