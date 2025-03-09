from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ""

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3"
    },
    "xyz_db": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3"
    }
}
# Add database router
DATABASE_ROUTERS = ['csoa.routers.XYZRouter']
# email
SENDGRID_API_KEY = ""

EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_PORT = 587  # 25,587 for unencrypted/TSL; 465 FOR ssl
EMAIL_HOST_USER = "apikey"
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = True
# Email address that error messages come from.
SERVER_EMAIL = "csoa_test@csoa.com"
ADMINS = [("Cuishan", "csoa_test@gmail.com")]
# the site managers.
DEFAULT_FROM_EMAIL = "csoa_test@csoa.com"

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB_SESSIONS = 0 # 0-15 for default redis server, 0 is used for sessions
REDIS_DB_CACHE = 2
REDIS_PASSWORD = ""

CACHE_TIMEOUT_DEFAULT = 60 * 5  # 5 minutes
CACHE_TIMEOUT_L1 = 60 * 15  # 15 minutes
CACHE_TIMEOUT_L2 = 60 * 30  # 30 minutes
CACHE_TIMEOUT_L3 = 60 * 60  # 60 minutes

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = os.path.join(BASE_DIR, "staticProd")

MEDIA_URL = "/files/"  # URL prefix for media files
# File system path to the directory for storing media files
MEDIA_ROOT = os.path.join(BASE_DIR, "files")
