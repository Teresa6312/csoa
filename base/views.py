from django.shortcuts import render, redirect
from userManagement.models import CustomUser, Permission, AppMenu
from .util import CustomJSONEncoder, no_permission_redirect, get_object_or_redirect
from django.http import HttpResponseRedirect, HttpResponse
from .models import FileModel
import mimetypes
from django.contrib import messages
import json


import logging

logger = logging.getLogger("django")


# @cache_page(60 * 60 * 24)  # 缓存 60*24 分钟
def get_home_view(request):
    template_name = "base/home.html"
    return render(request, template_name)


# @cache_page(60 * 60 * 24)  # 缓存 60*24 分钟
# should be redirect to the page it has permission with
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


def get_user_profile_view(request):
    template_name = "base/user_profile.html"
    fields = CustomUser.selected_fields_info()
    profile = CustomUser.objects.filter(id=request.user.id).values(*fields)
    profile_data = json.dumps(list(profile), cls=CustomJSONEncoder)
    permission_fields = Permission.selected_fields_info()
    permission = Permission.objects.filter(user_permissions=request.user.id).values(
        *permission_fields
    )
    permission_data = json.dumps(list(permission), cls=CustomJSONEncoder)
    return render(
        request,
        template_name,
        {
            "profile": json.loads(profile_data)[0],
            "fields": fields,
            "permission": json.loads(permission_data),
            "permission_fields": permission_fields,
        },
    )


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
