from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

    def ready(self) -> None:
        # Verify Postgres TLS posture once per process boot in production.
        # No-op in dev/test (SQLite, non-prod settings module). Failure
        # raises so a misconfigured deploy fails its health check instead
        # of silently serving over a non-TLS link.
        from apps.core.db_tls_check import maybe_verify_at_startup

        maybe_verify_at_startup()
