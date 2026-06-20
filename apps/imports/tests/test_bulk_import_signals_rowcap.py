"""
Bulk gift import: signal suppression, stat recompute, and the row cap (#118).

Synchronous CSV import runs inside the web request (Celery is off in prod). Two
mitigations keep it inside the gunicorn timeout:

(2) The gift importers suppress the per-gift stat/notification signal cascade and
    recompute each affected contact exactly once. These tests pin that the final
    stats are still correct, that per-gift Events are not created, and -- the
    critical safety property -- that gift signals are always re-enabled afterward
    (even on error), so the thread-local disable flag can never leak.

(3) The gift views reject uploads above MAX_GIFT_IMPORT_ROWS up front with a 400,
    while the service itself stays uncapped (the bulk migration runs via a
    management command with no request timeout).
"""

from unittest.mock import patch

from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.events.models import Event, EventType
from apps.gifts.models import Gift
from apps.gifts.signals import _signals_disabled, gift_signals_disabled
from apps.imports.generic_services import import_generic_donations
from apps.imports.models import ImportBatchStatus
from apps.users.models import User, UserRole


def _bytes(s: str) -> bytes:
    return s.encode("utf-8")


class BulkImportSignalSuppressionTests(TestCase):
    """import_generic_donations suppresses signals but recomputes stats once."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="staff@test.com",
            password="testpass123",
            first_name="Staff",
            last_name="User",
            role=UserRole.MISSIONARY,
        )
        self.contact = Contact.objects.create(
            owner=self.user,
            first_name="John",
            last_name="Smith",
            email="john@example.com",
        )

    def _import(self, csv_content):
        return import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="email"
        )

    def test_stats_correct_after_bulk_import(self):
        """Final giving stats are accurate even though per-gift signals were off."""
        self._import(
            "email,amount,date\n"
            "john@example.com,100.00,2026-01-15\n"
            "john@example.com,50.00,2026-02-01\n"
            "john@example.com,25.00,2026-03-01"
        )
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.gift_count, 3)
        self.assertEqual(self.contact.total_given, 175)
        self.assertEqual(str(self.contact.last_gift_date), "2026-03-01")

    def test_per_gift_events_not_created_on_bulk_import(self):
        """Bulk import does not emit a DONATION_RECEIVED event per gift."""
        self._import(
            "email,amount,date\n"
            "john@example.com,100.00,2026-01-15\n"
            "john@example.com,50.00,2026-02-01"
        )
        self.assertEqual(Gift.objects.count(), 2)
        self.assertEqual(Event.objects.filter(event_type=EventType.DONATION_RECEIVED).count(), 0)
        self.contact.refresh_from_db()
        self.assertFalse(self.contact.needs_thank_you)

    def test_signals_reenabled_after_successful_import(self):
        self.assertFalse(_signals_disabled())
        self._import("email,amount,date\njohn@example.com,100.00,2026-01-15")
        self.assertFalse(_signals_disabled(), "signals must be re-enabled after import")

    def test_signals_reenabled_after_failed_import(self):
        """Even if the import raises mid-flight, the disable flag must not leak."""
        self.assertFalse(_signals_disabled())
        # Patched on the signals module because the importer imports it lazily.
        with patch(
            "apps.gifts.signals.recompute_giving_stats",
            side_effect=RuntimeError("boom"),
        ):
            batch = self._import("email,amount,date\njohn@example.com,100.00,2026-01-15")
        # The service swallows the error into a FAILED batch...
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        # ...but the signal flag is restored regardless.
        self.assertFalse(_signals_disabled())

    def test_normal_gift_create_still_fires_signal_after_import(self):
        """A regular create outside the importer still recomputes (no global leak)."""
        self._import("email,amount,date\njohn@example.com,100.00,2026-01-15")
        # A subsequent direct create must trigger the signal cascade normally.
        Gift.objects.create(donor_contact=self.contact, amount_cents=4200, gift_date="2026-04-01")
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.gift_count, 2)
        self.assertEqual(self.contact.total_given, 142)


class GiftSignalsContextManagerTests(TestCase):
    """The context-manager form (used by import_spo_gifts) is exception-safe."""

    def test_reenables_on_normal_exit(self):
        self.assertFalse(_signals_disabled())
        with gift_signals_disabled():
            self.assertTrue(_signals_disabled())
        self.assertFalse(_signals_disabled())

    def test_reenables_on_exception(self):
        self.assertFalse(_signals_disabled())
        with self.assertRaises(ValueError):
            with gift_signals_disabled():
                self.assertTrue(_signals_disabled())
                raise ValueError("boom")
        self.assertFalse(_signals_disabled())

    def test_reentrant_nesting(self):
        with gift_signals_disabled():
            with gift_signals_disabled():
                self.assertTrue(_signals_disabled())
            # Still disabled after the inner block exits (counter > 0).
            self.assertTrue(_signals_disabled())
        self.assertFalse(_signals_disabled())


class GiftImportRowCapTests(TestCase):
    """The gift views reject oversized uploads up front (issue #118)."""

    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            email="staff@test.com",
            password="testpass123",
            first_name="Staff",
            last_name="User",
            role=UserRole.MISSIONARY,
        )
        Contact.objects.create(
            owner=self.staff, first_name="John", last_name="Smith", email="john@example.com"
        )
        self.client.force_authenticate(user=self.staff)
        self.url = "/api/v1/imports/generic/donations/"

    def _upload(self, csv_content):
        from django.core.files.uploadedfile import SimpleUploadedFile

        f = SimpleUploadedFile("d.csv", _bytes(csv_content), content_type="text/csv")
        return self.client.post(self.url, {"file": f, "match_by": "email"}, format="multipart")

    @patch("apps.imports.views.MAX_GIFT_IMPORT_ROWS", 2)
    def test_upload_over_cap_is_rejected(self):
        csv_content = (
            "email,amount,date\n"
            "john@example.com,10.00,2026-01-01\n"
            "john@example.com,20.00,2026-01-02\n"
            "john@example.com,30.00,2026-01-03"
        )
        resp = self._upload(csv_content)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceeds", resp.json()["detail"])
        # Nothing imported on rejection.
        self.assertEqual(Gift.objects.count(), 0)

    @patch("apps.imports.views.MAX_GIFT_IMPORT_ROWS", 2)
    def test_upload_at_cap_is_accepted(self):
        csv_content = (
            "email,amount,date\n"
            "john@example.com,10.00,2026-01-01\n"
            "john@example.com,20.00,2026-01-02"
        )
        resp = self._upload(csv_content)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Gift.objects.count(), 2)

    def test_count_helper_ignores_header_and_handles_garbage(self):
        from apps.imports.views import _count_csv_data_rows

        self.assertEqual(_count_csv_data_rows(_bytes("email,amount,date\na@b.com,1,2026-01-01")), 1)
        self.assertEqual(_count_csv_data_rows(_bytes("email,amount,date\n")), 0)
