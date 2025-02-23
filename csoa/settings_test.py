import os
from .settings_base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-lk+ed7e!ek)7b(-d69*)b4%=!rl3ka5nkk1y#jz&gr37am*qr4"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# email
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")

EMAIL_HOST = os.environ.get("SENDGRID_SMTP_HOST", "")
EMAIL_PORT = 587
EMAIL_HOST_USER = os.environ.get("SENDGRID_USERNAME", "")
EMAIL_HOST_PASSWORD = os.environ.get("SENDGRID_PASSWORD", "")
EMAIL_USE_TLS = True
# Email address that error messages come from.
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "")
ADMINS = [("Your Name", "your_email@example.com")]
# Default email address to use for various automated correspondence from
# the site managers.
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "")

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 2
REDIS_PASSWORD = ""

# myproject/settings.py
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

CACHE_TIMEOUT_DEFAULT = 60 * 5  # 5 minutes
CACHE_TIMEOUT_L1 = 60 * 15  # 15 minutes
CACHE_TIMEOUT_L2 = 60 * 30  # 30 minutes
CACHE_TIMEOUT_L3 = 60 * 60  # 60 minutes

#
# Redis Key format "%s:%s:%s" % (key_prefix, version, key)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",  # Redis 服务器地址
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "DECODE_RESPONSES": True,  # Important for correct data handling
        },
        "TIMEOUT": CACHE_TIMEOUT_DEFAULT,
        # 'KEY_PREFIX': 'global'  # Optional prefix to avoid namespacing issues
    }
}

if DEBUG == False:
    MIDDLEWARE.append(
        "base.middleware.CustomErrorHandlingMiddleware"
    )  # middleware to handle error pages
