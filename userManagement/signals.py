from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging
from .models import CustomUser, Team
from django.core.cache import cache
from django.contrib.sessions.backends.cache import SessionStore
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
    key = f"active_user:{user.id}"
    record = cache.get(key)
    if record is not None:
        session_store  = SessionStore(session_key=record)
        session_store.delete()  # Delete session from Redis
    cache.set(key, request.session.session_key, 60*60*24)

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        request.session["user_info"] = None
        logger.info(f"User logged out", extra={"user_id": user.id})
    else:
        logger.info("Anonymous user logged out")
    key = f"active_user:{user.id}"
    cache.delete(key)
