from userManagement.models import AppMenu
import json
import logging
from django.conf import settings
from .util import get_menu_key_in_list
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger("django")


def default_context(request):
    context = {
        "site_header": settings.SITE_NAME,
        "title": settings.SITE_NAME,
        "site_title": None,
        "is_nav_sidebar_enabled": False,
        "is_popup": False,
        "datatables": True,
        "exception_notes": None,
        "app_tree": [],
        "current_page_menu": {},
        "level_1_menu": [],
        "permission_list": [],
        "request_path": request.path,
        "mini_app": None,
        "user_info": request.session.get("user_info", None),
    }
    current_page_menu = None
    if not (
        request.path.startswith("/accounts/") or request.path.startswith("/admin/")
    ):
        current_page_menu = (
            request.current_page_menu if hasattr(request, "current_page_menu") else None
        )
        permission_list = (
            request.permission_list if hasattr(request, "permission_list") else None
        )
        context["app_tree"] = request.app_tree if hasattr(request, "app_tree") else None
        context["current_page_menu"] = current_page_menu
        context["level_1_menu"] = (
            request.level_1_menu if hasattr(request, "level_1_menu") else None
        )
        context["permission_list"] = permission_list
        if permission_list is not None:
            for k in permission_list:
                context["permission__%s" % k] = True
    return context


# def get_user_current_page_menu_permission_context(
#     request, current_page_menu, permission_list
# ):
#     if current_page_menu is not None:
#         cache_key = f"user_current_page_menu_permission_context[:{request.user.id}:{current_page_menu.get('id', '')}]"
#         context = cache.get(cache_key)
#         if context is not None:
#             return context
#         context = {}
#         original_menu = AppMenu.get_menu_tree_by_id_key(
#             current_page_menu.get("id"), current_page_menu.get("key")
#         )
#         if original_menu is not None:
#             if len(original_menu.get("sub_menu", [])) > 0:
#                 keys = get_menu_key_in_list(original_menu.get("sub_menu"), None)
#                 for k in keys:
#                     context["permission__%s" % k] = False
#                 for k in request.permission_list:
#                     context["permission__%s" % k] = True
#         # logger.debug(f'context: {json.dumps(context)}')
#         cache.set(cache_key, context, settings.CACHE_TIMEOUT_L3)
#         return context
#     else:
#         return {}
