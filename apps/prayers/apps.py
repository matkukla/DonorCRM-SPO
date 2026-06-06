"""
App configuration for prayer intentions.
"""

from django.apps import AppConfig


class PrayersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.prayers"
    verbose_name = "Prayer Intentions"
