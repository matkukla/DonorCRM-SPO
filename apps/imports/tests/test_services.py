"""
Tests for import/export services.
"""
from decimal import Decimal

import pytest

from apps.contacts.models import Contact
from apps.contacts.tests.factories import ContactFactory
from apps.donations.models import Donation
from apps.donations.tests.factories import DonationFactory
from apps.imports.services import (
    export_contacts_csv,
    export_donations_csv,
    get_contacts_template,
    get_donations_template,
    import_contacts,
    import_donations,
    parse_contacts_csv,
    parse_donations_csv,
)
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestContactImport:
    """Tests for contact CSV import."""

    def test_parse_valid_contacts_csv(self):
        """Test parsing valid contacts CSV."""
        user = UserFactory()
        csv_content = """first_name,last_name,email,phone
John,Doe,john@example.com,555-1234
Jane,Smith,jane@example.com,555-5678"""

        valid, errors = parse_contacts_csv(csv_content, user)

        assert len(valid) == 2
        assert len(errors) == 0
        assert valid[0]['first_name'] == 'John'
        assert valid[1]['email'] == 'jane@example.com'

    def test_parse_contacts_missing_required_field(self):
        """Test parsing contacts with missing required field."""
        user = UserFactory()
        csv_content = """first_name,last_name,email
John,,john@example.com"""

        valid, errors = parse_contacts_csv(csv_content, user)

        assert len(valid) == 0
        assert len(errors) == 1
        assert 'Missing required field: last_name' in errors[0]['errors']

    def test_parse_contacts_duplicate_email(self):
        """Test parsing contacts with duplicate email."""
        user = UserFactory()
        ContactFactory(owner=user, email='existing@example.com')

        csv_content = """first_name,last_name,email
John,Doe,existing@example.com"""

        valid, errors = parse_contacts_csv(csv_content, user)

        assert len(valid) == 0
        assert len(errors) == 1
        assert 'already exists' in errors[0]['errors'][0]

    def test_import_contacts(self):
        """Test importing valid contact records."""
        user = UserFactory()
        records = [
            {'first_name': 'John', 'last_name': 'Doe', 'email': 'john@example.com',
             'phone': '', 'street_address': '', 'city': '', 'state': '',
             'postal_code': '', 'country': 'USA', 'notes': ''},
        ]

        count, contacts = import_contacts(records, user)

        assert count == 1
        assert len(contacts) == 1
        assert contacts[0].first_name == 'John'
        assert contacts[0].owner == user


@pytest.mark.django_db
class TestDonationImport:
    """Tests for donation CSV import."""

    def test_parse_valid_donations_csv(self):
        """Test parsing valid donations CSV."""
        user = UserFactory(role='fundraiser')
        contact = ContactFactory(owner=user, email='john@example.com')

        csv_content = """contact_email,amount,date
john@example.com,100.00,2024-01-15"""

        valid, errors = parse_donations_csv(csv_content, user)

        assert len(valid) == 1
        assert len(errors) == 0
        assert valid[0]['amount'] == Decimal('100.00')
        assert valid[0]['contact'] == contact

    def test_parse_donations_missing_amount(self):
        """Test parsing donations with missing amount."""
        user = UserFactory()
        csv_content = """contact_email,amount,date
john@example.com,,2024-01-15"""

        valid, errors = parse_donations_csv(csv_content, user)

        assert len(valid) == 0
        assert len(errors) == 1
        assert 'Amount is required' in errors[0]['errors']

    def test_parse_donations_invalid_date(self):
        """Test parsing donations with invalid date."""
        user = UserFactory()
        ContactFactory(owner=user, email='john@example.com')

        csv_content = """contact_email,amount,date
john@example.com,100,not-a-date"""

        valid, errors = parse_donations_csv(csv_content, user)

        assert len(valid) == 0
        assert len(errors) == 1
        assert 'Invalid date format' in errors[0]['errors'][0]

    def test_parse_donations_contact_not_found(self):
        """Test parsing donations with non-existent contact."""
        user = UserFactory()
        csv_content = """contact_email,amount,date
nonexistent@example.com,100,2024-01-15"""

        valid, errors = parse_donations_csv(csv_content, user)

        assert len(valid) == 0
        assert len(errors) == 1
        assert 'No contact found' in errors[0]['errors'][0]

    def test_parse_donations_by_name(self):
        """Test parsing donations using contact name."""
        user = UserFactory(role='fundraiser')
        contact = ContactFactory(owner=user, first_name='John', last_name='Doe')

        csv_content = """contact_first_name,contact_last_name,amount,date
John,Doe,50.00,2024-02-20"""

        valid, errors = parse_donations_csv(csv_content, user)

        assert len(valid) == 1
        assert valid[0]['contact'] == contact

    def test_import_donations(self):
        """Test importing valid donation records."""
        contact = ContactFactory()
        records = [
            {
                'contact': contact,
                'amount': Decimal('100.00'),
                'date': '2024-01-15',
                'donation_type': 'one_time',
                'payment_method': 'check',
                'external_id': '',
                'notes': ''
            }
        ]

        count, donations = import_donations(records)

        assert count == 1
        assert len(donations) == 1
        assert donations[0].amount == Decimal('100.00')
        assert donations[0].import_batch is not None


@pytest.mark.django_db
class TestContactExport:
    """Tests for contact CSV export."""

    def test_export_contacts_csv(self):
        """Test exporting contacts to CSV."""
        user = UserFactory()
        ContactFactory(owner=user, first_name='John', last_name='Doe', email='john@example.com')
        ContactFactory(owner=user, first_name='Jane', last_name='Smith', email='jane@example.com')

        queryset = Contact.objects.filter(owner=user)
        csv_output = export_contacts_csv(queryset)

        assert 'first_name,last_name,email' in csv_output
        assert 'John,Doe,john@example.com' in csv_output
        assert 'Jane,Smith,jane@example.com' in csv_output


@pytest.mark.django_db
class TestDonationExport:
    """Tests for donation CSV export."""

    def test_export_donations_csv(self):
        """Test exporting donations to CSV."""
        contact = ContactFactory(first_name='John', last_name='Doe', email='john@example.com')
        DonationFactory(contact=contact, amount=Decimal('100.00'))

        queryset = Donation.objects.all()
        csv_output = export_donations_csv(queryset)

        assert 'contact_first_name,contact_last_name' in csv_output
        assert 'John,Doe' in csv_output
        assert '100.00' in csv_output


class TestTemplates:
    """Tests for CSV templates."""

    def test_get_contacts_template(self):
        """Test getting contacts CSV template."""
        template = get_contacts_template()
        assert 'first_name' in template
        assert 'last_name' in template
        assert 'email' in template

    def test_get_donations_template(self):
        """Test getting donations CSV template."""
        template = get_donations_template()
        assert 'contact_email' in template
        assert 'amount' in template
        assert 'date' in template
