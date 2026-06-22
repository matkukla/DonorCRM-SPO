"""Regression tests for the 2026-06-22 re-scan finding #12.

Demo/test-account management commands must not (a) run under production-like
settings, nor (b) fall back to a publicly-known default password like
``changeme``/``Test1234`` (CWE-798).

Each test fails if the production guard or the secure password resolver is
reverted (project rule #1).
"""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

import pytest

from apps.core.demo_accounts import assert_not_production, resolve_demo_password


@override_settings(DEBUG=False)
def test_assert_not_production_refuses_without_override(monkeypatch):
    monkeypatch.delenv("ALLOW_DEMO_COMMANDS", raising=False)
    with pytest.raises(CommandError):
        assert_not_production()


@override_settings(DEBUG=False)
def test_assert_not_production_allows_with_override(monkeypatch):
    monkeypatch.setenv("ALLOW_DEMO_COMMANDS", "1")
    # Should not raise.
    assert_not_production()


@override_settings(DEBUG=True)
def test_assert_not_production_allows_in_debug(monkeypatch):
    monkeypatch.delenv("ALLOW_DEMO_COMMANDS", raising=False)
    assert_not_production()


def test_resolve_demo_password_uses_env(monkeypatch):
    monkeypatch.setenv("DEMO_USER_PASSWORD", "from-env-secret")
    assert resolve_demo_password() == "from-env-secret"


def test_resolve_demo_password_random_when_unset(monkeypatch):
    monkeypatch.delenv("DEMO_USER_PASSWORD", raising=False)
    pw1 = resolve_demo_password()
    pw2 = resolve_demo_password()
    # No public default; random and unguessable.
    assert pw1 not in ("changeme", "Test1234", "")
    assert len(pw1) >= 16
    assert pw1 != pw2


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_create_test_accounts_command_refuses_in_production(monkeypatch):
    monkeypatch.delenv("ALLOW_DEMO_COMMANDS", raising=False)
    with pytest.raises(CommandError):
        call_command("create_test_accounts", stdout=StringIO())
