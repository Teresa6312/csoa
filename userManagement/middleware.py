from .models import AppMenu, CustomUser
from base.redis import get_redis_data_json
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)
class MenuMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		# Define your menu based on any logic, such as user permissions
		menu = self.get_menu_for_user(request)
		# Attach the menu to the request object
		request.menu = menu
		response = self.get_response(request)
		return response

	def get_menu_for_user(self, request):
		if request.path.startswith('/admin/') or not request.user.is_authenticated:
			return {}
		if request.user.is_superuser:
			app_list = get_redis_data_json('app_list_active')
			menu_list = []
			if app_list is None:
				AppMenu.build_app_list_active_redis()
				app_list = get_redis_data_json('app_list_active')
			for app in app_list:
				menu = get_redis_data_json(f"menu_list_active_{app.get('key')}")
				if menu is None:
					AppMenu.build_menu_tree_redis()
					menu = get_redis_data_json(f"menu_list_active_{app.get('key')}")
				menu_list.append(menu)
			return menu_list
		else:
			return request.user.get_user_menu_permissions()

class UserActivityMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response
		self.logger = logging.getLogger('user_activity')

	def __call__(self, request):
		response = self.get_response(request)

		request_params = ''

		if request.method == 'POST':
			request_params = request.POST.urlencode()
		elif request.method == 'GET':
			request_params = request.GET.urlencode()  # For GET parameters

		if request.user.is_authenticated:
			self.logger.info(
				f'User Activity - "{request.method} {request.path} parms: {request_params}"',
				extra={'user_id': request.user.id}
			)
		else:
			self.logger.info(
				f'User Activity - "{request.method} {request.path} parms: {request_params}"',
				extra={'user_id': '(Anonymous user)'}
			)
		return response

# place it in MIDDLEWARE  'yourapp.middleware.CustomErrorHandlingMiddleware',
class CustomErrorHandlingMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        # Log the full exception details
        logger.error("An error occurred", exc_info=True)
        
        # Return a generic error response
        return JsonResponse({'error': 'System error'}, status=500)