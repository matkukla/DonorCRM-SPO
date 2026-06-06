"""
End-to-end fixture mapping tests for all 4 SPO CSV files.

Unlike test_spo_services.py (which uses synthetic in-memory CSV helpers),
these tests read the actual test_data/ fixture files from disk. This exercises
real header aliases, column layouts, and data formats.

Fixture files:
  test_data/test_solicitors.csv      — type-label "Solicitor", 20 missionaries
  test_data/test_gifts.csv           — type-label "Gift", "Fund Split Amount" alias, 100 rows
  test_data/test_recurring_gifts.csv — type-label "Recurring Gift", 300 rows
  test_data/test_constituents.csv    — type-label "Constituent", 400 rows
"""

import os

from django.test import TestCase

import pytest

from apps.imports.models import ImportBatchStatus
from apps.users.models import User

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "test_data")

# These tests read real CSVs from the gitignored, local-only test_data/
# directory (sizable realistic donor data that must not be committed). Skip the
# whole module when those fixtures are absent (e.g. CI) instead of hard-failing
# with FileNotFoundError. test_spo_services.py covers the same logic with
# synthetic in-memory CSVs and runs everywhere.
pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(FIXTURE_DIR, "test_solicitors.csv")),
    reason="SPO CSV fixtures live in gitignored test_data/ (local-only, absent in CI)",
)


def _fixture_bytes(filename):
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, "rb") as f:
        return f.read()


def _make_admin():
    return User.objects.create_user(
        email="admin@example.com",
        password="adminpass",
        first_name="Admin",
        last_name="User",
        role="admin",
    )


def _make_staff_owner():
    return User.objects.create_user(
        email="owner@example.com",
        password="ownerpass",
        first_name="Owner",
        last_name="Staff",
        role="missionary",
    )


# ---------------------------------------------------------------------------
# Class 1: Solicitors
# ---------------------------------------------------------------------------


class TestSolicitorsFixtureMapping(TestCase):
    """Tests for test_solicitors.csv → reconcile_missionaries()."""

    def test_reconcile_missionaries_with_fixture(self):
        """test_solicitors.csv maps all 20 missionaries without failure."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        file_bytes = _fixture_bytes("test_solicitors.csv")

        batch = reconcile_missionaries(file_bytes, "test_solicitors.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 20)
        self.assertEqual(batch.summary["missionaries_expected"], 20)
        self.assertEqual(batch.summary["created"], 20)
        self.assertEqual(batch.summary["unresolved"], 0)
        self.assertEqual(User.objects.filter(role="missionary").count(), 20)

    def test_reconcile_creates_solicitor_records(self):
        """reconcile_missionaries() creates one Solicitor per missionary."""
        from apps.gifts.models import Solicitor
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        file_bytes = _fixture_bytes("test_solicitors.csv")

        reconcile_missionaries(file_bytes, "test_solicitors.csv", admin)

        self.assertEqual(Solicitor.objects.count(), 20)


# ---------------------------------------------------------------------------
# Class 2: Gifts
# ---------------------------------------------------------------------------


class TestGiftsFixtureMapping(TestCase):
    """Tests for test_gifts.csv → import_spo_gifts()."""

    def setUp(self):
        """Create admin, reconcile missionaries, and import constituents so gift import
        can resolve all contact lookups and solicitor credit records."""
        from apps.imports.re_services import import_re_constituents
        from apps.imports.spo_services import reconcile_missionaries

        self.admin = _make_admin()
        self.owner = _make_staff_owner()
        solicitors_bytes = _fixture_bytes("test_solicitors.csv")
        reconcile_missionaries(solicitors_bytes, "test_solicitors.csv", self.admin)
        # Import constituents so gift contact lookups succeed (all gifts reference
        # constituent IDs that exist in test_constituents.csv)
        constituents_bytes = _fixture_bytes("test_constituents.csv")
        import_re_constituents(constituents_bytes, "test_constituents.csv", self.admin, self.owner)

    def test_import_spo_gifts_with_fixture(self):
        """test_gifts.csv imports all 100 rows without parse errors."""
        from apps.imports.spo_services import import_spo_gifts

        file_bytes = _fixture_bytes("test_gifts.csv")
        batch = import_spo_gifts(file_bytes, "test_gifts.csv", self.admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.error_count, 0)
        self.assertEqual(batch.created_count, 100)

    def test_gifts_fund_split_amount_header_resolves(self):
        """'Fund Split Amount' header alias resolves as gift_amount without errors."""
        from apps.gifts.models import Gift
        from apps.imports.spo_services import import_spo_gifts

        file_bytes = _fixture_bytes("test_gifts.csv")
        batch = import_spo_gifts(file_bytes, "test_gifts.csv", self.admin)

        # No row failures due to amount parse errors
        self.assertEqual(batch.summary["error_details"], [])
        # At least 1 gift created (anonymous or blank-constituent rows)
        self.assertGreater(Gift.objects.count(), 0)
        # Amounts parsed from Fund Split Amount column — not left as 0
        self.assertTrue(Gift.objects.filter(amount_cents__gt=0).exists())

    def test_gifts_all_rows_imported_via_named_contacts(self):
        """All test gifts reference named constituents — all 100 rows create gifts.

        test_gifts.csv contains no anonymous rows (Gift Is Anonymous = No for all rows).
        All 100 constituent IDs resolve to contacts imported from test_constituents.csv.
        """
        from apps.gifts.models import Gift
        from apps.imports.spo_services import import_spo_gifts

        file_bytes = _fixture_bytes("test_gifts.csv")
        batch = import_spo_gifts(file_bytes, "test_gifts.csv", self.admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.error_count, 0)
        self.assertEqual(batch.created_count, 100)
        self.assertEqual(Gift.objects.count(), 100)


# ---------------------------------------------------------------------------
# Class 3: Recurring Gifts
# ---------------------------------------------------------------------------


class TestRecurringGiftsFixtureMapping(TestCase):
    """Tests for test_recurring_gifts.csv → import_re_recurring_gifts()."""

    def setUp(self):
        """Create admin and staff owner; import constituents and missionaries so both
        contact lookups and solicitor credit lookups succeed."""
        from apps.imports.re_services import import_re_constituents
        from apps.imports.spo_services import reconcile_missionaries

        self.admin = _make_admin()
        self.owner = _make_staff_owner()
        # Reconcile missionaries so Solicitor records exist for gift credit creation
        solicitors_bytes = _fixture_bytes("test_solicitors.csv")
        reconcile_missionaries(solicitors_bytes, "test_solicitors.csv", self.admin)
        # Import constituents so recurring gift contact lookups succeed
        constituents_bytes = _fixture_bytes("test_constituents.csv")
        import_re_constituents(constituents_bytes, "test_constituents.csv", self.admin, self.owner)

    def test_import_recurring_gifts_with_fixture(self):
        """test_recurring_gifts.csv imports without errors after contacts exist."""
        from apps.imports.re_services import import_re_recurring_gifts

        file_bytes = _fixture_bytes("test_recurring_gifts.csv")
        batch = import_re_recurring_gifts(
            file_bytes,
            "test_recurring_gifts.csv",
            self.admin,
            self.owner,
        )

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.error_count, 0)
        self.assertEqual(batch.total_rows, 300)

    def test_recurring_gifts_type_label_row_skipped(self):
        """Type-label 'Recurring Gift' row is skipped; data row count is 300, not 301."""
        from apps.imports.re_services import import_re_recurring_gifts

        file_bytes = _fixture_bytes("test_recurring_gifts.csv")
        batch = import_re_recurring_gifts(
            file_bytes,
            "test_recurring_gifts.csv",
            self.admin,
            self.owner,
        )

        # 300 data rows (type-label row stripped, header row not counted)
        self.assertEqual(batch.total_rows, 300)


# ---------------------------------------------------------------------------
# Class 4: Constituents
# ---------------------------------------------------------------------------


class TestConstituentsFixtureMapping(TestCase):
    """Tests for test_constituents.csv → import_re_constituents()."""

    def setUp(self):
        self.admin = _make_admin()
        self.owner = _make_staff_owner()

    def test_import_constituents_with_fixture(self):
        """test_constituents.csv imports without errors; contacts created."""
        from apps.imports.re_services import import_re_constituents

        file_bytes = _fixture_bytes("test_constituents.csv")
        batch = import_re_constituents(
            file_bytes,
            "test_constituents.csv",
            self.admin,
            self.owner,
        )

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.error_count, 0)
        self.assertGreater(batch.created_count, 0)

    def test_constituents_type_label_row_skipped(self):
        """Type-label 'Constituent' row is skipped; data rows >= 100."""
        from apps.imports.re_services import import_re_constituents

        file_bytes = _fixture_bytes("test_constituents.csv")
        batch = import_re_constituents(
            file_bytes,
            "test_constituents.csv",
            self.admin,
            self.owner,
        )

        self.assertGreaterEqual(batch.total_rows, 100)
