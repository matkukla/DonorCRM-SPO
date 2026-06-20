"""
Behavioral coverage tests for apps/imports/generic_services.py.

Targets currently-uncovered branches of import_generic_contacts and
import_generic_donations:
- header validation failures for every match_by strategy
- decode failure path (FAILED batch)
- match_by=external_id create / update / idempotency
- match_by=name create + missing-name row errors
- org-only contact creation with optional fields
- donation amount/date validation, name/external_id matching, fund matching
- row-level exception collection (per-row try/except)

These exercise real import behavior with realistic CSV rows and assert on the
records actually written (money in cents) and the returned ImportBatch summary.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.contacts.models import Contact
from apps.core.blind_index import lookup_hashes
from apps.gifts.models import Gift
from apps.imports.generic_services import import_generic_contacts, import_generic_donations
from apps.imports.models import Fund, ImportBatchStatus, ImportBatchType
from apps.users.models import User, UserRole


def _bytes(csv_text: str) -> bytes:
    return csv_text.encode("utf-8")


class GenericContactHeaderValidationTests(TestCase):
    """Missing-header validation per match_by strategy -> FAILED batch."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@test.com",
            password="testpass123",
            first_name="Owner",
            last_name="User",
            role=UserRole.MISSIONARY,
        )

    def test_match_by_email_missing_email_header_fails(self):
        # Has name columns (so create requirement satisfied) but no email column.
        csv_content = "first_name,last_name,phone\nJohn,Smith,555-1234"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="email"
        )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        self.assertIn("email", batch.summary["errors"][0]["error"])
        # No contacts created on header failure.
        self.assertEqual(Contact.objects.count(), 0)

    def test_match_by_external_id_missing_id_header_fails(self):
        csv_content = "first_name,last_name,phone\nJohn,Smith,555-1234"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        self.assertIn("external_id", batch.summary["errors"][0]["error"])

    def test_match_by_name_missing_name_headers_fails(self):
        # Only email column present; name matching needs first+last AND
        # creation needs name-or-org -> two missing-header complaints.
        csv_content = "email\njohn@example.com"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="name"
        )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        error = batch.summary["errors"][0]["error"]
        self.assertIn("first_name", error)
        self.assertIn("last_name", error)

    def test_missing_name_and_org_creation_headers_fails(self):
        # email present (satisfies match_by=email) but neither name nor org
        # columns exist -> can't create new contacts.
        csv_content = "email,phone\njohn@example.com,555-1234"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="email"
        )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        self.assertIn("organization_name", batch.summary["errors"][0]["error"])

    def test_undecodable_file_returns_failed_batch(self):
        # decode_csv_bytes only raises ValueError if every encoding fails;
        # windows-1252 accepts all bytes, so we patch to simulate a hard
        # decode failure and assert the FAILED branch is taken.
        with patch(
            "apps.imports.generic_services.decode_csv_bytes",
            side_effect=ValueError("Unable to decode file: donor@example.com"),
        ):
            batch = import_generic_contacts(
                _bytes("first_name,last_name\nJohn,Smith"),
                "bad.csv",
                self.user,
                self.user,
                match_by="name",
            )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        self.assertEqual(batch.summary["errors"][0]["row"], 0)
        # The raw exception text (which can carry PII) is scrubbed to the class
        # name only -- see ADR 0003. Never echo str(e) into the summary.
        self.assertEqual(batch.summary["errors"][0]["error"], "ValueError")
        self.assertNotIn("donor@example.com", batch.summary["errors"][0]["error"])


class GenericContactExternalIdMatchingTests(TestCase):
    """match_by=external_id: create, update, idempotency."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner2@test.com",
            password="testpass123",
            first_name="Owner",
            last_name="Two",
            role=UserRole.MISSIONARY,
        )

    def test_create_new_contact_with_external_id_and_optional_fields(self):
        csv_content = (
            "id,first_name,last_name,email,phone,city,state,postal_code,country,notes\n"
            "EXT-100,Alice,Walker,alice@example.com,555-9999,Austin,TX,73301,USA,VIP donor"
        )
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 1)
        self.assertEqual(batch.updated_count, 0)

        contact = Contact.objects.get(owner=self.user, external_id="EXT-100")
        self.assertEqual(contact.first_name, "Alice")
        self.assertEqual(contact.last_name, "Walker")
        self.assertEqual(contact.email, "alice@example.com")
        self.assertEqual(contact.phone, "555-9999")
        self.assertEqual(contact.city, "Austin")
        self.assertEqual(contact.state, "TX")
        self.assertEqual(contact.postal_code, "73301")
        self.assertEqual(contact.notes, "VIP donor")

    def test_update_existing_contact_matched_by_external_id(self):
        Contact.objects.create(
            owner=self.user,
            first_name="Bob",
            last_name="Jones",
            external_id="EXT-200",
            email="",
        )
        csv_content = "external_id,first_name,last_name,email\nEXT-200,Bob,Jones,bob@example.com"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 0)
        self.assertEqual(batch.updated_count, 1)

        contact = Contact.objects.get(owner=self.user, external_id="EXT-200")
        # merge-only filled the blank email
        self.assertEqual(contact.email, "bob@example.com")

    def test_missing_external_id_value_is_row_error(self):
        # Header present but the row's external_id cell is blank.
        csv_content = "external_id,first_name,last_name\n" "EXT-1,Carl,King\n" ",Dora,Queen"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 1)
        self.assertEqual(batch.error_count, 1)
        self.assertIn("Missing external_id", batch.summary["errors"][0]["error"])

    def test_external_id_import_is_idempotent(self):
        # Importing one file creates; re-importing a *different* file body with
        # the same external_id must update, not duplicate.
        first = "external_id,first_name,last_name\nEXT-9,Ann,Lee"
        import_generic_contacts(
            _bytes(first), "a.csv", self.user, self.user, match_by="external_id"
        )
        second = "external_id,first_name,last_name,phone\nEXT-9,Ann,Lee,555-0001"
        import_generic_contacts(
            _bytes(second), "b.csv", self.user, self.user, match_by="external_id"
        )
        # Only one contact with that external_id exists.
        self.assertEqual(
            Contact.objects.filter(owner=self.user, external_id="EXT-9").count(),
            1,
        )
        contact = Contact.objects.get(owner=self.user, external_id="EXT-9")
        self.assertEqual(contact.phone, "555-0001")


class GenericContactNameMatchingTests(TestCase):
    """match_by=name: create new + missing-name row errors."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner3@test.com",
            password="testpass123",
            first_name="Owner",
            last_name="Three",
            role=UserRole.MISSIONARY,
        )

    def test_create_new_contact_when_no_name_match(self):
        csv_content = "first_name,last_name,email\nNew,Person,new@example.com"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="name"
        )
        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 1)
        self.assertTrue(
            Contact.objects.filter(owner=self.user, first_name="New", last_name="Person").exists()
        )

    def test_missing_name_cell_with_name_matching_is_row_error(self):
        csv_content = (
            "first_name,last_name,email\n" "Valid,Name,v@example.com\n" ",,blank@example.com"
        )
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="name"
        )
        self.assertEqual(batch.created_count, 1)
        self.assertEqual(batch.error_count, 1)
        self.assertIn(
            "Missing first_name or last_name",
            batch.summary["errors"][0]["error"],
        )


class GenericContactOrgAndSkipTests(TestCase):
    """Org-only creation, and skip path when nothing to merge."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner4@test.com",
            password="testpass123",
            first_name="Owner",
            last_name="Four",
            role=UserRole.MISSIONARY,
        )

    def test_org_only_contact_creation(self):
        # No first/last but an organization column -> create org contact.
        csv_content = "organization,email,city\n" "Acme Foundation,acme@example.com,Dallas"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="email"
        )
        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 1)
        contact = Contact.objects.get(owner=self.user, organization_name="Acme Foundation")
        self.assertEqual(contact.email, "acme@example.com")
        self.assertEqual(contact.city, "Dallas")

    def test_existing_contact_with_nothing_to_merge_is_skipped(self):
        # Existing contact already fully populated; re-import same data -> skip.
        Contact.objects.create(
            owner=self.user,
            first_name="Sam",
            last_name="Fox",
            email="sam@example.com",
            phone="555-2222",
        )
        csv_content = "first_name,last_name,email,phone\nSam,Fox,sam@example.com,555-9999"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="email"
        )
        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 0)
        self.assertEqual(batch.updated_count, 0)
        self.assertEqual(batch.skipped_count, 1)
        # merge-only never overwrites a populated phone.
        contact = Contact.objects.get(
            owner=self.user, email_hash__in=lookup_hashes("sam@example.com")
        )
        self.assertEqual(contact.phone, "555-2222")

    def test_all_rows_errored_marks_batch_failed(self):
        # match_by=email but every row has a blank email -> every row errors,
        # nothing created/updated/skipped -> batch status FAILED.
        csv_content = "first_name,last_name,email\n" "Foo,Bar,\n" "Baz,Qux,"
        batch = import_generic_contacts(
            _bytes(csv_content), "c.csv", self.user, self.user, match_by="email"
        )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        self.assertEqual(batch.created_count, 0)
        self.assertEqual(batch.error_count, 2)


class GenericContactRowExceptionTests(TestCase):
    """A per-row exception is caught and collected, not fatal."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner5@test.com",
            password="testpass123",
            first_name="Owner",
            last_name="Five",
            role=UserRole.MISSIONARY,
        )

    def test_row_level_exception_collected_and_other_rows_succeed(self):
        # Force Contact.objects.create to blow up on the *second* invocation so
        # the per-row try/except (lines 435-445) records an error while the
        # first row still imports.
        original_create = Contact.objects.create
        calls = {"n": 0}

        def flaky_create(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("boom")
            return original_create(*args, **kwargs)

        csv_content = (
            "first_name,last_name,email\n"
            "Good,One,good1@example.com\n"
            "Good,Two,good2@example.com"
        )
        with patch.object(Contact.objects, "create", side_effect=flaky_create):
            batch = import_generic_contacts(
                _bytes(csv_content), "c.csv", self.user, self.user, match_by="email"
            )
        self.assertEqual(batch.created_count, 1)
        self.assertEqual(batch.error_count, 1)
        self.assertIn("RuntimeError", batch.summary["errors"][0]["error"])


class GenericDonationValidationTests(TestCase):
    """Donation header validation + amount/date row validation."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="downer@test.com",
            password="testpass123",
            first_name="Down",
            last_name="Owner",
            role=UserRole.MISSIONARY,
        )
        self.contact = Contact.objects.create(
            owner=self.user,
            first_name="John",
            last_name="Smith",
            email="john@example.com",
            external_id="DON-1",
        )

    def test_missing_amount_and_date_headers_fails(self):
        csv_content = "email\njohn@example.com"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="email"
        )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        error = batch.summary["errors"][0]["error"]
        self.assertIn("amount", error)
        self.assertIn("date", error)

    def test_missing_contact_email_header_fails(self):
        csv_content = "amount,date\n100.00,2026-01-15"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="email"
        )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        self.assertIn("contact_email", batch.summary["errors"][0]["error"])

    def test_missing_contact_name_headers_fails(self):
        csv_content = "amount,date\n100.00,2026-01-15"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="name"
        )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        error = batch.summary["errors"][0]["error"]
        self.assertIn("contact_first_name", error)
        self.assertIn("contact_last_name", error)

    def test_missing_contact_external_id_header_fails(self):
        csv_content = "amount,date\n100.00,2026-01-15"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        self.assertIn("contact_external_id", batch.summary["errors"][0]["error"])

    def test_undecodable_donation_file_returns_failed_batch(self):
        with patch(
            "apps.imports.generic_services.decode_csv_bytes",
            side_effect=ValueError("Unable to decode file"),
        ):
            batch = import_generic_donations(
                _bytes("email,amount,date\njohn@example.com,100,2026-01-15"),
                "bad.csv",
                self.user,
                self.user,
                match_by="email",
            )
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        self.assertEqual(batch.summary["errors"][0]["row"], 0)

    def test_zero_and_invalid_amounts_are_row_errors(self):
        csv_content = (
            "email,amount,date\n"
            "john@example.com,0.00,2026-01-15\n"
            "john@example.com,notmoney,2026-01-16\n"
            "john@example.com,75.50,2026-01-17"
        )
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="email"
        )
        # Only the $75.50 gift is created; the 0 and non-numeric rows error.
        self.assertEqual(batch.created_count, 1)
        self.assertEqual(batch.error_count, 2)
        gift = Gift.objects.get(donor_contact=self.contact)
        self.assertEqual(gift.amount_cents, 7550)
        joined = " ".join(e["error"] for e in batch.summary["errors"])
        self.assertIn("Invalid or zero amount", joined)

    def test_invalid_date_is_row_error(self):
        csv_content = "email,amount,date\n" "john@example.com,40.00,not-a-date"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="email"
        )
        self.assertEqual(batch.created_count, 0)
        self.assertEqual(batch.error_count, 1)
        self.assertEqual(batch.status, ImportBatchStatus.FAILED)
        self.assertIn("Invalid date", batch.summary["errors"][0]["error"])


class GenericDonationMatchingTests(TestCase):
    """Donation contact matching by name / external_id + fund matching."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="downer2@test.com",
            password="testpass123",
            first_name="Down",
            last_name="Owner2",
            role=UserRole.MISSIONARY,
        )
        self.contact = Contact.objects.create(
            owner=self.user,
            first_name="Mary",
            last_name="Major",
            email="mary@example.com",
            external_id="C-77",
        )

    def test_match_by_name_creates_gift(self):
        csv_content = (
            "contact_first_name,contact_last_name,amount,date,description\n"
            "Mary,Major,125.00,2026-03-01,Spring gift"
        )
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="name"
        )
        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 1)
        gift = Gift.objects.get(donor_contact=self.contact)
        self.assertEqual(gift.amount_cents, 12500)
        self.assertEqual(gift.description, "Spring gift")

    def test_match_by_name_no_match_is_row_error(self):
        csv_content = (
            "contact_first_name,contact_last_name,amount,date\n" "Ghost,Person,10.00,2026-03-01"
        )
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="name"
        )
        self.assertEqual(batch.created_count, 0)
        self.assertEqual(batch.error_count, 1)
        self.assertIn("No contact found", batch.summary["errors"][0]["error"])

    def test_match_by_name_missing_name_cell_is_row_error(self):
        csv_content = "contact_first_name,contact_last_name,amount,date\n" ",,10.00,2026-03-01"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="name"
        )
        self.assertEqual(batch.error_count, 1)
        self.assertIn("Missing contact name", batch.summary["errors"][0]["error"])

    def test_match_by_external_id_creates_gift(self):
        csv_content = "contact_external_id,amount,date\n" "C-77,200.00,2026-04-01"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.created_count, 1)
        gift = Gift.objects.get(donor_contact=self.contact)
        self.assertEqual(gift.amount_cents, 20000)

    def test_match_by_external_id_no_match_is_row_error(self):
        csv_content = "contact_external_id,amount,date\n" "NOPE,200.00,2026-04-01"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.created_count, 0)
        self.assertEqual(batch.error_count, 1)
        self.assertIn("No contact found", batch.summary["errors"][0]["error"])

    def test_match_by_external_id_missing_cell_is_row_error(self):
        csv_content = "contact_external_id,amount,date\n" ",200.00,2026-04-01"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.error_count, 1)
        self.assertIn("Missing external_id", batch.summary["errors"][0]["error"])

    def test_email_match_missing_cell_is_row_error(self):
        csv_content = "contact_email,amount,date\n" ",50.00,2026-04-01"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="email"
        )
        self.assertEqual(batch.error_count, 1)
        self.assertIn("Missing email", batch.summary["errors"][0]["error"])

    def test_gift_links_matched_fund(self):
        fund = Fund.objects.create(external_id="F-1", name="General Fund", status="active")
        csv_content = "contact_external_id,amount,date,fund\n" "C-77,60.00,2026-05-01,General Fund"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.created_count, 1)
        gift = Gift.objects.get(donor_contact=self.contact)
        self.assertEqual(gift.fund_id, fund.id)

    def test_unknown_fund_name_leaves_gift_without_fund(self):
        csv_content = (
            "contact_external_id,amount,date,fund\n" "C-77,60.00,2026-05-01,Nonexistent Fund"
        )
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.created_count, 1)
        gift = Gift.objects.get(donor_contact=self.contact)
        self.assertIsNone(gift.fund_id)

    def test_donation_dedup_returns_duplicate_status(self):
        csv_content = "contact_external_id,amount,date\n" "C-77,99.00,2026-06-01"
        first = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(first.status, ImportBatchStatus.COMPLETED)
        second = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(second.status, ImportBatchStatus.DUPLICATE)
        # No second gift was created on the duplicate import.
        self.assertEqual(Gift.objects.filter(donor_contact=self.contact).count(), 1)

    def test_batch_type_recorded_for_donations(self):
        csv_content = "contact_external_id,amount,date\n" "C-77,15.00,2026-06-02"
        batch = import_generic_donations(
            _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
        )
        self.assertEqual(batch.import_type, ImportBatchType.GENERIC_DONATIONS)


class GenericDonationRowExceptionTests(TestCase):
    """A per-row exception during Gift creation is caught and collected."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="downer3@test.com",
            password="testpass123",
            first_name="Down",
            last_name="Owner3",
            role=UserRole.MISSIONARY,
        )
        self.contact = Contact.objects.create(
            owner=self.user,
            first_name="Jay",
            last_name="Doe",
            external_id="GX-1",
        )

    def test_gift_create_exception_recorded_as_row_error(self):
        original_create = Gift.objects.create
        calls = {"n": 0}

        def flaky_create(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("gift boom")
            return original_create(*args, **kwargs)

        csv_content = (
            "contact_external_id,amount,date\n" "GX-1,10.00,2026-07-01\n" "GX-1,20.00,2026-07-02"
        )
        with patch.object(Gift.objects, "create", side_effect=flaky_create):
            batch = import_generic_donations(
                _bytes(csv_content), "d.csv", self.user, self.user, match_by="external_id"
            )
        self.assertEqual(batch.created_count, 1)
        self.assertEqual(batch.error_count, 1)
        self.assertIn("RuntimeError", batch.summary["errors"][0]["error"])
