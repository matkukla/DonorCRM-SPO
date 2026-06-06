"""
Tests for generic CSV import (contacts and donations).

Covers:
- Contact import: create, update by email/name, SHA256 dedup, row errors
- Donation import: Gift creation, missing contact errors, stat recalculation
- API views: endpoints, response shape, staff access, coach denied
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.gifts.models import Gift
from apps.imports.generic_services import import_generic_contacts, import_generic_donations
from apps.imports.models import ImportBatchStatus
from apps.users.models import User, UserRole


class GenericContactImportTests(TestCase):
    """Tests for import_generic_contacts service function."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="staff@test.com",
            password="testpass123",
            first_name="Staff",
            last_name="User",
            role=UserRole.MISSIONARY,
        )

    def test_generic_contact_import_creates_new_contacts(self):
        """CSV with 2 new contacts, match_by=email -> 2 created."""
        csv_content = (
            "first_name,last_name,email,phone\n"
            "John,Smith,john@example.com,555-1234\n"
            "Jane,Doe,jane@example.com,555-5678"
        )
        file_bytes = csv_content.encode("utf-8")

        batch = import_generic_contacts(
            file_bytes,
            "contacts.csv",
            self.user,
            self.user,
            match_by="email",
        )

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 2)
        self.assertEqual(batch.updated_count, 0)
        self.assertEqual(batch.error_count, 0)
        self.assertEqual(batch.total_rows, 2)

        # Verify contacts exist. email is encrypted at rest; equality
        # lookups go via the email_hash blind index.
        from apps.core.blind_index import lookup_hashes

        self.assertTrue(
            Contact.objects.filter(
                owner=self.user,
                email_hash__in=lookup_hashes("john@example.com"),
            ).exists()
        )
        self.assertTrue(
            Contact.objects.filter(
                owner=self.user,
                email_hash__in=lookup_hashes("jane@example.com"),
            ).exists()
        )

    def test_generic_contact_import_updates_existing_by_email(self):
        """CSV with contact matching existing email -> merge fields, 1 updated."""
        # Create existing contact with email but no phone
        Contact.objects.create(
            owner=self.user,
            first_name="John",
            last_name="Smith",
            email="john@example.com",
        )

        csv_content = "first_name,last_name,email,phone\n" "John,Smith,john@example.com,555-1234"
        file_bytes = csv_content.encode("utf-8")

        batch = import_generic_contacts(
            file_bytes,
            "contacts.csv",
            self.user,
            self.user,
            match_by="email",
        )

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 0)
        self.assertEqual(batch.updated_count, 1)

        # Verify phone was merged. email is encrypted; look up via blind index.
        from apps.core.blind_index import lookup_hashes

        contact = Contact.objects.get(
            owner=self.user,
            email_hash__in=lookup_hashes("john@example.com"),
        )
        self.assertEqual(contact.phone, "555-1234")

    def test_generic_contact_import_match_by_name(self):
        """CSV with name matching, existing contact found -> updated."""
        Contact.objects.create(
            owner=self.user,
            first_name="John",
            last_name="Smith",
            email="",
        )

        csv_content = "first_name,last_name,email\n" "John,Smith,john@example.com"
        file_bytes = csv_content.encode("utf-8")

        batch = import_generic_contacts(
            file_bytes,
            "contacts.csv",
            self.user,
            self.user,
            match_by="name",
        )

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.updated_count, 1)
        self.assertEqual(batch.created_count, 0)

        # Verify email was merged
        contact = Contact.objects.get(
            owner=self.user,
            first_name="John",
            last_name="Smith",
        )
        self.assertEqual(contact.email, "john@example.com")

    def test_generic_contact_import_duplicate_name_skips(self):
        """Two contacts with same name exist, match_by=name -> row error."""
        Contact.objects.create(
            owner=self.user,
            first_name="John",
            last_name="Smith",
            email="john1@example.com",
        )
        Contact.objects.create(
            owner=self.user,
            first_name="John",
            last_name="Smith",
            email="john2@example.com",
        )

        csv_content = "first_name,last_name,phone\n" "John,Smith,555-0000"
        file_bytes = csv_content.encode("utf-8")

        batch = import_generic_contacts(
            file_bytes,
            "contacts.csv",
            self.user,
            self.user,
            match_by="name",
        )

        self.assertEqual(batch.error_count, 1)
        self.assertIn(
            "Multiple contacts match",
            batch.summary["errors"][0]["error"],
        )

    def test_generic_contact_import_sha256_dedup(self):
        """Upload same file twice -> second returns is_duplicate=True."""
        csv_content = "first_name,last_name,email\n" "John,Smith,john@example.com"
        file_bytes = csv_content.encode("utf-8")

        batch1 = import_generic_contacts(
            file_bytes,
            "contacts.csv",
            self.user,
            self.user,
            match_by="email",
        )
        self.assertEqual(batch1.status, ImportBatchStatus.COMPLETED)

        batch2 = import_generic_contacts(
            file_bytes,
            "contacts.csv",
            self.user,
            self.user,
            match_by="email",
        )
        self.assertEqual(batch2.status, ImportBatchStatus.DUPLICATE)

    def test_generic_contact_import_row_errors_collected(self):
        """CSV with invalid rows (missing name and org) -> errors collected."""
        csv_content = (
            "first_name,last_name,email\n"
            "John,Smith,john@example.com\n"
            ",,missing@example.com\n"
            "Jane,Doe,jane@example.com"
        )
        file_bytes = csv_content.encode("utf-8")

        batch = import_generic_contacts(
            file_bytes,
            "contacts.csv",
            self.user,
            self.user,
            match_by="email",
        )

        # 2 valid + 1 error
        self.assertEqual(batch.created_count, 2)
        self.assertEqual(batch.error_count, 1)
        self.assertIn("Missing name or organization", batch.summary["errors"][0]["error"])


class GenericDonationImportTests(TestCase):
    """Tests for import_generic_donations service function."""

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

    def test_generic_donation_import_creates_gifts(self):
        """CSV with valid donations matching existing contacts -> gifts created."""
        csv_content = (
            "email,amount,date,description\n"
            "john@example.com,100.00,2026-01-15,Test donation\n"
            "john@example.com,50.00,2026-02-01,Second donation"
        )
        file_bytes = csv_content.encode("utf-8")

        batch = import_generic_donations(
            file_bytes,
            "donations.csv",
            self.user,
            self.user,
            match_by="email",
        )

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 2)
        self.assertEqual(batch.error_count, 0)

        # Verify Gift records
        gifts = Gift.objects.filter(donor_contact=self.contact)
        self.assertEqual(gifts.count(), 2)
        self.assertEqual(
            gifts.order_by("gift_date").first().amount_cents,
            10000,
        )

    def test_generic_donation_import_missing_contact_errors(self):
        """CSV with unknown contact -> row error 'No contact found'."""
        csv_content = "email,amount,date\n" "unknown@example.com,100.00,2026-01-15"
        file_bytes = csv_content.encode("utf-8")

        batch = import_generic_donations(
            file_bytes,
            "donations.csv",
            self.user,
            self.user,
            match_by="email",
        )

        self.assertEqual(batch.error_count, 1)
        self.assertIn(
            "No contact found",
            batch.summary["errors"][0]["error"],
        )

    def test_generic_donation_import_stat_recalculation(self):
        """After import, contact stats are updated via Gift post_save signal."""
        csv_content = (
            "email,amount,date\n"
            "john@example.com,100.00,2026-01-15\n"
            "john@example.com,50.00,2026-02-01"
        )
        file_bytes = csv_content.encode("utf-8")

        import_generic_donations(
            file_bytes,
            "donations.csv",
            self.user,
            self.user,
            match_by="email",
        )

        # Refresh contact from DB to get updated stats
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.gift_count, 2)
        self.assertEqual(self.contact.total_given, 150)


class GenericImportAPITests(TestCase):
    """Tests for GenericContactImportView and GenericDonationImportView."""

    def setUp(self):
        self.staff_user = User.objects.create_user(
            email="staff@test.com",
            password="testpass123",
            first_name="Staff",
            last_name="User",
            role=UserRole.MISSIONARY,
        )
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
        )
        self.coach_user = User.objects.create_user(
            email="coach@test.com",
            password="testpass123",
            first_name="Coach",
            last_name="User",
            role=UserRole.COACH,
        )
        self.client = APIClient()

    def test_generic_contact_import_api_endpoint(self):
        """POST to /imports/generic/contacts/ with file and match_by=email -> 200."""
        self.client.force_authenticate(user=self.staff_user)

        csv_content = (
            "first_name,last_name,email,phone\n"
            "John,Smith,john@example.com,555-1234\n"
            "Jane,Doe,jane@example.com,555-5678"
        )
        csv_file = SimpleUploadedFile(
            "contacts.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/v1/imports/generic/contacts/",
            {"file": csv_file, "match_by": "email"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Verify response shape matches RE import views
        self.assertIn("batch_id", data)
        self.assertIn("status", data)
        self.assertIn("is_duplicate", data)
        self.assertIn("created_count", data)
        self.assertIn("updated_count", data)
        self.assertIn("skipped_count", data)
        self.assertIn("error_count", data)
        self.assertIn("total_rows", data)
        self.assertIn("summary", data)

        self.assertEqual(data["created_count"], 2)
        self.assertFalse(data["is_duplicate"])

    def test_generic_donation_import_api_endpoint(self):
        """POST to /imports/generic/donations/ with file -> 200."""
        self.client.force_authenticate(user=self.staff_user)

        # Create contact first
        Contact.objects.create(
            owner=self.staff_user,
            first_name="John",
            last_name="Smith",
            email="john@example.com",
        )

        csv_content = (
            "email,amount,date,description\n" "john@example.com,100.00,2026-01-15,Test donation"
        )
        csv_file = SimpleUploadedFile(
            "donations.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/v1/imports/generic/donations/",
            {"file": csv_file, "match_by": "email"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["created_count"], 1)

    def test_generic_import_staff_access(self):
        """Staff user (not admin) can access generic import endpoints -> 200."""
        self.client.force_authenticate(user=self.staff_user)

        csv_content = "first_name,last_name,email\n" "John,Smith,john@example.com"
        csv_file = SimpleUploadedFile(
            "contacts.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/v1/imports/generic/contacts/",
            {"file": csv_file, "match_by": "email"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generic_import_coach_denied(self):
        """Coach user cannot access generic import endpoints -> 403."""
        self.client.force_authenticate(user=self.coach_user)

        csv_content = "first_name,last_name,email\n" "John,Smith,john@example.com"
        csv_file = SimpleUploadedFile(
            "contacts.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/v1/imports/generic/contacts/",
            {"file": csv_file, "match_by": "email"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
