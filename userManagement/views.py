# views.py
from django.contrib.auth.views import LoginView
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse_lazy
from .models import CustomUser, Permission
import json
from base.util import CustomJSONEncoder
from django.shortcuts import render


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
