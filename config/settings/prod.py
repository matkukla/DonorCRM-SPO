"""
Production settings for DonorCRM.
"""
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
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Static files with Whitenoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa: F405
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

# Database connection pooling
# Use django-db-connection-pool for SQLAlchemy-based pooling
DATABASES['default'] = {  # noqa: F405
    'ENGINE': 'dj_db_conn_pool.backends.postgresql',
    'NAME': config('DB_NAME', default='donorcrm'),  # noqa: F405
    'USER': config('DB_USER', default='donorcrm'),  # noqa: F405
    'PASSWORD': config('DB_PASSWORD', default=''),  # noqa: F405
    'HOST': config('DB_HOST', default='localhost'),  # noqa: F405
    'PORT': config('DB_PORT', default='5432'),  # noqa: F405
    'POOL_OPTIONS': {
        'POOL_SIZE': 20,  # Base connections to keep open
        'MAX_OVERFLOW': 30,  # Additional connections under load
        'RECYCLE': 300,  # Recycle connections after 5 minutes
        'PRE_PING': True,  # Verify connections before use
    }
}

# Cache (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),  # noqa: F405
    }
}

# Logging for production
LOGGING['handlers']['console']['formatter'] = 'verbose'  # noqa: F405
LOGGING['root']['level'] = 'WARNING'  # noqa: F405
