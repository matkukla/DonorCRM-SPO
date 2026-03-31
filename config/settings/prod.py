"""
Production settings for DonorCRM.
"""
import os

import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *  # noqa: F401, F403

DEBUG = False

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Static files with Whitenoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa: F405

# Content-Security-Policy via django-csp (after SecurityMiddleware + WhiteNoise)
MIDDLEWARE.insert(2, 'csp.middleware.CSPMiddleware')  # noqa: F405
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Sentry for error tracking
SENTRY_DSN = config('SENTRY_DSN', default='')  # noqa: F405
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=config('ENVIRONMENT', default='production'),  # noqa: F405
    )

# Database configuration
# Parse DATABASE_URL (provided by Render) or fall back to individual vars
if os.environ.get('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.config(  # noqa: F405
        default=os.environ['DATABASE_URL'],
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )
else:
    DATABASES['default'] = {  # noqa: F405
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='donorcrm'),  # noqa: F405
        'USER': config('DB_USER', default='donorcrm'),  # noqa: F405
        'PASSWORD': config('DB_PASSWORD', default=''),  # noqa: F405
        'HOST': config('DB_HOST', default='localhost'),  # noqa: F405
        'PORT': config('DB_PORT', default='5432'),  # noqa: F405
    }

# Cache — use Redis if available, otherwise in-memory
REDIS_URL = config('REDIS_URL', default='')  # noqa: F405
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Content-Security-Policy directives (django-csp 4.0 format)
# Strict policy for API responses (Django serves JSON, not HTML pages).
# Admin and API docs are excluded because they use inline styles/scripts.
CONTENT_SECURITY_POLICY = {
    "EXCLUDE_URL_PREFIXES": ["/backstage", "/api/v1/docs", "/api/v1/redoc"],
    "DIRECTIVES": {
        "default-src": ["'none'"],
        "script-src": ["'self'"],
        "style-src": ["'self'"],
        "img-src": ["'self'"],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "form-action": ["'self'"],
        "base-uri": ["'self'"],
    },
}

# Referrer-Policy (natively supported by Django SecurityMiddleware 4.2+)
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Note: Permissions-Policy is not added to the Django API server because it is
# primarily a browser-enforced policy for HTML pages. Django serves JSON API
# responses. Permissions-Policy is set on the frontend static site via render.yaml.

# Logging for production
LOGGING['handlers']['console']['formatter'] = 'verbose'  # noqa: F405
LOGGING['root']['level'] = 'WARNING'  # noqa: F405
