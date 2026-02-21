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

from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError

from apps.contacts.models import Contact
from apps.gifts.models import Solicitor
from apps.imports.models import ImportBatch, ImportBatchStatus, ImportBatchType
from apps.users.models import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def decode_csv_bytes(file_bytes: bytes) -> str:
    """Decode CSV bytes with cascading encoding fallback.

    RE exports may use UTF-8 (modern), UTF-8-sig (Excel BOM), or
    Windows-1252 (legacy with smart quotes, accented names).

    Raises ValueError if no encoding works (should never happen
    since Windows-1252 accepts all byte values 0x00-0xFF).
    """
    for encoding in ('utf-8-sig', 'utf-8', 'windows-1252'):
        try:
            return file_bytes.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError('Unable to decode file with any supported encoding')


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
        return existing

    # Step 2: Decode
    try:
        content = decode_csv_bytes(file_bytes)
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
                raw_name = (row.get(name_col) or '').strip()
                if not raw_name:
                    errors.append({
                        'row': row_number,
                        'error': 'Missing solicitor name',
                    })
                    continue

                # Extract external ID if present
                ext_id = ''
                if ext_id_col:
                    ext_id = (row.get(ext_id_col) or '').strip()

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
        return existing

    # Step 2: Decode
    try:
        content = decode_csv_bytes(file_bytes)
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
                    # Build row_data dict from mapped columns
                    row_data: dict[str, str] = {}
                    for canonical_name, actual_col in col_map.items():
                        if actual_col is not None:
                            row_data[canonical_name] = (row.get(actual_col) or '').strip()

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
