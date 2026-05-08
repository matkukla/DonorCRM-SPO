"""
Development settings for DonorCRM.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Add browsable API renderer for development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Django Debug Toolbar
INSTALLED_APPS += ["debug_toolbar", "django_extensions"]  # noqa: F405

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

INTERNAL_IPS = ["127.0.0.1", "localhost"]

# More permissive CORS for development. Hard-guarded so this file cannot
# accidentally be loaded as the production settings module via DJANGO_SETTINGS_MODULE.
assert DEBUG is True, "config.settings.dev must only be loaded with DEBUG=True"
CORS_ALLOW_ALL_ORIGINS = True

# Longer JWT tokens for development convenience
SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] = timedelta(hours=1)  # noqa: F405
SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] = timedelta(days=30)  # noqa: F405

# More permissive throttle rates for development. Keep the same scope keys
# defined in base.py so tests covering throttle behavior don't fail under dev.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "auth": "100/min",
    "auth_hour": "1000/hour",
    "password": "100/min",
    "password_hour": "1000/hour",
    "feedback": "1000/hour",
    "export": "1000/hour",
}

# django-axes: relax thresholds for local dev to avoid lockout during testing.
AXES_FAILURE_LIMIT = 50
AXES_COOLOFF_TIME = 0.05  # ~3 minutes

# Email backend for development (console)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Logging
LOGGING["loggers"]["django"]["level"] = "DEBUG"  # noqa: F405
