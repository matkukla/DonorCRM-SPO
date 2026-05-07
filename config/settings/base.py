"""
Base settings for DonorCRM project.
"""
import os
from datetime import timedelta
from pathlib import Path

from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Default value is INSECURE and only intended for local dev. Production startup
# guard in config/settings/prod.py refuses to boot with this value.
INSECURE_DEFAULT_SECRET_KEY = "django-insecure-change-me-in-production"
SECRET_KEY = config("SECRET_KEY", default=INSECURE_DEFAULT_SECRET_KEY)

# Field-level encryption keys for donor PII. Comma-separated Fernet keys; the
# first is the current write key, remaining keys decrypt rotated rows. Empty
# in dev/test — apps.core.encryption raises ImproperlyConfigured on first use,
# so columns not yet migrated to EncryptedTextField remain unaffected.
# See docs/security/encryption-rollout.md for the rollout procedure.
PII_ENCRYPTION_KEYS = config("PII_ENCRYPTION_KEYS", default="")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=lambda v: [s.strip() for s in v.split(",")]
)

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "axes",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.contacts",
    "apps.groups",
    "apps.tasks",
    "apps.events",
    "apps.dashboard",
    "apps.imports",
    "apps.gifts",
    "apps.prayers",
    "apps.journals",
    "apps.insights",
    "apps.feedback",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.ViewAsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # AxesMiddleware must be the LAST middleware — it inspects the response
    # to detect failed login attempts and increment the lockout counter.
    "axes.middleware.AxesMiddleware",
]

# django-axes: per-account + per-IP lockout. Defends credential stuffing that
# bypasses per-IP throttling. 5 failures within 1 hour locks for 1 hour;
# successful login resets the counter for that user.
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = None
# Don't store the password in axes' AccessAttempt records.
AXES_SENSITIVE_PARAMETERS = ["password"]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="donorcrm"),
        "USER": config("DB_USER", default="donorcrm"),
        "PASSWORD": config("DB_PASSWORD", default="donorcrm"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# Custom User Model
AUTH_USER_MODEL = "users.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "apps.core.validators.AlphanumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Login burst: 5/min covers normal retries; 30/hour caps slow credential
        # stuffing across IP rotation. Account-lockout via django-axes is the
        # primary defense — these are belt-and-suspenders.
        "auth": "5/min",
        "auth_hour": "30/hour",
        "password": "5/min",
        "feedback": "20/hour",
        # Export endpoints: bulk PII egress is high-risk if a JWT is stolen.
        "export": "20/hour",
    },
}

# API Documentation (drf-spectacular)
SPECTACULAR_SETTINGS = {
    "TITLE": "DonorCRM API",
    "DESCRIPTION": "A missionary support management CRM API for tracking donors, gifts, recurring gifts, and tasks.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "TAGS": [
        {"name": "auth", "description": "Authentication endpoints"},
        {"name": "users", "description": "User management"},
        {"name": "contacts", "description": "Donor and prospect management"},
        {"name": "gifts", "description": "Gift and recurring gift tracking"},
        {"name": "tasks", "description": "Reminders and action items"},
        {"name": "events", "description": "Notifications and audit trail"},
        {"name": "groups", "description": "Contact tags and segments"},
        {"name": "dashboard", "description": "Dashboard aggregations"},
        {"name": "imports", "description": "CSV import and export"},
    ],
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_LIFETIME_MINUTES", 15))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# CORS Settings
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=lambda v: [s.strip() for s in v.split(",")],
)
# CSRF trusted origins (Django 4+ requires this for cross-origin POST/PUT/DELETE).
# Defaults to mirror CORS_ALLOWED_ORIGINS so production deploys don't drift.
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default=",".join(CORS_ALLOWED_ORIGINS),
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-view-as-user-id",
]

# Cookie security
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# File upload limits (10 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# Celery Configuration
# CELERY_ENABLED: when False, code paths that would call .delay() must instead
# return an explicit error (or run synchronously). render.yaml currently runs
# without a Redis broker or worker dyno, so the default is False.
CELERY_ENABLED = config("CELERY_ENABLED", default=False, cast=bool)
CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Celery performance and reliability settings
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minute soft limit
CELERY_TASK_TIME_LIMIT = 600  # 10 minute hard limit
CELERY_TASK_ACKS_LATE = True  # Acknowledge after task completes (better reliability)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Don't prefetch too many tasks

# Email Configuration
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="DonorCRM <noreply@donorcrm.app>")

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": config("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        # Dedicated audit channel — see apps.core.audit.audit_event.
        "security.audit": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # django-axes lockout events — surface these alongside audit events.
        "axes": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
