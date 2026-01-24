"""
Journals app configuration.
"""
from django.apps import AppConfig


class JournalsConfig(AppConfig):
    name = 'apps.journals'
    verbose_name = 'Journals'

    def ready(self):
        import apps.journals.signals  # noqa: F401
