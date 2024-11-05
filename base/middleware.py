from userManagement.models import AppMenu, CustomGroup
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import F
from django.db import transaction
from django.http import HttpResponseRedirect
from django.http import Http404
from django.urls import NoReverseMatch
from .util import get_menu_key_in_list

logger = logging.getLogger('django')

# csoa.middleware.py control which pages required login, this middleware controls menus and permissions
class MenuMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		
		app_tree, menu_tree = self.get_app_tree_for_user(request)
		request.app_tree = app_tree # app in tree that user has permissions with
		request.menu_tree = menu_tree # app in tree that user has permissions with

		# convert the request.path to meet with the link in menus
		path = request.path.lower()
		new_path = ''
		if path.startswith('/api'):
			path = path.replace('/api', '')
		if path.endswith('-filter'):
			path_split = path.split("/")
			for p in path_split:
				if not p.endswith('-filter') and p !='':
					new_path = f'{new_path}/{p}'
		if new_path == '':
			new_path = path
		# for values will be changed in different request
		current_page_menu = self.get_current_page_menu_for_user(menu_tree, new_path) # menu in tree of the page that user is opening
		request.current_page_menu = current_page_menu
		request.permission_list = self.get_permission_list(current_page_menu)
		role_unit = current_page_menu.get('role_unit', [])
		current_app_key = None
		if len(role_unit) > 0:
			current_app_key = role_unit[0].get('permission_role__app__key', None)
		request.level_1_menu = self.get_level_1_menu(request, app_tree, current_app_key)
		
		# only admin has permission to /admin/ control by Django by default
		# all users have accesses to /accounts/ pages
		# all users have access to home page
		if request.path.startswith('/accounts/') or (request.path.startswith('/admin/') and request.user.is_superuser and request.user.is_staff) or request.path in ['', '/', '/favicon.ico'] or current_page_menu != {}:
			response = self.get_response(request)
			return response
		else:
			messages.error(request, f"You do not have permission to view this page ({new_path}).")
			referer = request.META.get('HTTP_REFERER')  # Previous URL (if exists)
			if request.path.startswith('/api'):
				return JsonResponse({"message_type": "error", "message": "No Permission", "data": []}, status=403)
			elif referer:
				return redirect(referer)
			else:
				return redirect('/')

	def get_app_tree_for_user(self, request):
		if request.path.startswith('/admin/') or not request.user.is_authenticated:
			return {}, {}
		if request.user.is_superuser:
			apps = AppMenu.get_app_tree()
			menus = AppMenu.get_menu_tree()
		else:
			apps, menus = request.user.get_user_app_tree()
		return apps, menus

	def get_current_page_menu_for_user(self, menu_tree, new_path):
		current_page_menu = {}
		# check if the new_path in menu_list that user has permissions with
		for m in menu_tree:
			link = m.get('link', None)
			if link is not None and new_path == link.lower():
				current_page_menu = m
				return current_page_menu
		return current_page_menu

	def get_level_1_menu(self, request, app_tree, app_key):
		if request.user.is_superuser:
			return next((m for m in app_tree if f"/{m.get('key', '')}/" in request.path), None)
		if app_key is not None:
			return next((m for m in app_tree if m.get('key', '') == app_key), None)
		else:
			return None

	def get_permission_list(self, current_page_menu):
		if current_page_menu is not None and len(current_page_menu.get('sub_menu', []))>0: 
			return get_menu_key_in_list(current_page_menu.get('sub_menu'), None)
		return []

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

class AtomicTransactionMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		if request.method == 'POST':
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
		else:
			return_message = f"Please contact system support as needed. An error of type {error_type} occurred at {request_path}: {error_message}"

		# Full error details with stack trace
		logger.error(
			f"Please contact system support as needed. An error of type {error_type} occurred at {request_path}: {error_message}",
			exc_info=True  # includes stack trace
		)

		if request.path.startswith('/api'):
			return JsonResponse({"message_type": "error", "message": return_message, "data": []}, status=500)
		
		referer = request.META.get('HTTP_REFERER')
		messages.error(request, return_message)
		if referer:
			return HttpResponseRedirect(referer)
		else:
			return redirect('app:home')
