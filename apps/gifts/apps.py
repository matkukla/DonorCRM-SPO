"""
App configuration for the gifts app.
"""

from django.apps import AppConfig


class GiftsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gifts"
    verbose_name = "Gifts"

    def ready(self):
        import apps.gifts.signals  # noqa: F401
