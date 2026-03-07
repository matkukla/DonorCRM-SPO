"""
End-to-end fixture mapping tests for all 4 SPO CSV files.

Unlike test_spo_services.py (which uses synthetic in-memory CSV helpers),
these tests read the actual test_data/ fixture files from disk. This exercises
real header aliases, column layouts, and data formats.

Fixture files:
  test_data/test_solicitors.csv      — type-label "Solicitor", 25 missionaries
  test_data/test_gifts.csv           — type-label "Gift", "Fund Split Amount" alias
  test_data/test_recurring_gifts.csv — type-label "Recurring Gift", 100 rows
  test_data/test_constituents.csv    — type-label "Constituent", 100+ rows
"""
import os

from django.test import TestCase

from apps.imports.models import ImportBatch, ImportBatchStatus
from apps.users.models import User

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_data')


def _fixture_bytes(filename):
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, 'rb') as f:
        return f.read()


def _make_admin():
    return User.objects.create_user(
        email='admin@example.com', password='adminpass',
        first_name='Admin', last_name='User', role='admin',
    )


def _make_staff_owner():
    return User.objects.create_user(
        email='owner@example.com', password='ownerpass',
        first_name='Owner', last_name='Staff', role='staff',
    )


# ---------------------------------------------------------------------------
# Class 1: Solicitors
# ---------------------------------------------------------------------------

class TestSolicitorsFixtureMapping(TestCase):
    """Tests for test_solicitors.csv → reconcile_missionaries()."""

    def test_reconcile_missionaries_with_fixture(self):
        """test_solicitors.csv maps all 25 missionaries without failure."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        file_bytes = _fixture_bytes('test_solicitors.csv')

        batch = reconcile_missionaries(file_bytes, 'test_solicitors.csv', admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 25)
        self.assertEqual(batch.summary['missionaries_expected'], 25)
        self.assertEqual(batch.summary['created'], 25)
        self.assertEqual(batch.summary['unresolved'], 0)
        self.assertEqual(User.objects.filter(role='missionary').count(), 25)

    def test_reconcile_creates_solicitor_records(self):
        """reconcile_missionaries() creates one Solicitor per missionary."""
        from apps.gifts.models import Solicitor
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        file_bytes = _fixture_bytes('test_solicitors.csv')

        reconcile_missionaries(file_bytes, 'test_solicitors.csv', admin)

        self.assertEqual(Solicitor.objects.count(), 25)


# ---------------------------------------------------------------------------
# Class 2: Gifts
# ---------------------------------------------------------------------------

class TestGiftsFixtureMapping(TestCase):
    """Tests for test_gifts.csv → import_spo_gifts()."""

    def setUp(self):
        """Create admin and reconcile missionaries so gift import has solicitor records."""
        from apps.imports.spo_services import reconcile_missionaries

        self.admin = _make_admin()
        solicitors_bytes = _fixture_bytes('test_solicitors.csv')
        reconcile_missionaries(solicitors_bytes, 'test_solicitors.csv', self.admin)

    def test_import_spo_gifts_with_fixture(self):
        """test_gifts.csv imports without parse errors; anonymous/blank gifts created."""
        from apps.imports.spo_services import import_spo_gifts

        file_bytes = _fixture_bytes('test_gifts.csv')
        batch = import_spo_gifts(file_bytes, 'test_gifts.csv', self.admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.error_count, 0)
        self.assertGreater(batch.created_count, 0)

    def test_gifts_fund_split_amount_header_resolves(self):
        """'Fund Split Amount' header alias resolves as gift_amount without errors."""
        from apps.gifts.models import Gift
        from apps.imports.spo_services import import_spo_gifts

        file_bytes = _fixture_bytes('test_gifts.csv')
        batch = import_spo_gifts(file_bytes, 'test_gifts.csv', self.admin)

        # No row failures due to amount parse errors
        self.assertEqual(batch.summary['error_details'], [])
        # At least 1 gift created (anonymous or blank-constituent rows)
        self.assertGreater(Gift.objects.count(), 0)
        # Amounts parsed from Fund Split Amount column — not left as 0
        self.assertTrue(Gift.objects.filter(amount_cents__gt=0).exists())

    def test_gifts_anonymous_rows_imported(self):
        """Rows with Gift Is Anonymous = 'Yes' create gifts via anonymous contact."""
        from apps.contacts.models import Contact
        from apps.imports.spo_services import import_spo_gifts

        file_bytes = _fixture_bytes('test_gifts.csv')
        import_spo_gifts(file_bytes, 'test_gifts.csv', self.admin)

        self.assertTrue(
            Contact.objects.filter(first_name='Anonymous', last_name='Donor').exists()
        )


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
        solicitors_bytes = _fixture_bytes('test_solicitors.csv')
        reconcile_missionaries(solicitors_bytes, 'test_solicitors.csv', self.admin)
        # Import constituents so recurring gift contact lookups succeed
        constituents_bytes = _fixture_bytes('test_constituents.csv')
        import_re_constituents(constituents_bytes, 'test_constituents.csv', self.admin, self.owner)

    def test_import_recurring_gifts_with_fixture(self):
        """test_recurring_gifts.csv imports without errors after contacts exist."""
        from apps.imports.re_services import import_re_recurring_gifts

        file_bytes = _fixture_bytes('test_recurring_gifts.csv')
        batch = import_re_recurring_gifts(
            file_bytes, 'test_recurring_gifts.csv', self.admin, self.owner,
        )

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.error_count, 0)
        self.assertEqual(batch.total_rows, 100)

    def test_recurring_gifts_type_label_row_skipped(self):
        """Type-label 'Recurring Gift' row is skipped; data row count is 100, not 101."""
        from apps.imports.re_services import import_re_recurring_gifts

        file_bytes = _fixture_bytes('test_recurring_gifts.csv')
        batch = import_re_recurring_gifts(
            file_bytes, 'test_recurring_gifts.csv', self.admin, self.owner,
        )

        # 100 data rows (type-label row stripped, header row not counted)
        self.assertEqual(batch.total_rows, 100)


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

        file_bytes = _fixture_bytes('test_constituents.csv')
        batch = import_re_constituents(
            file_bytes, 'test_constituents.csv', self.admin, self.owner,
        )

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.error_count, 0)
        self.assertGreater(batch.created_count, 0)

    def test_constituents_type_label_row_skipped(self):
        """Type-label 'Constituent' row is skipped; data rows >= 100."""
        from apps.imports.re_services import import_re_constituents

        file_bytes = _fixture_bytes('test_constituents.csv')
        batch = import_re_constituents(
            file_bytes, 'test_constituents.csv', self.admin, self.owner,
        )

        self.assertGreaterEqual(batch.total_rows, 100)
