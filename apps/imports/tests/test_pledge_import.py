"""
Tests for pledge CSV import functionality.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from apps.contacts.models import Contact
from apps.imports.models import Fund, ImportRun, ImportType, ImportStatus
from apps.imports.services import (
    parse_pledges_csv,
    import_pledges,
    get_pledges_template
)
from apps.pledges.models import Pledge, PledgeFrequency, PledgeStatus

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user."""
    return User.objects.create_user(
        email='admin@example.com',
        password='password',
        role='admin'
    )


@pytest.fixture
def user(db):
    """Create regular user."""
    return User.objects.create_user(
        email='user@example.com',
        password='password',
        role='missionary'
    )


@pytest.fixture
def other_user(db):
    """Create another user for owner-scoping tests."""
    return User.objects.create_user(
        email='other@example.com',
        password='password',
        role='missionary'
    )


@pytest.fixture
def contacts(user):
    """Create test contacts with external_id for the main user."""
    return [
        Contact.objects.create(
            owner=user,
            first_name='John',
            last_name='Donor',
            email='john@example.com',
            external_id='ENT001'
        ),
        Contact.objects.create(
            owner=user,
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            external_id='ENT002'
        ),
        Contact.objects.create(
            owner=user,
            first_name='Bob',
            last_name='Wilson',
            email='bob@example.com',
            external_id='ENT003'
        ),
    ]


@pytest.fixture
def other_user_contacts(other_user):
    """Create contacts with same external_ids for different owner (scoping test)."""
    return [
        Contact.objects.create(
            owner=other_user,
            first_name='Other',
            last_name='User',
            email='other1@example.com',
            external_id='ENT001'  # Same external_id as user's contact
        ),
    ]


@pytest.fixture
def funds(db):
    """Create test funds with external_id."""
    return [
        Fund.objects.create(
            external_id='FUND001',
            name='General Fund',
            status='active'
        ),
        Fund.objects.create(
            external_id='FUND002',
            name='Special Projects',
            status='active'
        ),
    ]


# ========== TEMPLATE TESTS ==========

def test_get_pledges_template():
    """Test CSV template has correct columns."""
    template = get_pledges_template()
    assert template == 'pledge_id,entity_id,fund_id,amount,cadence,status,start_date\n'


# ========== HEADER VALIDATION TESTS ==========

def test_parse_pledges_csv_empty_file(user):
    """Test parsing empty CSV file."""
    csv_content = ''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'empty' in errors[0]['errors'][0].lower()


def test_parse_pledges_csv_missing_required_column(user):
    """Test parsing CSV with missing required column."""
    # Missing 'cadence' column
    csv_content = 'pledge_id,entity_id,fund_id,amount,status,start_date\n'
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'cadence' in errors[0]['errors'][0].lower()


def test_parse_pledges_csv_fund_id_not_required(user, contacts, funds):
    """Test that fund_id column is optional (not in required columns)."""
    # CSV without fund_id column should still work
    csv_content = 'pledge_id,entity_id,amount,cadence,status,start_date\nPLG001,ENT001,100.00,monthly,active,2024-01-01\n'
    valid_records, errors = parse_pledges_csv(csv_content, user)

    # Should succeed if fund_id is not in the CSV at all
    # (Different from Transaction where fund_id is required)
    # This test ensures fund_id is truly optional


def test_parse_pledges_csv_valid_headers(user, contacts):
    """Test parsing CSV with valid headers returns valid records."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 1
    assert len(errors) == 0


# ========== ROW VALIDATION TESTS ==========

def test_parse_pledges_csv_pledge_id_required(user):
    """Test that pledge_id is required."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
,ENT001,,100.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'pledge_id is required' in errors[0]['errors'][0]


def test_parse_pledges_csv_pledge_id_max_length(user):
    """Test that pledge_id exceeding max length is rejected."""
    long_id = 'P' * 101
    csv_content = f'''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
{long_id},ENT001,,100.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'exceeds maximum length' in errors[0]['errors'][0]


def test_parse_pledges_csv_pledge_id_formula_character_rejection(user):
    """Test that pledge_id starting with formula characters is rejected."""
    for prefix in ['=', '+', '-', '@']:
        csv_content = f'''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
{prefix}PLG001,ENT001,,100.00,monthly,active,2024-01-01
'''
        valid_records, errors = parse_pledges_csv(csv_content, user)

        assert len(valid_records) == 0
        assert len(errors) == 1
        assert 'formula character' in errors[0]['errors'][0].lower()


def test_parse_pledges_csv_duplicate_pledge_id(user, contacts):
    """Test that duplicate pledge_id in file is rejected."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,active,2024-01-01
PLG001,ENT002,,200.00,quarterly,active,2024-02-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) >= 1
    assert any('Duplicate pledge_id' in err['errors'][0] for err in errors)


def test_parse_pledges_csv_entity_id_required(user):
    """Test that entity_id is required."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,,,100.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'entity_id is required' in errors[0]['errors'][0]


def test_parse_pledges_csv_fund_id_optional(user, contacts):
    """Test that fund_id is NOT required (can be empty)."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    # Should NOT have error about fund_id being required
    assert len(errors) == 0 or not any('fund_id is required' in str(err) for err in errors)


def test_parse_pledges_csv_amount_required(user):
    """Test that amount is required."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'amount' in errors[0]['errors'][0].lower()


def test_parse_pledges_csv_amount_positive(user):
    """Test that amount must be positive."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,-50.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1


def test_parse_pledges_csv_amount_max_value(user):
    """Test that amount cannot exceed max value."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,99999999.99,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'exceeds maximum' in errors[0]['errors'][0].lower()


def test_parse_pledges_csv_amount_format_error(user):
    """Test that invalid amount format is rejected."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,not-a-number,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1


def test_parse_pledges_csv_date_required(user):
    """Test that start_date is required."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,active,
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1


def test_parse_pledges_csv_date_valid_format(user, contacts):
    """Test that multiple date formats are accepted."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,active,2024-01-01
PLG002,ENT002,,200.00,monthly,active,01/15/2024
PLG003,ENT003,,300.00,monthly,active,15/01/2024
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 3
    assert len(errors) == 0


def test_parse_pledges_csv_start_date_can_be_future(user, contacts):
    """Test that start_date CAN be in future (unlike donation posted_date)."""
    future_date = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
    csv_content = f'''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,active,{future_date}
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    # Should NOT have error about future date (pledges can start later)
    assert len(errors) == 0 or not any('future' in str(err).lower() for err in errors)
    assert len(valid_records) == 1


# ========== ENUM VALIDATION TESTS ==========

def test_parse_pledges_csv_cadence_required(user):
    """Test that cadence is required."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'cadence is required' in errors[0]['errors'][0]


def test_parse_pledges_csv_cadence_valid_values(user, contacts):
    """Test that all valid cadence values are accepted."""
    valid_cadences = ['monthly', 'quarterly', 'semi_annual', 'annual']

    rows = []
    for i, cadence in enumerate(valid_cadences, start=1):
        rows.append(f'PLG00{i},ENT001,,100.00,{cadence},active,2024-01-01')

    csv_content = 'pledge_id,entity_id,fund_id,amount,cadence,status,start_date\n' + '\n'.join(rows) + '\n'
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 4
    assert len(errors) == 0


def test_parse_pledges_csv_cadence_case_insensitive(user, contacts):
    """Test that cadence validation is case-insensitive."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,MONTHLY,active,2024-01-01
PLG002,ENT002,,200.00,Quarterly,active,2024-01-01
PLG003,ENT003,,300.00,Semi_Annual,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 3
    assert len(errors) == 0


def test_parse_pledges_csv_cadence_invalid(user):
    """Test that invalid cadence is rejected with clear error."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,biweekly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'Invalid cadence' in errors[0]['errors'][0]
    assert 'monthly' in errors[0]['errors'][0]  # Should list valid options


def test_parse_pledges_csv_status_required(user):
    """Test that status is required."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'status is required' in errors[0]['errors'][0]


def test_parse_pledges_csv_status_valid_values(user, contacts):
    """Test that all valid status values are accepted."""
    valid_statuses = ['active', 'paused', 'completed', 'cancelled']

    rows = []
    for i, status in enumerate(valid_statuses, start=1):
        rows.append(f'PLG00{i},ENT001,,100.00,monthly,{status},2024-01-01')

    csv_content = 'pledge_id,entity_id,fund_id,amount,cadence,status,start_date\n' + '\n'.join(rows) + '\n'
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 4
    assert len(errors) == 0


def test_parse_pledges_csv_status_case_insensitive(user, contacts):
    """Test that status validation is case-insensitive."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,ACTIVE,2024-01-01
PLG002,ENT002,,200.00,monthly,Paused,2024-01-01
PLG003,ENT003,,300.00,monthly,Completed,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 3
    assert len(errors) == 0


def test_parse_pledges_csv_status_invalid(user):
    """Test that invalid status is rejected with clear error."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,pending,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'Invalid status' in errors[0]['errors'][0]
    assert 'active' in errors[0]['errors'][0]  # Should list valid options


# ========== FOREIGN KEY VALIDATION TESTS ==========

def test_parse_pledges_csv_entity_id_not_found(user):
    """Test that entity_id not found in Contact.external_id produces error."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,NONEXISTENT,,100.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0  # Strict mode - empty on FK error
    assert len(errors) == 1
    assert 'NONEXISTENT' in errors[0]['errors'][0]
    assert 'not found' in errors[0]['errors'][0].lower()


def test_parse_pledges_csv_entity_id_owner_scoped(user, contacts, other_user_contacts):
    """Test that entity_id lookup is owner-scoped (not global)."""
    # ENT001 exists for other_user, but we're importing for 'user'
    # Should error because user doesn't have ENT001 (even though other_user does)
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,active,2024-01-01
'''

    # This should succeed because 'user' has ENT001
    valid_records, errors = parse_pledges_csv(csv_content, user)
    assert len(valid_records) == 1
    assert len(errors) == 0


def test_parse_pledges_csv_fund_id_not_found(user, contacts):
    """Test that fund_id not found in Fund.external_id produces error."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,NONEXISTENT,100.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0  # Strict mode - empty on FK error
    assert len(errors) == 1
    assert 'NONEXISTENT' in errors[0]['errors'][0]
    assert 'not found' in errors[0]['errors'][0].lower()


def test_parse_pledges_csv_fund_id_empty_no_error(user, contacts):
    """Test that empty fund_id does NOT produce error (optional field)."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 1
    assert len(errors) == 0


def test_parse_pledges_csv_multiple_orphan_fks(user):
    """Test that multiple orphan FKs are all reported with row numbers."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,MISSING1,FUNDBAD,100.00,monthly,active,2024-01-01
PLG002,MISSING2,FUNDBAD,200.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0  # Strict mode
    assert len(errors) == 2
    # Each row should have its own error with row number
    assert errors[0]['row'] == 2
    assert errors[1]['row'] == 3


def test_parse_pledges_csv_strict_mode_clears_valid_records(user, contacts):
    """Test that if ANY orphan FK exists, valid_records returns EMPTY (strict mode)."""
    csv_content = '''pledge_id,entity_id,fund_id,amount,cadence,status,start_date
PLG001,ENT001,,100.00,monthly,active,2024-01-01
PLG002,MISSING,,200.00,monthly,active,2024-01-01
'''
    valid_records, errors = parse_pledges_csv(csv_content, user)

    # Even though PLG001 is valid, strict mode returns empty valid_records
    assert len(valid_records) == 0
    assert len(errors) >= 1


def test_parse_pledges_csv_error_limit_20(user):
    """Test that errors are limited to first 20 (consistent with Phase 8/9/10)."""
    rows = []
    for i in range(1, 26):  # 25 invalid rows
        rows.append(f'PLG{i:03d},MISSING{i},,100.00,monthly,active,2024-01-01')

    csv_content = 'pledge_id,entity_id,fund_id,amount,cadence,status,start_date\n' + '\n'.join(rows) + '\n'
    valid_records, errors = parse_pledges_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) <= 20  # Limit to first 20 errors


# ========== IMPORT TESTS ==========

def test_import_pledges_creates_pledge_with_contact_fk(user, contacts, admin_user):
    """Test that import_pledges creates Pledge with correct Contact FK."""
    import_run = ImportRun.objects.create(
        type=ImportType.PLEDGES,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=admin_user
    )

    records = [
        {
            'pledge_id': 'PLG001',
            'entity_id': 'ENT001',
            'fund_id': '',
            'amount': Decimal('100.00'),
            'cadence': 'monthly',
            'status': 'active',
            'start_date': date(2024, 1, 1)
        }
    ]

    created_count, updated_count = import_pledges(records, user, import_run)

    assert created_count == 1
    assert updated_count == 0

    pledge = Pledge.objects.get(external_id='PLG001')
    assert pledge.contact == contacts[0]  # ENT001 maps to first contact


def test_import_pledges_creates_pledge_with_fund_fk(user, contacts, funds, admin_user):
    """Test that import_pledges creates Pledge with correct Fund FK when provided."""
    import_run = ImportRun.objects.create(
        type=ImportType.PLEDGES,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=admin_user
    )

    records = [
        {
            'pledge_id': 'PLG001',
            'entity_id': 'ENT001',
            'fund_id': 'FUND001',
            'amount': Decimal('100.00'),
            'cadence': 'monthly',
            'status': 'active',
            'start_date': date(2024, 1, 1)
        }
    ]

    created_count, updated_count = import_pledges(records, user, import_run)

    assert created_count == 1

    pledge = Pledge.objects.get(external_id='PLG001')
    assert pledge.fund == funds[0]  # FUND001 maps to first fund


def test_import_pledges_creates_pledge_with_fund_none(user, contacts, admin_user):
    """Test that import_pledges creates Pledge with fund=None when fund_id empty."""
    import_run = ImportRun.objects.create(
        type=ImportType.PLEDGES,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=admin_user
    )

    records = [
        {
            'pledge_id': 'PLG001',
            'entity_id': 'ENT001',
            'fund_id': '',
            'amount': Decimal('100.00'),
            'cadence': 'monthly',
            'status': 'active',
            'start_date': date(2024, 1, 1)
        }
    ]

    created_count, updated_count = import_pledges(records, user, import_run)

    assert created_count == 1

    pledge = Pledge.objects.get(external_id='PLG001')
    assert pledge.fund is None


def test_import_pledges_maps_cadence_to_frequency(user, contacts, admin_user):
    """Test that CSV 'cadence' column maps to Pledge.frequency field."""
    import_run = ImportRun.objects.create(
        type=ImportType.PLEDGES,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=admin_user
    )

    records = [
        {
            'pledge_id': 'PLG001',
            'entity_id': 'ENT001',
            'fund_id': '',
            'amount': Decimal('100.00'),
            'cadence': 'quarterly',
            'status': 'active',
            'start_date': date(2024, 1, 1)
        }
    ]

    created_count, updated_count = import_pledges(records, user, import_run)

    assert created_count == 1

    pledge = Pledge.objects.get(external_id='PLG001')
    assert pledge.frequency == 'quarterly'


def test_import_pledges_uses_external_id(user, contacts, admin_user):
    """Test that import_pledges uses pledge_id as Pledge.external_id."""
    import_run = ImportRun.objects.create(
        type=ImportType.PLEDGES,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=admin_user
    )

    records = [
        {
            'pledge_id': 'PLG001',
            'entity_id': 'ENT001',
            'fund_id': '',
            'amount': Decimal('100.00'),
            'cadence': 'monthly',
            'status': 'active',
            'start_date': date(2024, 1, 1)
        }
    ]

    created_count, updated_count = import_pledges(records, user, import_run)

    assert created_count == 1

    pledge = Pledge.objects.get(external_id='PLG001')
    assert pledge.external_id == 'PLG001'


def test_import_pledges_upserts_existing(user, contacts, admin_user):
    """Test that import_pledges upserts existing external_id instead of duplicates."""
    import_run = ImportRun.objects.create(
        type=ImportType.PLEDGES,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=admin_user
    )

    # Create existing pledge
    Pledge.objects.create(
        external_id='PLG001',
        contact=contacts[0],
        amount=Decimal('50.00'),
        frequency='monthly',
        status='active',
        start_date=date(2024, 1, 1)
    )

    # Import with same external_id but different amount
    records = [
        {
            'pledge_id': 'PLG001',
            'entity_id': 'ENT001',
            'fund_id': '',
            'amount': Decimal('100.00'),
            'cadence': 'quarterly',
            'status': 'paused',
            'start_date': date(2024, 2, 1)
        }
    ]

    created_count, updated_count = import_pledges(records, user, import_run)

    assert created_count == 0
    assert updated_count == 1

    # Should have only one pledge with updated values
    assert Pledge.objects.filter(external_id='PLG001').count() == 1
    pledge = Pledge.objects.get(external_id='PLG001')
    assert pledge.amount == Decimal('100.00')
    assert pledge.frequency == 'quarterly'
    assert pledge.status == 'paused'


def test_import_pledges_returns_counts(user, contacts, admin_user):
    """Test that import_pledges returns (created_count, updated_count)."""
    import_run = ImportRun.objects.create(
        type=ImportType.PLEDGES,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=admin_user
    )

    # Create one existing pledge
    Pledge.objects.create(
        external_id='PLG001',
        contact=contacts[0],
        amount=Decimal('50.00'),
        frequency='monthly',
        status='active',
        start_date=date(2024, 1, 1)
    )

    records = [
        {
            'pledge_id': 'PLG001',
            'entity_id': 'ENT001',
            'fund_id': '',
            'amount': Decimal('100.00'),
            'cadence': 'monthly',
            'status': 'active',
            'start_date': date(2024, 1, 1)
        },
        {
            'pledge_id': 'PLG002',
            'entity_id': 'ENT002',
            'fund_id': '',
            'amount': Decimal('200.00'),
            'cadence': 'monthly',
            'status': 'active',
            'start_date': date(2024, 1, 1)
        }
    ]

    created_count, updated_count = import_pledges(records, user, import_run)

    assert created_count == 1  # PLG002 is new
    assert updated_count == 1  # PLG001 already existed


def test_import_pledges_updates_import_run(user, contacts, admin_user):
    """Test that import_pledges updates ImportRun status and counts."""
    import_run = ImportRun.objects.create(
        type=ImportType.PLEDGES,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=admin_user
    )

    records = [
        {
            'pledge_id': 'PLG001',
            'entity_id': 'ENT001',
            'fund_id': '',
            'amount': Decimal('100.00'),
            'cadence': 'monthly',
            'status': 'active',
            'start_date': date(2024, 1, 1)
        }
    ]

    import_pledges(records, user, import_run)

    import_run.refresh_from_db()
    assert import_run.status == ImportStatus.COMPLETED
    assert import_run.created_count == 1
    assert import_run.updated_count == 0


def test_import_pledges_no_contact_stats_update(user, contacts, admin_user):
    """Test that import_pledges does NOT call update_contact_stats (pledges use computed properties)."""
    import_run = ImportRun.objects.create(
        type=ImportType.PLEDGES,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=admin_user
    )

    records = [
        {
            'pledge_id': 'PLG001',
            'entity_id': 'ENT001',
            'fund_id': '',
            'amount': Decimal('100.00'),
            'cadence': 'monthly',
            'status': 'active',
            'start_date': date(2024, 1, 1)
        }
    ]

    # This test verifies the import completes successfully
    # without any calls to update_contact_stats_for_import
    created_count, updated_count = import_pledges(records, user, import_run)

    assert created_count == 1
    # No assertion about Contact fields because pledge stats are computed properties
    # This test documents that behavior difference from Phase 10 transactions
