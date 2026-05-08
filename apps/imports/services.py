"""
Service functions for CSV import/export.
"""
import csv
import io
import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Tuple

from apps.contacts.models import Contact
from apps.core.blind_index import lookup_hashes
from apps.imports.models import Fund, ImportStatus

logger = logging.getLogger(__name__)


# Valid enum values for validation
VALID_FUND_STATUSES = ["active", "inactive", "closed"]

# Formula characters for CSV injection prevention
FORMULA_PREFIXES = ("=", "+", "-", "@")


def sanitize_csv_value(value):
    """Prevent CSV formula injection by prefixing dangerous characters with single quote."""
    if value and isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


# Date formats to try when parsing
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y"]

# Email validation pattern
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


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
        return None, "Amount is required"

    # Clean the string
    cleaned = amount_str.strip().replace("$", "").replace(",", "").replace(" ", "")

    # Check for negative values
    if cleaned.startswith("-"):
        return None, "Amount cannot be negative"

    try:
        amount = Decimal(cleaned)
        if amount <= 0:
            return None, "Amount must be greater than zero"
        if amount > Decimal("9999999.99"):
            return None, "Amount exceeds maximum allowed value"
        return amount, None
    except InvalidOperation:
        return (
            None,
            f'Invalid amount format: "{amount_str}". Expected a number like "100.00" or "$1,234.56"',
        )


def _parse_date(date_str: str) -> Tuple[datetime.date, str]:
    """
    Parse date string to date object.
    Returns (date, error_message).
    """
    if not date_str:
        return None, "Date is required"

    cleaned = date_str.strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date(), None
        except ValueError:
            continue

    return None, (
        f'Invalid date format: "{date_str}". '
        f"Accepted formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY"
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
        return [], [{"row": 1, "errors": [f"Invalid CSV format: {e}"], "data": {}}]

    valid_records = []
    errors = []
    seen_emails = set()

    required_fields = ["first_name", "last_name"]

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Check required fields
        for field in required_fields:
            value = row.get(field, "").strip()
            if not value:
                row_errors.append(f"Missing required field: {field}")
            elif len(value) > 150:
                row_errors.append(f"{field} exceeds maximum length of 150 characters")

        # Validate email format
        email = row.get("email", "").strip().lower()
        if email:
            if not _validate_email(email):
                row_errors.append(f'Invalid email format: "{email}"')
            elif email in seen_emails:
                row_errors.append(f"Duplicate email in file: {email}")
            elif Contact.objects.filter(
                owner=user,
                email_hash__in=lookup_hashes(email),
                is_merged=False,
            ).exists():
                row_errors.append(f'Contact with email "{email}" already exists in your account')
            else:
                seen_emails.add(email)

        # Validate phone format (basic)
        phone = row.get("phone", "").strip()
        if phone and len(phone) > 20:
            row_errors.append("Phone number exceeds maximum length of 20 characters")

        # Validate postal code
        postal_code = row.get("postal_code", "").strip()
        if postal_code and len(postal_code) > 20:
            row_errors.append("Postal code exceeds maximum length of 20 characters")

        if row_errors:
            errors.append({"row": row_num, "errors": row_errors, "data": dict(row)})
        else:
            valid_records.append(
                {
                    "first_name": row.get("first_name", "").strip(),
                    "last_name": row.get("last_name", "").strip(),
                    "email": email,
                    "phone": phone,
                    "street_address": row.get("street_address", "").strip()[:255],
                    "city": row.get("city", "").strip()[:100],
                    "state": row.get("state", "").strip()[:50],
                    "postal_code": postal_code,
                    "country": row.get("country", "USA").strip()[:100] or "USA",
                    "notes": row.get("notes", "").strip(),
                }
            )

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
    logger.info("Starting contact import: %d records for user %s", len(records), user.id)
    created_contacts = []

    for record in records:
        contact = Contact.objects.create(owner=user, **record)
        created_contacts.append(contact)

    logger.info(f"Contact import completed: {len(created_contacts)} contacts created")
    return len(created_contacts), created_contacts


## Old SPO donation import functions (parse_donations_csv, import_donations) removed.
## Superseded by Phase 28-29 RE import pipeline in apps/imports/re_services.py.


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
        "first_name",
        "last_name",
        "email",
        "phone",
        "street_address",
        "city",
        "state",
        "postal_code",
        "country",
        "status",
        "total_given",
        "gift_count",
        "last_gift_date",
        "notes",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for contact in queryset:
        writer.writerow(
            {
                "first_name": sanitize_csv_value(contact.first_name),
                "last_name": sanitize_csv_value(contact.last_name),
                "email": sanitize_csv_value(contact.email),
                "phone": sanitize_csv_value(contact.phone),
                "street_address": sanitize_csv_value(contact.street_address),
                "city": sanitize_csv_value(contact.city),
                "state": sanitize_csv_value(contact.state),
                "postal_code": sanitize_csv_value(contact.postal_code),
                "country": sanitize_csv_value(contact.country),
                "status": contact.status,
                "total_given": str(contact.total_given),
                "gift_count": contact.gift_count,
                "last_gift_date": str(contact.last_gift_date) if contact.last_gift_date else "",
                "notes": sanitize_csv_value(contact.notes),
            }
        )

    return output.getvalue()


def export_gifts_csv(queryset) -> str:
    """
    Export gifts to CSV string.

    Args:
        queryset: Gift queryset to export

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    fieldnames = [
        "contact_first_name",
        "contact_last_name",
        "contact_email",
        "amount",
        "gift_date",
        "external_gift_id",
        "description",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for gift in queryset.select_related("donor_contact"):
        writer.writerow(
            {
                "contact_first_name": sanitize_csv_value(gift.donor_contact.first_name),
                "contact_last_name": sanitize_csv_value(gift.donor_contact.last_name),
                "contact_email": sanitize_csv_value(gift.donor_contact.email),
                "amount": f"{gift.amount_dollars:.2f}",
                "gift_date": str(gift.gift_date),
                "external_gift_id": sanitize_csv_value(gift.external_gift_id),
                "description": sanitize_csv_value(gift.description),
            }
        )

    return output.getvalue()


def get_contacts_template() -> str:
    """
    Get CSV template for contact imports.

    Returns:
        CSV header row as string
    """
    return "first_name,last_name,email,phone,street_address,city,state,postal_code,country,notes\n"


## Old get_donations_template removed. Superseded by RE import pipeline.


def get_funds_template() -> str:
    """
    Get CSV template for fund imports.

    Returns:
        CSV header row as string
    """
    return "fund_id,name,status\n"


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
        return [], [{"row": 1, "errors": [f"Invalid CSV format: {e}"], "data": {}}]

    # Validate required column headers before processing rows
    if reader.fieldnames is None:
        return [], [{"row": 1, "errors": ["CSV file is empty or has no headers"], "data": {}}]

    required_columns = ["fund_id", "name"]
    missing_columns = [col for col in required_columns if col not in reader.fieldnames]
    if missing_columns:
        return [], [
            {
                "row": 1,
                "errors": [f'Missing required column: {", ".join(missing_columns)}'],
                "data": {},
            }
        ]

    valid_records = []
    errors = []
    seen_fund_ids = set()

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Get and trim values
        fund_id = row.get("fund_id", "").strip()
        name = row.get("name", "").strip()
        status = row.get("status", "").strip().lower() or "active"

        # Validate fund_id
        if not fund_id:
            row_errors.append("fund_id is required")
        elif len(fund_id) > 100:
            row_errors.append("fund_id exceeds maximum length of 100 characters")
        elif fund_id.startswith(FORMULA_PREFIXES):
            row_errors.append(f"fund_id cannot start with formula character ({fund_id[0]})")
        elif fund_id in seen_fund_ids:
            row_errors.append(f"Duplicate fund_id in file: {fund_id}")
        else:
            seen_fund_ids.add(fund_id)

        # Validate name
        if not name:
            row_errors.append("name is required")
        elif len(name) > 255:
            row_errors.append("name exceeds maximum length of 255 characters")
        elif name.startswith(FORMULA_PREFIXES):
            row_errors.append(f"name cannot start with formula character ({name[0]})")

        # Validate status
        if status not in VALID_FUND_STATUSES:
            row_errors.append(
                f'Invalid status: "{status}". Valid options: {", ".join(VALID_FUND_STATUSES)}'
            )

        if row_errors:
            errors.append({"row": row_num, "errors": row_errors, "data": dict(row)})
        else:
            valid_records.append(
                {
                    "fund_id": fund_id,
                    "name": name,
                    "status": status,
                }
            )

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
    logger.info(f"Starting fund import: {len(records)} records for import run {import_run.id}")

    if not records:
        # Update import run for empty records
        import_run.created_count = 0
        import_run.updated_count = 0
        import_run.status = ImportStatus.COMPLETED
        import_run.save()
        return 0, 0

    # Get existing external_ids to calculate created vs updated
    external_ids = [record["fund_id"] for record in records]
    existing_external_ids = set(
        Fund.objects.filter(external_id__in=external_ids).values_list("external_id", flat=True)
    )

    # Prepare Fund objects for bulk create
    fund_objects = [
        Fund(
            external_id=record["fund_id"],
            name=record["name"],
            status=record["status"],
            owner=None,  # Funds are org-wide
        )
        for record in records
    ]

    # Bulk upsert
    Fund.objects.bulk_create(
        fund_objects,
        update_conflicts=True,
        unique_fields=["external_id"],
        update_fields=["name", "status"],
    )

    # Calculate counts
    created_count = sum(1 for record in records if record["fund_id"] not in existing_external_ids)
    updated_count = sum(1 for record in records if record["fund_id"] in existing_external_ids)

    # Update import run
    import_run.created_count = created_count
    import_run.updated_count = updated_count
    import_run.status = ImportStatus.COMPLETED
    import_run.save()

    logger.info(f"Fund import completed: {created_count} created, {updated_count} updated")
    return created_count, updated_count


def get_entities_template() -> str:
    """
    Get CSV template for entity imports.

    Returns:
        CSV header row as string
    """
    return "entity_id,name,email,phone,address,entity_type\n"


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
        return [], [{"row": 1, "errors": [f"Invalid CSV format: {e}"], "data": {}}]

    # Validate required column headers before processing rows
    if reader.fieldnames is None:
        return [], [{"row": 1, "errors": ["CSV file is empty or has no headers"], "data": {}}]

    required_columns = ["entity_id", "name"]
    missing_columns = [col for col in required_columns if col not in reader.fieldnames]
    if missing_columns:
        return [], [
            {
                "row": 1,
                "errors": [f'Missing required column: {", ".join(missing_columns)}'],
                "data": {},
            }
        ]

    valid_records = []
    errors = []
    seen_entity_ids = set()

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Get and trim values
        entity_id = row.get("entity_id", "").strip()
        name = row.get("name", "").strip()
        email = row.get("email", "").strip()
        phone = row.get("phone", "").strip()
        address = row.get("address", "").strip()
        # entity_type is intentionally ignored - Contact has no such field

        # Validate entity_id
        if not entity_id:
            row_errors.append("entity_id is required")
        elif len(entity_id) > 100:
            row_errors.append("entity_id exceeds maximum length of 100 characters")
        elif entity_id.startswith(FORMULA_PREFIXES):
            row_errors.append(f"entity_id cannot start with formula character ({entity_id[0]})")
        elif entity_id in seen_entity_ids:
            row_errors.append(f"Duplicate entity_id in file: {entity_id}")
        else:
            seen_entity_ids.add(entity_id)

        # Validate name
        if not name:
            row_errors.append("name is required")
        elif len(name) > 300:
            row_errors.append("name exceeds maximum length of 300 characters")
        elif name.startswith(FORMULA_PREFIXES):
            row_errors.append(f"name cannot start with formula character ({name[0]})")

        # Split name into first_name and last_name
        # Last word is last_name, everything else is first_name
        first_name = ""
        last_name = ""
        if name and not row_errors:
            parts = name.split()
            if len(parts) > 1:
                first_name = " ".join(parts[:-1])
                last_name = parts[-1]
            else:
                first_name = parts[0] if parts else ""
                last_name = ""

        # Validate email (optional)
        if email:
            if len(email) > 254:
                row_errors.append("email exceeds maximum length of 254 characters")
            elif not _validate_email(email):
                row_errors.append(f'Invalid email format: "{email}"')

        # Validate phone (optional)
        if phone and len(phone) > 20:
            row_errors.append("phone exceeds maximum length of 20 characters")

        # Validate address (optional) - maps to street_address
        if address and len(address) > 255:
            row_errors.append("address exceeds maximum length of 255 characters")

        if row_errors:
            errors.append({"row": row_num, "errors": row_errors, "data": dict(row)})
        else:
            valid_records.append(
                {
                    "entity_id": entity_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "street_address": address,  # address maps to street_address
                }
            )

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
    logger.info("Starting entity import: %d records for user %s", len(records), user.id)

    if not records:
        # Update import run for empty records
        import_run.created_count = 0
        import_run.updated_count = 0
        import_run.status = ImportStatus.COMPLETED
        import_run.save()
        return 0, 0

    # Get existing external_ids for this user to calculate created vs updated
    external_ids = [record["entity_id"] for record in records]
    existing_external_ids = set(
        Contact.objects.filter(owner=user, external_id__in=external_ids).values_list(
            "external_id", flat=True
        )
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
            external_id=record["entity_id"],
            defaults={
                "first_name": record["first_name"],
                "last_name": record["last_name"],
                "email": record.get("email", ""),
                "phone": record.get("phone", ""),
                "street_address": record.get("street_address", ""),
            },
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

    logger.info(f"Entity import completed: {created_count} created, {updated_count} updated")
    return created_count, updated_count


## Old SPO transaction/pledge import functions removed.
## (get_transactions_template, parse_transactions_csv, import_transactions,
##  update_contact_stats_for_import, get_pledges_template, parse_pledges_csv, import_pledges)
## Superseded by Phase 28-29 RE import pipeline in apps/imports/re_services.py.
