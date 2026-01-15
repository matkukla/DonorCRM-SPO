"""
Service functions for CSV import/export.
"""
import csv
import io
import re
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Tuple

from django.utils import timezone

from apps.contacts.models import Contact
from apps.donations.models import Donation, DonationType, PaymentMethod


# Valid enum values for validation
VALID_DONATION_TYPES = [dt.value for dt in DonationType]
VALID_PAYMENT_METHODS = [pm.value for pm in PaymentMethod]

# Date formats to try when parsing
DATE_FORMATS = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']

# Email validation pattern
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def _validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return True  # Empty email is allowed
    return bool(EMAIL_PATTERN.match(email))


def _parse_amount(amount_str: str) -> Tuple[Decimal, str]:
    """
    Parse amount string to Decimal.
    Returns (amount, error_message).
    """
    if not amount_str:
        return None, 'Amount is required'

    # Clean the string
    cleaned = amount_str.strip().replace('$', '').replace(',', '').replace(' ', '')

    # Check for negative values
    if cleaned.startswith('-'):
        return None, 'Amount cannot be negative'

    try:
        amount = Decimal(cleaned)
        if amount <= 0:
            return None, 'Amount must be greater than zero'
        if amount > Decimal('9999999.99'):
            return None, 'Amount exceeds maximum allowed value'
        return amount, None
    except InvalidOperation:
        return None, f'Invalid amount format: "{amount_str}". Expected a number like "100.00" or "$1,234.56"'


def _parse_date(date_str: str) -> Tuple[datetime.date, str]:
    """
    Parse date string to date object.
    Returns (date, error_message).
    """
    if not date_str:
        return None, 'Date is required'

    cleaned = date_str.strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date(), None
        except ValueError:
            continue

    return None, (
        f'Invalid date format: "{date_str}". '
        f'Accepted formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY'
    )


def parse_contacts_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    """
    Parse contacts CSV and return (valid_records, errors).

    Expected columns: first_name, last_name, email, phone, street_address,
                     city, state, postal_code, country, notes

    Args:
        file_content: CSV file content as string
        user: User performing the import

    Returns:
        Tuple of (valid_records, errors) where:
        - valid_records: List of dicts ready for import
        - errors: List of dicts with row number, errors, and original data
    """
    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except csv.Error as e:
        return [], [{'row': 1, 'errors': [f'Invalid CSV format: {e}'], 'data': {}}]

    valid_records = []
    errors = []
    seen_emails = set()

    required_fields = ['first_name', 'last_name']

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Check required fields
        for field in required_fields:
            value = row.get(field, '').strip()
            if not value:
                row_errors.append(f'Missing required field: {field}')
            elif len(value) > 150:
                row_errors.append(f'{field} exceeds maximum length of 150 characters')

        # Validate email format
        email = row.get('email', '').strip().lower()
        if email:
            if not _validate_email(email):
                row_errors.append(f'Invalid email format: "{email}"')
            elif email in seen_emails:
                row_errors.append(f'Duplicate email in file: {email}')
            elif Contact.objects.filter(owner=user, email=email).exists():
                row_errors.append(f'Contact with email "{email}" already exists in your account')
            else:
                seen_emails.add(email)

        # Validate phone format (basic)
        phone = row.get('phone', '').strip()
        if phone and len(phone) > 20:
            row_errors.append('Phone number exceeds maximum length of 20 characters')

        # Validate postal code
        postal_code = row.get('postal_code', '').strip()
        if postal_code and len(postal_code) > 20:
            row_errors.append('Postal code exceeds maximum length of 20 characters')

        if row_errors:
            errors.append({
                'row': row_num,
                'errors': row_errors,
                'data': dict(row)
            })
        else:
            valid_records.append({
                'first_name': row.get('first_name', '').strip(),
                'last_name': row.get('last_name', '').strip(),
                'email': email,
                'phone': phone,
                'street_address': row.get('street_address', '').strip()[:255],
                'city': row.get('city', '').strip()[:100],
                'state': row.get('state', '').strip()[:50],
                'postal_code': postal_code,
                'country': row.get('country', 'USA').strip()[:100] or 'USA',
                'notes': row.get('notes', '').strip(),
            })

    return valid_records, errors


def import_contacts(records: List[dict], user) -> Tuple[int, List[Contact]]:
    """
    Import contacts from parsed records.

    Args:
        records: List of validated contact dicts
        user: User performing the import

    Returns:
        Tuple of (count, created_contacts)
    """
    created_contacts = []

    for record in records:
        contact = Contact.objects.create(
            owner=user,
            **record
        )
        created_contacts.append(contact)

    return len(created_contacts), created_contacts


def parse_donations_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    """
    Parse donations CSV and return (valid_records, errors).

    Expected columns: contact_email OR (contact_first_name + contact_last_name),
                     amount, date, donation_type, payment_method, external_id, notes

    Args:
        file_content: CSV file content as string
        user: User performing the import

    Returns:
        Tuple of (valid_records, errors) where:
        - valid_records: List of dicts ready for import
        - errors: List of dicts with row number, errors, and original data
    """
    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except csv.Error as e:
        return [], [{'row': 1, 'errors': [f'Invalid CSV format: {e}'], 'data': {}}]

    valid_records = []
    errors = []
    seen_external_ids = set()

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Parse and validate amount
        amount, amount_error = _parse_amount(row.get('amount', ''))
        if amount_error:
            row_errors.append(amount_error)

        # Parse and validate date
        parsed_date, date_error = _parse_date(row.get('date', ''))
        if date_error:
            row_errors.append(date_error)

        # Validate date is not in the future
        if parsed_date and parsed_date > timezone.now().date():
            row_errors.append('Donation date cannot be in the future')

        # Find contact by email or name
        contact = None
        contact_email = row.get('contact_email', '').strip().lower()
        contact_first = row.get('contact_first_name', '').strip()
        contact_last = row.get('contact_last_name', '').strip()

        if contact_email:
            try:
                if user.role in ['admin', 'finance']:
                    contact = Contact.objects.get(email=contact_email)
                else:
                    contact = Contact.objects.get(owner=user, email=contact_email)
            except Contact.DoesNotExist:
                row_errors.append(f'No contact found with email: "{contact_email}"')
            except Contact.MultipleObjectsReturned:
                row_errors.append(
                    f'Multiple contacts found with email: "{contact_email}". '
                    f'Please use contact_first_name and contact_last_name instead.'
                )
        elif contact_first and contact_last:
            try:
                if user.role in ['admin', 'finance']:
                    contact = Contact.objects.get(
                        first_name__iexact=contact_first,
                        last_name__iexact=contact_last
                    )
                else:
                    contact = Contact.objects.get(
                        owner=user,
                        first_name__iexact=contact_first,
                        last_name__iexact=contact_last
                    )
            except Contact.DoesNotExist:
                row_errors.append(f'No contact found named "{contact_first} {contact_last}"')
            except Contact.MultipleObjectsReturned:
                row_errors.append(
                    f'Multiple contacts found named "{contact_first} {contact_last}". '
                    f'Please add contact_email to disambiguate.'
                )
        else:
            row_errors.append(
                'Contact identification required: provide either contact_email '
                'or both contact_first_name and contact_last_name'
            )

        # Validate and check for duplicate external_id
        external_id = row.get('external_id', '').strip()
        if external_id:
            if len(external_id) > 100:
                row_errors.append('External ID exceeds maximum length of 100 characters')
            elif external_id in seen_external_ids:
                row_errors.append(f'Duplicate external_id in file: "{external_id}"')
            elif Donation.objects.filter(external_id=external_id).exists():
                row_errors.append(f'Donation with external_id "{external_id}" already exists')
            else:
                seen_external_ids.add(external_id)

        # Validate donation_type
        donation_type = row.get('donation_type', '').strip().lower() or DonationType.ONE_TIME
        if donation_type and donation_type not in VALID_DONATION_TYPES:
            row_errors.append(
                f'Invalid donation_type: "{donation_type}". '
                f'Valid options: {", ".join(VALID_DONATION_TYPES)}'
            )

        # Validate payment_method
        payment_method = row.get('payment_method', '').strip().lower() or PaymentMethod.CHECK
        if payment_method and payment_method not in VALID_PAYMENT_METHODS:
            row_errors.append(
                f'Invalid payment_method: "{payment_method}". '
                f'Valid options: {", ".join(VALID_PAYMENT_METHODS)}'
            )

        if row_errors:
            errors.append({
                'row': row_num,
                'errors': row_errors,
                'data': dict(row)
            })
        else:
            valid_records.append({
                'contact': contact,
                'amount': amount,
                'date': parsed_date,
                'donation_type': donation_type,
                'payment_method': payment_method,
                'external_id': external_id,
                'notes': row.get('notes', '').strip(),
            })

    return valid_records, errors


def import_donations(records: List[dict]) -> Tuple[int, List[Donation]]:
    """
    Import donations from parsed records.

    Args:
        records: List of validated donation dicts

    Returns:
        Tuple of (count, created_donations)
    """
    created_donations = []
    batch_id = f'import-{uuid.uuid4().hex[:8]}'

    for record in records:
        donation = Donation.objects.create(
            import_batch=batch_id,
            imported_at=timezone.now(),
            **record
        )
        created_donations.append(donation)

    return len(created_donations), created_donations


def export_contacts_csv(queryset) -> str:
    """
    Export contacts to CSV string.

    Args:
        queryset: Contact queryset to export

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    fieldnames = [
        'first_name', 'last_name', 'email', 'phone',
        'street_address', 'city', 'state', 'postal_code', 'country',
        'status', 'total_given', 'gift_count', 'last_gift_date', 'notes'
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for contact in queryset:
        writer.writerow({
            'first_name': contact.first_name,
            'last_name': contact.last_name,
            'email': contact.email,
            'phone': contact.phone,
            'street_address': contact.street_address,
            'city': contact.city,
            'state': contact.state,
            'postal_code': contact.postal_code,
            'country': contact.country,
            'status': contact.status,
            'total_given': str(contact.total_given),
            'gift_count': contact.gift_count,
            'last_gift_date': str(contact.last_gift_date) if contact.last_gift_date else '',
            'notes': contact.notes,
        })

    return output.getvalue()


def export_donations_csv(queryset) -> str:
    """
    Export donations to CSV string.

    Args:
        queryset: Donation queryset to export

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    fieldnames = [
        'contact_first_name', 'contact_last_name', 'contact_email',
        'amount', 'date', 'donation_type', 'payment_method',
        'external_id', 'thanked', 'notes'
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for donation in queryset.select_related('contact'):
        writer.writerow({
            'contact_first_name': donation.contact.first_name,
            'contact_last_name': donation.contact.last_name,
            'contact_email': donation.contact.email,
            'amount': str(donation.amount),
            'date': str(donation.date),
            'donation_type': donation.donation_type,
            'payment_method': donation.payment_method,
            'external_id': donation.external_id,
            'thanked': 'Yes' if donation.thanked else 'No',
            'notes': donation.notes,
        })

    return output.getvalue()


def get_contacts_template() -> str:
    """
    Get CSV template for contact imports.

    Returns:
        CSV header row as string
    """
    return 'first_name,last_name,email,phone,street_address,city,state,postal_code,country,notes\n'


def get_donations_template() -> str:
    """
    Get CSV template for donation imports.

    Returns:
        CSV header row as string
    """
    return 'contact_email,contact_first_name,contact_last_name,amount,date,donation_type,payment_method,external_id,notes\n'
