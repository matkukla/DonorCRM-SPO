"""
Tests for Fund CSV import functionality.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.imports.models import Fund, ImportRun, ImportType, ImportStatus
from apps.imports.services import parse_funds_csv, import_funds

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def import_run(test_user):
    """Create a test ImportRun."""
    return ImportRun.objects.create(
        type=ImportType.FUNDS,
        status=ImportStatus.PENDING,
        filename='test_funds.csv',
        uploaded_by=test_user
    )


class TestParseFundsCSV:
    """Tests for parse_funds_csv function."""

    def test_valid_csv_returns_records(self):
        """Valid CSV should return parsed records."""
        csv_content = """fund_id,name,status
FUND001,General Ministry,active
FUND002,Special Projects,inactive"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 2
        assert len(errors) == 0
        assert records[0]['fund_id'] == 'FUND001'
        assert records[0]['name'] == 'General Ministry'
        assert records[0]['status'] == 'active'
        assert records[1]['fund_id'] == 'FUND002'
        assert records[1]['name'] == 'Special Projects'
        assert records[1]['status'] == 'inactive'

    def test_missing_fund_id_returns_error(self):
        """Missing fund_id should return error."""
        csv_content = """fund_id,name,status
,General Ministry,active"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'fund_id is required' in errors[0]['errors'][0]

    def test_missing_name_returns_error(self):
        """Missing name should return error."""
        csv_content = """fund_id,name,status
FUND001,,active"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'name is required' in errors[0]['errors'][0]

    def test_missing_status_defaults_to_active(self):
        """Missing status should default to 'active'."""
        csv_content = """fund_id,name,status
FUND001,General Ministry,"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 1
        assert len(errors) == 0
        assert records[0]['status'] == 'active'

    def test_invalid_status_returns_error(self):
        """Invalid status should return error."""
        csv_content = """fund_id,name,status
FUND001,General Ministry,invalid_status"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'Invalid status' in errors[0]['errors'][0]

    def test_status_is_case_insensitive(self):
        """Status validation should be case-insensitive."""
        csv_content = """fund_id,name,status
FUND001,General Ministry,ACTIVE
FUND002,Special Projects,Inactive
FUND003,Old Fund,CLOSED"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 3
        assert len(errors) == 0
        assert records[0]['status'] == 'active'
        assert records[1]['status'] == 'inactive'
        assert records[2]['status'] == 'closed'

    def test_duplicate_fund_id_in_file_returns_error(self):
        """Duplicate fund_id in same file should return error."""
        csv_content = """fund_id,name,status
FUND001,General Ministry,active
FUND001,Duplicate Fund,active"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 1  # First one is valid
        assert len(errors) == 1  # Second one errors
        assert errors[0]['row'] == 3
        assert 'Duplicate fund_id' in errors[0]['errors'][0]

    def test_fund_id_exceeds_max_length_returns_error(self):
        """fund_id exceeding 100 characters should return error."""
        long_fund_id = 'F' * 101
        csv_content = f"""fund_id,name,status
{long_fund_id},General Ministry,active"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'fund_id exceeds maximum length' in errors[0]['errors'][0]

    def test_name_exceeds_max_length_returns_error(self):
        """name exceeding 255 characters should return error."""
        long_name = 'N' * 256
        csv_content = f"""fund_id,name,status
FUND001,{long_name},active"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'name exceeds maximum length' in errors[0]['errors'][0]

    def test_missing_required_column_header_returns_error(self):
        """Missing required column header should return error."""
        csv_content = """fund_id,status
FUND001,active"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 0
        assert len(errors) == 1
        assert 'Missing required column' in errors[0]['errors'][0]
        assert 'name' in errors[0]['errors'][0]

    def test_empty_csv_returns_empty_lists(self):
        """Empty CSV should return empty lists."""
        csv_content = """fund_id,name,status"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 0
        assert len(errors) == 0

    def test_whitespace_is_trimmed(self):
        """Whitespace in values should be trimmed."""
        csv_content = """fund_id,name,status
  FUND001  ,  General Ministry  ,  active  """

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 1
        assert len(errors) == 0
        assert records[0]['fund_id'] == 'FUND001'
        assert records[0]['name'] == 'General Ministry'
        assert records[0]['status'] == 'active'

    def test_fund_id_starting_with_formula_characters_rejected(self):
        """fund_id starting with formula characters should be rejected."""
        csv_content = """fund_id,name,status
=FUND001,General Ministry,active
+FUND002,Special Projects,active
-FUND003,Old Fund,active
@FUND004,Another Fund,active"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 0
        assert len(errors) == 4
        for error in errors:
            assert 'formula character' in error['errors'][0].lower()

    def test_name_starting_with_formula_characters_rejected(self):
        """name starting with formula characters should be rejected."""
        csv_content = """fund_id,name,status
FUND001,=Dangerous Name,active
FUND002,+Another Bad,active
FUND003,-Bad Name,active
FUND004,@Also Bad,active"""

        records, errors = parse_funds_csv(csv_content)

        assert len(records) == 0
        assert len(errors) == 4
        for error in errors:
            assert 'formula character' in error['errors'][0].lower()


class TestImportFunds:
    """Tests for import_funds function."""

    def test_creates_new_funds(self, import_run):
        """Should create new funds from records."""
        records = [
            {'fund_id': 'FUND001', 'name': 'General Ministry', 'status': 'active'},
            {'fund_id': 'FUND002', 'name': 'Special Projects', 'status': 'inactive'},
        ]

        created, updated = import_funds(records, import_run)

        assert created == 2
        assert updated == 0
        assert Fund.objects.count() == 2

        fund1 = Fund.objects.get(external_id='FUND001')
        assert fund1.name == 'General Ministry'
        assert fund1.status == 'active'
        assert fund1.owner is None

        # Check ImportRun was updated
        import_run.refresh_from_db()
        assert import_run.created_count == 2
        assert import_run.updated_count == 0
        assert import_run.status == ImportStatus.COMPLETED

    def test_updates_existing_funds_matching_external_id(self, import_run):
        """Should update existing funds based on external_id."""
        # Create existing fund
        Fund.objects.create(
            external_id='FUND001',
            name='Old Name',
            status='inactive'
        )

        records = [
            {'fund_id': 'FUND001', 'name': 'Updated Name', 'status': 'active'},
        ]

        created, updated = import_funds(records, import_run)

        assert created == 0
        assert updated == 1
        assert Fund.objects.count() == 1

        fund = Fund.objects.get(external_id='FUND001')
        assert fund.name == 'Updated Name'
        assert fund.status == 'active'

        # Check ImportRun was updated
        import_run.refresh_from_db()
        assert import_run.created_count == 0
        assert import_run.updated_count == 1
        assert import_run.status == ImportStatus.COMPLETED

    def test_mixed_create_update_works_correctly(self, import_run):
        """Should handle mix of creates and updates correctly."""
        # Create existing fund
        Fund.objects.create(
            external_id='FUND001',
            name='Old Name',
            status='inactive'
        )

        records = [
            {'fund_id': 'FUND001', 'name': 'Updated Name', 'status': 'active'},
            {'fund_id': 'FUND002', 'name': 'New Fund', 'status': 'active'},
        ]

        created, updated = import_funds(records, import_run)

        assert created == 1
        assert updated == 1
        assert Fund.objects.count() == 2

        # Check ImportRun was updated
        import_run.refresh_from_db()
        assert import_run.created_count == 1
        assert import_run.updated_count == 1
        assert import_run.status == ImportStatus.COMPLETED

    def test_updates_import_run_counts(self, import_run):
        """Should update ImportRun counts accurately."""
        records = [
            {'fund_id': 'FUND001', 'name': 'General Ministry', 'status': 'active'},
        ]

        created, updated = import_funds(records, import_run)

        import_run.refresh_from_db()
        assert import_run.created_count == 1
        assert import_run.updated_count == 0
        assert import_run.status == ImportStatus.COMPLETED

    def test_empty_records_completes_with_zero_counts(self, import_run):
        """Should handle empty records gracefully."""
        records = []

        created, updated = import_funds(records, import_run)

        assert created == 0
        assert updated == 0

        import_run.refresh_from_db()
        assert import_run.created_count == 0
        assert import_run.updated_count == 0
        assert import_run.status == ImportStatus.COMPLETED

    def test_fund_owner_is_null(self, import_run):
        """Funds should be created with null owner (org-wide)."""
        records = [
            {'fund_id': 'FUND001', 'name': 'General Ministry', 'status': 'active'},
        ]

        created, updated = import_funds(records, import_run)

        fund = Fund.objects.get(external_id='FUND001')
        assert fund.owner is None
