"""
Test settings for DonorCRM.
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# Use faster password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use in-memory SQLite for faster tests (optional - can use PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Disable migrations for faster test runs
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Celery settings for tests
CELERY_ENABLED = True
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# django-axes: never lock out during the test suite. Tests intentionally
# exercise login failure paths and the lockout would cause flaky cascades.
AXES_ENABLED = False

# Static AES-256 key for tests so factories that populate encrypted fields
# (Contact.notes, Contact.phone_secondary, Contact.street_address,
# JournalStageEvent.notes) work out of the box. Tests that exercise the
# encryption module directly use override_settings to inject fresh keys.
# This value is non-secret — it's only ever used against an in-memory SQLite
# DB that doesn't survive the process.
PII_ENCRYPTION_KEYS = "aes256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

# Static blind-index key for tests. Non-secret — see PII_ENCRYPTION_KEYS note.
BLIND_INDEX_KEYS = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
