"""Tests for apps.core.db_tls_check.

Limited to backends-agnostic behavior because the test DB is SQLite. The
Postgres TLS query is exercised in production by ``CoreConfig.ready()``.
"""
from __future__ import annotations

from unittest import mock

from django.test import override_settings

import pytest

from apps.core import db_tls_check


def test_verify_returns_none_on_non_postgres():
    """SQLite (test backend) is exempt — TLS doesn't apply at the DB layer."""
    with mock.patch.object(db_tls_check, "connection") as conn:
        conn.vendor = "sqlite"
        assert db_tls_check.verify_db_tls(strict=True) is None


def test_strict_mode_raises_on_no_tls():
    with mock.patch.object(db_tls_check, "connection") as conn:
        conn.vendor = "postgresql"
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (False, None, None, None)
        with pytest.raises(RuntimeError, match="not using TLS"):
            db_tls_check.verify_db_tls(strict=True)


def test_strict_mode_raises_on_old_tls():
    with mock.patch.object(db_tls_check, "connection") as conn:
        conn.vendor = "postgresql"
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (True, "TLSv1.1", "ECDHE-RSA-AES128-SHA", 128)
        with pytest.raises(RuntimeError, match="below the minimum"):
            db_tls_check.verify_db_tls(strict=True)


def test_strict_mode_accepts_tls12():
    with mock.patch.object(db_tls_check, "connection") as conn:
        conn.vendor = "postgresql"
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (True, "TLSv1.2", "ECDHE-RSA-AES256-GCM-SHA384", 256)
        info = db_tls_check.verify_db_tls(strict=True)
        assert info["ssl"] is True
        assert info["version"] == "TLSv1.2"
        assert info["bits"] == 256


def test_strict_mode_accepts_tls13():
    with mock.patch.object(db_tls_check, "connection") as conn:
        conn.vendor = "postgresql"
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (True, "TLSv1.3", "TLS_AES_256_GCM_SHA384", 256)
        info = db_tls_check.verify_db_tls(strict=True)
        assert info["version"] == "TLSv1.3"


def test_maybe_verify_noop_outside_prod():
    """The startup hook is gated on the settings module ending in '.prod'."""
    with override_settings(SETTINGS_MODULE="config.settings.test"):
        # Should not raise even though the test DB has no TLS.
        db_tls_check.maybe_verify_at_startup()
