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

from django.db import IntegrityError, transaction

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
    "first_name": "first_name",
    "first name": "first_name",
    "firstname": "first_name",
    "fname": "first_name",
    "given name": "first_name",
    "given_name": "first_name",
    # last_name
    "last_name": "last_name",
    "last name": "last_name",
    "lastname": "last_name",
    "lname": "last_name",
    "surname": "last_name",
    "family name": "last_name",
    "family_name": "last_name",
    # email
    "email": "email",
    "email_address": "email",
    "email address": "email",
    "e-mail": "email",
    # phone
    "phone": "phone",
    "phone_number": "phone",
    "phone number": "phone",
    "mobile": "phone",
    "cell": "phone",
    # external_id
    "external_id": "external_id",
    "id": "external_id",
    "contact_id": "external_id",
    # organization_name
    "organization": "organization_name",
    "org_name": "organization_name",
    "organization_name": "organization_name",
    "company": "organization_name",
    # street_address
    "street_address": "street_address",
    "address": "street_address",
    "street": "street_address",
    # city
    "city": "city",
    # state
    "state": "state",
    "province": "state",
    # postal_code
    "postal_code": "postal_code",
    "zip": "postal_code",
    "zip_code": "postal_code",
    "zipcode": "postal_code",
    # country
    "country": "country",
    # notes
    "notes": "notes",
    "note": "notes",
    "comments": "notes",
}


# ---------------------------------------------------------------------------
# Generic donation header aliases
# ---------------------------------------------------------------------------

GENERIC_DONATION_HEADER_ALIASES: dict[str, str] = {
    # contact_first_name
    "contact_first_name": "contact_first_name",
    "first_name": "contact_first_name",
    "first name": "contact_first_name",
    "firstname": "contact_first_name",
    "donor_first_name": "contact_first_name",
    "donor first name": "contact_first_name",
    # contact_last_name
    "contact_last_name": "contact_last_name",
    "last_name": "contact_last_name",
    "last name": "contact_last_name",
    "lastname": "contact_last_name",
    "donor_last_name": "contact_last_name",
    "donor last name": "contact_last_name",
    # contact_email
    "contact_email": "contact_email",
    "email": "contact_email",
    "email_address": "contact_email",
    "donor_email": "contact_email",
    # contact_external_id
    "contact_external_id": "contact_external_id",
    "external_id": "contact_external_id",
    "contact_id": "contact_external_id",
    "donor_id": "contact_external_id",
    # amount
    "amount": "amount",
    "gift_amount": "amount",
    "donation_amount": "amount",
    "total": "amount",
    # date
    "date": "date",
    "gift_date": "date",
    "donation_date": "date",
    # description
    "description": "description",
    "memo": "description",
    "notes": "description",
    "purpose": "description",
    # fund_name
    "fund": "fund_name",
    "fund_name": "fund_name",
    "campaign": "fund_name",
    "account": "fund_name",
    # external_gift_id -- per-gift idempotency key (NOT the contact's external id)
    "external_gift_id": "external_gift_id",
    "gift_id": "external_gift_id",
    "gift_external_id": "external_gift_id",
    "transaction_id": "external_gift_id",
    "donation_id": "external_gift_id",
    "reference": "external_gift_id",
    "reference_number": "external_gift_id",
}

VALID_MATCH_BY = ("name", "email", "external_id")


def _generic_gift_identity(
    *,
    explicit_id: str,
    owner_id,
    contact_id,
    amount_cents: int,
    gift_date,
    fund_id,
    description: str,
) -> str:
    """Return a stable per-gift idempotency key for a generic donation row.

    Both forms are namespaced so generic identities never collide with the raw
    ``external_gift_id`` values that the RE/SPO importers write into the same
    globally-unique column. Without a namespace, a generic ``gift_id`` of "100"
    would dedup against an unrelated RE gift "100" and silently drop a real
    donation -- under-counting a donor.

    - Explicit CSV gift ID -> ``genid:<id>`` (idempotent across generic
      re-uploads regardless of changed fund/amount/memo). Source IDs too long
      to fit the 100-char column once prefixed are hashed to ``genidh:<sha256>``
      instead -- deterministic, so re-uploads still dedup, with no truncation
      collision between two distinct long IDs sharing a prefix.
    - No ID -> deterministic ``gen:<sha256>`` over the gift's *normalized*
      identity (owner, donor, amount in cents, parsed date (ISO), fund,
      description). Normalizing before hashing means a re-export with reordered
      columns or a reformatted date yields the same key, so re-uploads dedup
      via the ``unique_external_gift_id`` constraint instead of double-counting.

    Funds and descriptions are part of the hashed identity so that two genuinely
    distinct gifts (same donor/amount/date, different fund or memo) are not
    collapsed on first import. The trade-off: with no explicit ID, a later
    correction to the fund or memo looks like a new gift -- still far better
    than the old whole-file hash, which re-created *every* row.
    """
    if explicit_id:
        namespaced = "genid:" + explicit_id
        # external_gift_id is CharField(max_length=100); _sanitize_field only
        # caps at 10k, so an overlong source ID would raise DataError on
        # Postgres (and store silently on SQLite). Hash those to a fixed,
        # collision-free key that stays within budget.
        if len(namespaced) <= 100:
            return namespaced
        return "genidh:" + hashlib.sha256(explicit_id.encode("utf-8")).hexdigest()
    parts = "|".join(
        [
            str(owner_id),
            str(contact_id),
            str(amount_cents),
            gift_date.isoformat(),
            str(fund_id) if fund_id is not None else "",
            description,
        ]
    )
    return "gen:" + hashlib.sha256(parts.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Generic contact import orchestrator
# ---------------------------------------------------------------------------


def import_generic_contacts(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    owner: User,
    match_by: str = "email",
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
        logger.info("Duplicate generic contact import detected for %s", filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=["status"])
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
            summary={"errors": [{"row": 0, "error": type(e).__name__}]},
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
            summary={"errors": [{"row": 0, "error": f"CSV parse error: {type(e).__name__}"}]},
        )
        return batch

    col_map = _build_header_mapping(fieldnames, GENERIC_CONTACT_HEADER_ALIASES)

    # Step 4: Validate required headers based on match_by
    missing_headers = []
    if match_by == "name":
        if col_map.get("first_name") is None:
            missing_headers.append("first_name")
        if col_map.get("last_name") is None:
            missing_headers.append("last_name")
    elif match_by == "email":
        if col_map.get("email") is None:
            missing_headers.append("email")
    elif match_by == "external_id":
        if col_map.get("external_id") is None:
            missing_headers.append("external_id")

    # Always require name or org columns for new contact creation
    has_name_headers = (
        col_map.get("first_name") is not None and col_map.get("last_name") is not None
    )
    has_org_header = col_map.get("organization_name") is not None
    if not has_name_headers and not has_org_header:
        missing_headers.append("(first_name + last_name) or organization_name")

    if missing_headers:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_CONTACTS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={
                "errors": [
                    {
                        "row": 0,
                        "error": (
                            f"Missing required headers for match_by={match_by}: "
                            f'{", ".join(missing_headers)}'
                        ),
                    }
                ],
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
                                row.get(actual_col) or "",
                            )

                    # Match contact based on match_by
                    contact = None
                    multiple_matches = False

                    if match_by == "name":
                        first_name = row_data.get("first_name", "")
                        last_name = row_data.get("last_name", "")
                        if not first_name or not last_name:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: Missing first_name or "
                                        f"last_name for name matching"
                                    ),
                                }
                            )
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

                    elif match_by == "email":
                        email = row_data.get("email", "")
                        if not email:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: Missing email for " f"email matching"
                                    ),
                                }
                            )
                            continue
                        # email is encrypted; equality lookups go via blind index.
                        from apps.core.blind_index import lookup_hashes

                        email_hashes = lookup_hashes(email)
                        contact = (
                            Contact.objects.filter(
                                owner=owner,
                                email_hash__in=email_hashes,
                                is_merged=False,
                            ).first()
                            if email_hashes
                            else None
                        )

                    elif match_by == "external_id":
                        external_id = row_data.get("external_id", "")
                        if not external_id:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: Missing external_id for "
                                        f"external_id matching"
                                    ),
                                }
                            )
                            continue
                        contact = Contact.objects.filter(
                            owner=owner,
                            external_id=external_id,
                            is_merged=False,
                        ).first()

                    if multiple_matches:
                        errors.append(
                            {
                                "row": row_number,
                                "error": (
                                    f"Row {row_number}: Multiple contacts match "
                                    f"-- use email or external ID matching"
                                ),
                            }
                        )
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
                        first_name = row_data.get("first_name", "")
                        last_name = row_data.get("last_name", "")
                        org_name = row_data.get("organization_name", "")

                        has_name = first_name and last_name
                        has_org = bool(org_name)

                        if not has_name and not has_org:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: Missing name or "
                                        f"organization -- cannot create contact"
                                    ),
                                }
                            )
                            continue

                        new_contact_data = {
                            "owner": owner,
                            "first_name": first_name,
                            "last_name": last_name,
                        }
                        if org_name:
                            new_contact_data["organization_name"] = org_name

                        # Add optional fields
                        optional_fields = [
                            "email",
                            "phone",
                            "street_address",
                            "city",
                            "state",
                            "postal_code",
                            "country",
                            "notes",
                        ]
                        for field in optional_fields:
                            value = row_data.get(field, "")
                            if value:
                                new_contact_data[field] = value

                        # Add external_id if present
                        ext_id = row_data.get("external_id", "")
                        if ext_id:
                            new_contact_data["external_id"] = ext_id

                        Contact.objects.create(**new_contact_data)
                        created_count += 1

                except Exception as e:
                    logger.exception(
                        "Row %s failed in import_generic_contacts",
                        row_number,
                    )
                    errors.append(
                        {
                            "row": row_number,
                            "error": f"Row {row_number}: {type(e).__name__}",
                        }
                    )

    except Exception as e:
        # logger.exception attaches the traceback so a programming error
        # (AttributeError, TypeError, KeyError, etc) surfaces in Sentry
        # rather than getting silently rolled into a FAILED ImportBatch.
        logger.exception("Generic contact import failed for %s", filename)
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_CONTACTS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={"errors": [{"row": 0, "error": f"Import error: {type(e).__name__}"}]},
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
        summary={"errors": errors},
    )

    logger.info(
        "Generic contact import complete for %s: %d created, %d updated, " "%d skipped, %d errors",
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
    match_by: str = "email",
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
        logger.info("Duplicate generic donation import detected for %s", filename)
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=["status"])
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
            summary={"errors": [{"row": 0, "error": type(e).__name__}]},
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
            summary={"errors": [{"row": 0, "error": f"CSV parse error: {type(e).__name__}"}]},
        )
        return batch

    col_map = _build_header_mapping(fieldnames, GENERIC_DONATION_HEADER_ALIASES)

    # Step 4: Validate required headers
    missing_headers = []
    if col_map.get("amount") is None:
        missing_headers.append("amount")
    if col_map.get("date") is None:
        missing_headers.append("date")

    # Contact matching columns
    if match_by == "name":
        if col_map.get("contact_first_name") is None:
            missing_headers.append("contact_first_name")
        if col_map.get("contact_last_name") is None:
            missing_headers.append("contact_last_name")
    elif match_by == "email":
        if col_map.get("contact_email") is None:
            missing_headers.append("contact_email")
    elif match_by == "external_id":
        if col_map.get("contact_external_id") is None:
            missing_headers.append("contact_external_id")

    if missing_headers:
        batch = ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_DONATIONS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={
                "errors": [
                    {
                        "row": 0,
                        "error": (
                            f"Missing required headers for match_by={match_by}: "
                            f'{", ".join(missing_headers)}'
                        ),
                    }
                ],
            },
        )
        return batch

    # Step 5: Iterate rows with error collection.
    #
    # The ImportBatch row carries the unique (import_type, sha256_hash)
    # constraint. It is created FIRST, inside the same transaction as the
    # gifts, so two concurrent identical uploads collide on that constraint and
    # the loser rolls back its gifts instead of double-committing them.
    errors: list[dict] = []
    created_count = 0
    skipped_count = 0
    total_rows = 0
    affected_contact_ids: set = set()

    # Bulk-import fast path (issue #118): suppress the per-gift stat/notification
    # signal cascade and recompute each affected contact exactly once at the end,
    # so a large synchronous import stays inside the request timeout.
    from apps.gifts.signals import disable_gift_signals, enable_gift_signals, recompute_giving_stats

    disable_gift_signals()
    try:
        with transaction.atomic():
            batch = ImportBatch.objects.create(
                import_type=ImportBatchType.GENERIC_DONATIONS,
                status=ImportBatchStatus.PROCESSING,
                filename=filename,
                sha256_hash=sha256_hash,
                uploaded_by=uploaded_by,
            )

            for row_number, row in enumerate(reader, start=2):
                total_rows += 1

                try:
                    # Build row_data from col_map with sanitization
                    row_data: dict[str, str] = {}
                    for canonical_name, actual_col in col_map.items():
                        if actual_col is not None:
                            row_data[canonical_name] = _sanitize_field(
                                row.get(actual_col) or "",
                            )

                    # Parse amount
                    amount_cents = _parse_amount_to_cents(
                        row_data.get("amount", ""),
                    )
                    if amount_cents <= 0:
                        errors.append(
                            {
                                "row": row_number,
                                "error": (
                                    f"Row {row_number}: Invalid or zero amount "
                                    f'"{row_data.get("amount", "")}"'
                                ),
                            }
                        )
                        continue

                    # Parse date
                    parsed_date = _parse_date(row_data.get("date", ""))
                    if parsed_date is None:
                        errors.append(
                            {
                                "row": row_number,
                                "error": (
                                    f"Row {row_number}: Invalid date "
                                    f'"{row_data.get("date", "")}"'
                                ),
                            }
                        )
                        continue

                    # Match contact
                    contact = None

                    if match_by == "name":
                        first_name = row_data.get("contact_first_name", "")
                        last_name = row_data.get("contact_last_name", "")
                        if not first_name or not last_name:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: Missing contact name "
                                        f"for name matching"
                                    ),
                                }
                            )
                            continue
                        contact = Contact.objects.filter(
                            owner=owner,
                            first_name__iexact=first_name,
                            last_name__iexact=last_name,
                            is_merged=False,
                        ).first()
                        if not contact:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: No contact found "
                                        f"matching the provided name "
                                        f"-- import contacts first"
                                    ),
                                }
                            )
                            continue

                    elif match_by == "email":
                        email = row_data.get("contact_email", "")
                        if not email:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: Missing email for " f"email matching"
                                    ),
                                }
                            )
                            continue
                        # email is encrypted; equality lookups go via blind index.
                        from apps.core.blind_index import lookup_hashes

                        email_hashes = lookup_hashes(email)
                        contact = (
                            Contact.objects.filter(
                                owner=owner,
                                email_hash__in=email_hashes,
                                is_merged=False,
                            ).first()
                            if email_hashes
                            else None
                        )
                        if not contact:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: No contact found "
                                        f"matching the provided email "
                                        f"-- import contacts first"
                                    ),
                                }
                            )
                            continue

                    elif match_by == "external_id":
                        ext_id = row_data.get("contact_external_id", "")
                        if not ext_id:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: Missing external_id "
                                        f"for external_id matching"
                                    ),
                                }
                            )
                            continue
                        contact = Contact.objects.filter(
                            owner=owner,
                            external_id=ext_id,
                            is_merged=False,
                        ).first()
                        if not contact:
                            errors.append(
                                {
                                    "row": row_number,
                                    "error": (
                                        f"Row {row_number}: No contact found "
                                        f"matching the provided external_id "
                                        f"-- import contacts first"
                                    ),
                                }
                            )
                            continue

                    # Build Gift creation kwargs
                    gift_kwargs = {
                        "donor_contact": contact,
                        "amount_cents": amount_cents,
                        "gift_date": parsed_date,
                        "description": row_data.get("description", ""),
                    }

                    # Optionally match fund
                    fund_name = row_data.get("fund_name", "")
                    if fund_name:
                        matched_fund = Fund.objects.filter(
                            name__iexact=fund_name,
                        ).first()
                        if matched_fund:
                            gift_kwargs["fund"] = matched_fund

                    # Per-gift idempotency: dedup on a stable identity key so a
                    # re-export (reordered columns, reformatted date) does not
                    # re-create gifts. Skip if this gift already exists.
                    identity = _generic_gift_identity(
                        explicit_id=row_data.get("external_gift_id", ""),
                        owner_id=owner.id,
                        contact_id=contact.id,
                        amount_cents=amount_cents,
                        gift_date=parsed_date,
                        fund_id=gift_kwargs.get("fund").id if gift_kwargs.get("fund") else None,
                        description=gift_kwargs["description"],
                    )

                    if Gift.objects.filter(external_gift_id=identity).exists():
                        skipped_count += 1
                        continue

                    # Savepoint so a lost race on the unique constraint (a
                    # concurrent upload created this exact gift first) is treated
                    # as a dedup instead of poisoning the whole batch.
                    try:
                        with transaction.atomic():
                            Gift.objects.create(external_gift_id=identity, **gift_kwargs)
                        created_count += 1
                        affected_contact_ids.add(contact.id)
                    except IntegrityError:
                        skipped_count += 1

                except Exception as e:
                    logger.exception(
                        "Row %s failed in import_generic_donations",
                        row_number,
                    )
                    errors.append(
                        {
                            "row": row_number,
                            "error": f"Row {row_number}: {type(e).__name__}",
                        }
                    )

            # Recompute giving stats once per affected contact (signals were
            # suppressed during creation). Inside the atomic block so it sees the
            # just-created gifts and commits with them.
            recompute_giving_stats(affected_contact_ids)

            # Step 6: Finalize the batch inside the same transaction. A run is
            # only FAILED when every row errored -- an all-skipped re-upload is
            # a successful idempotent no-op.
            all_errored = total_rows > 0 and created_count == 0 and skipped_count == 0
            batch.status = ImportBatchStatus.FAILED if all_errored else ImportBatchStatus.COMPLETED
            batch.total_rows = total_rows
            batch.created_count = created_count
            batch.skipped_count = skipped_count
            batch.error_count = len(errors)
            batch.summary = {"errors": errors}
            batch.save(
                update_fields=[
                    "status",
                    "total_rows",
                    "created_count",
                    "skipped_count",
                    "error_count",
                    "summary",
                    "updated_at",
                ]
            )

    except IntegrityError:
        # A concurrent identical upload claimed this (type, sha256) first; our
        # batch insert collided and the whole transaction -- including any
        # gifts -- rolled back. Report the winning batch as a duplicate.
        logger.info("Concurrent duplicate generic donation import for %s", filename)
        existing = ImportBatch.objects.filter(
            import_type=ImportBatchType.GENERIC_DONATIONS,
            sha256_hash=sha256_hash,
        ).first()
        if existing:
            existing.status = ImportBatchStatus.DUPLICATE
            existing.save(update_fields=["status"])
            return existing
        # Constraint fired but no committed row found -- re-raise so the
        # anomaly surfaces rather than masquerading as success.
        raise

    except Exception as e:
        logger.exception("Generic donation import failed for %s", filename)
        return ImportBatch.objects.create(
            import_type=ImportBatchType.GENERIC_DONATIONS,
            status=ImportBatchStatus.FAILED,
            filename=filename,
            sha256_hash=sha256_hash,
            uploaded_by=uploaded_by,
            summary={"errors": [{"row": 0, "error": f"Import error: {type(e).__name__}"}]},
        )

    finally:
        enable_gift_signals()

    logger.info(
        "Generic donation import complete for %s: %d created, %d skipped, %d errors",
        filename,
        created_count,
        skipped_count,
        len(errors),
    )

    return batch
