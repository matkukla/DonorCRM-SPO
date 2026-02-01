"""
Tests for Entity CSV import functionality.
"""
import io
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.imports.models import ImportRun, ImportType, ImportStatus
from apps.imports.services import parse_entities_csv, import_entities

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
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        email='admin@example.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User',
        role='admin'
    )


@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def import_run(test_user):
    """Create a test ImportRun."""
    return ImportRun.objects.create(
        type=ImportType.ENTITIES,
        status=ImportStatus.PENDING,
        filename='test_entities.csv',
        uploaded_by=test_user
    )


class TestParseEntitiesCSV:
    """Tests for parse_entities_csv function."""

    def test_valid_csv_returns_records(self, test_user):
        """Valid CSV should return parsed records."""
        csv_content = """entity_id,name,email,phone,address,entity_type
ENT001,John Smith,john@example.com,555-1234,123 Main St,person
ENT002,Mary Jane Smith,mary@example.com,555-5678,456 Oak Ave,person"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 2
        assert len(errors) == 0
        assert records[0]['entity_id'] == 'ENT001'
        assert records[0]['first_name'] == 'John'
        assert records[0]['last_name'] == 'Smith'
        assert records[0]['email'] == 'john@example.com'
        assert records[0]['phone'] == '555-1234'
        assert records[0]['street_address'] == '123 Main St'
        assert records[1]['entity_id'] == 'ENT002'
        assert records[1]['first_name'] == 'Mary Jane'
        assert records[1]['last_name'] == 'Smith'

    def test_missing_entity_id_column_returns_error(self, test_user):
        """Missing entity_id column should return error at row 1."""
        csv_content = """name,email
John Smith,john@example.com"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 1
        assert 'Missing required column' in errors[0]['errors'][0]
        assert 'entity_id' in errors[0]['errors'][0]

    def test_missing_name_column_returns_error(self, test_user):
        """Missing name column should return error at row 1."""
        csv_content = """entity_id,email
ENT001,john@example.com"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 1
        assert 'Missing required column' in errors[0]['errors'][0]
        assert 'name' in errors[0]['errors'][0]

    def test_empty_entity_id_returns_error(self, test_user):
        """Empty entity_id should return row-level error."""
        csv_content = """entity_id,name,email
,John Smith,john@example.com"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'entity_id is required' in errors[0]['errors'][0]

    def test_empty_name_returns_error(self, test_user):
        """Empty name should return row-level error."""
        csv_content = """entity_id,name,email
ENT001,,john@example.com"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'name is required' in errors[0]['errors'][0]

    def test_duplicate_entity_id_in_file_returns_error(self, test_user):
        """Duplicate entity_id in file should return error."""
        csv_content = """entity_id,name,email
ENT001,John Smith,john@example.com
ENT001,Jane Doe,jane@example.com"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 1  # First one is valid
        assert len(errors) == 1  # Second one errors
        assert errors[0]['row'] == 3
        assert 'Duplicate entity_id' in errors[0]['errors'][0]
        assert 'ENT001' in errors[0]['errors'][0]

    def test_entity_id_exceeds_max_length_returns_error(self, test_user):
        """entity_id exceeding 100 characters should return error."""
        long_entity_id = 'E' * 101
        csv_content = f"""entity_id,name,email
{long_entity_id},John Smith,john@example.com"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'entity_id exceeds maximum length' in errors[0]['errors'][0]

    def test_name_exceeds_max_length_returns_error(self, test_user):
        """name exceeding 300 characters should return error."""
        long_name = 'N' * 301
        csv_content = f"""entity_id,name,email
ENT001,{long_name},john@example.com"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'name exceeds maximum length' in errors[0]['errors'][0]

    def test_invalid_email_format_returns_error(self, test_user):
        """Invalid email format should return error."""
        csv_content = """entity_id,name,email
ENT001,John Smith,not-an-email"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'Invalid email format' in errors[0]['errors'][0]

    def test_email_exceeds_max_length_returns_error(self, test_user):
        """email exceeding 254 characters should return error."""
        long_email = 'a' * 246 + '@test.com'  # 246 + 9 = 255 characters
        csv_content = f"""entity_id,name,email
ENT001,John Smith,{long_email}"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'email exceeds maximum length' in errors[0]['errors'][0]

    def test_phone_exceeds_max_length_returns_error(self, test_user):
        """phone exceeding 20 characters should return error."""
        long_phone = '1' * 21
        csv_content = f"""entity_id,name,email,phone
ENT001,John Smith,john@example.com,{long_phone}"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'phone exceeds maximum length' in errors[0]['errors'][0]

    def test_address_exceeds_max_length_returns_error(self, test_user):
        """address exceeding 255 characters should return error."""
        long_address = 'A' * 256
        csv_content = f"""entity_id,name,email,phone,address
ENT001,John Smith,john@example.com,555-1234,{long_address}"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 1
        assert errors[0]['row'] == 2
        assert 'address exceeds maximum length' in errors[0]['errors'][0]

    def test_formula_character_in_entity_id_returns_error(self, test_user):
        """Formula character in entity_id should return error."""
        csv_content = """entity_id,name,email
=ENT001,John Smith,john@example.com
+ENT002,Jane Doe,jane@example.com
-ENT003,Bob Jones,bob@example.com
@ENT004,Alice Brown,alice@example.com"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 4
        for error in errors:
            assert 'formula character' in error['errors'][0].lower()

    def test_formula_character_in_name_returns_error(self, test_user):
        """Formula character in name should return error."""
        csv_content = """entity_id,name,email
ENT001,=John Smith,john@example.com
ENT002,+Jane Doe,jane@example.com
ENT003,-Bob Jones,bob@example.com
ENT004,@Alice Brown,alice@example.com"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 4
        for error in errors:
            assert 'formula character' in error['errors'][0].lower()

    def test_name_split_two_words(self, test_user):
        """Name 'John Smith' should split to first_name='John', last_name='Smith'."""
        csv_content = """entity_id,name
ENT001,John Smith"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 1
        assert len(errors) == 0
        assert records[0]['first_name'] == 'John'
        assert records[0]['last_name'] == 'Smith'

    def test_name_split_three_words(self, test_user):
        """Name 'Mary Jane Smith' should split to first_name='Mary Jane', last_name='Smith'."""
        csv_content = """entity_id,name
ENT001,Mary Jane Smith"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 1
        assert len(errors) == 0
        assert records[0]['first_name'] == 'Mary Jane'
        assert records[0]['last_name'] == 'Smith'

    def test_name_split_single_word(self, test_user):
        """Name 'Madonna' should split to first_name='Madonna', last_name=''."""
        csv_content = """entity_id,name
ENT001,Madonna"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 1
        assert len(errors) == 0
        assert records[0]['first_name'] == 'Madonna'
        assert records[0]['last_name'] == ''

    def test_entity_type_column_is_ignored(self, test_user):
        """entity_type column should be ignored (no error, not in output)."""
        csv_content = """entity_id,name,entity_type
ENT001,John Smith,person
ENT002,Jane Doe,organization"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 2
        assert len(errors) == 0
        # entity_type should NOT be in the output
        assert 'entity_type' not in records[0]
        assert 'entity_type' not in records[1]

    def test_address_maps_to_street_address(self, test_user):
        """address should map to street_address in output."""
        csv_content = """entity_id,name,address
ENT001,John Smith,123 Main St"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 1
        assert len(errors) == 0
        assert records[0]['street_address'] == '123 Main St'
        assert 'address' not in records[0]

    def test_optional_fields_can_be_empty(self, test_user):
        """Optional fields (email, phone, address) can be empty."""
        csv_content = """entity_id,name,email,phone,address
ENT001,John Smith,,,"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 1
        assert len(errors) == 0
        assert records[0]['email'] == ''
        assert records[0]['phone'] == ''
        assert records[0]['street_address'] == ''

    def test_whitespace_is_trimmed(self, test_user):
        """Whitespace in values should be trimmed."""
        csv_content = """entity_id,name,email
  ENT001  ,  John Smith  ,  john@example.com  """

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 1
        assert len(errors) == 0
        assert records[0]['entity_id'] == 'ENT001'
        assert records[0]['first_name'] == 'John'
        assert records[0]['last_name'] == 'Smith'
        assert records[0]['email'] == 'john@example.com'

    def test_empty_csv_returns_empty_lists(self, test_user):
        """Empty CSV should return empty lists."""
        csv_content = """entity_id,name,email"""

        records, errors = parse_entities_csv(csv_content, test_user)

        assert len(records) == 0
        assert len(errors) == 0


class TestImportEntities:
    """Tests for import_entities function."""

    def test_empty_records_returns_zero_counts(self, test_user, import_run):
        """Empty records should return (0, 0) and update ImportRun."""
        records = []

        created, updated = import_entities(records, test_user, import_run)

        assert created == 0
        assert updated == 0

        import_run.refresh_from_db()
        assert import_run.created_count == 0
        assert import_run.updated_count == 0
        assert import_run.status == ImportStatus.COMPLETED

    def test_creates_contacts_with_owner_and_external_id(self, test_user, import_run):
        """Should create contacts with owner=user and external_id."""
        records = [
            {'entity_id': 'ENT001', 'first_name': 'John', 'last_name': 'Smith',
             'email': 'john@example.com', 'phone': '555-1234', 'street_address': '123 Main St'},
            {'entity_id': 'ENT002', 'first_name': 'Jane', 'last_name': 'Doe',
             'email': 'jane@example.com', 'phone': '555-5678', 'street_address': '456 Oak Ave'},
        ]

        created, updated = import_entities(records, test_user, import_run)

        assert created == 2
        assert updated == 0
        assert Contact.objects.count() == 2

        contact1 = Contact.objects.get(external_id='ENT001')
        assert contact1.owner == test_user
        assert contact1.first_name == 'John'
        assert contact1.last_name == 'Smith'
        assert contact1.email == 'john@example.com'
        assert contact1.phone == '555-1234'
        assert contact1.street_address == '123 Main St'

        import_run.refresh_from_db()
        assert import_run.created_count == 2
        assert import_run.updated_count == 0
        assert import_run.status == ImportStatus.COMPLETED

    def test_updates_existing_contacts_with_matching_owner_external_id(self, test_user, import_run):
        """Should update existing contacts with matching owner+external_id."""
        # Create existing contact
        Contact.objects.create(
            owner=test_user,
            external_id='ENT001',
            first_name='Old',
            last_name='Name',
            email='old@example.com'
        )

        records = [
            {'entity_id': 'ENT001', 'first_name': 'John', 'last_name': 'Smith',
             'email': 'john@example.com', 'phone': '555-1234', 'street_address': '123 Main St'},
        ]

        created, updated = import_entities(records, test_user, import_run)

        assert created == 0
        assert updated == 1
        assert Contact.objects.count() == 1

        contact = Contact.objects.get(external_id='ENT001')
        assert contact.owner == test_user
        assert contact.first_name == 'John'
        assert contact.last_name == 'Smith'
        assert contact.email == 'john@example.com'

        import_run.refresh_from_db()
        assert import_run.created_count == 0
        assert import_run.updated_count == 1
        assert import_run.status == ImportStatus.COMPLETED

    def test_correctly_calculates_created_vs_updated_counts(self, test_user, import_run):
        """Should correctly calculate created vs updated counts."""
        # Create existing contact
        Contact.objects.create(
            owner=test_user,
            external_id='ENT001',
            first_name='Old',
            last_name='Name',
            email='old@example.com'
        )

        records = [
            {'entity_id': 'ENT001', 'first_name': 'John', 'last_name': 'Smith',
             'email': 'john@example.com', 'phone': '', 'street_address': ''},
            {'entity_id': 'ENT002', 'first_name': 'Jane', 'last_name': 'Doe',
             'email': 'jane@example.com', 'phone': '', 'street_address': ''},
        ]

        created, updated = import_entities(records, test_user, import_run)

        assert created == 1
        assert updated == 1
        assert Contact.objects.count() == 2

        import_run.refresh_from_db()
        assert import_run.created_count == 1
        assert import_run.updated_count == 1

    def test_does_not_update_owner_field_on_existing_contacts(self, test_user, admin_user, import_run):
        """Should NOT update owner field on existing contacts."""
        # Create existing contact owned by test_user
        existing = Contact.objects.create(
            owner=test_user,
            external_id='ENT001',
            first_name='Old',
            last_name='Name',
            email='old@example.com'
        )

        # Try to import with different user (should still match on owner+external_id)
        records = [
            {'entity_id': 'ENT001', 'first_name': 'Updated', 'last_name': 'Name',
             'email': 'updated@example.com', 'phone': '', 'street_address': ''},
        ]

        created, updated = import_entities(records, test_user, import_run)

        assert updated == 1
        existing.refresh_from_db()
        assert existing.owner == test_user  # Owner should NOT change
        assert existing.first_name == 'Updated'  # But other fields should update

    def test_sets_import_run_status_to_completed(self, test_user, import_run):
        """Should set ImportRun status to COMPLETED after import."""
        records = [
            {'entity_id': 'ENT001', 'first_name': 'John', 'last_name': 'Smith',
             'email': '', 'phone': '', 'street_address': ''},
        ]

        import_entities(records, test_user, import_run)

        import_run.refresh_from_db()
        assert import_run.status == ImportStatus.COMPLETED

    def test_handles_mixed_create_update_batch_correctly(self, test_user, import_run):
        """Should handle mixed create/update batch correctly."""
        # Create existing contacts
        Contact.objects.create(
            owner=test_user,
            external_id='ENT001',
            first_name='Old1',
            last_name='Name1'
        )
        Contact.objects.create(
            owner=test_user,
            external_id='ENT003',
            first_name='Old3',
            last_name='Name3'
        )

        records = [
            {'entity_id': 'ENT001', 'first_name': 'Updated1', 'last_name': 'Name1',
             'email': '', 'phone': '', 'street_address': ''},
            {'entity_id': 'ENT002', 'first_name': 'New2', 'last_name': 'Name2',
             'email': '', 'phone': '', 'street_address': ''},
            {'entity_id': 'ENT003', 'first_name': 'Updated3', 'last_name': 'Name3',
             'email': '', 'phone': '', 'street_address': ''},
            {'entity_id': 'ENT004', 'first_name': 'New4', 'last_name': 'Name4',
             'email': '', 'phone': '', 'street_address': ''},
        ]

        created, updated = import_entities(records, test_user, import_run)

        assert created == 2
        assert updated == 2
        assert Contact.objects.filter(owner=test_user).count() == 4

    def test_multiple_imports_same_entity_id_updates_not_duplicates(self, test_user, import_run):
        """Multiple imports of same entity_id should update, not create duplicates."""
        records1 = [
            {'entity_id': 'ENT001', 'first_name': 'John', 'last_name': 'Smith',
             'email': 'john@example.com', 'phone': '', 'street_address': ''},
        ]

        # First import
        created1, updated1 = import_entities(records1, test_user, import_run)
        assert created1 == 1
        assert updated1 == 0

        # Second import with same entity_id
        import_run2 = ImportRun.objects.create(
            type=ImportType.ENTITIES,
            status=ImportStatus.PENDING,
            filename='test2.csv',
            uploaded_by=test_user
        )

        records2 = [
            {'entity_id': 'ENT001', 'first_name': 'John', 'last_name': 'Updated',
             'email': 'updated@example.com', 'phone': '', 'street_address': ''},
        ]

        created2, updated2 = import_entities(records2, test_user, import_run2)
        assert created2 == 0
        assert updated2 == 1

        # Should only have one contact
        assert Contact.objects.filter(owner=test_user).count() == 1
        contact = Contact.objects.get(owner=test_user, external_id='ENT001')
        assert contact.last_name == 'Updated'
        assert contact.email == 'updated@example.com'


@pytest.mark.django_db
class TestEntityImportAPIEndpoint:
    """Integration tests for EntityImportView API endpoint."""

    def test_admin_can_import_entities(self, api_client, admin_user):
        """Admin can POST valid CSV and receive import results."""
        api_client.force_authenticate(user=admin_user)
        csv_content = b"""entity_id,name,email
ENT001,John Smith,john@example.com
ENT002,Jane Doe,jane@example.com"""

        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'entities.csv'

        url = reverse('imports:import-entities')
        response = api_client.post(url, {'file': csv_file}, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['created_count'] == 2
        assert response.data['updated_count'] == 0
        assert response.data['error_count'] == 0
        assert 'import_run_id' in response.data
        assert Contact.objects.count() == 2

    def test_non_admin_receives_403(self, api_client, test_user):
        """Non-admin users (staff) should receive 403 Forbidden."""
        api_client.force_authenticate(user=test_user)
        csv_content = b"""entity_id,name
ENT001,John Smith"""

        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'entities.csv'

        url = reverse('imports:import-entities')
        response = api_client.post(url, {'file': csv_file}, format='multipart')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_file_returns_400(self, api_client, admin_user):
        """POST without file should return 400 with detail message."""
        api_client.force_authenticate(user=admin_user)

        url = reverse('imports:import-entities')
        response = api_client.post(url, {}, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == 'No file provided.'

    def test_non_csv_file_returns_400(self, api_client, admin_user):
        """POST with non-CSV file should return 400."""
        api_client.force_authenticate(user=admin_user)
        txt_content = b"This is a text file"

        txt_file = io.BytesIO(txt_content)
        txt_file.name = 'entities.txt'

        url = reverse('imports:import-entities')
        response = api_client.post(url, {'file': txt_file}, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == 'File must be a CSV.'

    def test_validation_errors_return_error_details(self, api_client, admin_user):
        """POST CSV with invalid rows should return error details."""
        api_client.force_authenticate(user=admin_user)
        csv_content = b"""entity_id,name,email
,John Smith,john@example.com
ENT002,Jane Doe,not-an-email"""

        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'entities.csv'

        url = reverse('imports:import-entities')
        response = api_client.post(url, {'file': csv_file}, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['created_count'] == 0
        assert response.data['error_count'] == 2
        assert len(response.data['errors']) == 2
        assert any('entity_id is required' in str(err['errors']) for err in response.data['errors'])
        assert any('Invalid email format' in str(err['errors']) for err in response.data['errors'])

    def test_validate_only_dry_run(self, api_client, admin_user):
        """POST with ?validate_only=true should not create DB records."""
        api_client.force_authenticate(user=admin_user)
        csv_content = b"""entity_id,name,email
ENT001,John Smith,john@example.com
ENT002,Jane Doe,jane@example.com"""

        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'entities.csv'

        url = reverse('imports:import-entities') + '?validate_only=true'
        response = api_client.post(url, {'file': csv_file}, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid_count'] == 2
        assert response.data['error_count'] == 0
        # No DB records created
        assert Contact.objects.count() == 0
        # No import_run_id in response for validate_only
        assert 'import_run_id' not in response.data

    def test_successful_import_returns_counts(self, api_client, admin_user):
        """Successful import should return created_count and updated_count."""
        # Create existing contact
        Contact.objects.create(
            owner=admin_user,
            external_id='ENT001',
            first_name='Old',
            last_name='Name'
        )

        api_client.force_authenticate(user=admin_user)
        csv_content = b"""entity_id,name,email
ENT001,John Smith Updated,john@example.com
ENT002,Jane Doe,jane@example.com"""

        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'entities.csv'

        url = reverse('imports:import-entities')
        response = api_client.post(url, {'file': csv_file}, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['created_count'] == 1
        assert response.data['updated_count'] == 1
        assert response.data['error_count'] == 0
        assert Contact.objects.count() == 2

    def test_import_creates_import_run_record(self, api_client, admin_user):
        """Import should create ImportRun record with type=ENTITIES."""
        api_client.force_authenticate(user=admin_user)
        csv_content = b"""entity_id,name
ENT001,John Smith"""

        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'entities.csv'

        url = reverse('imports:import-entities')
        response = api_client.post(url, {'file': csv_file}, format='multipart')

        assert response.status_code == status.HTTP_200_OK

        # Verify ImportRun exists
        import_run = ImportRun.objects.get(id=response.data['import_run_id'])
        assert import_run.type == ImportType.ENTITIES
        assert import_run.status == ImportStatus.COMPLETED
        assert import_run.filename == 'entities.csv'
        assert import_run.uploaded_by == admin_user
        assert import_run.created_count == 1
        assert import_run.updated_count == 0

    def test_utf8_bom_handled(self, api_client, admin_user):
        """CSV with UTF-8 BOM should parse correctly."""
        api_client.force_authenticate(user=admin_user)
        # UTF-8 BOM followed by CSV content
        csv_content = b'\xef\xbb\xbfentity_id,name,email\nENT001,John Smith,john@example.com'

        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'entities.csv'

        url = reverse('imports:import-entities')
        response = api_client.post(url, {'file': csv_file}, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['created_count'] == 1
        assert response.data['error_count'] == 0
        # Verify contact was created correctly
        contact = Contact.objects.get(external_id='ENT001')
        assert contact.first_name == 'John'
        assert contact.last_name == 'Smith'

    def test_import_run_id_in_response(self, api_client, admin_user):
        """Response should include import_run_id."""
        api_client.force_authenticate(user=admin_user)
        csv_content = b"""entity_id,name
ENT001,John Smith"""

        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'entities.csv'

        url = reverse('imports:import-entities')
        response = api_client.post(url, {'file': csv_file}, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        assert 'import_run_id' in response.data
        assert response.data['import_run_id'] is not None

    def test_template_download(self, api_client, admin_user):
        """GET /templates/entities/ should return CSV template."""
        api_client.force_authenticate(user=admin_user)

        url = reverse('imports:template-entities')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/csv'
        assert response['Content-Disposition'] == 'attachment; filename="entities_template.csv"'
        # Verify template content
        content = response.content.decode('utf-8')
        assert 'entity_id' in content
        assert 'name' in content
        assert 'email' in content

    def test_template_requires_admin(self, api_client, test_user):
        """Non-admin should get 403 on template download."""
        api_client.force_authenticate(user=test_user)

        url = reverse('imports:template-entities')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
