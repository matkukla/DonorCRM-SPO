"""
SPO (Support Processing Operations) import services.

Implements the three-step SPO data pipeline:
  Step 1 (plan 02): reconcile_missionaries() — establish the missionary User population
  Step 2 (plan 03): import_spo_gifts() — import gifts with GiftCredit attribution
  Step 3 (plan 03): import_spo_prayers() — prayer-only extraction pass

Both management commands and API endpoints call these service functions.
"""
import csv
import hashlib
import io
import logging
import re
import unicodedata
from typing import Optional

from django.db import transaction

from apps.contacts.models import Contact
from apps.gifts.models import Gift, GiftCredit, Solicitor
from apps.imports.models import (
    ImportBatch,
    ImportBatchStatus,
    ImportBatchType,
    MissionaryAlias,
    MPDSnapshot,
)
from apps.imports.re_services import (
    _build_header_mapping,
    _maybe_create_prayer_intention,
    _normalize_payment_type,
    _parse_amount_to_cents,
    _parse_date,
    check_duplicate_import,
    decode_csv_bytes,
    normalize_solicitor_name,
    skip_re_type_label_row,
)
from apps.users.models import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# reconcile_missionaries — Step 1 entry point
# ---------------------------------------------------------------------------

def reconcile_missionaries(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    force: bool = False,
) -> ImportBatch:
    """Reconcile SPO missionary User accounts from a Solicitors CSV.

    Three-level name matching:
      1. Exact full name match (normalized to 'last, first')
      2. Punctuation-stripped lowercase match (catches O'Brien vs OBrien)
      3. MissionaryAlias table lookup (admin-curated overrides)

    Unmatched names: auto-create User with role=missionary and placeholder
    email (firstname.lastname@spo.org). Suffix added on collision.

    Unresolvable names (MissionaryAlias with user=None): flagged and skipped —
    NOT auto-created. Names persisted to summary['unresolved_names'].

    Every resolved or created missionary User gets a corresponding Solicitor
    record so that import_spo_gifts (Step 2) can create GiftCredit attribution.

    Returns ImportBatch (DUPLICATE if same file already imported and not force).
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: SHA256 dedup
    existing = check_duplicate_import(file_bytes, ImportBatchType.SPO_MISSIONARY)
    if existing and not force:
        logger.info('Duplicate SPO missionary import detected for %s', filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing
    elif existing and force:
        # Remove old batch so we can create a fresh one with the same hash
        logger.info('Force flag set — re-importing %s (deleting old batch %s)', filename, existing.id)
        existing.delete()

    # Step 2: Decode CSV
    try:
        content = skip_re_type_label_row(decode_csv_bytes(file_bytes))
    except ValueError as e:
        return ImportBatch.objects.create(
            import_type=ImportBatchType.SPO_MISSIONARY,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': str(e)}]},
        )

    # Step 3: Parse CSV
    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames or []

    # Find the 'Name' column (case-insensitive)
    name_col = None
    for col in fieldnames:
        if col.strip().lower() == 'name':
            name_col = col
            break

    if name_col is None:
        return ImportBatch.objects.create(
            import_type=ImportBatchType.SPO_MISSIONARY,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': 'Missing required "Name" column'}]},
        )

    # Step 4: Build lookups
    # Include ALL active users (not just missionaries) to avoid creating duplicates
    all_active_users = User.objects.filter(is_active=True)
    user_lookup = _build_user_lookup(all_active_users)
    alias_lookup = _build_alias_lookup()

    # Step 5: Process rows
    total_rows = 0
    created_count = 0
    updated_count = 0
    skipped_count = 0

    matched_exact = 0
    matched_normalized = 0
    matched_alias = 0
    created = 0
    unresolved = 0
    unresolved_names: list[str] = []
    needs_real_email: list[str] = []
    per_missionary: list[dict] = []

    # Collect CSV names for tri-source comparison
    csv_names: set[str] = set()
    seen_in_csv: set[str] = set()  # dedup within file

    rows = list(reader)  # consume before tri-source query
    for row in rows:
        raw_name = (row.get(name_col) or '').strip()
        if not raw_name:
            skipped_count += 1
            continue

        total_rows += 1
        norm_key = normalize_solicitor_name(raw_name)

        # Dedup within file
        if norm_key in seen_in_csv:
            skipped_count += 1
            continue
        seen_in_csv.add(norm_key)
        csv_names.add(norm_key)

    # Re-parse (already consumed reader, use rows list)
    seen_in_csv_2: set[str] = set()

    with transaction.atomic():
        for row in rows:
            raw_name = (row.get(name_col) or '').strip()
            if not raw_name:
                continue

            norm_key = normalize_solicitor_name(raw_name)
            if norm_key in seen_in_csv_2:
                continue
            seen_in_csv_2.add(norm_key)

            matched_user, match_type = _match_missionary_name(raw_name, user_lookup, alias_lookup)

            entry: dict = {'name': raw_name, 'match_type': match_type}

            if match_type == 'unresolved':
                unresolved += 1
                unresolved_names.append(raw_name)
                skipped_count += 1
                entry['action'] = 'skipped_unresolved'

            elif match_type == 'new':
                # Auto-create missionary User
                new_user, placeholder_email = _auto_create_missionary_user(raw_name, uploaded_by)
                needs_real_email.append(placeholder_email)
                created += 1
                created_count += 1
                entry['action'] = 'created'
                entry['email'] = placeholder_email

                # Ensure Solicitor record exists for Step 2
                _get_or_create_missionary_solicitor(new_user)

                # Add to user_lookup for future rows in same file
                user_lookup[normalize_solicitor_name(new_user.full_name)] = new_user

            else:
                # matched_user is set (exact, normalized, alias)
                if match_type == 'exact':
                    matched_exact += 1
                elif match_type == 'normalized':
                    matched_normalized += 1
                elif match_type == 'alias':
                    matched_alias += 1

                # Merge-only: fill blank User fields from CSV name
                _merge_missionary_name_fields(matched_user, raw_name)
                updated_count += 1
                entry['action'] = 'matched'
                entry['email'] = matched_user.email

                # Ensure Solicitor record exists for Step 2
                _get_or_create_missionary_solicitor(matched_user)

            per_missionary.append(entry)

    # Step 6: Tri-source comparison
    # MPD names: all missionaries in MPD snapshots
    mpd_names: set[str] = set()
    for snap in MPDSnapshot.objects.select_related('user').values(
        'user__first_name', 'user__last_name'
    ).distinct():
        first = snap['user__first_name'] or ''
        last = snap['user__last_name'] or ''
        if first or last:
            mpd_names.add(normalize_solicitor_name(f'{first} {last}'.strip()))

    # DB names: all active missionary users
    db_names: set[str] = set()
    for user in User.objects.filter(is_active=True, role='missionary'):
        db_names.add(normalize_solicitor_name(user.full_name))

    tri_source = _build_tri_source_comparison(csv_names, mpd_names, db_names)
    # Convert sets to lists for JSON serialization
    tri_source_json = {k: sorted(v) for k, v in tri_source.items()}

    # Step 7: Create ImportBatch
    summary = {
        'missionaries_expected': len(csv_names),
        'matched_exact': matched_exact,
        'matched_normalized': matched_normalized,
        'matched_alias': matched_alias,
        'created': created,
        'unresolved': unresolved,
        'unresolved_names': unresolved_names,
        'needs_real_email': needs_real_email,
        'per_missionary': per_missionary,
        'tri_source': tri_source_json,
    }

    batch = ImportBatch.objects.create(
        import_type=ImportBatchType.SPO_MISSIONARY,
        status=ImportBatchStatus.COMPLETED,
        filename=filename,
        sha256_hash=sha256_hash,
        uploaded_by=uploaded_by,
        total_rows=total_rows,
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=0,
        summary=summary,
    )

    logger.info(
        'SPO missionary reconciliation complete for %s: '
        '%d exact, %d normalized, %d alias, %d created, %d unresolved',
        filename,
        matched_exact,
        matched_normalized,
        matched_alias,
        created,
        unresolved,
    )
    if unresolved_names:
        logger.warning('Unresolved missionary names: %s', ', '.join(unresolved_names))

    return batch


# ---------------------------------------------------------------------------
# Name matching helpers
# ---------------------------------------------------------------------------

def _match_missionary_name(
    raw_name: str,
    user_lookup: dict[str, 'User'],
    alias_lookup: dict[str, 'MissionaryAlias'],
) -> tuple[Optional['User'], str]:
    """Three-level match: exact → normalized → alias → ('unresolved'|'new').

    Returns:
        (user, 'exact')       — exact normalized name match in user_lookup
        (user, 'normalized')  — punctuation-stripped match in user_lookup
        (user, 'alias')       — alias table match with user set
        (None, 'unresolved')  — alias table match with user=None (admin-flagged)
        (None, 'new')         — no match found; caller should auto-create
    """
    # Level 1: Exact normalized match
    norm = normalize_solicitor_name(raw_name)
    if norm in user_lookup:
        return user_lookup[norm], 'exact'

    # Level 2: Punctuation-stripped (normalized) match
    stripped = _strip_punctuation(norm)
    for key, user in user_lookup.items():
        if _strip_punctuation(key) == stripped:
            return user, 'normalized'

    # Level 3: Alias table lookup
    alias_key = raw_name.strip().lower()
    if alias_key in alias_lookup:
        alias = alias_lookup[alias_key]
        if alias.user is None:
            return None, 'unresolved'
        return alias.user, 'alias'

    # No match
    return None, 'new'


def _strip_punctuation(name: str) -> str:
    """Remove all punctuation and normalize unicode for fuzzy matching.

    'o'brien, pat' → 'obrien pat'
    """
    # Normalize unicode (NFD so accents are decomposed)
    name = unicodedata.normalize('NFD', name)
    # Strip combining characters and punctuation
    result = ''.join(
        ch for ch in name
        if not unicodedata.combining(ch) and (ch.isalnum() or ch.isspace() or ch == ',')
    )
    # Remove remaining punctuation (apostrophes, hyphens, etc.)
    result = re.sub(r"[^\w\s,]", '', result)
    return result.lower().strip()


def _build_user_lookup(users_qs) -> dict[str, 'User']:
    """Build {normalized_name: User} dict for O(1) lookup.

    Uses normalize_solicitor_name() — 'last, first' lowercase form.
    Excludes ambiguous duplicates (two users same normalized name).
    """
    lookup: dict[str, User] = {}
    ambiguous: set[str] = set()

    for user in users_qs:
        key = normalize_solicitor_name(user.full_name)
        if not key:
            continue
        if key in ambiguous:
            continue
        if key in lookup:
            del lookup[key]
            ambiguous.add(key)
            logger.warning(
                'Ambiguous missionary name "%s" — excluding both users from auto-match',
                key,
            )
        else:
            lookup[key] = user

    return lookup


def _build_alias_lookup() -> dict[str, 'MissionaryAlias']:
    """Build {source_name_lower: MissionaryAlias} for O(1) alias lookup."""
    return {
        alias.source_name.strip().lower(): alias
        for alias in MissionaryAlias.objects.select_related('user').all()
    }


# ---------------------------------------------------------------------------
# Auto-create missionary User
# ---------------------------------------------------------------------------

def _auto_create_missionary_user(raw_name: str, uploaded_by: 'User') -> tuple['User', str]:
    """Create User with role='missionary' and placeholder email.

    Email: firstname.lastname@spo.org
    Collision: firstname.lastname2@spo.org, firstname.lastname3@spo.org, ...

    Returns (user, email).
    """
    name = raw_name.strip()
    # Parse first/last from "First Last" or "Last, First"
    if ',' in name:
        parts = [p.strip() for p in name.split(',', 1)]
        last_name = parts[0]
        first_name = parts[1] if len(parts) > 1 else ''
    else:
        parts = name.split()
        if len(parts) >= 2:
            first_name = ' '.join(parts[:-1])
            last_name = parts[-1]
        else:
            first_name = name
            last_name = ''

    # Build placeholder email
    email_first = first_name.lower().replace(' ', '.')
    email_last = last_name.lower().replace(' ', '.')
    base_email = f'{email_first}.{email_last}@spo.org'

    # Handle collision with numeric suffix
    email = base_email
    suffix = 2
    while User.objects.filter(email=email).exists():
        # Insert suffix before @
        local, domain = base_email.split('@')
        email = f'{local}{suffix}@{domain}'
        suffix += 1

    user = User.objects.create_user(
        email=email,
        password=User.objects.make_random_password(),
        first_name=first_name,
        last_name=last_name,
        role='missionary',
        is_active=True,
    )
    logger.info(
        'Auto-created missionary User: %s (email=%s)',
        user.full_name,
        email,
    )
    return user, email


def _merge_missionary_name_fields(user: 'User', raw_name: str) -> None:
    """Fill blank first_name/last_name fields from CSV name (merge-only, never overwrite)."""
    # Parse name
    name = raw_name.strip()
    if ',' in name:
        parts = [p.strip() for p in name.split(',', 1)]
        last_name = parts[0]
        first_name = parts[1] if len(parts) > 1 else ''
    else:
        parts = name.split()
        if len(parts) >= 2:
            first_name = ' '.join(parts[:-1])
            last_name = parts[-1]
        else:
            first_name = name
            last_name = ''

    updated_fields = []
    if not user.first_name and first_name:
        user.first_name = first_name
        updated_fields.append('first_name')
    if not user.last_name and last_name:
        user.last_name = last_name
        updated_fields.append('last_name')

    if updated_fields:
        user.save(update_fields=updated_fields)


# ---------------------------------------------------------------------------
# Tri-source comparison
# ---------------------------------------------------------------------------

def _build_tri_source_comparison(
    csv_names: set[str],
    mpd_names: set[str],
    db_names: set[str],
) -> dict[str, set[str]]:
    """Compare three name sets; return categorized dict.

    Categories:
        csv_only          — in CSV but not MPD or DB
        mpd_only          — in MPD but not CSV or DB
        db_only           — in DB but not CSV or MPD
        all_three         — in all three
        csv_and_mpd_not_db — in CSV and MPD but not DB
        csv_and_db_not_mpd — in CSV and DB but not MPD
        mpd_and_db_not_csv — in MPD and DB but not CSV
    """
    return {
        'csv_only': csv_names - mpd_names - db_names,
        'mpd_only': mpd_names - csv_names - db_names,
        'db_only': db_names - csv_names - mpd_names,
        'all_three': csv_names & mpd_names & db_names,
        'csv_and_mpd_not_db': (csv_names & mpd_names) - db_names,
        'csv_and_db_not_mpd': (csv_names & db_names) - mpd_names,
        'mpd_and_db_not_csv': (mpd_names & db_names) - csv_names,
    }


# ---------------------------------------------------------------------------
# Solicitor and Contact helpers
# ---------------------------------------------------------------------------

def _get_or_create_missionary_solicitor(missionary: 'User') -> 'Solicitor':
    """Get or create a Solicitor record for a missionary User.

    Required so import_spo_gifts (Step 2) can create GiftCredit attribution
    rows via the Solicitor FK. Idempotent — safe to call on re-runs.
    """
    solicitor, created = Solicitor.objects.get_or_create(
        user=missionary,
        defaults={
            'normalized_name': normalize_solicitor_name(missionary.full_name),
        },
    )
    if created:
        logger.debug(
            'Created Solicitor record for missionary %s (id=%d)',
            missionary.email,
            solicitor.id,
        )
    return solicitor


def _get_or_create_anonymous_contact(missionary: 'User') -> 'Contact':
    """Get or create the per-missionary Anonymous Donor contact.

    The external_id key ensures idempotency — same contact reused across
    multiple gift imports for the same missionary.

    Contact.owner = missionary ensures supervisor/coach scope visibility
    works without code changes.
    """
    contact, created = Contact.objects.get_or_create(
        owner=missionary,
        external_id=f'spo_anonymous_{missionary.id}',
        defaults={
            'first_name': 'Anonymous',
            'last_name': 'Donor',
            'status': 'donor',
        },
    )
    if created:
        logger.debug(
            'Created Anonymous Donor contact for missionary %s',
            missionary.email,
        )
    return contact


# ---------------------------------------------------------------------------
# SPO Gift header aliases
# ---------------------------------------------------------------------------

# Nested form: {canonical: [alias1, alias2, ...]}
# Used to build the flat alias_map for _build_header_mapping.
_SPO_GIFT_HEADER_ALIASES_NESTED: dict[str, list[str]] = {
    'gift_id': ['Gift ID', 'GiftID', 'gift_id'],
    'constituent_id': ['Constituent ID', 'ConstituentID', 'constituent_id'],
    'is_anonymous': ['Gift Is Anonymous', 'IsAnonymous', 'is_anonymous'],
    'solicitor_name': ['Solicitor Name', 'SolicitorName', 'solicitor_name'],
    'solicitor_amount': ['Solicitor Amount', 'SolicitorAmount', 'solicitor_amount'],
    'gift_amount': ['Gift Amount', 'Fund Split Amount', 'Amount', 'gift_amount'],
    'gift_date': ['Gift Date', 'Date', 'gift_date'],
    'payment_type': ['Gift Payment Type', 'Payment Type', 'payment_type'],
    'prayer_description': [
        'Gift Specific Attributes Prayer Requests Description',
        'Prayer Description',
        'prayer_description',
    ],
}

# Flat alias map: {alias_lowercase: canonical_name}
SPO_GIFT_HEADER_ALIAS_MAP: dict[str, str] = {
    alias.lower(): canonical
    for canonical, aliases in _SPO_GIFT_HEADER_ALIASES_NESTED.items()
    for alias in aliases
}


# ---------------------------------------------------------------------------
# import_spo_gifts — Step 2 entry point
# ---------------------------------------------------------------------------

def import_spo_gifts(
    file_bytes: bytes,
    filename: str,
    uploaded_by: 'User',
    force: bool = False,
) -> ImportBatch:
    """Step 2: Import SPO gifts CSV, attribute to missionaries, create GiftCredit records.

    Contact resolution:
      - Named donor:     Contact.objects.filter(external_constituent_id=...).first()
      - Anonymous/blank: _get_or_create_anonymous_contact(missionary)
      - Unresolved sol:  skip row, count in summary['unmatched_unresolved']
      - Contact not found: skip row, count in summary['contact_not_found']

    GiftCredit: created after each Gift for the missionary's Solicitor record
    (created by reconcile_missionaries in plan 02).

    Prayer: _maybe_create_prayer_intention() called when description column non-empty.

    Row errors isolated via savepoints — one bad row does not roll back others.

    Returns ImportBatch (DUPLICATE if same file already imported and not force).
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: SHA256 dedup
    existing = check_duplicate_import(file_bytes, ImportBatchType.SPO_GIFT)
    if existing and not force:
        logger.info('Duplicate SPO gift import detected for %s', filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing
    elif existing and force:
        logger.info(
            'Force flag set — re-importing gifts %s (deleting old batch %s)',
            filename, existing.id,
        )
        existing.delete()

    # Step 2: Decode CSV
    try:
        content = skip_re_type_label_row(decode_csv_bytes(file_bytes))
    except ValueError as e:
        return ImportBatch.objects.create(
            import_type=ImportBatchType.SPO_GIFT,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': str(e)}]},
        )

    # Step 3: Parse CSV headers
    reader = csv.DictReader(io.StringIO(content))
    fieldnames = list(reader.fieldnames or [])
    col_map = _build_header_mapping(fieldnames, SPO_GIFT_HEADER_ALIAS_MAP)

    # Helper to safely read a canonical column from a row
    def _get(row, canonical):
        actual_col = col_map.get(canonical)
        if actual_col is None:
            return ''
        return (row.get(actual_col) or '').strip()

    # Step 4: Pre-build missionary lookups
    all_active_users = User.objects.filter(is_active=True)
    user_lookup = _build_user_lookup(all_active_users)
    alias_lookup = _build_alias_lookup()

    # Pre-build solicitor lookup: {user_id: Solicitor}
    solicitor_by_user_id: dict[int, Solicitor] = {
        s.user_id: s
        for s in Solicitor.objects.filter(user__isnull=False).select_related('user')
    }

    # Step 5: Process rows
    total_rows = 0
    created_count = 0
    skipped_count = 0
    error_count = 0

    unmatched_unresolved: list[str] = []
    contact_not_found: list[str] = []
    errors: list[dict] = []
    per_missionary: list[dict] = []
    seen_prayers: dict = {}

    rows = list(reader)

    with transaction.atomic():
        for row_num, row in enumerate(rows, start=2):  # row 1 = headers
            gift_id = _get(row, 'gift_id')
            if not gift_id:
                skipped_count += 1
                continue

            total_rows += 1
            solicitor_name_raw = _get(row, 'solicitor_name')
            constituent_id = _get(row, 'constituent_id')
            is_anonymous_raw = _get(row, 'is_anonymous').lower()
            gift_amount_raw = _get(row, 'gift_amount')
            solicitor_amount_raw = _get(row, 'solicitor_amount')
            gift_date_raw = _get(row, 'gift_date')
            prayer_description = _get(row, 'prayer_description')

            sp = transaction.savepoint()
            try:
                # 7a. Resolve missionary via solicitor_name column
                missionary, match_type = _match_missionary_name(
                    solicitor_name_raw, user_lookup, alias_lookup,
                )
                if missionary is None:
                    # 'unresolved' (alias with user=None) or 'new' (unknown name)
                    # Either way: no Solicitor record exists → skip
                    logger.debug(
                        'Skipping gift %s — unresolved solicitor "%s" (match_type=%s)',
                        gift_id, solicitor_name_raw, match_type,
                    )
                    unmatched_unresolved.append(solicitor_name_raw)
                    skipped_count += 1
                    transaction.savepoint_rollback(sp)
                    continue

                # 7b. Resolve contact
                is_anonymous = is_anonymous_raw in ('yes', 'true', '1')
                if is_anonymous or not constituent_id:
                    contact = _get_or_create_anonymous_contact(missionary)
                else:
                    contact = Contact.objects.filter(
                        external_constituent_id=constituent_id,
                        is_merged=False,
                    ).first()
                    if contact is None:
                        logger.debug(
                            'Skipping gift %s — contact not found for constituent_id=%s',
                            gift_id, constituent_id,
                        )
                        contact_not_found.append(constituent_id)
                        skipped_count += 1
                        transaction.savepoint_rollback(sp)
                        continue

                # 7c. Idempotency: skip if gift already exists
                if Gift.objects.filter(external_gift_id=gift_id).exists():
                    logger.debug('Skipping gift %s — already imported', gift_id)
                    skipped_count += 1
                    transaction.savepoint_commit(sp)
                    continue

                # 7d. Parse gift fields
                amount_cents = _parse_amount_to_cents(gift_amount_raw)
                if amount_cents == 0:
                    errors.append({'row': row_num, 'error': f'Unparseable or zero amount: {gift_amount_raw!r}'})
                    error_count += 1
                    transaction.savepoint_rollback(sp)
                    continue

                gift_date = _parse_date(gift_date_raw)
                if gift_date is None:
                    errors.append({'row': row_num, 'error': f'Invalid date: {gift_date_raw!r}'})
                    error_count += 1
                    transaction.savepoint_rollback(sp)
                    continue

                payment_type_raw = _get(row, 'payment_type')
                payment_type = _normalize_payment_type(payment_type_raw)

                # 7d. Create Gift
                gift = Gift.objects.create(
                    donor_contact=contact,
                    amount_cents=amount_cents,
                    gift_date=gift_date,
                    external_gift_id=gift_id,
                    payment_type=payment_type,
                )

                # 7e. Create GiftCredit for missionary's Solicitor
                solicitor = solicitor_by_user_id.get(missionary.id)
                if solicitor is None:
                    # Solicitor should exist (created by plan 02 reconcile), but be safe
                    solicitor = _get_or_create_missionary_solicitor(missionary)
                    solicitor_by_user_id[missionary.id] = solicitor

                credit_amount_cents = _parse_amount_to_cents(solicitor_amount_raw) or amount_cents
                GiftCredit.objects.get_or_create(
                    gift=gift,
                    solicitor=solicitor,
                    defaults={'amount_cents': credit_amount_cents},
                )

                # 7f. Prayer intention
                if prayer_description:
                    _maybe_create_prayer_intention(gift, prayer_description, contact, seen_prayers)

                created_count += 1
                per_missionary.append({
                    'gift_id': gift_id,
                    'missionary': solicitor_name_raw,
                    'match_type': match_type,
                    'constituent_id': constituent_id,
                    'amount_cents': amount_cents,
                })
                transaction.savepoint_commit(sp)

            except Exception as exc:
                logger.exception('Error processing gift row %d (gift_id=%s): %s', row_num, gift_id, exc)
                errors.append({'row': row_num, 'error': str(exc)})
                error_count += 1
                transaction.savepoint_rollback(sp)

    summary = {
        'created': created_count,
        'skipped': skipped_count,
        'errors': error_count,
        'unmatched_unresolved': unmatched_unresolved,
        'contact_not_found': contact_not_found,
        'per_missionary': per_missionary,
        'error_details': errors,
    }

    batch = ImportBatch.objects.create(
        import_type=ImportBatchType.SPO_GIFT,
        status=ImportBatchStatus.COMPLETED,
        filename=filename,
        sha256_hash=sha256_hash,
        uploaded_by=uploaded_by,
        total_rows=total_rows,
        created_count=created_count,
        skipped_count=skipped_count,
        error_count=error_count,
        summary=summary,
    )

    logger.info(
        'SPO gift import complete for %s: %d created, %d skipped, %d errors',
        filename, created_count, skipped_count, error_count,
    )
    return batch


# ---------------------------------------------------------------------------
# import_spo_prayers — Step 3 entry point
# ---------------------------------------------------------------------------

def import_spo_prayers(
    file_bytes: bytes,
    filename: str,
    uploaded_by: 'User',
    force: bool = False,
) -> ImportBatch:
    """Step 3: Extract prayer intentions from SPO gifts CSV (prayer-only rerun pass).

    Reads the same gifts CSV format as import_spo_gifts() but ONLY extracts
    prayer intentions. No Gift or GiftCredit records are created.

    Uses ImportBatchType.SPO_PRAYER for dedup — separate namespace from SPO_GIFT,
    allowing this pass to run independently after a force gift re-import.

    Prayer import is best-effort: unresolvable contacts cause a graceful skip
    (not a failure), since prayer data is not financial.

    Returns ImportBatch with created_count = prayer intentions created.
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: SHA256 dedup
    existing = check_duplicate_import(file_bytes, ImportBatchType.SPO_PRAYER)
    if existing and not force:
        logger.info('Duplicate SPO prayer import detected for %s', filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing
    elif existing and force:
        logger.info(
            'Force flag set — re-importing prayers %s (deleting old batch %s)',
            filename, existing.id,
        )
        existing.delete()

    # Step 2: Decode CSV
    try:
        content = skip_re_type_label_row(decode_csv_bytes(file_bytes))
    except ValueError as e:
        return ImportBatch.objects.create(
            import_type=ImportBatchType.SPO_PRAYER,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={'errors': [{'row': 0, 'error': str(e)}]},
        )

    # Step 3: Parse CSV headers
    reader = csv.DictReader(io.StringIO(content))
    fieldnames = list(reader.fieldnames or [])
    col_map = _build_header_mapping(fieldnames, SPO_GIFT_HEADER_ALIAS_MAP)

    def _get(row, canonical):
        actual_col = col_map.get(canonical)
        if actual_col is None:
            return ''
        return (row.get(actual_col) or '').strip()

    # Step 4: Pre-build missionary lookups
    all_active_users = User.objects.filter(is_active=True)
    user_lookup = _build_user_lookup(all_active_users)
    alias_lookup = _build_alias_lookup()

    # Step 5: Process rows — prayer extraction only
    total_rows = 0
    created_count = 0
    skipped_count = 0
    seen_prayers: dict = {}
    rows = list(reader)

    with transaction.atomic():
        for row in rows:
            gift_id = _get(row, 'gift_id')
            prayer_description = _get(row, 'prayer_description')
            if not prayer_description:
                skipped_count += 1
                continue

            total_rows += 1
            solicitor_name_raw = _get(row, 'solicitor_name')
            constituent_id = _get(row, 'constituent_id')
            is_anonymous_raw = _get(row, 'is_anonymous').lower()

            # Resolve missionary (best-effort)
            missionary, match_type = _match_missionary_name(
                solicitor_name_raw, user_lookup, alias_lookup,
            )
            if missionary is None:
                # Best-effort: can't link prayer to missionary — skip
                skipped_count += 1
                continue

            # Resolve contact (best-effort)
            is_anonymous = is_anonymous_raw in ('yes', 'true', '1')
            if is_anonymous or not constituent_id:
                contact = _get_or_create_anonymous_contact(missionary)
            else:
                contact = Contact.objects.filter(
                    external_constituent_id=constituent_id,
                ).first()
                if contact is None:
                    # Best-effort: skip unresolvable contacts
                    skipped_count += 1
                    continue

            # Look up existing Gift for M2M linkage (if imported already)
            gift = Gift.objects.filter(external_gift_id=gift_id).first() if gift_id else None

            sp = transaction.savepoint()
            try:
                if gift is not None:
                    result = _maybe_create_prayer_intention(gift, prayer_description, contact, seen_prayers)
                    if result:
                        created_count += 1
                else:
                    # No gift to link — create prayer intention without M2M
                    from apps.prayers.models import PrayerIntention, PrayerIntentionStatus
                    PRAYER_STOPLIST = {
                        'n/a', 'na', 'none', 'no', '-', '--', '---', 'no prayer request',
                        'x', 'xx', 'xxx', 'general', 'same', 'same as above',
                        'see above', 'ditto', 'tbd', 'unknown',
                    }
                    text = prayer_description.strip()
                    if text and text.lower() not in PRAYER_STOPLIST and any(c.isalnum() for c in text):
                        normalized = text.lower().strip()
                        dedup_key = (contact.id, normalized)
                        if dedup_key not in seen_prayers:
                            existing_prayer = PrayerIntention.objects.filter(
                                contact=contact,
                                description__iexact=text,
                            ).first()
                            if existing_prayer:
                                seen_prayers[dedup_key] = existing_prayer
                            else:
                                title = text[:80].rsplit(' ', 1)[0] if len(text) > 80 else text
                                prayer = PrayerIntention.objects.create(
                                    contact=contact,
                                    title=title,
                                    description=text,
                                    status=PrayerIntentionStatus.ACTIVE,
                                )
                                seen_prayers[dedup_key] = prayer
                                created_count += 1
                transaction.savepoint_commit(sp)
            except Exception as exc:
                logger.exception('Error extracting prayer from gift %s: %s', gift_id, exc)
                transaction.savepoint_rollback(sp)

    summary = {
        'prayers_created': created_count,
        'skipped': skipped_count,
    }

    batch = ImportBatch.objects.create(
        import_type=ImportBatchType.SPO_PRAYER,
        status=ImportBatchStatus.COMPLETED,
        filename=filename,
        sha256_hash=sha256_hash,
        uploaded_by=uploaded_by,
        total_rows=total_rows,
        created_count=created_count,
        skipped_count=skipped_count,
        summary=summary,
    )

    logger.info(
        'SPO prayer extraction complete for %s: %d prayers created, %d skipped',
        filename, created_count, skipped_count,
    )
    return batch
