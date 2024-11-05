from userManagement.models import AppMenu
import json
import logging
from django.conf import settings
from .util import get_menu_key_in_list

logger = logging.getLogger('django')

def default_context(request):
    context = {
        'site_header': settings.SITE_NAME,
        'title': settings.SITE_NAME,
        'subtitle': None,
		'is_nav_sidebar_enabled': False,
		'is_popup': False,
        'datatables': True,
        'django_tables2': False,
        'exception_notes': None,
        'app_tree': [],
        'current_page_menu': {},
        'level_1_menu': [],
        'permission_list': [],
        'request_path': request.path
    }
    current_page_menu=None
    if not(request.path.startswith('/accounts/') or request.path.startswith('/admin/')):
        current_page_menu = request.current_page_menu
        context['app_tree'] = request.app_tree
        context['current_page_menu'] = current_page_menu
        context['level_1_menu'] = request.level_1_menu
        context['permission_list'] = request.permission_list
    if current_page_menu is not None:
        original_menu = AppMenu.get_menu_tree_by_id_key(current_page_menu.get('id'), current_page_menu.get('key'))
        if original_menu is not None:
            if len(original_menu.get('sub_menu', []))>0: 
                keys = get_menu_key_in_list(original_menu.get('sub_menu'), None)
                for k in keys:
                    context['permission__%s'%k]= False
                for k in request.permission_list:
                    context['permission__%s'%k]= True
        logger.debug(f'context: {json.dumps(context)}')
    return context
