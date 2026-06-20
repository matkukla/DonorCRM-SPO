"""
Export hardening from the pilot-audit cleanup (issue #119).

- The dedicated streaming export views declare ``throttle_scope = "export"`` so a
  stolen token cannot pull the donor base uncapped (item 2).
- The legacy in-memory exporters cap the rows they materialize (item 3).
"""

import csv
import io
from unittest.mock import patch

from django.test import TestCase

from apps.contacts.export_views import ContactExportCSVView
from apps.contacts.models import Contact
from apps.gifts.export_views import GiftExportCSVView, RecurringGiftExportCSVView
from apps.gifts.models import Gift
from apps.imports.services import export_contacts_csv, export_gifts_csv
from apps.users.models import User, UserRole


class ExportThrottleScopeTests(TestCase):
    """The dedicated export views participate in the 'export' throttle scope."""

    def test_dedicated_export_views_declare_export_scope(self):
        self.assertEqual(ContactExportCSVView.throttle_scope, "export")
        self.assertEqual(GiftExportCSVView.throttle_scope, "export")
        self.assertEqual(RecurringGiftExportCSVView.throttle_scope, "export")


class LegacyExporterCapTests(TestCase):
    """export_contacts_csv / export_gifts_csv never materialize an unbounded set."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@test.com",
            password="testpass123",
            first_name="Owner",
            last_name="User",
            role=UserRole.MISSIONARY,
        )

    @staticmethod
    def _data_rows(csv_text):
        reader = csv.reader(io.StringIO(csv_text))
        next(reader, None)  # header
        return [r for r in reader if r]

    @patch("apps.imports.services.MAX_EXPORT_ROWS", 2)
    def test_contact_export_is_capped(self):
        for i in range(3):
            Contact.objects.create(
                owner=self.user, first_name=f"C{i}", last_name="X", email=f"c{i}@example.com"
            )
        out = export_contacts_csv(Contact.objects.all())
        self.assertEqual(len(self._data_rows(out)), 2)

    @patch("apps.imports.services.MAX_EXPORT_ROWS", 2)
    def test_gift_export_is_capped(self):
        contact = Contact.objects.create(
            owner=self.user, first_name="John", last_name="Smith", email="john@example.com"
        )
        for i in range(3):
            Gift.objects.create(
                donor_contact=contact, amount_cents=1000 + i, gift_date="2026-01-0%d" % (i + 1)
            )
        out = export_gifts_csv(Gift.objects.all())
        self.assertEqual(len(self._data_rows(out)), 2)

    def test_export_under_cap_returns_all_rows(self):
        for i in range(3):
            Contact.objects.create(
                owner=self.user, first_name=f"C{i}", last_name="X", email=f"c{i}@example.com"
            )
        out = export_contacts_csv(Contact.objects.all())
        self.assertEqual(len(self._data_rows(out)), 3)
