from django.shortcuts import redirect
from django.conf import settings


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_info = request.session.get("user_info", {})
        if (
            user_info.get("is_authenticated", False) is False
            and not request.path.startswith(settings.LOGIN_URL)
            and not request.path.startswith("/static/")
            and not request.path.startswith("/media/")
        ):
            return redirect(settings.LOGIN_URL)
        return self.get_response(request)
