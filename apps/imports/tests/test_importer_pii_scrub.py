"""
Donor PII must not leak into importer error *messages* (issue #117, ADR 0003).

The admin SPO/RE importers were scrubbed in PR #115; these tests pin the same
guarantee for the self-service generic and contact/entity importers:

- Error message strings carry the field name / reason but never the raw donor
  name, email, or external_id.
- Raw exception text is reduced to the exception class name.
- The structured ``data`` row is deliberately kept unredacted (it round-trips
  the uploader's own data for the fix-and-reupload workflow).
"""

from unittest.mock import patch

from django.test import TestCase

from apps.contacts.models import Contact
from apps.imports.generic_services import import_generic_donations
from apps.imports.models import ImportBatchStatus
from apps.imports.services import parse_contacts_csv
from apps.users.models import User, UserRole


def _bytes(s: str) -> bytes:
    return s.encode("utf-8")


class GenericDonationMessageScrubTests(TestCase):
    """import_generic_donations: no donor PII in 'No contact found' messages."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="staff@test.com",
            password="testpass123",
            first_name="Staff",
            last_name="User",
            role=UserRole.MISSIONARY,
        )

    def _error(self, csv_content, match_by):
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by=match_by
        )
        return batch.summary["errors"][0]["error"]

    def test_unknown_contact_by_email_omits_email(self):
        msg = self._error(
            "email,amount,date\nsecret.donor@example.com,100.00,2026-01-15",
            match_by="email",
        )
        self.assertIn("No contact found", msg)
        self.assertNotIn("secret.donor@example.com", msg)

    def test_unknown_contact_by_name_omits_name(self):
        msg = self._error(
            "first_name,last_name,amount,date\nReginald,Worthington,100.00,2026-01-15",
            match_by="name",
        )
        self.assertIn("No contact found", msg)
        self.assertNotIn("Reginald", msg)
        self.assertNotIn("Worthington", msg)

    def test_unknown_contact_by_external_id_omits_id(self):
        msg = self._error(
            "external_id,amount,date\nDONOR-SECRET-9001,100.00,2026-01-15",
            match_by="external_id",
        )
        self.assertIn("No contact found", msg)
        self.assertNotIn("DONOR-SECRET-9001", msg)

    def test_decode_failure_message_is_class_name_only(self):
        with patch(
            "apps.imports.generic_services.decode_csv_bytes",
            side_effect=ValueError("decode failed for big.donor@example.com"),
        ):
            batch = import_generic_donations(
                _bytes("email,amount,date\na@b.com,1.00,2026-01-15"),
                "d.csv",
                self.user,
                self.user,
                match_by="email",
            )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        msg = batch.summary["errors"][0]["error"]
        self.assertEqual(msg, "ValueError")
        self.assertNotIn("big.donor@example.com", msg)


class ContactCsvMessageScrubTests(TestCase):
    """parse_contacts_csv: email reasons carry no raw value; data row is kept."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@test.com",
            password="testpass123",
            first_name="Owner",
            last_name="User",
            role=UserRole.ADMIN,
        )

    def _row_errors(self, csv_content):
        _, errors = parse_contacts_csv(csv_content, self.user)
        return errors

    def test_invalid_email_message_omits_value_but_data_keeps_it(self):
        errors = self._row_errors("first_name,last_name,email\nJane,Doe,not-an-email")
        self.assertEqual(len(errors), 1)
        messages = " ".join(errors[0]["errors"])
        self.assertIn("Invalid email format", messages)
        self.assertNotIn("not-an-email", messages)
        # ADR 0003: the structured row is intentionally NOT redacted.
        self.assertEqual(errors[0]["data"]["email"], "not-an-email")

    def test_duplicate_email_message_omits_value(self):
        csv_content = (
            "first_name,last_name,email\n" "Jane,Doe,dupe@example.com\n" "John,Roe,dupe@example.com"
        )
        errors = self._row_errors(csv_content)
        messages = " ".join(e for err in errors for e in err["errors"])
        self.assertIn("Duplicate email in file", messages)
        self.assertNotIn("dupe@example.com", messages)

    def test_existing_email_message_omits_value(self):
        Contact.objects.create(
            owner=self.user,
            first_name="Existing",
            last_name="Donor",
            email="already@example.com",
        )
        errors = self._row_errors("first_name,last_name,email\nNew,Person,already@example.com")
        messages = " ".join(errors[0]["errors"])
        self.assertIn("already exists", messages)
        self.assertNotIn("already@example.com", messages)
