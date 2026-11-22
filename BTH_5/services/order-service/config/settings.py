"""Configuration for the independent Order Service."""
import math
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR.parent.parent


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def positive_timeout(name):
    try:
        value = float(os.getenv(name, "3"))
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be a positive finite number") from exc
    if not math.isfinite(value) or value <= 0:
        raise ImproperlyConfigured(f"{name} must be a positive finite number")
    return value


DEBUG = env_bool("ORDER_DEBUG", True)
SECRET_KEY = os.getenv("ORDER_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("ORDER_SECRET_KEY is required when ORDER_DEBUG is false")
    SECRET_KEY = "django-insecure-order-service-local-dev-only"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ORDER_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
AUTH_SERVICE_TIMEOUT_SECONDS = positive_timeout("AUTH_SERVICE_TIMEOUT_SECONDS")
PRODUCT_SERVICE_TIMEOUT_SECONDS = positive_timeout("PRODUCT_SERVICE_TIMEOUT_SECONDS")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "orders",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = []
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
APPEND_SLASH = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": WORKSPACE_DIR / "database" / "orders.sqlite3",
        # Acquire the write reservation before reading mutable local state.
        # Only the service layer opens atomic blocks; HTTP happens beforehand.
        "OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": 3},
        "TEST": {"NAME": os.getenv("ORDER_TEST_DB") or None},
    }
}
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["orders.authentication.RemoteJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
