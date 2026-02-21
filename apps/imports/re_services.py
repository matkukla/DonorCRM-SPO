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

from django.db import transaction

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
