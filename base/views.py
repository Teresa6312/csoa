from django.shortcuts import render, redirect
from userManagement.models import CustomUser, Permission, AppMenu
from .util import CustomJSONEncoder
from django.http import HttpResponseRedirect
from django.contrib import messages
import json

import logging
logger = logging.getLogger('django')

# @cache_page(60 * 60 * 24)  # 缓存 60*24 分钟
def get_home_view(request):
	template_name = 'base/home.html'
	return render(request, template_name, {
		'menu': request.menu
	})

# @cache_page(60 * 60 * 24)  # 缓存 60*24 分钟
# should be redirect to the page it has permission with
def get_app_home_view(request, app_name):
	user_app_menu = request.menu
	for menu in user_app_menu:
		if menu.get('key', None) == app_name and len(menu.get('subMenu', []))!= 0:
			link = menu.get('subMenu')[0].get('link')
			return HttpResponseRedirect(link)
	mini_app = AppMenu.objects.filter(key=app_name, menu_level=0)
	if mini_app is None or mini_app.count() != 1:
		messages.warning(request, "Application is not found")
		return redirect('app:home')
	messages.warning(request, "No permission")
	return redirect('app:home')

def get_user_profile_view(request):
	template_name = 'base/user_profile.html'
	fields = CustomUser.selected_fields_info()
	profile = CustomUser.objects.filter(id = request.user.id).values(*fields)
	profile_data = json.dumps(list(profile), cls=CustomJSONEncoder)
	permission_fields = Permission.selected_fields_info()
	permission = Permission.objects.filter(user_permissions=request.user.id).values(*permission_fields)
	permission_data = json.dumps(list(permission), cls=CustomJSONEncoder)
	return render(request, template_name, {
		'menu': request.menu,
		'profile': json.loads(profile_data)[0],
		'fields': fields,
		'permission': json.loads(permission_data),
		'permission_fields': permission_fields
	})
