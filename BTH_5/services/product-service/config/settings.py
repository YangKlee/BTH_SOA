"""Settings for the independent Product Service."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR.parent.parent


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("PRODUCT_DEBUG", True)
SECRET_KEY = os.getenv("PRODUCT_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("PRODUCT_SECRET_KEY is required when PRODUCT_DEBUG is false")
    SECRET_KEY = "django-insecure-product-service-local-dev-only"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("PRODUCT_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
AUTH_SERVICE_TIMEOUT_SECONDS = float(os.getenv("AUTH_SERVICE_TIMEOUT_SECONDS", "3"))
if AUTH_SERVICE_TIMEOUT_SECONDS <= 0:
    raise ValueError("AUTH_SERVICE_TIMEOUT_SECONDS must be positive")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "products",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = []
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": WORKSPACE_DIR / "database" / "products.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["products.authentication.RemoteJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
