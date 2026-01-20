"""
Development settings for DonorCRM.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'donorcrm-web.onrender.com']

# Add browsable API renderer for development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [  # noqa: F405
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]

# Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar', 'django_extensions']  # noqa: F405

MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405

INTERNAL_IPS = ['127.0.0.1', 'localhost']

# More permissive CORS for development
CORS_ALLOW_ALL_ORIGINS = True

# Longer JWT tokens for development convenience
SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(hours=1)  # noqa: F405
SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] = timedelta(days=30)  # noqa: F405

# Email backend for development (console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging
LOGGING['loggers']['django']['level'] = 'DEBUG'  # noqa: F405
