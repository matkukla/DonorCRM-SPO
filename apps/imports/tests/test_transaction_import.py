"""
Tests for transaction CSV import functionality.
"""
import pytest
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model

from apps.contacts.models import Contact
from apps.donations.models import Donation, DonationType, PaymentMethod
from apps.imports.models import Fund, ImportRun, ImportType, ImportStatus
from apps.imports.services import (
    parse_transactions_csv,
    import_transactions,
    update_contact_stats_for_import,
    get_transactions_template
)

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user for testing."""
    return User.objects.create_user(
        email='admin@example.com',
        password='testpass',
        role='admin'
    )


@pytest.fixture
def user(db):
    """Create regular user for testing."""
    return User.objects.create_user(
        email='user@example.com',
        password='testpass',
        role='staff'
    )


@pytest.fixture
def other_user(db):
    """Create another user for owner-scoping tests."""
    return User.objects.create_user(
        email='other@example.com',
        password='testpass',
        role='staff'
    )


@pytest.fixture
def contacts(user):
    """Create contacts with external_ids for testing."""
    return [
        Contact.objects.create(
            owner=user,
            external_id='E001',
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        ),
        Contact.objects.create(
            owner=user,
            external_id='E002',
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com'
        ),
        Contact.objects.create(
            owner=user,
            external_id='E003',
            first_name='Bob',
            last_name='Johnson',
            email='bob@example.com'
        )
    ]


@pytest.fixture
def other_user_contacts(other_user):
    """Create contacts with same external_ids but different owner."""
    return [
        Contact.objects.create(
            owner=other_user,
            external_id='E001',  # Same as user's contact
            first_name='Other',
            last_name='Person',
            email='other1@example.com'
        ),
        Contact.objects.create(
            owner=other_user,
            external_id='E002',  # Same as user's contact
            first_name='Another',
            last_name='Person',
            email='other2@example.com'
        )
    ]


@pytest.fixture
def funds(db):
    """Create funds with external_ids for testing."""
    return [
        Fund.objects.create(
            external_id='F001',
            name='General Fund',
            status='active'
        ),
        Fund.objects.create(
            external_id='F002',
            name='Building Fund',
            status='active'
        ),
        Fund.objects.create(
            external_id='F003',
            name='Missions Fund',
            status='active'
        )
    ]


# ============================================================================
# HEADER VALIDATION TESTS
# ============================================================================

@pytest.mark.django_db
def test_empty_file_returns_error(user):
    """Empty CSV file should return error."""
    csv_content = ''
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) > 0
    assert 'empty' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_missing_required_column_transaction_id(user):
    """Missing transaction_id column should return error."""
    csv_content = 'entity_id,fund_id,amount,posted_date\n'
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) > 0
    assert 'transaction_id' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_missing_required_column_entity_id(user):
    """Missing entity_id column should return error."""
    csv_content = 'transaction_id,fund_id,amount,posted_date\n'
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) > 0
    assert 'entity_id' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_missing_required_column_fund_id(user):
    """Missing fund_id column should return error."""
    csv_content = 'transaction_id,entity_id,amount,posted_date\n'
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) > 0
    assert 'fund_id' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_missing_required_column_amount(user):
    """Missing amount column should return error."""
    csv_content = 'transaction_id,entity_id,fund_id,posted_date\n'
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) > 0
    assert 'amount' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_missing_required_column_posted_date(user):
    """Missing posted_date column should return error."""
    csv_content = 'transaction_id,entity_id,fund_id,amount\n'
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) > 0
    assert 'posted_date' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_valid_headers_return_valid_records(user, contacts, funds):
    """CSV with valid headers and data should parse correctly."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,100.00,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 1
    assert len(errors) == 0
    assert valid_records[0]['transaction_id'] == 'T001'


# ============================================================================
# ROW VALIDATION TESTS
# ============================================================================

@pytest.mark.django_db
def test_transaction_id_required(user, contacts, funds):
    """transaction_id is required."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
,E001,F001,100.00,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'transaction_id' in errors[0]['errors'][0].lower()
    assert 'required' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_transaction_id_max_length(user, contacts, funds):
    """transaction_id cannot exceed 100 characters."""
    long_id = 'T' * 101
    csv_content = f"""transaction_id,entity_id,fund_id,amount,posted_date
{long_id},E001,F001,100.00,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'length' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_transaction_id_formula_character_rejection(user, contacts, funds):
    """transaction_id starting with formula character should be rejected."""
    for prefix in ['=', '+', '-', '@']:
        csv_content = f"""transaction_id,entity_id,fund_id,amount,posted_date
{prefix}T001,E001,F001,100.00,2024-01-15
"""
        valid_records, errors = parse_transactions_csv(csv_content, user)

        assert len(valid_records) == 0
        assert len(errors) == 1
        assert 'formula' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_duplicate_transaction_id_in_file(user, contacts, funds):
    """Duplicate transaction_id in file should be rejected."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,100.00,2024-01-15
T001,E002,F002,200.00,2024-01-16
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 1  # First one is valid
    assert len(errors) == 1  # Second one errors
    assert errors[0]['row'] == 3
    assert 'duplicate' in errors[0]['errors'][0].lower()
    assert 'T001' in errors[0]['errors'][0]


@pytest.mark.django_db
def test_entity_id_required(user, contacts, funds):
    """entity_id is required."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,,F001,100.00,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'entity_id' in errors[0]['errors'][0].lower()
    assert 'required' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_fund_id_required(user, contacts, funds):
    """fund_id is required."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,,100.00,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'fund_id' in errors[0]['errors'][0].lower()
    assert 'required' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_amount_required(user, contacts, funds):
    """Amount is required."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'amount' in errors[0]['errors'][0].lower()
    assert 'required' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_amount_must_be_positive(user, contacts, funds):
    """Amount must be positive."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,-100.00,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'negative' in errors[0]['errors'][0].lower() or 'positive' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_amount_max_value(user, contacts, funds):
    """Amount cannot exceed max value."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,99999999.99,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'maximum' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_amount_format_error(user, contacts, funds):
    """Invalid amount format should return error."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,not-a-number,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'amount' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_posted_date_required(user, contacts, funds):
    """posted_date is required."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,100.00,
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'date' in errors[0]['errors'][0].lower()
    assert 'required' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_posted_date_invalid_format(user, contacts, funds):
    """Invalid date format should return error."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,100.00,not-a-date
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0
    assert len(errors) == 1
    assert 'date' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_posted_date_multiple_formats_accepted(user, contacts, funds):
    """Multiple date formats should be accepted."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,100.00,2024-01-15
T002,E002,F002,200.00,01/16/2024
T003,E003,F003,300.00,17/01/2024
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 3
    assert len(errors) == 0


# ============================================================================
# FOREIGN KEY VALIDATION TESTS (CRITICAL - STRICT MODE)
# ============================================================================

@pytest.mark.django_db
def test_entity_id_not_found_returns_error(user, contacts, funds):
    """entity_id not found in Contact.external_id should return error."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E999,F001,100.00,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0  # Strict mode: empty if any FK error
    assert len(errors) == 1
    assert 'E999' in str(errors[0])
    assert 'not found' in errors[0]['errors'][0].lower()
    assert 2 == errors[0]['row']


@pytest.mark.django_db
def test_entity_id_found_for_different_owner_returns_error(user, other_user_contacts, funds):
    """entity_id found for DIFFERENT owner should return error (owner-scoped)."""
    # other_user_contacts created E001 for other_user
    # user tries to import transaction with E001
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,100.00,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0  # Strict mode: empty if any FK error
    assert len(errors) == 1
    assert 'E001' in str(errors[0])
    assert 'not found' in errors[0]['errors'][0].lower()


@pytest.mark.django_db
def test_fund_id_not_found_returns_error(user, contacts, funds):
    """fund_id not found in Fund.external_id should return error."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F999,100.00,2024-01-15
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0  # Strict mode: empty if any FK error
    assert len(errors) == 1
    assert 'F999' in str(errors[0])
    assert 'not found' in errors[0]['errors'][0].lower()
    assert 2 == errors[0]['row']


@pytest.mark.django_db
def test_multiple_orphan_fks_all_reported(user, contacts, funds):
    """Multiple orphan FK references should all be reported."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E999,F001,100.00,2024-01-15
T002,E001,F999,200.00,2024-01-16
T003,E888,F888,300.00,2024-01-17
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0  # Strict mode: empty if any FK error
    assert len(errors) == 3
    # All orphan references should be reported
    # Flatten all error messages from all rows
    error_messages = [msg for err in errors for msg in err['errors']]
    assert any('E999' in msg for msg in error_messages)
    assert any('F999' in msg for msg in error_messages)
    assert any('E888' in msg for msg in error_messages)
    assert any('F888' in msg for msg in error_messages)


@pytest.mark.django_db
def test_strict_mode_returns_empty_valid_records_on_any_orphan_fk(user, contacts, funds):
    """If ANY orphan FK exists, valid_records returns EMPTY (strict mode)."""
    csv_content = """transaction_id,entity_id,fund_id,amount,posted_date
T001,E001,F001,100.00,2024-01-15
T002,E002,F002,200.00,2024-01-16
T003,E999,F003,300.00,2024-01-17
"""
    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0  # Strict mode: ALL rejected if ANY error
    assert len(errors) == 1
    assert 'E999' in str(errors[0])


@pytest.mark.django_db
def test_first_20_errors_returned(user, contacts, funds):
    """Return first 20 errors when many orphan FKs exist."""
    # Generate 25 rows with orphan entity_ids
    rows = ['transaction_id,entity_id,fund_id,amount,posted_date']
    for i in range(25):
        rows.append(f'T{i:03d},E{i+900},F001,100.00,2024-01-15')
    csv_content = '\n'.join(rows)

    valid_records, errors = parse_transactions_csv(csv_content, user)

    assert len(valid_records) == 0  # Strict mode
    assert len(errors) <= 20  # Limited to first 20


# ============================================================================
# IMPORT_TRANSACTIONS TESTS
# ============================================================================

@pytest.mark.django_db
def test_import_creates_donation_with_correct_contact_fk(user, contacts, funds):
    """import_transactions should create Donation with correct Contact FK."""
    import_run = ImportRun.objects.create(
        type=ImportType.TRANSACTIONS,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=user
    )

    records = [{
        'transaction_id': 'T001',
        'entity_id': 'E001',
        'fund_id': 'F001',
        'amount': Decimal('100.00'),
        'posted_date': '2024-01-15'
    }]

    created_count, updated_count = import_transactions(records, user, import_run)

    assert created_count == 1
    assert updated_count == 0

    donation = Donation.objects.get(external_id='T001')
    assert donation.contact.external_id == 'E001'
    assert donation.contact.owner == user


@pytest.mark.django_db
def test_import_creates_donation_with_correct_fund_fk(user, contacts, funds):
    """import_transactions should create Donation with correct Fund FK."""
    import_run = ImportRun.objects.create(
        type=ImportType.TRANSACTIONS,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=user
    )

    records = [{
        'transaction_id': 'T001',
        'entity_id': 'E001',
        'fund_id': 'F001',
        'amount': Decimal('100.00'),
        'posted_date': '2024-01-15'
    }]

    created_count, updated_count = import_transactions(records, user, import_run)

    donation = Donation.objects.get(external_id='T001')
    assert donation.fund.external_id == 'F001'


@pytest.mark.django_db
def test_import_uses_transaction_id_as_external_id(user, contacts, funds):
    """import_transactions should use transaction_id as Donation.external_id."""
    import_run = ImportRun.objects.create(
        type=ImportType.TRANSACTIONS,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=user
    )

    records = [{
        'transaction_id': 'T001',
        'entity_id': 'E001',
        'fund_id': 'F001',
        'amount': Decimal('100.00'),
        'posted_date': '2024-01-15'
    }]

    created_count, updated_count = import_transactions(records, user, import_run)

    donation = Donation.objects.get(external_id='T001')
    assert donation.external_id == 'T001'


@pytest.mark.django_db
def test_import_upserts_existing_external_id(user, contacts, funds):
    """import_transactions should update existing record with same external_id."""
    import_run = ImportRun.objects.create(
        type=ImportType.TRANSACTIONS,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=user
    )

    # First import
    records = [{
        'transaction_id': 'T001',
        'entity_id': 'E001',
        'fund_id': 'F001',
        'amount': Decimal('100.00'),
        'posted_date': '2024-01-15'
    }]

    created_count, updated_count = import_transactions(records, user, import_run)
    assert created_count == 1
    assert updated_count == 0

    # Second import with same transaction_id but different amount
    import_run2 = ImportRun.objects.create(
        type=ImportType.TRANSACTIONS,
        status=ImportStatus.IMPORTING,
        filename='test2.csv',
        uploaded_by=user
    )

    records2 = [{
        'transaction_id': 'T001',
        'entity_id': 'E002',
        'fund_id': 'F002',
        'amount': Decimal('200.00'),
        'posted_date': '2024-01-16'
    }]

    created_count2, updated_count2 = import_transactions(records2, user, import_run2)
    assert created_count2 == 0
    assert updated_count2 == 1

    # Should only be one donation with updated values
    assert Donation.objects.filter(external_id='T001').count() == 1
    donation = Donation.objects.get(external_id='T001')
    assert donation.amount == Decimal('200.00')
    assert donation.contact.external_id == 'E002'


@pytest.mark.django_db
def test_import_returns_created_and_updated_counts(user, contacts, funds):
    """import_transactions should return (created_count, updated_count)."""
    import_run = ImportRun.objects.create(
        type=ImportType.TRANSACTIONS,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=user
    )

    # Create one donation first
    Donation.objects.create(
        external_id='T001',
        contact=contacts[0],
        fund=funds[0],
        amount=Decimal('100.00'),
        date='2024-01-15',
        donation_type=DonationType.ONE_TIME,
        payment_method=PaymentMethod.OTHER
    )

    # Import 3 records: 1 update, 2 creates
    records = [
        {
            'transaction_id': 'T001',  # Update
            'entity_id': 'E001',
            'fund_id': 'F001',
            'amount': Decimal('150.00'),
            'posted_date': '2024-01-15'
        },
        {
            'transaction_id': 'T002',  # Create
            'entity_id': 'E002',
            'fund_id': 'F002',
            'amount': Decimal('200.00'),
            'posted_date': '2024-01-16'
        },
        {
            'transaction_id': 'T003',  # Create
            'entity_id': 'E003',
            'fund_id': 'F003',
            'amount': Decimal('300.00'),
            'posted_date': '2024-01-17'
        }
    ]

    created_count, updated_count = import_transactions(records, user, import_run)

    assert created_count == 2
    assert updated_count == 1


@pytest.mark.django_db
def test_import_updates_import_run_status_and_counts(user, contacts, funds):
    """import_transactions should update ImportRun with status and counts."""
    import_run = ImportRun.objects.create(
        type=ImportType.TRANSACTIONS,
        status=ImportStatus.IMPORTING,
        filename='test.csv',
        uploaded_by=user
    )

    records = [
        {
            'transaction_id': 'T001',
            'entity_id': 'E001',
            'fund_id': 'F001',
            'amount': Decimal('100.00'),
            'posted_date': '2024-01-15'
        },
        {
            'transaction_id': 'T002',
            'entity_id': 'E002',
            'fund_id': 'F002',
            'amount': Decimal('200.00'),
            'posted_date': '2024-01-16'
        }
    ]

    created_count, updated_count = import_transactions(records, user, import_run)

    import_run.refresh_from_db()
    assert import_run.status == ImportStatus.COMPLETED
    assert import_run.created_count == 2
    assert import_run.updated_count == 0


# ============================================================================
# UPDATE_CONTACT_STATS_FOR_IMPORT TESTS
# ============================================================================

@pytest.mark.django_db
def test_update_contact_stats_updates_total_given(user, contacts, funds):
    """update_contact_stats_for_import should update total_given."""
    # Create donations
    Donation.objects.create(
        external_id='T001',
        contact=contacts[0],
        fund=funds[0],
        amount=Decimal('100.00'),
        date='2024-01-15'
    )
    Donation.objects.create(
        external_id='T002',
        contact=contacts[0],
        fund=funds[0],
        amount=Decimal('200.00'),
        date='2024-01-16'
    )

    records = [
        {'entity_id': 'E001'},
    ]

    update_contact_stats_for_import(records, user)

    contacts[0].refresh_from_db()
    assert contacts[0].total_given == Decimal('300.00')


@pytest.mark.django_db
def test_update_contact_stats_updates_gift_count(user, contacts, funds):
    """update_contact_stats_for_import should update gift_count."""
    # Create donations
    Donation.objects.create(
        external_id='T001',
        contact=contacts[0],
        fund=funds[0],
        amount=Decimal('100.00'),
        date='2024-01-15'
    )
    Donation.objects.create(
        external_id='T002',
        contact=contacts[0],
        fund=funds[0],
        amount=Decimal('200.00'),
        date='2024-01-16'
    )

    records = [
        {'entity_id': 'E001'},
    ]

    update_contact_stats_for_import(records, user)

    contacts[0].refresh_from_db()
    assert contacts[0].gift_count == 2


@pytest.mark.django_db
def test_update_contact_stats_updates_last_gift_date(user, contacts, funds):
    """update_contact_stats_for_import should update last_gift_date."""
    from datetime import date

    # Create donations
    Donation.objects.create(
        external_id='T001',
        contact=contacts[0],
        fund=funds[0],
        amount=Decimal('100.00'),
        date=date(2024, 1, 15)
    )
    Donation.objects.create(
        external_id='T002',
        contact=contacts[0],
        fund=funds[0],
        amount=Decimal('200.00'),
        date=date(2024, 1, 20)
    )

    records = [
        {'entity_id': 'E001'},
    ]

    update_contact_stats_for_import(records, user)

    contacts[0].refresh_from_db()
    assert contacts[0].last_gift_date == date(2024, 1, 20)


@pytest.mark.django_db
def test_update_contact_stats_only_updates_affected_contacts(user, contacts, funds):
    """update_contact_stats_for_import should only update affected contacts."""
    # Create donation for first contact only
    Donation.objects.create(
        external_id='T001',
        contact=contacts[0],
        fund=funds[0],
        amount=Decimal('100.00'),
        date='2024-01-15'
    )

    # Record initial state of other contacts
    initial_total_1 = contacts[1].total_given
    initial_total_2 = contacts[2].total_given

    records = [
        {'entity_id': 'E001'},  # Only E001 affected
    ]

    update_contact_stats_for_import(records, user)

    # First contact should be updated
    contacts[0].refresh_from_db()
    assert contacts[0].total_given == Decimal('100.00')

    # Other contacts should NOT be updated
    contacts[1].refresh_from_db()
    contacts[2].refresh_from_db()
    assert contacts[1].total_given == initial_total_1
    assert contacts[2].total_given == initial_total_2


@pytest.mark.django_db
def test_update_contact_stats_multiple_affected_contacts(user, contacts, funds):
    """update_contact_stats_for_import should handle multiple affected contacts."""
    # Create donations for multiple contacts
    Donation.objects.create(
        external_id='T001',
        contact=contacts[0],
        fund=funds[0],
        amount=Decimal('100.00'),
        date='2024-01-15'
    )
    Donation.objects.create(
        external_id='T002',
        contact=contacts[1],
        fund=funds[1],
        amount=Decimal('200.00'),
        date='2024-01-16'
    )

    records = [
        {'entity_id': 'E001'},
        {'entity_id': 'E002'},
    ]

    update_contact_stats_for_import(records, user)

    # Verify both contacts were updated
    contacts[0].refresh_from_db()
    contacts[1].refresh_from_db()
    assert contacts[0].total_given == Decimal('100.00')
    assert contacts[1].total_given == Decimal('200.00')


# ============================================================================
# GET_TRANSACTIONS_TEMPLATE TEST
# ============================================================================

@pytest.mark.django_db
def test_get_transactions_template_returns_correct_header():
    """get_transactions_template should return correct CSV header."""
    template = get_transactions_template()

    assert template == 'transaction_id,entity_id,fund_id,amount,posted_date\n'


# ============================================================================
# INTEGRATION TESTS - TransactionImportView API
# ============================================================================

from django.urls import reverse
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.fixture
def api_client():
    """Create API client for testing."""
    return APIClient()


@pytest.fixture
def contacts_with_external_id(admin_user):
    """Create contacts with external_id for FK testing."""
    return [
        Contact.objects.create(
            owner=admin_user,
            first_name='John',
            last_name='Doe',
            external_id='E001'
        ),
        Contact.objects.create(
            owner=admin_user,
            first_name='Jane',
            last_name='Smith',
            external_id='E002'
        ),
    ]


@pytest.fixture
def funds_with_external_id():
    """Create funds with external_id for FK testing."""
    return [
        Fund.objects.create(external_id='F001', name='General Fund', status='active'),
        Fund.objects.create(external_id='F002', name='Building Fund', status='active'),
    ]


@pytest.mark.django_db
class TestTransactionImportView:
    """Integration tests for TransactionImportView API endpoint."""

    def test_admin_can_import_transactions(
        self, api_client, admin_user, contacts_with_external_id, funds_with_external_id
    ):
        """Admin user can successfully import transactions via POST."""
        api_client.force_authenticate(user=admin_user)
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'
        csv_content += 'T001,E001,F001,100.00,2024-01-15\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 200
        assert response.data['created_count'] == 1
        assert response.data['updated_count'] == 0
        assert response.data['error_count'] == 0
        assert response.data['import_run_id'] is not None

        # Verify donation created
        donation = Donation.objects.get(external_id='T001')
        assert donation.contact == contacts_with_external_id[0]
        assert donation.fund == funds_with_external_id[0]
        assert donation.amount == Decimal('100.00')

    def test_non_admin_receives_403(self, api_client, user):
        """Non-admin user receives 403 Forbidden."""
        api_client.force_authenticate(user=user)
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 403

    def test_unauthenticated_receives_401(self, api_client):
        """Unauthenticated request receives 401."""
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 401

    def test_missing_file_returns_400(self, api_client, admin_user):
        """Missing file returns 400 with 'No file provided' message."""
        api_client.force_authenticate(user=admin_user)

        response = api_client.post(
            reverse('imports:import-transactions'),
            {},
            format='multipart'
        )

        assert response.status_code == 400
        assert response.data['detail'] == 'No file provided.'

    def test_non_csv_file_returns_400(self, api_client, admin_user):
        """Non-CSV file returns 400 with 'File must be a CSV' message."""
        api_client.force_authenticate(user=admin_user)

        file = SimpleUploadedFile('test.txt', b'not a csv', content_type='text/plain')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 400
        assert response.data['detail'] == 'File must be a CSV.'

    def test_utf8_bom_from_excel_handled_correctly(
        self, api_client, admin_user, contacts_with_external_id, funds_with_external_id
    ):
        """UTF-8 BOM from Excel is handled correctly (utf-8-sig decoding)."""
        api_client.force_authenticate(user=admin_user)

        # BOM + CSV content
        bom = b'\xef\xbb\xbf'
        csv_content = b'transaction_id,entity_id,fund_id,amount,posted_date\n'
        csv_content += b'T001,E001,F001,50.00,2024-01-15\n'

        file = SimpleUploadedFile('test.csv', bom + csv_content, content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 200
        assert response.data['created_count'] == 1

    def test_validation_errors_return_with_error_count(
        self, api_client, admin_user, contacts_with_external_id, funds_with_external_id
    ):
        """Validation errors return with error_count and errors array."""
        api_client.force_authenticate(user=admin_user)
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'
        csv_content += 'T001,E001,F001,invalid_amount,2024-01-15\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 200
        assert response.data['created_count'] == 0
        assert response.data['updated_count'] == 0
        assert response.data['error_count'] == 1
        assert len(response.data['errors']) == 1
        assert 'amount' in response.data['errors'][0]['errors'][0]

    def test_orphan_entity_id_returns_error(
        self, api_client, admin_user, funds_with_external_id
    ):
        """Orphan entity_id (not found) returns error with row number."""
        # No contacts created - entity_id won't be found
        api_client.force_authenticate(user=admin_user)
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'
        csv_content += 'T001,MISSING,F001,100.00,2024-01-15\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 200
        assert response.data['created_count'] == 0
        assert response.data['updated_count'] == 0
        assert response.data['error_count'] == 1
        assert "entity_id 'MISSING' not found" in response.data['errors'][0]['errors'][0]

    def test_orphan_fund_id_returns_error(
        self, api_client, admin_user, contacts_with_external_id
    ):
        """Orphan fund_id (not found) returns error with row number."""
        # No funds created - fund_id won't be found
        api_client.force_authenticate(user=admin_user)
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'
        csv_content += 'T001,E001,MISSING,100.00,2024-01-15\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 200
        assert response.data['created_count'] == 0
        assert response.data['updated_count'] == 0
        assert response.data['error_count'] == 1
        assert "fund_id 'MISSING' not found" in response.data['errors'][0]['errors'][0]

    def test_validate_only_performs_dry_run(
        self, api_client, admin_user, contacts_with_external_id, funds_with_external_id
    ):
        """validate_only=true performs dry-run validation without importing."""
        api_client.force_authenticate(user=admin_user)
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'
        csv_content += 'T001,E001,F001,100.00,2024-01-15\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions') + '?validate_only=true',
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 200
        assert response.data['valid_count'] == 1
        assert response.data['error_count'] == 0

        # Verify NO donations were created
        assert Donation.objects.filter(external_id='T001').count() == 0

    def test_successful_import_creates_import_run(
        self, api_client, admin_user, contacts_with_external_id, funds_with_external_id
    ):
        """Successful import creates ImportRun audit record."""
        api_client.force_authenticate(user=admin_user)
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'
        csv_content += 'T001,E001,F001,100.00,2024-01-15\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 200
        import_run_id = response.data['import_run_id']

        # Verify ImportRun created
        import_run = ImportRun.objects.get(id=import_run_id)
        assert import_run.type == ImportType.TRANSACTIONS
        assert import_run.status == ImportStatus.COMPLETED
        assert import_run.created_count == 1
        assert import_run.updated_count == 0
        assert import_run.uploaded_by == admin_user

    def test_import_run_id_included_in_response(
        self, api_client, admin_user, contacts_with_external_id, funds_with_external_id
    ):
        """Response includes import_run_id."""
        api_client.force_authenticate(user=admin_user)
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'
        csv_content += 'T001,E001,F001,100.00,2024-01-15\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 200
        assert 'import_run_id' in response.data
        assert response.data['import_run_id'] is not None

    def test_contact_stats_updated_after_import(
        self, api_client, admin_user, contacts_with_external_id, funds_with_external_id
    ):
        """Contact denormalized stats are updated after successful import."""
        api_client.force_authenticate(user=admin_user)
        csv_content = 'transaction_id,entity_id,fund_id,amount,posted_date\n'
        csv_content += 'T001,E001,F001,100.00,2024-01-15\n'
        csv_content += 'T002,E001,F001,50.00,2024-01-16\n'

        file = SimpleUploadedFile('test.csv', csv_content.encode('utf-8'), content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-transactions'),
            {'file': file},
            format='multipart'
        )

        assert response.status_code == 200
        assert response.data['created_count'] == 2

        # Verify contact stats updated
        contact = contacts_with_external_id[0]
        contact.refresh_from_db()
        assert contact.total_given == Decimal('150.00')
        assert contact.gift_count == 2


@pytest.mark.django_db
class TestTransactionTemplateView:
    """Integration tests for TransactionTemplateView API endpoint."""

    def test_admin_can_download_template(self, api_client, admin_user):
        """Admin user can download transaction CSV template."""
        api_client.force_authenticate(user=admin_user)

        response = api_client.get(reverse('imports:template-transactions'))

        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert response['Content-Disposition'] == 'attachment; filename="transactions_template.csv"'
        assert b'transaction_id,entity_id,fund_id,amount,posted_date' in response.content

    def test_non_admin_receives_403(self, api_client, user):
        """Non-admin user receives 403 Forbidden."""
        api_client.force_authenticate(user=user)

        response = api_client.get(reverse('imports:template-transactions'))

        assert response.status_code == 403

    def test_unauthenticated_receives_401(self, api_client):
        """Unauthenticated request receives 401."""
        response = api_client.get(reverse('imports:template-transactions'))

        assert response.status_code == 401
