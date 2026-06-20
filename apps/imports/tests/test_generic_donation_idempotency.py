"""
Per-gift idempotency for the generic donation importer (issue #116).

The generic importer historically relied only on a whole-file SHA256 to avoid
re-processing. Any re-export with a reformatted date, corrected fund, or
reordered columns produced a different hash, so every row re-created a new Gift
and double-counted ``total_given``/``gift_count``. These tests pin the fix:

- A trivial-change re-upload (different file SHA, same logical rows) creates
  no new gifts.
- An explicit per-gift ID column dedups across uploads.
- The ImportBatch sha256 unique constraint gates gift creation, so a concurrent
  identical upload that slips past the pre-check cannot double-commit gifts.
"""

import hashlib
from unittest.mock import patch

from django.test import TestCase

from apps.contacts.models import Contact
from apps.gifts.models import Gift
from apps.imports.generic_services import import_generic_donations
from apps.imports.models import ImportBatch, ImportBatchStatus, ImportBatchType
from apps.users.models import User, UserRole


class GenericDonationIdempotencyTests(TestCase):
    """Re-upload and concurrency idempotency for import_generic_donations."""

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

    def _import(self, csv_content, filename="donations.csv", match_by="email"):
        return import_generic_donations(
            csv_content.encode("utf-8"),
            filename,
            self.user,
            self.user,
            match_by=match_by,
        )

    def test_reupload_with_trivial_change_creates_no_new_gifts(self):
        """Reordered columns + reformatted date -> different SHA, same gifts.

        This is the core regression: the whole-file hash differs, but the
        per-gift identity is stable, so the second upload dedups every row.
        """
        first = self._import(
            "email,amount,date,description\n" "john@example.com,100.00,2026-01-15,Spring gift"
        )
        self.assertEqual(first.created_count, 1)
        self.assertEqual(Gift.objects.count(), 1)

        # Same logical row: columns reordered, date reformatted (MM/DD/YYYY).
        second = self._import(
            "amount,date,email,description\n" "100.00,01/15/2026,john@example.com,Spring gift",
            filename="donations_reexport.csv",
        )

        self.assertEqual(Gift.objects.count(), 1, "no new gift on trivial re-upload")
        self.assertEqual(second.created_count, 0)
        self.assertEqual(second.skipped_count, 1)
        self.assertEqual(second.status, ImportBatchStatus.COMPLETED)

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.gift_count, 1)
        self.assertEqual(self.contact.total_given, 100)

    def test_reupload_with_explicit_gift_id_dedups(self):
        """An explicit gift-id column dedups even when attributes change."""
        first = self._import(
            "gift_id,email,amount,date,fund\n" "GIFT-1,john@example.com,100.00,2026-01-15,General"
        )
        self.assertEqual(first.created_count, 1)
        self.assertEqual(Gift.objects.count(), 1)

        # Same gift_id, corrected fund + amount typo fixed: still the same gift.
        second = self._import(
            "gift_id,email,amount,date,fund\n" "GIFT-1,john@example.com,120.00,2026-01-15,Building",
            filename="corrected.csv",
        )
        self.assertEqual(Gift.objects.count(), 1)
        self.assertEqual(second.created_count, 0)
        self.assertEqual(second.skipped_count, 1)

        # Generic IDs are namespaced so they cannot collide with RE/SPO gift IDs
        # that share the same globally-unique external_gift_id column.
        gift = Gift.objects.get()
        self.assertEqual(gift.external_gift_id, "genid:GIFT-1")

    def test_explicit_gift_id_does_not_collide_with_re_gift_id(self):
        """A generic gift_id must not dedup against an RE/SPO gift sharing it.

        external_gift_id is globally unique across import sources; namespacing
        generic IDs prevents silently dropping a real donation whose CSV gift_id
        happens to equal an existing RE gift ID.
        """
        Gift.objects.create(
            donor_contact=self.contact,
            amount_cents=9999,
            gift_date="2025-01-01",
            external_gift_id="100",  # an RE-style raw gift ID
        )
        batch = self._import("gift_id,email,amount,date\n" "100,john@example.com,40.00,2026-05-01")
        self.assertEqual(batch.created_count, 1)
        self.assertTrue(Gift.objects.filter(external_gift_id="genid:100").exists())
        self.assertEqual(Gift.objects.count(), 2)

    def test_overlong_gift_id_is_hashed_within_column_budget(self):
        """A source gift ID too long for the 100-char column is hashed, not stored raw.

        Guards the Postgres-only DataError path: ``genid:`` + a long ID would
        exceed external_gift_id's max_length=100. The hashed fallback must keep
        the gift creatable and still dedup on re-upload.
        """
        long_id = "X" * 120
        first = self._import(
            f"gift_id,email,amount,date\n{long_id},john@example.com,60.00,2026-06-01"
        )
        self.assertEqual(first.created_count, 1)

        gift = Gift.objects.get()
        self.assertTrue(gift.external_gift_id.startswith("genidh:"))
        self.assertLessEqual(len(gift.external_gift_id), 100)

        # Re-upload (different file SHA via reordered columns) still dedups.
        second = self._import(
            f"email,gift_id,amount,date\njohn@example.com,{long_id},60.00,2026-06-01",
            filename="reexport.csv",
        )
        self.assertEqual(second.created_count, 0)
        self.assertEqual(second.skipped_count, 1)
        self.assertEqual(Gift.objects.count(), 1)

    def test_distinct_explicit_gift_ids_create_distinct_gifts(self):
        """Two rows sharing donor/amount/date but distinct IDs -> two gifts."""
        batch = self._import(
            "gift_id,email,amount,date\n"
            "G1,john@example.com,50.00,2026-03-01\n"
            "G2,john@example.com,50.00,2026-03-01"
        )
        self.assertEqual(batch.created_count, 2)
        self.assertEqual(Gift.objects.count(), 2)

    def test_distinct_gifts_without_ids_still_created(self):
        """No gift-id column: different amounts/dates remain distinct gifts."""
        batch = self._import(
            "email,amount,date\n"
            "john@example.com,100.00,2026-01-15\n"
            "john@example.com,50.00,2026-02-01"
        )
        self.assertEqual(batch.created_count, 2)
        self.assertEqual(Gift.objects.count(), 2)

    def test_identical_rows_in_same_file_dedup(self):
        """Two byte-identical rows collapse to one gift (idempotent identity)."""
        batch = self._import(
            "email,amount,date,description\n"
            "john@example.com,75.00,2026-04-01,Easter\n"
            "john@example.com,75.00,2026-04-01,Easter"
        )
        self.assertEqual(batch.created_count, 1)
        self.assertEqual(batch.skipped_count, 1)
        self.assertEqual(Gift.objects.count(), 1)

    @patch("apps.imports.generic_services.check_duplicate_import", return_value=None)
    def test_concurrent_identical_upload_does_not_double_commit(self, _mock_dup):
        """The batch sha256 unique constraint gates gift creation.

        Simulate the race where the pre-check sees nothing but a prior identical
        upload already committed its ImportBatch. The importer must hit the
        constraint, create zero gifts, and report the existing batch.
        """
        csv_content = "email,amount,date\n" "john@example.com,100.00,2026-01-15"
        file_bytes = csv_content.encode("utf-8")
        sha = hashlib.sha256(file_bytes).hexdigest()

        # The "winner" of the race: an already-committed batch for this file.
        winner = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_DONATIONS,
            status=ImportBatchStatus.COMPLETED,
            filename="donations.csv",
            sha256_hash=sha,
            uploaded_by=self.user,
        )

        before = Gift.objects.count()
        result = import_generic_donations(
            file_bytes, "donations.csv", self.user, self.user, match_by="email"
        )

        self.assertEqual(Gift.objects.count(), before, "loser created no gifts")
        self.assertEqual(result.id, winner.id)
        self.assertEqual(result.status, ImportBatchStatus.DUPLICATE)
