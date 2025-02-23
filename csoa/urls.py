"""
URL configuration for csoa project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include, re_path
from django.contrib import admin
from django.apps import apps
from django.contrib.auth import views as auth_views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path(
        "admin/doc/", include("django.contrib.admindocs.urls")
    ),  # Enable admindocs URLs
    path("admin/", admin.site.urls),
    path("", include("base.urls", namespace="app")),
    path("api/", include("base.urls_api", namespace="api")),
    path("forms/", include("jsonForm.urls", namespace="jsonForm")),
    path("user/", include("userManagement.urls", namespace="userManagement")),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(template_name="accounts/logged_out.html"),
        name="logout",
    ),
    path(
        "accounts/change-password/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change_form.html"
        ),
        name="password_change",
    ),
    path(
        "accounts/reset-password/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="email/password_reset_email.html",
        ),
        name="password_reset",
    ),
    path(
        "accounts/reset-password/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    re_path(
        r"^accounts/reset-password/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset-password/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = settings.SITE_NAME
admin.site.site_title = settings.SITE_NAME
admin.site.index_title = f"Welcome to CS {settings.SITE_NAME}"

# admin.site.sit_url = None

# # Practical Use Case:
# # This customization is particularly useful when:

# # You have many models within a single app, and you want to make the admin interface more user-friendly by ordering these models based on their importance.
# # You want to create a more intuitive admin experience, where the most critical models appear at the top.

# # enforce such an order dynamically by setting an admin_order attribute in your model admins.

# def get_app_list(self, request, app_label=None):
#     app_dict = self._build_app_dict(request, app_label)
#     from django.contrib.admin.sites import site
#     for app_name in app_dict.keys():
#         app = app_dict[app_name]
#         model_priority = {
#             model['object_name']: getattr(
#                 site._registry[apps.get_model(app_name, model['object_name'])],
#                 'admin_order',20 ##For each model, it checks for an admin_order attribute in the model's admin class (if it exists). If not, a default priority of 20 is assigned.
#             )
#             for model in app['models']

#         }
#         app['models'].sort(key=lambda x: model_priority[x['object_name']])

#     app_list = list(app_dict.values())
#     return app_list

# admin.AdminSite.get_app_list = get_app_list
