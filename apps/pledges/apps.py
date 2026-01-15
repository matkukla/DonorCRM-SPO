from django.apps import AppConfig


class PledgesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pledges'
    verbose_name = 'Pledges'

    def ready(self):
        import apps.pledges.signals  # noqa: F401
