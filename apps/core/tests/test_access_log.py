"""Tests for DataAccessLog model + DataAccessLogMiddleware.

Verifies the path-pattern classifier, that PII reads are recorded with
the right resource_type / resource_id, and that non-PII paths are skipped.
"""
from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core import access_log_middleware
from apps.core.models import DataAccessLog


class TestPathClassifier:
    """Direct unit tests of the regex-based path matcher."""

    def test_contact_list_classified(self):
        rt, rid = access_log_middleware._classify("/api/v1/contacts/")
        assert rt == "Contact"
        assert rid == ""

    def test_contact_retrieve_classified(self):
        path = "/api/v1/contacts/12345678-1234-5678-1234-567812345678/"
        rt, rid = access_log_middleware._classify(path)
        assert rt == "Contact"
        assert rid == "12345678-1234-5678-1234-567812345678"

    def test_gift_list_classified(self):
        rt, _ = access_log_middleware._classify("/api/v1/gifts/")
        assert rt == "Gift"

    def test_recurring_gift_retrieve(self):
        path = "/api/v1/recurring-gifts/12345678-1234-5678-1234-567812345678/"
        rt, rid = access_log_middleware._classify(path)
        assert rt == "RecurringGift"
        assert rid == "12345678-1234-5678-1234-567812345678"

    def test_journal_member_retrieve(self):
        path = "/api/v1/journal-members/12345678-1234-5678-1234-567812345678/"
        rt, rid = access_log_middleware._classify(path)
        assert rt == "JournalContact"
        assert rid == "12345678-1234-5678-1234-567812345678"

    def test_health_endpoint_skipped(self):
        rt, _ = access_log_middleware._classify("/api/v1/health/")
        assert rt == ""

    def test_auth_endpoints_skipped(self):
        for p in ["/api/v1/auth/login/", "/api/v1/auth/refresh/", "/api/v1/auth/logout/"]:
            rt, _ = access_log_middleware._classify(p)
            assert rt == "", f"{p} should be skipped (auth has its own audit channel)"

    def test_unmatched_path_returns_empty(self):
        rt, _ = access_log_middleware._classify("/api/v1/dashboard/")
        assert rt == ""

    def test_export_endpoint_classified(self):
        rt, _ = access_log_middleware._classify("/api/v1/imports/contacts/export/")
        assert rt == "ImportExport"


@pytest.mark.django_db
class TestMiddlewareIntegration:
    """End-to-end: hitting an endpoint creates exactly one DataAccessLog row."""

    def test_contact_list_writes_log_row(self, authenticated_client):
        from apps.contacts.models import Contact

        client, owner = authenticated_client
        # Need at least one contact so the list isn't trivially empty.
        Contact.objects.create(owner=owner, first_name="A", last_name="B")

        before = DataAccessLog.objects.count()
        url = reverse("contacts:contact-list")
        resp = client.get(url)
        assert resp.status_code == 200

        after = DataAccessLog.objects.count()
        assert after == before + 1
        log = DataAccessLog.objects.latest("timestamp")
        assert log.resource_type == "Contact"
        assert log.resource_id == ""
        assert log.method == "GET"
        assert log.status_code == 200
        # row_count populated from paginator
        assert log.row_count >= 1
        # actor recorded
        assert log.actor_id == owner.id

    def test_health_endpoint_does_not_log(self, authenticated_client):
        # authenticated_client is a (client, user) tuple — see conftest.
        client, _ = authenticated_client
        before = DataAccessLog.objects.count()
        # The health endpoint may not be wired in test settings; if reverse
        # fails, skip — the path classifier was already covered above.
        try:
            url = reverse("api-health")
        except Exception:
            pytest.skip("health endpoint not registered in test URLs")
        client.get(url)
        assert DataAccessLog.objects.count() == before

    def test_anonymous_request_to_pii_endpoint(self, api_client):
        """An unauthenticated request to a PII path is still logged.

        The endpoint will return 401/403; we want a row recording the
        attempt for forensics (correlate with auth failures).
        """
        url = reverse("contacts:contact-list")
        resp = api_client.get(url)
        # actor stays NULL for unauthenticated; ensure no crash.
        log_qs = DataAccessLog.objects.filter(path__startswith="/api/v1/contacts")
        # At least one row exists with no actor
        assert log_qs.filter(actor__isnull=True).exists()
        # Status code reflects the auth failure
        last = log_qs.latest("timestamp")
        assert last.status_code in (401, 403)
        assert resp.status_code in (401, 403)


@pytest.mark.django_db
class TestRetentionPurge:
    """purge_expired_data deletes DataAccessLog rows past 1 year."""

    def test_old_rows_purged(self, user_factory):
        from datetime import timedelta

        from django.utils import timezone

        owner = user_factory()
        # Create a fresh row and an old row.
        fresh = DataAccessLog.objects.create(
            actor=owner,
            actor_id_snapshot=owner.id,
            method="GET",
            path="/api/v1/contacts/",
            resource_type="Contact",
            status_code=200,
        )
        old = DataAccessLog.objects.create(
            actor=owner,
            actor_id_snapshot=owner.id,
            method="GET",
            path="/api/v1/contacts/",
            resource_type="Contact",
            status_code=200,
        )
        # Force timestamp into the past (auto_now_add bypasses on update).
        DataAccessLog.objects.filter(pk=old.pk).update(
            timestamp=timezone.now() - timedelta(days=400)
        )

        from io import StringIO

        from django.core.management import call_command

        call_command("purge_expired_data", stdout=StringIO())

        assert DataAccessLog.objects.filter(pk=fresh.pk).exists()
        assert not DataAccessLog.objects.filter(pk=old.pk).exists()
