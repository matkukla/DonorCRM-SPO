"""Shared helpers for demo/test-account management commands.

These commands create or reset accounts with shared passwords and are intended
for local development and demo seeding only. They must never run against a
production database, and they must not fall back to a publicly-known default
password (CWE-798).
"""

import os
import secrets
import string

from django.conf import settings
from django.core.management.base import CommandError


def assert_not_production():
    """Raise CommandError when running under production-like settings.

    Production is identified by ``DEBUG=False``. An explicit
    ``ALLOW_DEMO_COMMANDS=1`` escape hatch exists for the rare intentional case
    (e.g. seeding a disposable staging box), but the safe default is to refuse
    so a stray invocation cannot create predictable-password accounts — or wipe
    data — against real donor records.
    """
    if settings.DEBUG:
        return
    if os.environ.get("ALLOW_DEMO_COMMANDS") == "1":
        return
    raise CommandError(
        "Refusing to run a demo/test-account command with DEBUG=False "
        "(production-like settings). This command seeds shared-password "
        "accounts and is for local/dev use only. Set ALLOW_DEMO_COMMANDS=1 to "
        "override intentionally."
    )


def resolve_demo_password():
    """Return the demo password from ``DEMO_USER_PASSWORD`` or a random one.

    Never falls back to a public hardcoded default like ``changeme`` or
    ``Test1234`` (CWE-798). When the env var is unset, a strong random password
    is generated; callers surface it to the operator once via stdout.
    """
    password = os.environ.get("DEMO_USER_PASSWORD")
    if password:
        return password
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(20))
