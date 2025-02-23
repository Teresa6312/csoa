from userManagement.models import AppMenu, CustomGroup
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import F
from django.db import transaction
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.urls import NoReverseMatch
from .util import get_menu_key_in_list, normalized_url
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger("django")


class MenuMiddleware:
    """
    Middleware to control menu display and access permissions based on user roles and permissions.
    This middleware intercepts requests and sets up menu-related information (menu tree, app tree,
    current page menu, permissions, etc.) in the request object for use in views and templates.
    """

    def __init__(self, get_response):
        """
        Initializes the middleware.

        Args:
            get_response: The next middleware or view to call.
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Handles each incoming request.

        Args:
            request: The request object.

        Returns:
            The response object.
        """
        if request.user.is_authenticated:
            user_info = (
                request.session["user_info"] if "user_info" in request.session else None
            )
        else:
            user_info = None

        # Allow access to accounts/static/global pages, admin pages (for superusers), and favicon.
        if (
            request.path.startswith("/accounts/")
            or (
                request.path.startswith("/admin")
                and user_info is not None
                and user_info.get("is_superuser", False)
                and user_info.get("is_staff", False)
            )
            or request.path == "/favicon.ico"
            or request.path.startswith("/static/")
            or request.path.startswith("/global/")
            or request.path.startswith("/api/global/")
        ):
            response = self.get_response(request)
            return response

        # Normalize the request path to match menu links (remove /api prefix and -filter suffix).
        new_path = normalized_url(request.path)

        # Set up menu_tree, app_tree, current_page_menu, permission_list, and level_1_menu for the user.
        cache_key = f"MenuMiddleware[:{request.user.id}:{new_path}]"
        data = cache.get(cache_key)

        if data is not None:  # Retrieve from cache if available
            request.app_tree = data.get("app_tree")
            request.menu_tree = data.get("menu_tree")
            request.current_page_menu = data.get("current_page_menu")
            request.permission_list = data.get("permission_list")
            request.level_1_menu = data.get("level_1_menu")
        else:  # Build menu information and cache it
            data = {}
            app_tree, menu_tree = self.get_app_tree_for_user(request, user_info)
            request.app_tree = app_tree
            request.menu_tree = menu_tree
            data["app_tree"] = app_tree
            data["menu_tree"] = menu_tree

            if request.path not in ("/", ""):
                current_page_menu = self.get_current_page_menu_for_user(
                    menu_tree, new_path
                )
                request.current_page_menu = current_page_menu
                data["current_page_menu"] = current_page_menu

                permission_list = self.get_permission_list(current_page_menu)
                request.permission_list = permission_list
                data["permission_list"] = permission_list

                role_unit = current_page_menu.get("role_unit", [])
                current_app_key = (
                    role_unit[0].get("permission_role__app__key")
                    if len(role_unit) > 0
                    else None
                )
                level_1_menu = self.get_level_1_menu(
                    request, app_tree, current_app_key, user_info
                )

                request.level_1_menu = level_1_menu
                data["level_1_menu"] = level_1_menu

            cache.set(cache_key, data, settings.CACHE_TIMEOUT_L3)

        # Allow access to the home page.
        if request.path in ("/", ""):
            response = self.get_response(request)
            return response

        # Check if the user has permission to access the current page.
        if request.current_page_menu:
            response = self.get_response(request)
            return response
        else:  # Permission denied
            message = f"You do not have permission to view this page ({new_path})."
            messages.error(request, message)  # Use messages framework

            if request.path.startswith("/api"):  # API request
                return JsonResponse(
                    {"message_type": "error", "message": "No Permission", "data": []},
                    status=403,
                )
            elif request.META.get("HTTP_REFERER"):  # Redirect to previous page
                return redirect(request.META["HTTP_REFERER"])
            else:  # Redirect to home page
                return redirect("/")

    def get_app_tree_for_user(self, request, user_info):
        """
        Retrieves the app tree and menu tree for the user.  Handles superuser and anonymous user cases.

        Args:
            request: The request object.

        Returns:
            A tuple containing the app tree and menu tree.
        """
        if request.path.startswith("/admin") or not request.user.is_authenticated:
            return {}, {}  # Empty trees for admin or anonymous users

        if user_info.get(
            "is_superuser", False
        ):  # Check if user is superuser using get method to avoid KeyError
            apps = AppMenu.get_app_tree()
            menus = AppMenu.get_menu_tree()
        else:
            apps = request.user.get_user_app_tree()
            menus = request.user.get_user_menu_tree()
        return apps, menus

    def get_current_page_menu_for_user(self, menu_tree, new_path):
        """
        Finds the current page's menu item in the menu tree.

        Args:
            menu_tree: The user's menu tree.
            new_path: The normalized request path.

        Returns:
            The menu item dictionary or an empty dictionary if not found.
        """
        for m in menu_tree:
            link = m.get("link")
            if link and new_path == link.lower():
                return m
        return {}  # Return empty dictionary if not found

    def get_level_1_menu(self, request, app_tree, app_key, user_info):
        """
        Retrieves the level 1 menu item (top-level app) based on the request path or app key.

        Args:
            request: The request object.
            app_tree: The user's app tree.
            app_key: The current app key.

        Returns:
            The level 1 menu item dictionary or None.
        """
        if user_info.get("is_superuser", False):
            return next(
                (m for m in app_tree if f"/{m.get('key')}/" in request.path), None
            )
        elif app_key:
            return next((m for m in app_tree if m.get("key") == app_key), None)
        return None

    def get_permission_list(self, current_page_menu):
        """
        Retrieves the list of permissions associated with the current page's menu item.

        Args:
            current_page_menu: The current page's menu item dictionary.

        Returns:
            A list of permission keys or an empty list.
        """
        sub_menu = current_page_menu.get("sub_menu", [])
        return (
            get_menu_key_in_list(sub_menu) if sub_menu else []
        )  # More concise way to check and return


class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("user_activity")

    def __call__(self, request):
        # Only extend session if it exists and is modified
        if hasattr(request, "session") and request.session.modified:
            # Get session cookie age from settings (default or custom backend)
            session_age = settings.SESSION_COOKIE_AGE
            # Update session expiry
            request.session.set_expiry(session_age)

        response = self.get_response(request)

        request_params = ""

        if request.method == "POST":
            request_params = request.POST.urlencode()
        elif request.method == "GET":
            request_params = request.GET.urlencode()  # For GET parameters

        if request.user.is_authenticated:
            self.logger.info(
                f'User Activity - "{request.method} {request.path} parms: {request_params}"',
                extra={"user_id": request.user.id},
            )
        else:
            self.logger.info(
                f'User Activity - "{request.method} {request.path} parms: {request_params}"',
                extra={"user_id": "(Anonymous user)"},
            )
        return response


class AtomicTransactionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST":
            # 在事务中处理所有视图请求
            with transaction.atomic():
                response = self.get_response(request)
        else:
            response = self.get_response(request)
        return response


class CustomErrorHandlingMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        # Log the exception type, message, and stack trace
        error_type = type(exception).__name__
        error_message = str(exception)
        request_path = request.path

        if isinstance(exception, Http404) or isinstance(exception, NoReverseMatch):
            return_message = f"Page {request_path} not found"
        # elif isinstance(exception, HttpResponseForbidden) and "CSRF verification failed" in str(exception): #Check if it is a CSRF error
        # 	return redirect('login')  # Redirect to your login URL named 'login'
        else:
            return_message = f"Please contact system support as needed. An error of type {error_type} occurred at {request_path}: {error_message}"

        # Full error details with stack trace
        logger.error(
            f"Please contact system support as needed. An error of type {error_type} occurred at {request_path}: {error_message}",
            exc_info=True,  # includes stack trace
        )

        if request.path.startswith("/api"):
            return JsonResponse(
                {"message_type": "error", "message": return_message, "data": []},
                status=500,
            )

        referer = request.META.get("HTTP_REFERER")
        messages.error(request, return_message)
        if referer:
            return HttpResponseRedirect(referer)
        else:
            return redirect("app:home")
