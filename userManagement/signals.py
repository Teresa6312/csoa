from .models import Company, Department, Team, AppMenu
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
import logging

@receiver([post_save], sender=Company)
def company_saved(sender, instance, created, **kwargs):
    Company.company_list()
    Company.company_list_active()

@receiver([post_save], sender=Department)
def department_saved(sender, instance, created, **kwargs):
    Department.department_list()
    Department.department_list_active()

@receiver([post_save], sender=Team)
def team_saved(sender, instance, created, **kwargs):
    Team.team_list_active()
    Team.team_list()

@receiver([post_save], sender=AppMenu)
def appmenu_saved(sender, instance, created, **kwargs):
    AppMenu.build_app_list_active_redis()
    AppMenu.build_menu_tree_redis()

@receiver([post_delete], sender=Company)
def company_deleted(sender, instance, **kwargs):
    Company.company_list()
    Company.company_list_active()

@receiver([post_delete], sender=Department)
def department_deleted(sender, instance, **kwargs):
    Department.department_list()
    Department.department_list_active()

@receiver([post_delete], sender=Team)
def team_deleted(sender, instance, **kwargs):
    Team.team_list_active()
    Team.team_list()

@receiver([post_delete], sender=AppMenu)
def appmenu_deleted(sender, instance, **kwargs):
    AppMenu.build_app_list_active_redis()
    AppMenu.build_menu_tree_redis()

logger = logging.getLogger('user_activity')
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    logger.info(f"User logged in", extra={'user_id': user.id})

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        logger.info(f"User logged out", extra={'user_id': user.id})
    else:
        logger.info("Anonymous user logged out")