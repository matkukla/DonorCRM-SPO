"""
Generic CSV import services for contacts and donations.

Provides orchestrator functions for importing contacts and donations from
any CSV format (not just Raiser's Edge) with configurable matching strategy
(name, email, or external ID), SHA256 dedup, and row-level error reporting.

Returns ImportBatch in the same response shape as RE imports so the existing
ImportResultBanner works without modification.
"""
import csv
import hashlib
import io
import logging

from django.db import transaction

from apps.contacts.models import Contact
from apps.gifts.models import Gift
from apps.imports.models import Fund, ImportBatch, ImportBatchStatus, ImportBatchType
from apps.imports.re_services import (
    _build_header_mapping,
    _parse_amount_to_cents,
    _parse_date,
    _sanitize_field,
    check_duplicate_import,
    decode_csv_bytes,
    merge_contact_fields,
)
from apps.users.models import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Generic contact header aliases
# ---------------------------------------------------------------------------

# Maps lowercase alias -> canonical field name
GENERIC_CONTACT_HEADER_ALIASES: dict[str, str] = {
    # first_name
    'first_name': 'first_name',
    'first name': 'first_name',
    'firstname': 'first_name',
    'fname': 'first_name',
    'given name': 'first_name',
    'given_name': 'first_name',
    # last_name
    'last_name': 'last_name',
    'last name': 'last_name',
    'lastname': 'last_name',
    'lname': 'last_name',
    'surname': 'last_name',
    'family name': 'last_name',
    'family_name': 'last_name',
    # email
    'email': 'email',
    'email_address': 'email',
    'email address': 'email',
    'e-mail': 'email',
    # phone
    'phone': 'phone',
    'phone_number': 'phone',
    'phone number': 'phone',
    'mobile': 'phone',
    'cell': 'phone',
    # external_id
    'external_id': 'external_id',
    'id': 'external_id',
    'contact_id': 'external_id',
    # organization_name
    'organization': 'organization_name',
    'org_name': 'organization_name',
    'organization_name': 'organization_name',
    'company': 'organization_name',
    # street_address
    'street_address': 'street_address',
    'address': 'street_address',
    'street': 'street_address',
    # city
    'city': 'city',
    # state
    'state': 'state',
    'province': 'state',
    # postal_code
    'postal_code': 'postal_code',
    'zip': 'postal_code',
    'zip_code': 'postal_code',
    'zipcode': 'postal_code',
    # country
    'country': 'country',
    # notes
    'notes': 'notes',
    'note': 'notes',
    'comments': 'notes',
}


# ---------------------------------------------------------------------------
# Generic donation header aliases
# ---------------------------------------------------------------------------

GENERIC_DONATION_HEADER_ALIASES: dict[str, str] = {
    # contact_first_name
    'contact_first_name': 'contact_first_name',
    'first_name': 'contact_first_name',
    'first name': 'contact_first_name',
    'firstname': 'contact_first_name',
    'donor_first_name': 'contact_first_name',
    'donor first name': 'contact_first_name',
    # contact_last_name
    'contact_last_name': 'contact_last_name',
    'last_name': 'contact_last_name',
    'last name': 'contact_last_name',
    'lastname': 'contact_last_name',
    'donor_last_name': 'contact_last_name',
    'donor last name': 'contact_last_name',
    # contact_email
    'contact_email': 'contact_email',
    'email': 'contact_email',
    'email_address': 'contact_email',
    'donor_email': 'contact_email',
    # contact_external_id
    'contact_external_id': 'contact_external_id',
    'external_id': 'contact_external_id',
    'contact_id': 'contact_external_id',
    'donor_id': 'contact_external_id',
    # amount
    'amount': 'amount',
    'gift_amount': 'amount',
    'donation_amount': 'amount',
    'total': 'amount',
    # date
    'date': 'date',
    'gift_date': 'date',
    'donation_date': 'date',
    # description
    'description': 'description',
    'memo': 'description',
    'notes': 'description',
    'purpose': 'description',
    # fund_name
    'fund': 'fund_name',
    'fund_name': 'fund_name',
    'campaign': 'fund_name',
    'account': 'fund_name',
}

VALID_MATCH_BY = ('name', 'email', 'external_id')


# ---------------------------------------------------------------------------
# Generic contact import orchestrator
# ---------------------------------------------------------------------------

def import_generic_contacts(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    owner: User,
    match_by: str = 'email',
) -> ImportBatch:
    """Import generic contact CSV end-to-end.

    Steps:
    1. SHA256 dedup check
    2. Decode with cascading encoding
    3. Parse CSV and build header mapping
    4. Validate required headers based on match_by
    5. Iterate rows: match/create contacts with error collection
    6. Create ImportBatch record with results

    Args:
        file_bytes: Raw CSV file bytes.
        filename: Original filename for audit trail.
        uploaded_by: User who initiated the upload.
        owner: User who will own created contacts.
        match_by: Matching strategy -- 'name', 'email', or 'external_id'.

    Returns ImportBatch (may be existing if duplicate).
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: Check for duplicate
    existing = check_duplicate_import(file_bytes, ImportBatchType.GENERIC_CONTACTS)
    if existing:
        logger.info('Duplicate generic contact import detected for %s', filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing

    # Step 2: Decode
    try:
        content = decode_csv_bytes(file_bytes)
    except ValueError as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_CONTACTS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': str(e)}]},
        )
        return batch

    # Step 3: Parse CSV and build header mapping
    try:
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
    except Exception as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_CONTACTS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'CSV parse error: {e}'}]},
        )
        return batch

    col_map = _build_header_mapping(fieldnames, GENERIC_CONTACT_HEADER_ALIASES)

    # Step 4: Validate required headers based on match_by
    missing_headers = []
    if match_by == 'name':
        if col_map.get('first_name') is None:
            missing_headers.append('first_name')
        if col_map.get('last_name') is None:
            missing_headers.append('last_name')
    elif match_by == 'email':
        if col_map.get('email') is None:
            missing_headers.append('email')
    elif match_by == 'external_id':
        if col_map.get('external_id') is None:
            missing_headers.append('external_id')

    # Always require name or org columns for new contact creation
    has_name_headers = (
        col_map.get('first_name') is not None
        and col_map.get('last_name') is not None
    )
    has_org_header = col_map.get('organization_name') is not None
    if not has_name_headers and not has_org_header:
        missing_headers.append('(first_name + last_name) or organization_name')

    if missing_headers:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_CONTACTS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={
                'errors': [{
                    'row': 0,
                    'error': (
                        f'Missing required headers for match_by={match_by}: '
                        f'{", ".join(missing_headers)}'
                    ),
                }],
            },
        )
        return batch

    # Step 5: Iterate rows with error collection
    errors: list[dict] = []
    created_count = 0
    updated_count = 0
    skipped_count = 0
    total_rows = 0

    try:
        with transaction.atomic():
            for row_number, row in enumerate(reader, start=2):
                total_rows += 1

                try:
                    # Build row_data from col_map with sanitization
                    row_data: dict[str, str] = {}
                    for canonical_name, actual_col in col_map.items():
                        if actual_col is not None:
                            row_data[canonical_name] = _sanitize_field(
                                row.get(actual_col) or '',
                            )

                    # Match contact based on match_by
                    contact = None
                    multiple_matches = False

                    if match_by == 'name':
                        first_name = row_data.get('first_name', '')
                        last_name = row_data.get('last_name', '')
                        if not first_name or not last_name:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: Missing first_name or '
                                    f'last_name for name matching'
                                ),
                            })
                            continue
                        matches = Contact.objects.filter(
                            owner=owner,
                            first_name__iexact=first_name,
                            last_name__iexact=last_name,
                            is_merged=False,
                        )
                        if matches.count() > 1:
                            multiple_matches = True
                        elif matches.count() == 1:
                            contact = matches.first()

                    elif match_by == 'email':
                        email = row_data.get('email', '')
                        if not email:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: Missing email for '
                                    f'email matching'
                                ),
                            })
                            continue
                        contact = Contact.objects.filter(
                            owner=owner,
                            email__iexact=email,
                            is_merged=False,
                        ).first()

                    elif match_by == 'external_id':
                        external_id = row_data.get('external_id', '')
                        if not external_id:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: Missing external_id for '
                                    f'external_id matching'
                                ),
                            })
                            continue
                        contact = Contact.objects.filter(
                            owner=owner,
                            external_id=external_id,
                            is_merged=False,
                        ).first()

                    if multiple_matches:
                        errors.append({
                            'row': row_number,
                            'error': (
                                f'Row {row_number}: Multiple contacts match '
                                f'-- use email or external ID matching'
                            ),
                        })
                        continue

                    if contact:
                        # Existing contact -- merge fields (fill blanks only)
                        updated_fields = merge_contact_fields(contact, row_data)
                        if updated_fields:
                            contact.save(update_fields=updated_fields)
                            updated_count += 1
                        else:
                            skipped_count += 1
                    else:
                        # No match -- create new contact
                        first_name = row_data.get('first_name', '')
                        last_name = row_data.get('last_name', '')
                        org_name = row_data.get('organization_name', '')

                        has_name = first_name and last_name
                        has_org = bool(org_name)

                        if not has_name and not has_org:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: Missing name or '
                                    f'organization -- cannot create contact'
                                ),
                            })
                            continue

                        new_contact_data = {
                            'owner': owner,
                            'first_name': first_name,
                            'last_name': last_name,
                        }
                        if org_name:
                            new_contact_data['organization_name'] = org_name

                        # Add optional fields
                        optional_fields = [
                            'email', 'phone', 'street_address', 'city',
                            'state', 'postal_code', 'country', 'notes',
                        ]
                        for field in optional_fields:
                            value = row_data.get(field, '')
                            if value:
                                new_contact_data[field] = value

                        # Add external_id if present
                        ext_id = row_data.get('external_id', '')
                        if ext_id:
                            new_contact_data['external_id'] = ext_id

                        Contact.objects.create(**new_contact_data)
                        created_count += 1

                except Exception as e:
                    errors.append({
                        'row': row_number,
                        'error': f'Row {row_number}: {str(e)}',
                    })

    except Exception as e:
        logger.error('Generic contact import failed for %s: %s', filename, e)
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_CONTACTS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'Import error: {e}'}]},
        )
        return batch

    # Step 6: Create ImportBatch record
    all_errored = total_rows > 0 and (created_count + updated_count + skipped_count) == 0
    batch = ImportBatch.objects.create(
        import_type=ImportBatchType.GENERIC_CONTACTS,
        status=ImportBatchStatus.FAILED if all_errored else ImportBatchStatus.COMPLETED,
        filename=filename,
        sha256_hash=sha256_hash,
        uploaded_by=uploaded_by,
        total_rows=total_rows,
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=len(errors),
        summary={'errors': errors},
    )

    logger.info(
        'Generic contact import complete for %s: %d created, %d updated, '
        '%d skipped, %d errors',
        filename,
        created_count,
        updated_count,
        skipped_count,
        len(errors),
    )

    return batch


# ---------------------------------------------------------------------------
# Generic donation import orchestrator
# ---------------------------------------------------------------------------

def import_generic_donations(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    owner: User,
    match_by: str = 'email',
) -> ImportBatch:
    """Import generic donation CSV end-to-end.

    Steps:
    1. SHA256 dedup check
    2. Decode with cascading encoding
    3. Parse CSV and build header mapping
    4. Validate required headers (amount, date, contact matching columns)
    5. Iterate rows: match contact, create Gift with error collection
    6. Create ImportBatch record with results

    Args:
        file_bytes: Raw CSV file bytes.
        filename: Original filename for audit trail.
        uploaded_by: User who initiated the upload.
        owner: User who owns the contacts to match against.
        match_by: Contact matching strategy -- 'name', 'email', or 'external_id'.

    Returns ImportBatch (may be existing if duplicate).
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: Check for duplicate
    existing = check_duplicate_import(file_bytes, ImportBatchType.GENERIC_DONATIONS)
    if existing:
        logger.info('Duplicate generic donation import detected for %s', filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing

    # Step 2: Decode
    try:
        content = decode_csv_bytes(file_bytes)
    except ValueError as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_DONATIONS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': str(e)}]},
        )
        return batch

    # Step 3: Parse CSV and build header mapping
    try:
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
    except Exception as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_DONATIONS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'CSV parse error: {e}'}]},
        )
        return batch

    col_map = _build_header_mapping(fieldnames, GENERIC_DONATION_HEADER_ALIASES)

    # Step 4: Validate required headers
    missing_headers = []
    if col_map.get('amount') is None:
        missing_headers.append('amount')
    if col_map.get('date') is None:
        missing_headers.append('date')

    # Contact matching columns
    if match_by == 'name':
        if col_map.get('contact_first_name') is None:
            missing_headers.append('contact_first_name')
        if col_map.get('contact_last_name') is None:
            missing_headers.append('contact_last_name')
    elif match_by == 'email':
        if col_map.get('contact_email') is None:
            missing_headers.append('contact_email')
    elif match_by == 'external_id':
        if col_map.get('contact_external_id') is None:
            missing_headers.append('contact_external_id')

    if missing_headers:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_DONATIONS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={
                'errors': [{
                    'row': 0,
                    'error': (
                        f'Missing required headers for match_by={match_by}: '
                        f'{", ".join(missing_headers)}'
                    ),
                }],
            },
        )
        return batch

    # Step 5: Iterate rows with error collection
    errors: list[dict] = []
    created_count = 0
    error_count_rows = 0
    total_rows = 0

    try:
        with transaction.atomic():
            for row_number, row in enumerate(reader, start=2):
                total_rows += 1

                try:
                    # Build row_data from col_map with sanitization
                    row_data: dict[str, str] = {}
                    for canonical_name, actual_col in col_map.items():
                        if actual_col is not None:
                            row_data[canonical_name] = _sanitize_field(
                                row.get(actual_col) or '',
                            )

                    # Parse amount
                    amount_cents = _parse_amount_to_cents(
                        row_data.get('amount', ''),
                    )
                    if amount_cents <= 0:
                        errors.append({
                            'row': row_number,
                            'error': (
                                f'Row {row_number}: Invalid or zero amount '
                                f'"{row_data.get("amount", "")}"'
                            ),
                        })
                        continue

                    # Parse date
                    parsed_date = _parse_date(row_data.get('date', ''))
                    if parsed_date is None:
                        errors.append({
                            'row': row_number,
                            'error': (
                                f'Row {row_number}: Invalid date '
                                f'"{row_data.get("date", "")}"'
                            ),
                        })
                        continue

                    # Match contact
                    contact = None

                    if match_by == 'name':
                        first_name = row_data.get('contact_first_name', '')
                        last_name = row_data.get('contact_last_name', '')
                        if not first_name or not last_name:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: Missing contact name '
                                    f'for name matching'
                                ),
                            })
                            continue
                        contact = Contact.objects.filter(
                            owner=owner,
                            first_name__iexact=first_name,
                            last_name__iexact=last_name,
                            is_merged=False,
                        ).first()
                        if not contact:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: No contact found '
                                    f'matching "{first_name} {last_name}" '
                                    f'-- import contacts first'
                                ),
                            })
                            continue

                    elif match_by == 'email':
                        email = row_data.get('contact_email', '')
                        if not email:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: Missing email for '
                                    f'email matching'
                                ),
                            })
                            continue
                        contact = Contact.objects.filter(
                            owner=owner,
                            email__iexact=email,
                            is_merged=False,
                        ).first()
                        if not contact:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: No contact found '
                                    f'matching "{email}" '
                                    f'-- import contacts first'
                                ),
                            })
                            continue

                    elif match_by == 'external_id':
                        ext_id = row_data.get('contact_external_id', '')
                        if not ext_id:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: Missing external_id '
                                    f'for external_id matching'
                                ),
                            })
                            continue
                        contact = Contact.objects.filter(
                            owner=owner,
                            external_id=ext_id,
                            is_merged=False,
                        ).first()
                        if not contact:
                            errors.append({
                                'row': row_number,
                                'error': (
                                    f'Row {row_number}: No contact found '
                                    f'matching external_id "{ext_id}" '
                                    f'-- import contacts first'
                                ),
                            })
                            continue

                    # Build Gift creation kwargs
                    gift_kwargs = {
                        'donor_contact': contact,
                        'amount_cents': amount_cents,
                        'gift_date': parsed_date,
                        'description': row_data.get('description', ''),
                    }

                    # Optionally match fund
                    fund_name = row_data.get('fund_name', '')
                    if fund_name:
                        matched_fund = Fund.objects.filter(
                            name__iexact=fund_name,
                        ).first()
                        if matched_fund:
                            gift_kwargs['fund'] = matched_fund

                    Gift.objects.create(**gift_kwargs)
                    created_count += 1

                except Exception as e:
                    errors.append({
                        'row': row_number,
                        'error': f'Row {row_number}: {str(e)}',
                    })

    except Exception as e:
        logger.error('Generic donation import failed for %s: %s', filename, e)
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_DONATIONS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'Import error: {e}'}]},
        )
        return batch

    # Step 6: Create ImportBatch record
    all_errored = total_rows > 0 and created_count == 0
    batch = ImportBatch.objects.create(
        import_type=ImportBatchType.GENERIC_DONATIONS,
        status=ImportBatchStatus.FAILED if all_errored else ImportBatchStatus.COMPLETED,
        filename=filename,
        sha256_hash=sha256_hash,
        uploaded_by=uploaded_by,
        total_rows=total_rows,
        created_count=created_count,
        updated_count=0,
        skipped_count=0,
        error_count=len(errors),
        summary={'errors': errors},
    )

    logger.info(
        'Generic donation import complete for %s: %d created, %d errors',
        filename,
        created_count,
        len(errors),
    )

    return batch
