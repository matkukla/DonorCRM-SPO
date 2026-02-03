"""
Service functions for CSV import/export.
"""
import csv
import io
import logging
import re
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Tuple

from django.utils import timezone

from apps.contacts.models import Contact
from apps.donations.models import Donation, DonationType, PaymentMethod
from apps.imports.models import Fund, ImportStatus
from apps.pledges.models import Pledge, PledgeFrequency, PledgeStatus

logger = logging.getLogger(__name__)


# Valid enum values for validation
VALID_DONATION_TYPES = [dt.value for dt in DonationType]
VALID_PAYMENT_METHODS = [pm.value for pm in PaymentMethod]
VALID_FUND_STATUSES = ['active', 'inactive', 'closed']
VALID_PLEDGE_FREQUENCIES = [f.value for f in PledgeFrequency]  # ['monthly', 'quarterly', 'semi_annual', 'annual']
VALID_PLEDGE_STATUSES = [s.value for s in PledgeStatus]        # ['active', 'paused', 'completed', 'cancelled']

# Formula characters for CSV injection prevention
FORMULA_PREFIXES = ('=', '+', '-', '@')

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
    logger.info(f'Starting contact import: {len(records)} records for user {user.email}')
    created_contacts = []

    for record in records:
        contact = Contact.objects.create(
            owner=user,
            **record
        )
        created_contacts.append(contact)

    logger.info(f'Contact import completed: {len(created_contacts)} contacts created')
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
    logger.info(f'Starting donation import: {len(records)} records')
    created_donations = []
    batch_id = f'import-{uuid.uuid4().hex[:8]}'

    for record in records:
        donation = Donation.objects.create(
            import_batch=batch_id,
            imported_at=timezone.now(),
            **record
        )
        created_donations.append(donation)

    logger.info(f'Donation import completed: {len(created_donations)} donations created (batch {batch_id})')
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


def get_funds_template() -> str:
    """
    Get CSV template for fund imports.

    Returns:
        CSV header row as string
    """
    return 'fund_id,name,status\n'


def parse_funds_csv(file_content: str) -> Tuple[List[dict], List[dict]]:
    """
    Parse funds CSV and return (valid_records, errors).

    Expected columns: fund_id, name, status (optional, defaults to 'active')

    Args:
        file_content: CSV file content as string

    Returns:
        Tuple of (valid_records, errors) where:
        - valid_records: List of dicts ready for import
        - errors: List of dicts with row number, errors, and original data
    """
    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except csv.Error as e:
        return [], [{'row': 1, 'errors': [f'Invalid CSV format: {e}'], 'data': {}}]

    # Validate required column headers before processing rows
    if reader.fieldnames is None:
        return [], [{'row': 1, 'errors': ['CSV file is empty or has no headers'], 'data': {}}]

    required_columns = ['fund_id', 'name']
    missing_columns = [col for col in required_columns if col not in reader.fieldnames]
    if missing_columns:
        return [], [{
            'row': 1,
            'errors': [f'Missing required column: {", ".join(missing_columns)}'],
            'data': {}
        }]

    valid_records = []
    errors = []
    seen_fund_ids = set()

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Get and trim values
        fund_id = row.get('fund_id', '').strip()
        name = row.get('name', '').strip()
        status = row.get('status', '').strip().lower() or 'active'

        # Validate fund_id
        if not fund_id:
            row_errors.append('fund_id is required')
        elif len(fund_id) > 100:
            row_errors.append('fund_id exceeds maximum length of 100 characters')
        elif fund_id.startswith(FORMULA_PREFIXES):
            row_errors.append(f'fund_id cannot start with formula character ({fund_id[0]})')
        elif fund_id in seen_fund_ids:
            row_errors.append(f'Duplicate fund_id in file: {fund_id}')
        else:
            seen_fund_ids.add(fund_id)

        # Validate name
        if not name:
            row_errors.append('name is required')
        elif len(name) > 255:
            row_errors.append('name exceeds maximum length of 255 characters')
        elif name.startswith(FORMULA_PREFIXES):
            row_errors.append(f'name cannot start with formula character ({name[0]})')

        # Validate status
        if status not in VALID_FUND_STATUSES:
            row_errors.append(
                f'Invalid status: "{status}". Valid options: {", ".join(VALID_FUND_STATUSES)}'
            )

        if row_errors:
            errors.append({
                'row': row_num,
                'errors': row_errors,
                'data': dict(row)
            })
        else:
            valid_records.append({
                'fund_id': fund_id,
                'name': name,
                'status': status,
            })

    return valid_records, errors


def import_funds(records: List[dict], import_run) -> Tuple[int, int]:
    """
    Import funds from parsed records using bulk upsert.

    Args:
        records: List of validated fund dicts with keys: fund_id, name, status
        import_run: ImportRun instance to update with results

    Returns:
        Tuple of (created_count, updated_count)
    """
    logger.info(f'Starting fund import: {len(records)} records for import run {import_run.id}')

    if not records:
        # Update import run for empty records
        import_run.created_count = 0
        import_run.updated_count = 0
        import_run.status = ImportStatus.COMPLETED
        import_run.save()
        return 0, 0

    # Get existing external_ids to calculate created vs updated
    external_ids = [record['fund_id'] for record in records]
    existing_external_ids = set(
        Fund.objects.filter(external_id__in=external_ids).values_list('external_id', flat=True)
    )

    # Prepare Fund objects for bulk create
    fund_objects = [
        Fund(
            external_id=record['fund_id'],
            name=record['name'],
            status=record['status'],
            owner=None  # Funds are org-wide
        )
        for record in records
    ]

    # Bulk upsert
    Fund.objects.bulk_create(
        fund_objects,
        update_conflicts=True,
        unique_fields=['external_id'],
        update_fields=['name', 'status']
    )

    # Calculate counts
    created_count = sum(1 for record in records if record['fund_id'] not in existing_external_ids)
    updated_count = sum(1 for record in records if record['fund_id'] in existing_external_ids)

    # Update import run
    import_run.created_count = created_count
    import_run.updated_count = updated_count
    import_run.status = ImportStatus.COMPLETED
    import_run.save()

    logger.info(f'Fund import completed: {created_count} created, {updated_count} updated')
    return created_count, updated_count


def get_entities_template() -> str:
    """
    Get CSV template for entity imports.

    Returns:
        CSV header row as string
    """
    return 'entity_id,name,email,phone,address,entity_type\n'


def parse_entities_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    """
    Parse entities CSV and return (valid_records, errors).

    Expected columns: entity_id, name, email (optional), phone (optional),
                     address (optional), entity_type (ignored)

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

    # Validate required column headers before processing rows
    if reader.fieldnames is None:
        return [], [{'row': 1, 'errors': ['CSV file is empty or has no headers'], 'data': {}}]

    required_columns = ['entity_id', 'name']
    missing_columns = [col for col in required_columns if col not in reader.fieldnames]
    if missing_columns:
        return [], [{
            'row': 1,
            'errors': [f'Missing required column: {", ".join(missing_columns)}'],
            'data': {}
        }]

    valid_records = []
    errors = []
    seen_entity_ids = set()

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Get and trim values
        entity_id = row.get('entity_id', '').strip()
        name = row.get('name', '').strip()
        email = row.get('email', '').strip()
        phone = row.get('phone', '').strip()
        address = row.get('address', '').strip()
        # entity_type is intentionally ignored - Contact has no such field

        # Validate entity_id
        if not entity_id:
            row_errors.append('entity_id is required')
        elif len(entity_id) > 100:
            row_errors.append('entity_id exceeds maximum length of 100 characters')
        elif entity_id.startswith(FORMULA_PREFIXES):
            row_errors.append(f'entity_id cannot start with formula character ({entity_id[0]})')
        elif entity_id in seen_entity_ids:
            row_errors.append(f'Duplicate entity_id in file: {entity_id}')
        else:
            seen_entity_ids.add(entity_id)

        # Validate name
        if not name:
            row_errors.append('name is required')
        elif len(name) > 300:
            row_errors.append('name exceeds maximum length of 300 characters')
        elif name.startswith(FORMULA_PREFIXES):
            row_errors.append(f'name cannot start with formula character ({name[0]})')

        # Split name into first_name and last_name
        # Last word is last_name, everything else is first_name
        first_name = ''
        last_name = ''
        if name and not row_errors:
            parts = name.split()
            if len(parts) > 1:
                first_name = ' '.join(parts[:-1])
                last_name = parts[-1]
            else:
                first_name = parts[0] if parts else ''
                last_name = ''

        # Validate email (optional)
        if email:
            if len(email) > 254:
                row_errors.append('email exceeds maximum length of 254 characters')
            elif not _validate_email(email):
                row_errors.append(f'Invalid email format: "{email}"')

        # Validate phone (optional)
        if phone and len(phone) > 20:
            row_errors.append('phone exceeds maximum length of 20 characters')

        # Validate address (optional) - maps to street_address
        if address and len(address) > 255:
            row_errors.append('address exceeds maximum length of 255 characters')

        if row_errors:
            errors.append({
                'row': row_num,
                'errors': row_errors,
                'data': dict(row)
            })
        else:
            valid_records.append({
                'entity_id': entity_id,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'street_address': address,  # address maps to street_address
            })

    return valid_records, errors


def import_entities(records: List[dict], user, import_run) -> Tuple[int, int]:
    """
    Import entities from parsed records using bulk upsert.

    Args:
        records: List of validated entity dicts with keys: entity_id, first_name,
                last_name, email, phone, street_address
        user: User performing the import (owner of contacts)
        import_run: ImportRun instance to update with results

    Returns:
        Tuple of (created_count, updated_count)
    """
    logger.info(f'Starting entity import: {len(records)} records for user {user.email}')

    if not records:
        # Update import run for empty records
        import_run.created_count = 0
        import_run.updated_count = 0
        import_run.status = ImportStatus.COMPLETED
        import_run.save()
        return 0, 0

    # Get existing external_ids for this user to calculate created vs updated
    external_ids = [record['entity_id'] for record in records]
    existing_external_ids = set(
        Contact.objects.filter(
            owner=user,
            external_id__in=external_ids
        ).values_list('external_id', flat=True)
    )

    # Upsert contacts individually
    # Note: Using update_or_create instead of bulk_create with update_conflicts
    # because the Contact model has a conditional unique constraint which
    # doesn't work with ON CONFLICT in PostgreSQL/Django
    created_count = 0
    updated_count = 0

    for record in records:
        contact, created = Contact.objects.update_or_create(
            owner=user,
            external_id=record['entity_id'],
            defaults={
                'first_name': record['first_name'],
                'last_name': record['last_name'],
                'email': record.get('email', ''),
                'phone': record.get('phone', ''),
                'street_address': record.get('street_address', '')
            }
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    # Update import run
    import_run.created_count = created_count
    import_run.updated_count = updated_count
    import_run.status = ImportStatus.COMPLETED
    import_run.save()

    logger.info(f'Entity import completed: {created_count} created, {updated_count} updated')
    return created_count, updated_count


def get_transactions_template() -> str:
    """
    Get CSV template for transaction imports.

    Returns:
        CSV header row as string
    """
    return 'transaction_id,entity_id,fund_id,amount,posted_date\n'


def parse_transactions_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    """
    Parse transactions CSV and return (valid_records, errors).

    Expected columns: transaction_id, entity_id, fund_id, amount, posted_date

    STRICT MODE: If ANY orphan FK references found (entity_id not in Contact or
    fund_id not in Fund), returns empty valid_records and all errors.

    Args:
        file_content: CSV file content as string
        user: User performing import (for owner-scoped Contact lookup)

    Returns:
        Tuple of (valid_records, errors)
    """
    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except csv.Error as e:
        return [], [{'row': 1, 'errors': [f'Invalid CSV format: {e}'], 'data': {}}]

    # Validate required column headers before processing rows
    if reader.fieldnames is None:
        return [], [{'row': 1, 'errors': ['CSV file is empty or has no headers'], 'data': {}}]

    required_columns = ['transaction_id', 'entity_id', 'fund_id', 'amount', 'posted_date']
    missing_columns = [col for col in required_columns if col not in reader.fieldnames]
    if missing_columns:
        return [], [{
            'row': 1,
            'errors': [f'Missing required column: {", ".join(missing_columns)}'],
            'data': {}
        }]

    valid_records = []
    errors = []
    seen_transaction_ids = set()

    # Collect all entity_ids and fund_ids for batch validation
    all_entity_ids = set()
    all_fund_ids = set()
    pending_records = []  # Store records with their row numbers for FK validation

    # First pass: validate row format, collect FK references
    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Get and trim values
        transaction_id = row.get('transaction_id', '').strip()
        entity_id = row.get('entity_id', '').strip()
        fund_id = row.get('fund_id', '').strip()

        # Validate transaction_id
        if not transaction_id:
            row_errors.append('transaction_id is required')
        elif len(transaction_id) > 100:
            row_errors.append('transaction_id exceeds maximum length of 100 characters')
        elif transaction_id.startswith(FORMULA_PREFIXES):
            row_errors.append(f'transaction_id cannot start with formula character ({transaction_id[0]})')
        elif transaction_id in seen_transaction_ids:
            row_errors.append(f'Duplicate transaction_id in file: {transaction_id}')
        else:
            seen_transaction_ids.add(transaction_id)

        # Validate entity_id
        if not entity_id:
            row_errors.append('entity_id is required')
        else:
            all_entity_ids.add(entity_id)

        # Validate fund_id
        if not fund_id:
            row_errors.append('fund_id is required')
        else:
            all_fund_ids.add(fund_id)

        # Parse amount
        amount, amount_error = _parse_amount(row.get('amount', ''))
        if amount_error:
            row_errors.append(amount_error)

        # Parse date
        posted_date, date_error = _parse_date(row.get('posted_date', ''))
        if date_error:
            row_errors.append(date_error)

        if row_errors:
            errors.append({
                'row': row_num,
                'errors': row_errors,
                'data': dict(row)
            })
        else:
            record = {
                'transaction_id': transaction_id,
                'entity_id': entity_id,
                'fund_id': fund_id,
                'amount': amount,
                'posted_date': posted_date
            }
            valid_records.append(record)
            pending_records.append((row_num, record))

    # Second pass: Batch validate foreign key references
    if valid_records and not errors:
        # Validate entity_ids exist in Contact.external_id for this owner
        existing_entity_ids = set(
            Contact.objects.filter(
                owner=user,
                external_id__in=all_entity_ids
            ).values_list('external_id', flat=True)
        )

        missing_entity_ids = all_entity_ids - existing_entity_ids

        # Validate fund_ids exist in Fund.external_id (globally unique)
        existing_fund_ids = set(
            Fund.objects.filter(
                external_id__in=all_fund_ids
            ).values_list('external_id', flat=True)
        )

        missing_fund_ids = all_fund_ids - existing_fund_ids

        # If any orphan references, add errors with row numbers
        if missing_entity_ids or missing_fund_ids:
            fk_errors = []
            for row_num, record in pending_records:
                row_fk_errors = []
                if record['entity_id'] in missing_entity_ids:
                    row_fk_errors.append(f"entity_id '{record['entity_id']}' not found in Contacts")
                if record['fund_id'] in missing_fund_ids:
                    row_fk_errors.append(f"fund_id '{record['fund_id']}' not found in Funds")

                if row_fk_errors:
                    fk_errors.append({
                        'row': row_num,
                        'errors': row_fk_errors,
                        'data': record
                    })

            # Add FK errors to errors list (limit to first 20)
            errors.extend(fk_errors[:20])

            # Clear valid_records if any orphan references (strict mode)
            valid_records = []

    # Limit errors to first 20 (consistent with Phase 8/9)
    errors = errors[:20]

    return valid_records, errors


def import_transactions(records: List[dict], user, import_run) -> Tuple[int, int]:
    """
    Import transactions from parsed records.

    Uses update_or_create because Donation.external_id has conditional unique
    constraint (same issue as Contact.external_id in Phase 9).

    Args:
        records: List of validated transaction dicts
        user: User performing import (for Contact FK lookup)
        import_run: ImportRun instance to update

    Returns:
        Tuple of (created_count, updated_count)
    """
    logger.info(f'Starting transaction import: {len(records)} records for user {user.email}')

    if not records:
        # Update import run for empty records
        import_run.created_count = 0
        import_run.updated_count = 0
        import_run.status = ImportStatus.COMPLETED
        import_run.save()
        return 0, 0

    # Pre-fetch Contact and Fund objects by external_id for FK resolution
    entity_ids = [r['entity_id'] for r in records]
    fund_ids = [r['fund_id'] for r in records]

    # Build lookup dicts for FK resolution
    contacts_by_external_id = {
        c.external_id: c
        for c in Contact.objects.filter(
            owner=user,
            external_id__in=entity_ids
        )
    }

    funds_by_external_id = {
        f.external_id: f
        for f in Fund.objects.filter(external_id__in=fund_ids)
    }

    # Get existing external_ids to calculate created vs updated
    transaction_ids = [r['transaction_id'] for r in records]
    existing_transaction_ids = set(
        Donation.objects.filter(
            external_id__in=transaction_ids
        ).values_list('external_id', flat=True)
    )

    # Upsert donations individually using update_or_create
    # Note: Using update_or_create instead of bulk_create with update_conflicts
    # because the Donation model has a conditional unique constraint which
    # doesn't work reliably with ON CONFLICT in PostgreSQL/Django
    created_count = 0
    updated_count = 0

    for record in records:
        donation, created = Donation.objects.update_or_create(
            external_id=record['transaction_id'],
            defaults={
                'contact': contacts_by_external_id[record['entity_id']],
                'fund': funds_by_external_id[record['fund_id']],
                'amount': record['amount'],
                'date': record['posted_date'],
                'donation_type': DonationType.ONE_TIME,
                'payment_method': PaymentMethod.OTHER
            }
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    # Update import run
    import_run.created_count = created_count
    import_run.updated_count = updated_count
    import_run.status = ImportStatus.COMPLETED
    import_run.save()

    logger.info(f'Transaction import completed: {created_count} created, {updated_count} updated')
    return created_count, updated_count


def update_contact_stats_for_import(records: List[dict], user):
    """
    Update denormalized giving stats for contacts affected by import.

    Args:
        records: List of imported transaction dicts (need entity_id)
        user: User who owns the contacts
    """
    # Identify unique contact external_ids affected by this import
    affected_entity_ids = set(r['entity_id'] for r in records)

    # Fetch affected Contact objects
    affected_contacts = Contact.objects.filter(
        owner=user,
        external_id__in=affected_entity_ids
    )

    # Update stats for each affected contact
    count = 0
    for contact in affected_contacts:
        contact.update_giving_stats()
        count += 1

    logger.info(f'Updated giving stats for {count} contacts')


def get_pledges_template() -> str:
    """
    Get CSV template for pledge imports.

    Returns:
        CSV header row as string
    """
    return 'pledge_id,entity_id,fund_id,amount,cadence,status,start_date\n'


def parse_pledges_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    """
    Parse pledges CSV and return (valid_records, errors).

    Expected columns: pledge_id, entity_id, fund_id (optional), amount, cadence, status, start_date

    STRICT MODE: If ANY orphan FK references found (entity_id not in Contact or
    fund_id provided but not in Fund), returns empty valid_records and all errors.

    Key differences from parse_transactions_csv:
    - fund_id is OPTIONAL (validate only if provided)
    - cadence and status require enum validation
    - CSV 'cadence' maps to Pledge.frequency field
    - start_date CAN be in future (pledges can start later)

    Args:
        file_content: CSV file content as string
        user: User performing import (for owner-scoped Contact lookup)

    Returns:
        Tuple of (valid_records, errors)
    """
    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except csv.Error as e:
        return [], [{'row': 1, 'errors': [f'Invalid CSV format: {e}'], 'data': {}}]

    # Validate required column headers before processing rows
    if reader.fieldnames is None:
        return [], [{'row': 1, 'errors': ['CSV file is empty or has no headers'], 'data': {}}]

    required_columns = ['pledge_id', 'entity_id', 'amount', 'cadence', 'status', 'start_date']
    missing_columns = [col for col in required_columns if col not in reader.fieldnames]
    if missing_columns:
        return [], [{
            'row': 1,
            'errors': [f'Missing required column: {", ".join(missing_columns)}'],
            'data': {}
        }]

    valid_records = []
    errors = []
    seen_pledge_ids = set()

    # Collect all entity_ids and fund_ids for batch validation
    all_entity_ids = set()
    all_fund_ids = set()
    pending_records = []  # Store records with their row numbers for FK validation

    # First pass: validate row format, validate enums, collect FK references
    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Get and trim values
        pledge_id = row.get('pledge_id', '').strip()
        entity_id = row.get('entity_id', '').strip()
        fund_id = row.get('fund_id', '').strip()
        cadence = row.get('cadence', '').strip().lower()
        status = row.get('status', '').strip().lower()

        # Validate pledge_id
        if not pledge_id:
            row_errors.append('pledge_id is required')
        elif len(pledge_id) > 100:
            row_errors.append('pledge_id exceeds maximum length of 100 characters')
        elif pledge_id.startswith(FORMULA_PREFIXES):
            row_errors.append(f'pledge_id cannot start with formula character ({pledge_id[0]})')
        elif pledge_id in seen_pledge_ids:
            row_errors.append(f'Duplicate pledge_id in file: {pledge_id}')
        else:
            seen_pledge_ids.add(pledge_id)

        # Validate entity_id
        if not entity_id:
            row_errors.append('entity_id is required')
        else:
            all_entity_ids.add(entity_id)

        # Validate fund_id (OPTIONAL - only collect if provided)
        if fund_id:
            all_fund_ids.add(fund_id)

        # Validate cadence (required, must be valid enum)
        if not cadence:
            row_errors.append('cadence is required')
        elif cadence not in VALID_PLEDGE_FREQUENCIES:
            row_errors.append(
                f'Invalid cadence: "{cadence}". '
                f'Valid options: {", ".join(VALID_PLEDGE_FREQUENCIES)}'
            )

        # Validate status (required, must be valid enum)
        if not status:
            row_errors.append('status is required')
        elif status not in VALID_PLEDGE_STATUSES:
            row_errors.append(
                f'Invalid status: "{status}". '
                f'Valid options: {", ".join(VALID_PLEDGE_STATUSES)}'
            )

        # Parse amount
        amount, amount_error = _parse_amount(row.get('amount', ''))
        if amount_error:
            row_errors.append(amount_error)

        # Parse date (note: start_date CAN be in future for pledges)
        start_date, date_error = _parse_date(row.get('start_date', ''))
        if date_error:
            row_errors.append(date_error)

        if row_errors:
            errors.append({
                'row': row_num,
                'errors': row_errors,
                'data': dict(row)
            })
        else:
            record = {
                'pledge_id': pledge_id,
                'entity_id': entity_id,
                'fund_id': fund_id,  # May be empty string
                'amount': amount,
                'cadence': cadence,  # Keep CSV terminology in validated records
                'status': status,
                'start_date': start_date
            }
            valid_records.append(record)
            pending_records.append((row_num, record))

    # Second pass: Batch validate foreign key references
    if valid_records and not errors:
        # Validate entity_ids exist in Contact.external_id for this owner
        existing_entity_ids = set(
            Contact.objects.filter(
                owner=user,
                external_id__in=all_entity_ids
            ).values_list('external_id', flat=True)
        )

        missing_entity_ids = all_entity_ids - existing_entity_ids

        # Validate fund_ids exist in Fund.external_id (only if any fund_ids provided)
        missing_fund_ids = set()
        if all_fund_ids:
            existing_fund_ids = set(
                Fund.objects.filter(
                    external_id__in=all_fund_ids
                ).values_list('external_id', flat=True)
            )
            missing_fund_ids = all_fund_ids - existing_fund_ids

        # If any orphan references, add errors with row numbers
        if missing_entity_ids or missing_fund_ids:
            fk_errors = []
            for row_num, record in pending_records:
                row_fk_errors = []
                if record['entity_id'] in missing_entity_ids:
                    row_fk_errors.append(f"entity_id '{record['entity_id']}' not found in Contacts")
                if record['fund_id'] and record['fund_id'] in missing_fund_ids:
                    row_fk_errors.append(f"fund_id '{record['fund_id']}' not found in Funds")

                if row_fk_errors:
                    fk_errors.append({
                        'row': row_num,
                        'errors': row_fk_errors,
                        'data': record
                    })

            # Add FK errors to errors list (limit to first 20)
            errors.extend(fk_errors[:20])

            # Clear valid_records if any orphan references (strict mode)
            valid_records = []

    # Limit errors to first 20 (consistent with Phase 8/9/10)
    errors = errors[:20]

    return valid_records, errors


def import_pledges(records: List[dict], user, import_run) -> Tuple[int, int]:
    """
    Import pledges from parsed records.

    Uses update_or_create because Pledge.external_id has conditional unique
    constraint (globally unique, not owner-scoped like Contact).

    Note: NO Contact stats update needed. Contact.has_active_pledge and
    Contact.monthly_pledge_amount are computed properties that query
    pledges.filter(status='active') directly.

    Args:
        records: List of validated pledge dicts
        user: User performing import (for Contact FK lookup)
        import_run: ImportRun instance to update

    Returns:
        Tuple of (created_count, updated_count)
    """
    logger.info(f'Starting pledge import: {len(records)} records for user {user.email}')

    if not records:
        # Update import run for empty records
        import_run.created_count = 0
        import_run.updated_count = 0
        import_run.status = ImportStatus.COMPLETED
        import_run.save()
        return 0, 0

    # Pre-fetch Contact and Fund objects by external_id for FK resolution
    entity_ids = [r['entity_id'] for r in records]
    fund_ids = [r['fund_id'] for r in records if r['fund_id']]  # Only non-empty fund_ids

    # Build lookup dicts for FK resolution
    contacts_by_external_id = {
        c.external_id: c
        for c in Contact.objects.filter(
            owner=user,
            external_id__in=entity_ids
        )
    }

    # Only fetch funds if any fund_ids provided
    funds_by_external_id = {}
    if fund_ids:
        funds_by_external_id = {
            f.external_id: f
            for f in Fund.objects.filter(external_id__in=fund_ids)
        }

    # Upsert pledges individually using update_or_create
    # Note: Using update_or_create instead of bulk_create with update_conflicts
    # because the Pledge model has a conditional unique constraint which
    # doesn't work reliably with ON CONFLICT in PostgreSQL/Django
    created_count = 0
    updated_count = 0

    for record in records:
        fund = None
        if record['fund_id']:  # Only lookup if fund_id provided
            fund = funds_by_external_id.get(record['fund_id'])

        pledge, created = Pledge.objects.update_or_create(
            external_id=record['pledge_id'],
            defaults={
                'contact': contacts_by_external_id[record['entity_id']],
                'fund': fund,  # May be None
                'amount': record['amount'],
                'frequency': record['cadence'],  # CSV 'cadence' -> model 'frequency'
                'status': record['status'],
                'start_date': record['start_date']
            }
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    # Update import run
    import_run.created_count = created_count
    import_run.updated_count = updated_count
    import_run.status = ImportStatus.COMPLETED
    import_run.save()

    logger.info(f'Pledge import completed: {created_count} created, {updated_count} updated')

    # NO update_contact_stats_for_import call needed
    # Contact.has_active_pledge and Contact.monthly_pledge_amount are computed properties

    return created_count, updated_count
