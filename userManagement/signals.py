from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging
from .models import CustomUser, Team
import json

logger = logging.getLogger("user_activity")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    logger.info(f"User logged in", extra={"user_id": user.id})
    user_info = CustomUser.get_user_info(user.id)
    user_info["is_authenticated"] = (
        request.user.is_authenticated if user_info.get("is_active") else False
    )
    request.session["user_info"] = user_info


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        request.session["user_info"] = None
        logger.info(f"User logged out", extra={"user_id": user.id})
    else:
        logger.info("Anonymous user logged out")


# @receiver(post_save, sender=Team)
# def set_team_manager_first_support(sender, instance, created, **kwargs):
#     if instance.manager is not None and (instance.manager.team.count()==0 or instance.manager.team.filter(id=instance.id) is None):
#         user  = CustomUser.objects.get(id=instance.manager.id)
#         user.team.add(instance)
#         user.save()
#     if instance.first_support is not None and (instance.first_support.team.count()==0 or instance.first_support.team.filter(id=instance.id) is None):
#         user  = CustomUser.objects.get(id=instance.first_support.id)
#         user.team.add(instance)
#         user.save()
