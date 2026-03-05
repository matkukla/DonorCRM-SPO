"""
Shared Raiser's Edge import services.

Provides utility functions (cascading encoding, SHA256 dedup, header validation,
name normalization) and orchestrator functions for RE CSV imports.
Both management commands and API endpoints call the same service functions.
"""
import csv
import hashlib
import io
import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError

from apps.contacts.models import Contact
from apps.gifts.models import (
    Gift,
    GiftCredit,
    RecurringGift,
    RecurringGiftCredit,
    RecurringGiftFrequency,
    RecurringGiftStatus,
    Solicitor,
)
from apps.imports.models import Fund, ImportBatch, ImportBatchStatus, ImportBatchType
from apps.prayers.models import PrayerIntention, PrayerIntentionStatus
from apps.users.models import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def decode_csv_bytes(file_bytes: bytes) -> str:
    """Decode CSV bytes with cascading encoding fallback.

    RE exports may use UTF-8 (modern), UTF-8-sig (Excel BOM), or
    Windows-1252 (legacy with smart quotes, accented names).

    Strips null bytes that can appear in corrupted files or binary data
    pasted into CSV editors.

    Raises ValueError if no encoding works (should never happen
    since Windows-1252 accepts all byte values 0x00-0xFF).
    """
    for encoding in ('utf-8-sig', 'utf-8', 'windows-1252'):
        try:
            content = file_bytes.decode(encoding)
            # Strip null bytes that can break csv.reader
            return content.replace('\x00', '')
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError('Unable to decode file with any supported encoding')


_RE_TYPE_LABELS = frozenset({
    'constituent', 'gift', 'recurring gift', 'solicitor',
    'pledge', 'action', 'event', 'membership', 'relationship',
})


def skip_re_type_label_row(content: str) -> str:
    """Skip the RE export type-label row if present.

    RE CSV exports from Raiser's Edge often include a leading type-label row
    (e.g. "Constituent,,,,,," or "Gift ,,,,,") before the actual column
    headers. When present, this row is stripped so that csv.DictReader reads
    the real headers from the second row.

    Detection: the first row has exactly one non-empty cell AND that cell
    matches a known RE export type-label keyword.
    """
    lines = content.splitlines(keepends=True)
    if len(lines) < 2:
        return content

    # Parse first row with csv to respect quoting
    try:
        first_row = next(csv.reader([lines[0].rstrip('\r\n')]))
    except StopIteration:
        return content

    non_empty_first = [c.strip() for c in first_row if c.strip()]

    # Type-label row: exactly one non-empty cell that matches a known label
    if len(non_empty_first) == 1 and non_empty_first[0].lower() in _RE_TYPE_LABELS:
        return ''.join(lines[1:])

    return content


# Maximum length for string fields before DB save (prevents oversized values)
MAX_FIELD_LENGTH = 10000


def _sanitize_field(value: str) -> str:
    """Sanitize a CSV field value: strip whitespace and truncate to MAX_FIELD_LENGTH."""
    value = value.strip()
    if len(value) > MAX_FIELD_LENGTH:
        return value[:MAX_FIELD_LENGTH]
    return value


def check_duplicate_import(file_bytes: bytes, import_type: str) -> ImportBatch | None:
    """Check if file has already been imported. Returns existing batch if duplicate."""
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    try:
        return ImportBatch.objects.get(
            import_type=import_type,
            sha256_hash=sha256_hash,
        )
    except ImportBatch.DoesNotExist:
        return None


def validate_csv_headers(
    reader_fieldnames: list[str],
    required_headers: set[str],
    import_type_label: str,
) -> None:
    """Validate that required CSV headers are present (case-insensitive).

    Raises ValueError with descriptive message listing missing headers.
    """
    if not reader_fieldnames:
        raise ValueError(f'{import_type_label}: CSV file has no headers')

    actual_lower = {h.strip().lower() for h in reader_fieldnames if h}
    missing = {h for h in required_headers if h.lower() not in actual_lower}
    if missing:
        raise ValueError(
            f'{import_type_label}: Missing required headers: {", ".join(sorted(missing))}'
        )


def normalize_solicitor_name(raw_name: str) -> str:
    """Normalize solicitor name to 'last, first' format for matching.

    Handles:
    - "Last, First" -> "last, first" (already correct format)
    - "First Last" -> "last, first" (reverse)
    - Single-word names stay as-is, lowercased
    """
    name = raw_name.strip()
    if not name:
        return ''

    if ',' in name:
        # Already "Last, First" format
        parts = [p.strip() for p in name.split(',', 1)]
        last = parts[0].lower()
        first = parts[1].lower() if len(parts) > 1 else ''
        if first:
            return f'{last}, {first}'
        return last
    else:
        # "First Last" format -- reverse
        parts = name.split()
        if len(parts) >= 2:
            first = ' '.join(parts[:-1])
            last = parts[-1]
            return f'{last.lower()}, {first.lower()}'
        return name.lower()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_user_name_lookup() -> dict[str, User]:
    """Build dict mapping 'last, first' -> User for auto-linking.

    If two users normalize to the same key, exclude both (ambiguous match).
    """
    lookup: dict[str, User] = {}
    ambiguous: set[str] = set()

    for user in User.objects.filter(is_active=True):
        key = f'{user.last_name.lower()}, {user.first_name.lower()}'
        if key in ambiguous:
            continue
        if key in lookup:
            # Two users with same normalized name: ambiguous
            del lookup[key]
            ambiguous.add(key)
            logger.warning(
                'Ambiguous user name match for "%s" -- excluding both users',
                key,
            )
        else:
            lookup[key] = user

    return lookup


def _build_header_mapping(
    fieldnames: list[str],
    alias_map: dict[str, str],
) -> dict[str, str | None]:
    """Map canonical field names to actual CSV column names.

    alias_map: {alias_lower: canonical_name}
    Returns: {canonical_name: actual_column_name_or_None}
    """
    result: dict[str, str | None] = {}
    # Collect all canonical names
    canonical_names = set(alias_map.values())
    for name in canonical_names:
        result[name] = None

    for col in fieldnames:
        col_lower = col.strip().lower()
        if col_lower in alias_map:
            canonical = alias_map[col_lower]
            if result[canonical] is None:
                result[canonical] = col  # Use original column name for DictReader access

    return result


# ---------------------------------------------------------------------------
# Solicitor header aliases
# ---------------------------------------------------------------------------

# Maps lowercase alias -> canonical field name
SOLICITOR_HEADER_ALIASES: dict[str, str] = {
    # Solicitor ID aliases
    'solicitor_id': 'external_solicitor_id',
    'solid': 'external_solicitor_id',
    'sol_id': 'external_solicitor_id',
    'cnsol_1_01_solicit_id': 'external_solicitor_id',
    # Solicitor name aliases
    'solicitor_name': 'raw_name',
    'name': 'raw_name',
    'full_name': 'raw_name',
    'cnsol_1_01_name': 'raw_name',
}

# Only the name field is strictly required
SOLICITOR_REQUIRED_CANONICAL = {'raw_name'}


# ---------------------------------------------------------------------------
# Solicitor import orchestrator
# ---------------------------------------------------------------------------

def import_re_solicitors(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
) -> ImportBatch:
    """Import RE Solicitor CSV end-to-end.

    Steps:
    1. SHA256 dedup check
    2. Decode with cascading encoding
    3. Validate headers
    4. Build user name lookup
    5. Parse rows with error collection
    6. Create ImportBatch record with results

    Returns ImportBatch (may be existing if duplicate).
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: Check for duplicate
    existing = check_duplicate_import(file_bytes, ImportBatchType.RE_SOLICITOR)
    if existing:
        logger.info('Duplicate solicitor import detected for %s', filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing

    # Step 2: Decode
    try:
        content = skip_re_type_label_row(decode_csv_bytes(file_bytes))
    except ValueError as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_SOLICITOR,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': str(e)}]},
        )
        return batch

    # Step 3: Parse CSV and validate headers
    try:
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
    except Exception as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_SOLICITOR,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'CSV parse error: {e}'}]},
        )
        return batch

    # Build header mapping from aliases
    col_map = _build_header_mapping(fieldnames, SOLICITOR_HEADER_ALIASES)

    # Check that at least the name field is present
    missing_canonical = {
        name for name in SOLICITOR_REQUIRED_CANONICAL
        if col_map.get(name) is None
    }
    if missing_canonical:
        # Find which actual header aliases were expected
        expected_aliases = []
        for alias, canonical in SOLICITOR_HEADER_ALIASES.items():
            if canonical in missing_canonical:
                expected_aliases.append(alias)
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_SOLICITOR,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={
                'errors': [{
                    'row': 0,
                    'error': (
                        f'Missing required solicitor name header. '
                        f'Expected one of: {", ".join(sorted(expected_aliases))}'
                    ),
                }],
            },
        )
        return batch

    # Step 4: Build user name lookup
    user_lookup = _build_user_name_lookup()

    # Step 5: Iterate rows with error collection inside a transaction
    errors: list[dict] = []
    created_count = 0
    skipped_count = 0
    total_rows = 0
    unlinked_solicitors: list[dict] = []

    # Track dedup within the file
    seen_ext_ids: set[str] = set()
    seen_norm_names: set[str] = set()

    name_col = col_map['raw_name']
    ext_id_col = col_map.get('external_solicitor_id')

    try:
        with transaction.atomic():
            for row_number, row in enumerate(reader, start=2):
                total_rows += 1

                # Extract raw name
                raw_name = _sanitize_field(row.get(name_col) or '')
                if not raw_name:
                    errors.append({
                        'row': row_number,
                        'error': 'Missing solicitor name',
                    })
                    continue

                # Extract external ID if present
                ext_id = ''
                if ext_id_col:
                    ext_id = _sanitize_field(row.get(ext_id_col) or '')

                # Normalize name
                norm_name = normalize_solicitor_name(raw_name)

                # Dedup within file
                if ext_id:
                    if ext_id in seen_ext_ids:
                        skipped_count += 1
                        continue
                    seen_ext_ids.add(ext_id)
                else:
                    if norm_name in seen_norm_names:
                        skipped_count += 1
                        continue
                    seen_norm_names.add(norm_name)

                # Dedup against database
                if ext_id:
                    if Solicitor.objects.filter(external_solicitor_id=ext_id).exists():
                        skipped_count += 1
                        continue
                elif Solicitor.objects.filter(normalized_name=norm_name).exists():
                    skipped_count += 1
                    continue

                # Create new Solicitor
                solicitor = Solicitor(
                    normalized_name=norm_name,
                    external_solicitor_id=ext_id,
                )

                # Auto-link to User
                matched_user = user_lookup.get(norm_name)
                if matched_user:
                    solicitor.user = matched_user
                    logger.info(
                        'Auto-linked solicitor "%s" to user %s',
                        norm_name,
                        matched_user.email,
                    )

                solicitor.save()
                created_count += 1

                if not matched_user:
                    unlinked_solicitors.append({
                        'name': norm_name,
                        'external_id': ext_id,
                    })

    except Exception as e:
        logger.error('Solicitor import failed for %s: %s', filename, e)
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_SOLICITOR,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'Import error: {e}'}]},
        )
        return batch

    # Step 6: Create ImportBatch record
    batch = ImportBatch.objects.create(
        import_type=ImportBatchType.RE_SOLICITOR,
        status=ImportBatchStatus.COMPLETED,
        filename=filename,
        sha256_hash=sha256_hash,
        uploaded_by=uploaded_by,
        total_rows=total_rows,
        created_count=created_count,
        updated_count=0,
        skipped_count=skipped_count,
        error_count=len(errors),
        summary={
            'errors': errors,
            'unlinked_solicitors': unlinked_solicitors,
        },
    )

    logger.info(
        'Solicitor import complete for %s: %d created, %d skipped, %d errors',
        filename,
        created_count,
        skipped_count,
        len(errors),
    )

    return batch


# ---------------------------------------------------------------------------
# Constituent header aliases
# ---------------------------------------------------------------------------

# Maps lowercase alias -> canonical field name
CONSTITUENT_HEADER_ALIASES: dict[str, str] = {
    # Constituent ID aliases
    'cnbio_id': 'constituent_id',
    'consid': 'constituent_id',
    'constituent_id': 'constituent_id',
    'constituent id': 'constituent_id',
    'cons_id': 'constituent_id',
    'id': 'constituent_id',
    # First name aliases
    'cnbio_first_name': 'first_name',
    'firstname': 'first_name',
    'first_name': 'first_name',
    'first name': 'first_name',
    'fname': 'first_name',
    # Last name aliases
    'cnbio_last_name': 'last_name',
    'lastname': 'last_name',
    'last_name': 'last_name',
    'last name': 'last_name',
    'lname': 'last_name',
    # Organization name aliases
    'cnbio_org_name': 'organization_name',
    'orgname': 'organization_name',
    'org_name': 'organization_name',
    'organization': 'organization_name',
    'organization_name': 'organization_name',
    'organization name': 'organization_name',
    'org name': 'organization_name',
    # Email aliases
    'cnadrprf_email': 'email',
    'email': 'email',
    'email_address': 'email',
    'email address': 'email',
    'emailaddress': 'email',
    # Phone aliases
    'cnph_1_01_phone_number': 'phone',
    'phone': 'phone',
    'phone_number': 'phone',
    'phone number': 'phone',
    'phonenumber': 'phone',
    # Street address aliases
    'cnadrprf_addrline1': 'street_address',
    'address': 'street_address',
    'address_line_1': 'street_address',
    'address line 1': 'street_address',
    'street': 'street_address',
    'street_address': 'street_address',
    # City aliases
    'cnadrprf_city': 'city',
    'city': 'city',
    # State aliases
    'cnadrprf_state': 'state',
    'state': 'state',
    # Postal code aliases
    'cnadrprf_zip': 'postal_code',
    'zip': 'postal_code',
    'postal_code': 'postal_code',
    'postal code': 'postal_code',
    'zipcode': 'postal_code',
    'zip_code': 'postal_code',
    # Country aliases
    'cnadrprf_contrylongdsc': 'country',
    'country': 'country',
}


# ---------------------------------------------------------------------------
# Constituent import helpers
# ---------------------------------------------------------------------------

def merge_contact_fields(contact: Contact, new_data: dict) -> list[str]:
    """Merge new data into contact, only filling blank fields.

    Only fills BLANK fields (empty string or None). Never overwrites existing
    non-blank values. For email, first_name, last_name: also skip if new_data
    value is empty (never blank out names or email).

    Returns list of field names that were actually updated.
    Does NOT call contact.save() -- caller saves with update_fields.
    """
    updated_fields: list[str] = []
    merge_fields = [
        'first_name', 'last_name', 'email', 'phone', 'phone_secondary',
        'street_address', 'city', 'state', 'postal_code', 'country',
        'organization_name',
    ]
    # Fields where we should never set an empty value
    skip_empty_fields = {'first_name', 'last_name', 'email'}

    for field in merge_fields:
        current_value = getattr(contact, field, '') or ''
        new_value = new_data.get(field, '') or ''

        # Skip if current value is non-blank (merge-only: never overwrite)
        if current_value:
            continue

        # Skip if new value is empty
        if not new_value:
            continue

        # For protected fields, double-check new value is non-empty
        if field in skip_empty_fields and not new_value.strip():
            continue

        setattr(contact, field, new_value)
        updated_fields.append(field)

    return updated_fields


def _match_contact(row_data: dict, owner: User, row_number: int) -> tuple[Contact | None, str]:
    """Match a CSV row to an existing Contact using three-tier hierarchy.

    Match hierarchy:
    1. external_constituent_id (global, not owner-scoped)
    2. email (owner-scoped)
    3. phone (owner-scoped)

    Returns (contact, match_type) where match_type is one of:
    'constituent_id', 'email', 'phone', or 'none'.

    Logs warnings when ID matches but email/phone differs from existing.
    """
    ext_id = row_data.get('constituent_id', '').strip()
    email = row_data.get('email', '').strip()
    phone = row_data.get('phone', '').strip()

    # Tier 1: Match by external_constituent_id (global)
    if ext_id:
        contact = Contact.objects.filter(external_constituent_id=ext_id).first()
        if contact:
            # Log warnings for mismatched email/phone
            if email and contact.email and contact.email != email:
                logger.warning(
                    'Row %d: Constituent ID %s matched contact %s, but email '
                    'differs (existing: %s, CSV: %s)',
                    row_number, ext_id, contact.id, contact.email, email,
                )
            if phone and contact.phone and contact.phone != phone:
                logger.warning(
                    'Row %d: Constituent ID %s matched contact %s, but phone '
                    'differs (existing: %s, CSV: %s)',
                    row_number, ext_id, contact.id, contact.phone, phone,
                )
            return contact, 'constituent_id'

    # Tier 2: Match by email (owner-scoped)
    if email:
        contact = Contact.objects.filter(owner=owner, email=email).first()
        if contact:
            return contact, 'email'

    # Tier 3: Match by phone (owner-scoped)
    if phone:
        contact = Contact.objects.filter(owner=owner, phone=phone).first()
        if contact:
            return contact, 'phone'

    return None, 'none'


# ---------------------------------------------------------------------------
# Constituent import orchestrator
# ---------------------------------------------------------------------------

def import_re_constituents(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    owner: User,
) -> ImportBatch:
    """Import RE Constituent CSV end-to-end.

    Steps:
    1. SHA256 dedup check
    2. Decode with cascading encoding
    3. Parse CSV and validate headers
    4. Iterate rows with error collection
    5. Create ImportBatch record with results

    Returns ImportBatch (may be existing if duplicate).
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: Check for duplicate
    existing = check_duplicate_import(file_bytes, ImportBatchType.RE_CONSTITUENT)
    if existing:
        logger.info('Duplicate constituent import detected for %s', filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing

    # Step 2: Decode
    try:
        content = skip_re_type_label_row(decode_csv_bytes(file_bytes))
    except ValueError as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_CONSTITUENT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': str(e)}]},
        )
        return batch

    # Step 3: Parse CSV and validate headers
    try:
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
    except Exception as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_CONSTITUENT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'CSV parse error: {e}'}]},
        )
        return batch

    # Build header mapping from aliases
    col_map = _build_header_mapping(fieldnames, CONSTITUENT_HEADER_ALIASES)

    # Validate: at least one of first_name, last_name, or organization_name
    has_name_header = (
        col_map.get('first_name') is not None
        or col_map.get('last_name') is not None
        or col_map.get('organization_name') is not None
    )
    if not has_name_header:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_CONSTITUENT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={
                'errors': [{
                    'row': 0,
                    'error': (
                        'Missing required name headers. '
                        'CSV must contain at least one of: first_name/last_name '
                        'or organization_name (or RE equivalents).'
                    ),
                }],
                'file_error': (
                    'Missing required name headers. '
                    'CSV must contain at least one of: first_name/last_name '
                    'or organization_name (or RE equivalents).'
                ),
            },
        )
        return batch

    # Step 4: Iterate rows with error collection
    errors: list[dict] = []
    warnings: list[dict] = []
    created_count = 0
    updated_count = 0
    skipped_count = 0
    total_rows = 0

    try:
        with transaction.atomic():
            for row_number, row in enumerate(reader, start=2):
                total_rows += 1

                try:
                    # Build row_data dict from mapped columns with sanitization
                    row_data: dict[str, str] = {}
                    for canonical_name, actual_col in col_map.items():
                        if actual_col is not None:
                            row_data[canonical_name] = _sanitize_field(row.get(actual_col) or '')

                    # Minimum data validation: require (first_name + last_name) or organization_name
                    first_name = row_data.get('first_name', '')
                    last_name = row_data.get('last_name', '')
                    org_name = row_data.get('organization_name', '')

                    has_name = first_name and last_name
                    has_org = bool(org_name)

                    if not has_name and not has_org:
                        errors.append({
                            'row': row_number,
                            'error': (
                                f'Row {row_number}: Missing name or organization '
                                '-- cannot create contact'
                            ),
                        })
                        continue

                    # Extract external_constituent_id
                    ext_id = row_data.get('constituent_id', '')

                    # Match contact using three-tier hierarchy
                    contact, match_type = _match_contact(row_data, owner, row_number)

                    if contact:
                        # Existing contact found -- merge-only update
                        updated_fields = merge_contact_fields(contact, row_data)

                        # If contact doesn't have external_constituent_id but CSV row does
                        if ext_id and not contact.external_constituent_id:
                            contact.external_constituent_id = ext_id
                            updated_fields.append('external_constituent_id')

                        if updated_fields:
                            contact.save(update_fields=updated_fields)
                            updated_count += 1
                        else:
                            skipped_count += 1

                        # Record warnings for ID match conflicts
                        if match_type == 'constituent_id':
                            csv_email = row_data.get('email', '')
                            csv_phone = row_data.get('phone', '')
                            if csv_email and contact.email and contact.email != csv_email:
                                warnings.append({
                                    'row': row_number,
                                    'warning': (
                                        f'Constituent ID {ext_id} matched but email '
                                        f'differs (existing: {contact.email}, '
                                        f'CSV: {csv_email})'
                                    ),
                                })
                            if csv_phone and contact.phone and contact.phone != csv_phone:
                                warnings.append({
                                    'row': row_number,
                                    'warning': (
                                        f'Constituent ID {ext_id} matched but phone '
                                        f'differs (existing: {contact.phone}, '
                                        f'CSV: {csv_phone})'
                                    ),
                                })
                    else:
                        # No match -- create new Contact
                        new_contact_data = {
                            'owner': owner,
                            'first_name': first_name,
                            'last_name': last_name,
                        }
                        if ext_id:
                            new_contact_data['external_constituent_id'] = ext_id
                        if org_name:
                            new_contact_data['organization_name'] = org_name

                        # Add optional fields from row_data
                        optional_fields = [
                            'email', 'phone', 'phone_secondary',
                            'street_address', 'city', 'state',
                            'postal_code', 'country',
                        ]
                        for field in optional_fields:
                            value = row_data.get(field, '')
                            if value:
                                new_contact_data[field] = value

                        Contact.objects.create(**new_contact_data)
                        created_count += 1

                except (IntegrityError, ValidationError) as e:
                    errors.append({
                        'row': row_number,
                        'error': f'Row {row_number}: {str(e)}',
                    })
                except Exception as e:
                    errors.append({
                        'row': row_number,
                        'error': f'Row {row_number}: Unexpected error: {str(e)}',
                    })

    except Exception as e:
        logger.error('Constituent import failed for %s: %s', filename, e)
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_CONSTITUENT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'Import error: {e}'}]},
        )
        return batch

    # Step 5: Create ImportBatch record
    batch = ImportBatch.objects.create(
        import_type=ImportBatchType.RE_CONSTITUENT,
        status=ImportBatchStatus.COMPLETED,
        filename=filename,
        sha256_hash=sha256_hash,
        uploaded_by=uploaded_by,
        total_rows=total_rows,
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=len(errors),
        summary={
            'errors': errors,
            'warnings': warnings,
        },
    )

    logger.info(
        'Constituent import complete for %s: %d created, %d updated, '
        '%d skipped, %d errors',
        filename,
        created_count,
        updated_count,
        skipped_count,
        len(errors),
    )

    return batch


# ---------------------------------------------------------------------------
# Gift import helpers
# ---------------------------------------------------------------------------

def _parse_amount_to_cents(amount_str: str) -> int:
    """Parse dollar amount string to cents integer.

    Handles: "$1,234.56", "1234.56", "1,234", "$100"
    Returns 0 for empty/unparseable values.
    """
    if not amount_str:
        return 0
    cleaned = amount_str.replace('$', '').replace(',', '').strip()
    if not cleaned:
        return 0
    try:
        dollars = Decimal(cleaned)
        return int(dollars * 100)
    except (InvalidOperation, ValueError):
        return 0


def _parse_date(date_str: str):
    """Parse date string with multiple format support.

    Tries: YYYY-MM-DD, MM/DD/YYYY, M/D/YYYY, M/D/YY.
    Returns date object or None if all fail.
    """
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _build_fund_lookup() -> dict:
    """Build dict mapping lowercased external_id and name to Fund objects."""
    lookup: dict[str, Fund] = {}
    for fund in Fund.objects.all():
        if fund.external_id:
            lookup[fund.external_id.lower()] = fund
        lookup[fund.name.lower()] = fund
    return lookup


def _build_solicitor_lookup() -> dict:
    """Build dict mapping normalized_name to Solicitor objects."""
    lookup: dict[str, Solicitor] = {}
    for solicitor in Solicitor.objects.all():
        lookup[solicitor.normalized_name] = solicitor
    return lookup


def _group_rows_by_id(
    reader,
    col_map: dict,
    id_field: str,
) -> tuple:
    """Group CSV rows by a given ID field.

    Returns:
        groups: {id_value: [row_data_dicts]}
        errors: [{row, error}] for rows with missing ID
        total_rows: total CSV data rows processed
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    errors: list[dict] = []
    total_rows = 0

    for row_number, row in enumerate(reader, start=2):
        total_rows += 1
        # Build row_data from col_map with sanitization
        row_data: dict[str, str] = {}
        for canonical, actual_col in col_map.items():
            if actual_col is not None:
                row_data[canonical] = _sanitize_field(row.get(actual_col) or '')

        id_value = row_data.get(id_field, '')
        if not id_value:
            errors.append({
                'row': row_number,
                'error': f'Row {row_number}: Missing {id_field}',
            })
            continue

        row_data['_row_number'] = str(row_number)
        groups[id_value].append(row_data)

    return dict(groups), errors, total_rows


# Prayer auto-creation helpers
PRAYER_STOPLIST = {
    'n/a', 'na', 'none', 'no', 'yes', '-', '--', '---', '...', 'test',
    'x', 'xx', 'xxx', 'general', 'same', 'same as above',
    'see above', 'ditto', 'tbd', 'unknown',
}


def _maybe_create_prayer_intention(
    gift: Gift,
    prayer_text: str,
    contact: Contact,
    seen_prayers: dict,
) -> PrayerIntention | None:
    """Create or link PrayerIntention from gift prayer description.

    Dedup key: (contact.id, normalized_text).
    If same prayer already created for this contact in this import,
    add the gift to the existing M2M relationship.
    """
    text = prayer_text.strip()
    if not text:
        return None

    # Stoplist check (case-insensitive)
    if text.lower() in PRAYER_STOPLIST:
        return None

    # Sanity: skip if no alphanumeric characters
    if not any(c.isalnum() for c in text):
        return None

    # Normalize for dedup
    normalized = text.lower().strip()
    dedup_key = (contact.id, normalized)

    if dedup_key in seen_prayers:
        existing = seen_prayers[dedup_key]
        existing.gifts.add(gift)
        return existing

    # Check database for existing prayer with same text
    existing_db = PrayerIntention.objects.filter(
        contact=contact,
        description__iexact=text,
    ).first()

    if existing_db:
        existing_db.gifts.add(gift)
        seen_prayers[dedup_key] = existing_db
        return existing_db

    # Create new PrayerIntention with clean title truncation
    if len(text) > 80:
        truncated = text[:80].rsplit(' ', 1)
        title = truncated[0] if len(truncated) > 1 and truncated[0] != text[:80] else text[:80]
    else:
        title = text

    prayer = PrayerIntention.objects.create(
        contact=contact,
        title=title,
        description=text,
        status=PrayerIntentionStatus.ACTIVE,
    )
    prayer.gifts.add(gift)
    seen_prayers[dedup_key] = prayer
    return prayer


# ---------------------------------------------------------------------------
# Gift header aliases
# ---------------------------------------------------------------------------

GIFT_HEADER_ALIASES: dict[str, str] = {
    # Gift ID
    'gift_id': 'gift_id',
    'gf_id': 'gift_id',
    'gift id': 'gift_id',
    'gf_system_id': 'gift_id',
    'gift system record id': 'gift_id',
    # Constituent ID
    'gf_cnbio_id': 'constituent_id',
    'constituent_id': 'constituent_id',
    'constituent id': 'constituent_id',
    'cnbio_id': 'constituent_id',
    'consid': 'constituent_id',
    # Amount (gift-level)
    'gf_amount': 'amount',
    'gift_amount': 'amount',
    'gift amount': 'amount',
    'amount': 'amount',
    # Date
    'gf_date': 'gift_date',
    'gift_date': 'gift_date',
    'gift date': 'gift_date',
    'date': 'gift_date',
    # Fund
    'gf_fund': 'fund',
    'fund': 'fund',
    'fund_id': 'fund',
    'fund id': 'fund',
    'fund_description': 'fund',
    'fund split amount': 'amount',
    # Description
    'gf_description': 'description',
    'description': 'description',
    'gift description': 'description',
    # Solicitor name
    'solicitor_name': 'solicitor_name',
    'solicitor name': 'solicitor_name',
    'cnsol_1_01_name': 'solicitor_name',
    'gf_cnsol_1_01_name': 'solicitor_name',
    # Credit amount (per-solicitor)
    'credit_amount': 'credit_amount',
    'gf_cnsol_1_01_amount': 'credit_amount',
    'solicitor amount': 'credit_amount',
    # Prayer description
    'gift specific attributes prayer requests description': 'prayer_description',
    'prayer_requests_description': 'prayer_description',
    'prayer requests description': 'prayer_description',
    'prayer description': 'prayer_description',
}

GIFT_REQUIRED_CANONICAL = {'gift_id', 'constituent_id', 'amount'}


# ---------------------------------------------------------------------------
# Gift import orchestrator
# ---------------------------------------------------------------------------

def import_re_gifts(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    owner: User,
) -> ImportBatch:
    """Import RE Gift CSV end-to-end.

    Steps:
    1. SHA256 dedup check
    2. Decode with cascading encoding
    3. Parse CSV and validate headers via alias mapping
    4. Group rows by Gift ID (two-pass)
    5. Build solicitor + fund lookups
    6. Process each gift group with savepoint isolation:
       a. Find Contact by constituent_id (skip group if not found)
       b. Check external_gift_id dedup against DB (skip if exists)
       c. Create Gift with amount from first row
       d. Create GiftCredit for each solicitor row
       e. Auto-create PrayerIntention from prayer description column
    7. Create ImportBatch record with results

    Returns ImportBatch (may be existing if duplicate).
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: Check for duplicate
    existing = check_duplicate_import(file_bytes, ImportBatchType.RE_GIFT)
    if existing:
        logger.info('Duplicate gift import detected for %s', filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing

    # Step 2: Decode
    try:
        content = skip_re_type_label_row(decode_csv_bytes(file_bytes))
    except ValueError as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_GIFT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': str(e)}]},
        )
        return batch

    # Step 3: Parse CSV and validate headers
    try:
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
    except Exception as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_GIFT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'CSV parse error: {e}'}]},
        )
        return batch

    col_map = _build_header_mapping(fieldnames, GIFT_HEADER_ALIASES)

    # Check required canonical fields
    missing_canonical = {
        name for name in GIFT_REQUIRED_CANONICAL
        if col_map.get(name) is None
    }
    if missing_canonical:
        expected_aliases = []
        for alias, canonical in GIFT_HEADER_ALIASES.items():
            if canonical in missing_canonical:
                expected_aliases.append(alias)
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_GIFT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={
                'errors': [{
                    'row': 0,
                    'error': (
                        f'Missing required gift headers. '
                        f'Expected one of each: {", ".join(sorted(expected_aliases))}'
                    ),
                }],
            },
        )
        return batch

    # Step 4: Group rows by gift_id
    groups, grouping_errors, total_rows = _group_rows_by_id(
        reader, col_map, 'gift_id',
    )

    # Step 5: Build lookups
    solicitor_lookup = _build_solicitor_lookup()
    fund_lookup = _build_fund_lookup()

    # Step 6: Process each gift group
    errors: list[dict] = list(grouping_errors)
    warnings: list[dict] = []
    created_count = 0
    skipped_count = 0
    prayer_count = 0
    unmatched_solicitors: list[str] = []
    seen_prayers: dict = {}

    try:
        with transaction.atomic():
            for gift_id, rows in groups.items():
                sp = transaction.savepoint()
                try:
                    first_row = rows[0]

                    # Look up Contact by constituent_id
                    constituent_id = first_row.get('constituent_id', '')
                    contact = None
                    if constituent_id:
                        contact = Contact.objects.filter(
                            external_constituent_id=constituent_id,
                        ).first()

                    if not contact:
                        row_nums = ', '.join(r['_row_number'] for r in rows)
                        errors.append({
                            'row': int(first_row['_row_number']),
                            'error': (
                                f'Constituent ID "{constituent_id}" not found '
                                f'-- skipping gift group {gift_id} (rows {row_nums})'
                            ),
                        })
                        transaction.savepoint_rollback(sp)
                        continue

                    # Check for duplicate external_gift_id in database
                    if Gift.objects.filter(external_gift_id=gift_id).exists():
                        skipped_count += 1
                        transaction.savepoint_rollback(sp)
                        continue

                    # Parse amount from first row
                    amount_cents = _parse_amount_to_cents(
                        first_row.get('amount', ''),
                    )
                    if amount_cents == 0:
                        errors.append({
                            'row': int(first_row['_row_number']),
                            'error': (
                                f'Row {first_row["_row_number"]}: Invalid amount '
                                f'"{first_row.get("amount", "")}" for gift {gift_id}'
                            ),
                        })
                        transaction.savepoint_rollback(sp)
                        continue

                    # Parse date from first row
                    parsed_date = _parse_date(first_row.get('gift_date', ''))
                    if parsed_date is None:
                        errors.append({
                            'row': int(first_row['_row_number']),
                            'error': (
                                f'Row {first_row["_row_number"]}: Invalid date '
                                f'"{first_row.get("gift_date", "")}" for gift {gift_id}'
                            ),
                        })
                        transaction.savepoint_rollback(sp)
                        continue

                    # Match fund
                    fund_value = first_row.get('fund', '').lower()
                    matched_fund = None
                    if fund_value:
                        matched_fund = fund_lookup.get(fund_value)
                        if not matched_fund:
                            warnings.append({
                                'row': int(first_row['_row_number']),
                                'warning': (
                                    f'Fund "{first_row.get("fund", "")}" not found '
                                    f'for gift {gift_id}'
                                ),
                            })

                    # Create Gift
                    gift = Gift.objects.create(
                        external_gift_id=gift_id,
                        donor_contact=contact,
                        amount_cents=amount_cents,
                        gift_date=parsed_date,
                        fund=matched_fund,
                        description=first_row.get('description', ''),
                    )

                    # Create GiftCredits -- one per row with a solicitor
                    for row in rows:
                        solicitor_name = row.get('solicitor_name', '')
                        if not solicitor_name:
                            continue
                        norm_name = normalize_solicitor_name(solicitor_name)
                        solicitor = solicitor_lookup.get(norm_name)
                        if not solicitor:
                            errors.append({
                                'row': int(row['_row_number']),
                                'error': (
                                    f'Row {row["_row_number"]}: Solicitor '
                                    f'"{solicitor_name}" not found -- credit '
                                    f'skipped for gift {gift_id}'
                                ),
                            })
                            if norm_name not in unmatched_solicitors:
                                unmatched_solicitors.append(norm_name)
                            continue
                        credit_amount = _parse_amount_to_cents(
                            row.get('credit_amount', ''),
                        )
                        if credit_amount == 0:
                            credit_amount = amount_cents
                        GiftCredit.objects.create(
                            gift=gift,
                            solicitor=solicitor,
                            amount_cents=credit_amount,
                        )

                    # Check for prayer description
                    prayer_text = first_row.get('prayer_description', '')
                    if prayer_text:
                        prayer = _maybe_create_prayer_intention(
                            gift, prayer_text, contact, seen_prayers,
                        )
                        if prayer:
                            prayer_count += 1

                    transaction.savepoint_commit(sp)
                    created_count += 1

                except Exception as e:
                    transaction.savepoint_rollback(sp)
                    row_nums = ', '.join(r.get('_row_number', '?') for r in rows)
                    errors.append({
                        'row': int(rows[0].get('_row_number', 0)),
                        'error': (
                            f'Gift group {gift_id} (rows {row_nums}): '
                            f'Unexpected error: {str(e)}'
                        ),
                    })

    except Exception as e:
        logger.error('Gift import failed for %s: %s', filename, e)
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_GIFT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'Import error: {e}'}]},
        )
        return batch

    # Step 7: Create ImportBatch record
    batch = ImportBatch.objects.create(
        import_type=ImportBatchType.RE_GIFT,
        status=ImportBatchStatus.COMPLETED,
        filename=filename,
        sha256_hash=sha256_hash,
        uploaded_by=uploaded_by,
        total_rows=total_rows,
        created_count=created_count,
        updated_count=0,
        skipped_count=skipped_count,
        error_count=len(errors),
        summary={
            'errors': errors,
            'warnings': warnings,
            'prayer_count': prayer_count,
            'unmatched_solicitors': unmatched_solicitors,
        },
    )

    logger.info(
        'Gift import complete for %s: %d created, %d skipped, %d errors, '
        '%d prayers',
        filename,
        created_count,
        skipped_count,
        len(errors),
        prayer_count,
    )

    return batch


# ---------------------------------------------------------------------------
# Recurring Gift header aliases
# ---------------------------------------------------------------------------

RECURRING_GIFT_HEADER_ALIASES: dict[str, str] = {
    # Recurring Gift ID
    'recurring_gift_id': 'gift_id',
    'rg_id': 'gift_id',
    'recurring gift id': 'gift_id',
    'gift_id': 'gift_id',
    'gift id': 'gift_id',
    'gf_id': 'gift_id',
    # Constituent ID
    'gf_cnbio_id': 'constituent_id',
    'constituent_id': 'constituent_id',
    'constituent id': 'constituent_id',
    'cnbio_id': 'constituent_id',
    'consid': 'constituent_id',
    # Amount (per-installment)
    'gf_amount': 'amount',
    'amount': 'amount',
    'installment_amount': 'amount',
    'installment amount': 'amount',
    'solicitor amount': 'amount',
    # Frequency
    'gf_installment_frequency': 'frequency',
    'installment_frequency': 'frequency',
    'frequency': 'frequency',
    'installment frequency': 'frequency',
    'gift installment frequency': 'frequency',
    # Start date
    'gf_date': 'start_date',
    'start_date': 'start_date',
    'start date': 'start_date',
    'gift date': 'start_date',
    'date_1st_pay': 'start_date',
    # End date
    'gf_end_date': 'end_date',
    'end_date': 'end_date',
    'end date': 'end_date',
    # Status
    'gf_status': 'status',
    'status': 'status',
    'gift status': 'status',
    # Fund
    'gf_fund': 'fund',
    'fund': 'fund',
    'fund_id': 'fund',
    'fund id': 'fund',
    # Solicitor
    'solicitor_name': 'solicitor_name',
    'solicitor name': 'solicitor_name',
    'cnsol_1_01_name': 'solicitor_name',
    # Credit amount
    'credit_amount': 'credit_amount',
    'gf_cnsol_1_01_amount': 'credit_amount',
    # Prayer description
    'gift specific attributes prayer requests description': 'prayer_description',
    'prayer_requests_description': 'prayer_description',
    'prayer requests description': 'prayer_description',
    'prayer description': 'prayer_description',
    # Description
    'description': 'description',
    'gf_description': 'description',
}

RECURRING_GIFT_REQUIRED_CANONICAL = {'gift_id', 'constituent_id', 'amount'}


# ---------------------------------------------------------------------------
# Frequency and status mapping
# ---------------------------------------------------------------------------

FREQUENCY_MAP: dict[str, str] = {
    'monthly': RecurringGiftFrequency.MONTHLY,
    'quarterly': RecurringGiftFrequency.QUARTERLY,
    'semi-annually': RecurringGiftFrequency.SEMI_ANNUALLY,
    'semi-annual': RecurringGiftFrequency.SEMI_ANNUALLY,
    'semiannually': RecurringGiftFrequency.SEMI_ANNUALLY,
    'semi annually': RecurringGiftFrequency.SEMI_ANNUALLY,
    'annually': RecurringGiftFrequency.ANNUALLY,
    'annual': RecurringGiftFrequency.ANNUALLY,
    'yearly': RecurringGiftFrequency.ANNUALLY,
    'bimonthly': RecurringGiftFrequency.BIMONTHLY,
    'bi-monthly': RecurringGiftFrequency.BIMONTHLY,
    'bi monthly': RecurringGiftFrequency.BIMONTHLY,
    'biweekly': RecurringGiftFrequency.BIWEEKLY,
    'bi-weekly': RecurringGiftFrequency.BIWEEKLY,
    'bi weekly': RecurringGiftFrequency.BIWEEKLY,
    'weekly': RecurringGiftFrequency.WEEKLY,
    'irregular': RecurringGiftFrequency.IRREGULAR,
}

STATUS_MAP: dict[str, str] = {
    'active': RecurringGiftStatus.ACTIVE,
    'held': RecurringGiftStatus.HELD,
    'completed': RecurringGiftStatus.COMPLETED,
    'cancelled': RecurringGiftStatus.CANCELLED,
    'canceled': RecurringGiftStatus.CANCELLED,
    'terminated': RecurringGiftStatus.TERMINATED,
}


# ---------------------------------------------------------------------------
# Recurring Gift import orchestrator
# ---------------------------------------------------------------------------

def import_re_recurring_gifts(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    owner: User,
) -> ImportBatch:
    """Import RE Recurring Gift CSV end-to-end.

    Steps:
    1. SHA256 dedup check
    2. Decode with cascading encoding
    3. Parse CSV and validate headers via alias mapping
    4. Group rows by Recurring Gift ID (two-pass)
    5. Build solicitor + fund lookups
    6. Process each recurring gift group with savepoint isolation:
       a. Find Contact by constituent_id (skip group if not found)
       b. Check external_gift_id dedup against DB (skip if exists)
       c. Map frequency and status from RE string values
       d. Create RecurringGift with amount from first row
       e. Create RecurringGiftCredit for each solicitor row
    7. Create ImportBatch record with results

    Returns ImportBatch (may be existing if duplicate).
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: Check for duplicate
    existing = check_duplicate_import(file_bytes, ImportBatchType.RE_RECURRING_GIFT)
    if existing:
        logger.info('Duplicate recurring gift import detected for %s', filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing

    # Step 2: Decode
    try:
        content = skip_re_type_label_row(decode_csv_bytes(file_bytes))
    except ValueError as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_RECURRING_GIFT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': str(e)}]},
        )
        return batch

    # Step 3: Parse CSV and validate headers
    try:
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
    except Exception as e:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_RECURRING_GIFT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'CSV parse error: {e}'}]},
        )
        return batch

    col_map = _build_header_mapping(fieldnames, RECURRING_GIFT_HEADER_ALIASES)

    # Check required canonical fields
    missing_canonical = {
        name for name in RECURRING_GIFT_REQUIRED_CANONICAL
        if col_map.get(name) is None
    }
    if missing_canonical:
        expected_aliases = []
        for alias, canonical in RECURRING_GIFT_HEADER_ALIASES.items():
            if canonical in missing_canonical:
                expected_aliases.append(alias)
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_RECURRING_GIFT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={
                'errors': [{
                    'row': 0,
                    'error': (
                        f'Missing required recurring gift headers. '
                        f'Expected one of each: {", ".join(sorted(expected_aliases))}'
                    ),
                }],
            },
        )
        return batch

    # Step 4: Group rows by gift_id
    groups, grouping_errors, total_rows = _group_rows_by_id(
        reader, col_map, 'gift_id',
    )

    # Step 5: Build lookups
    solicitor_lookup = _build_solicitor_lookup()
    fund_lookup = _build_fund_lookup()

    # Step 6: Process each recurring gift group
    errors: list[dict] = list(grouping_errors)
    warnings: list[dict] = []
    created_count = 0
    skipped_count = 0
    unmatched_solicitors: list[str] = []

    try:
        with transaction.atomic():
            for gift_id, rows in groups.items():
                sp = transaction.savepoint()
                try:
                    first_row = rows[0]

                    # Look up Contact by constituent_id
                    constituent_id = first_row.get('constituent_id', '')
                    contact = None
                    if constituent_id:
                        contact = Contact.objects.filter(
                            external_constituent_id=constituent_id,
                        ).first()

                    if not contact:
                        row_nums = ', '.join(r['_row_number'] for r in rows)
                        errors.append({
                            'row': int(first_row['_row_number']),
                            'error': (
                                f'Constituent ID "{constituent_id}" not found '
                                f'-- skipping recurring gift group {gift_id} '
                                f'(rows {row_nums})'
                            ),
                        })
                        transaction.savepoint_rollback(sp)
                        continue

                    # Check for duplicate external_gift_id in database
                    if RecurringGift.objects.filter(
                        external_gift_id=gift_id,
                    ).exists():
                        skipped_count += 1
                        transaction.savepoint_rollback(sp)
                        continue

                    # Parse amount from first row
                    amount_cents = _parse_amount_to_cents(
                        first_row.get('amount', ''),
                    )
                    if amount_cents == 0:
                        errors.append({
                            'row': int(first_row['_row_number']),
                            'error': (
                                f'Row {first_row["_row_number"]}: Invalid amount '
                                f'"{first_row.get("amount", "")}" for recurring '
                                f'gift {gift_id}'
                            ),
                        })
                        transaction.savepoint_rollback(sp)
                        continue

                    # Parse start_date from first row (required)
                    start_date = _parse_date(first_row.get('start_date', ''))
                    if start_date is None:
                        errors.append({
                            'row': int(first_row['_row_number']),
                            'error': (
                                f'Row {first_row["_row_number"]}: Invalid or '
                                f'missing start date '
                                f'"{first_row.get("start_date", "")}" for '
                                f'recurring gift {gift_id}'
                            ),
                        })
                        transaction.savepoint_rollback(sp)
                        continue

                    # Parse end_date (optional -- None is acceptable)
                    end_date = _parse_date(first_row.get('end_date', ''))

                    # Map frequency
                    raw_frequency = first_row.get('frequency', '').strip()
                    if raw_frequency:
                        mapped_frequency = FREQUENCY_MAP.get(
                            raw_frequency.lower(),
                        )
                        if not mapped_frequency:
                            errors.append({
                                'row': int(first_row['_row_number']),
                                'error': (
                                    f'Row {first_row["_row_number"]}: Unknown '
                                    f'frequency "{raw_frequency}" for recurring '
                                    f'gift {gift_id}'
                                ),
                            })
                            transaction.savepoint_rollback(sp)
                            continue
                    else:
                        mapped_frequency = RecurringGiftFrequency.MONTHLY
                        warnings.append({
                            'row': int(first_row['_row_number']),
                            'warning': (
                                f'Row {first_row["_row_number"]}: Empty '
                                f'frequency for recurring gift {gift_id} '
                                f'-- defaulting to Monthly'
                            ),
                        })

                    # Map status
                    raw_status = first_row.get('status', '').strip()
                    if raw_status:
                        mapped_status = STATUS_MAP.get(raw_status.lower())
                        if not mapped_status:
                            errors.append({
                                'row': int(first_row['_row_number']),
                                'error': (
                                    f'Row {first_row["_row_number"]}: Unknown '
                                    f'status "{raw_status}" for recurring '
                                    f'gift {gift_id}'
                                ),
                            })
                            transaction.savepoint_rollback(sp)
                            continue
                    else:
                        mapped_status = RecurringGiftStatus.ACTIVE

                    # Match fund
                    fund_value = first_row.get('fund', '').lower()
                    matched_fund = None
                    if fund_value:
                        matched_fund = fund_lookup.get(fund_value)
                        if not matched_fund:
                            warnings.append({
                                'row': int(first_row['_row_number']),
                                'warning': (
                                    f'Fund "{first_row.get("fund", "")}" not '
                                    f'found for recurring gift {gift_id}'
                                ),
                            })

                    # Create RecurringGift
                    rg = RecurringGift.objects.create(
                        external_gift_id=gift_id,
                        donor_contact=contact,
                        amount_cents=amount_cents,
                        frequency=mapped_frequency,
                        start_date=start_date,
                        end_date=end_date,
                        status=mapped_status,
                        fund=matched_fund,
                        description=first_row.get('description', ''),
                    )

                    # Create RecurringGiftCredits -- one per row with a solicitor
                    for row in rows:
                        solicitor_name = row.get('solicitor_name', '')
                        if not solicitor_name:
                            continue
                        norm_name = normalize_solicitor_name(solicitor_name)
                        solicitor = solicitor_lookup.get(norm_name)
                        if not solicitor:
                            errors.append({
                                'row': int(row['_row_number']),
                                'error': (
                                    f'Row {row["_row_number"]}: Solicitor '
                                    f'"{solicitor_name}" not found -- credit '
                                    f'skipped for recurring gift {gift_id}'
                                ),
                            })
                            if norm_name not in unmatched_solicitors:
                                unmatched_solicitors.append(norm_name)
                            continue
                        credit_amount = _parse_amount_to_cents(
                            row.get('credit_amount', ''),
                        )
                        if credit_amount == 0:
                            credit_amount = amount_cents
                        RecurringGiftCredit.objects.create(
                            recurring_gift=rg,
                            solicitor=solicitor,
                            amount_cents=credit_amount,
                        )

                    transaction.savepoint_commit(sp)
                    created_count += 1

                except Exception as e:
                    transaction.savepoint_rollback(sp)
                    row_nums = ', '.join(
                        r.get('_row_number', '?') for r in rows
                    )
                    errors.append({
                        'row': int(rows[0].get('_row_number', 0)),
                        'error': (
                            f'Recurring gift group {gift_id} (rows {row_nums}): '
                            f'Unexpected error: {str(e)}'
                        ),
                    })

    except Exception as e:
        logger.error(
            'Recurring gift import failed for %s: %s', filename, e,
        )
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.RE_RECURRING_GIFT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': f'Import error: {e}'}]},
        )
        return batch

    # Step 7: Create ImportBatch record
    batch = ImportBatch.objects.create(
        import_type=ImportBatchType.RE_RECURRING_GIFT,
        status=ImportBatchStatus.COMPLETED,
        filename=filename,
        sha256_hash=sha256_hash,
        uploaded_by=uploaded_by,
        total_rows=total_rows,
        created_count=created_count,
        updated_count=0,
        skipped_count=skipped_count,
        error_count=len(errors),
        summary={
            'errors': errors,
            'warnings': warnings,
            'unmatched_solicitors': unmatched_solicitors,
        },
    )

    logger.info(
        'Recurring gift import complete for %s: %d created, %d skipped, '
        '%d errors',
        filename,
        created_count,
        skipped_count,
        len(errors),
    )

    return batch
