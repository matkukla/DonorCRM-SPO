"""
Service functions for Smartsheet MPD Dashboard Report import.

Handles file parsing (CSV/XLSX), column mapping, user matching,
currency/boolean/percentage parsing, and MPDSnapshot creation.
"""

import csv
import logging
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

from django.db import IntegrityError

from apps.imports.models import MPDSnapshot, MPDUpload

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column mapping: Smartsheet header (lowercased) -> model field name
# Fields prefixed with _ are matching keys, not stored on MPDSnapshot.
# ---------------------------------------------------------------------------
SMARTSHEET_COLUMN_MAP = {
    "full name": None,  # Skip - derived from First + Last
    "first name": "_first_name",  # matching key, not stored on snapshot
    "last name": "_last_name",  # matching key, not stored on snapshot
    "active recurring gifts": "active_recurring_gifts",
    "annual gifts": "annual_gifts",
    "monthly average": "monthly_average",
    "annual mpd estimate": "annual_mpd_estimate",
    "mpd standard": "mpd_standard",
    "$ amount below mpd standard": "amount_below_mpd_standard",
    "% standard to max": "pct_standard_to_max",
    "met mpd standard": "met_mpd_standard",
    "mpd maximum": "mpd_maximum",
    "met maximum": "met_maximum",
    "amount above/below maximum": "amount_above_below_maximum",
    "match met": "match_met",
    "match met for rest of fiscal year (based on rfb)": "match_met_rest_fy",
    "latest roll forward balance": "latest_roll_forward_balance",
    "current mpd cap": "current_mpd_cap",
    "months remaining in rf": "months_remaining_rf",
    "proj. monthly deduction from rfb (cap - rec.gifts)": "proj_monthly_deduction_rfb",
    "pay forecast over 12 months": "pay_forecast_12_months",
    "pay forecast over fiscal year": "pay_forecast_over_fy",
    "total one-time gifts - april": "total_one_time_gifts_april",
}

# Columns to skip entirely (coaching-related, not stored)
SKIP_COLUMNS = {
    "will be a coach in 2022 mpd season?",
    "do you understand the coaching contract?",
    "have you made these decisions w/ your supervisor?",
}

# Field classification for type-specific parsing
CURRENCY_FIELDS = {
    "active_recurring_gifts",
    "annual_gifts",
    "monthly_average",
    "annual_mpd_estimate",
    "mpd_standard",
    "amount_below_mpd_standard",
    "mpd_maximum",
    "amount_above_below_maximum",
    "latest_roll_forward_balance",
    "current_mpd_cap",
    "proj_monthly_deduction_rfb",
    "pay_forecast_12_months",
    "pay_forecast_over_fy",
    "total_one_time_gifts_april",
}

BOOLEAN_FIELDS = {
    "met_mpd_standard",
    "met_maximum",
    "match_met",
    "match_met_rest_fy",
}

PERCENTAGE_FIELDS = {"pct_standard_to_max"}

MONTHS_REMAINING_FIELD = "months_remaining_rf"

# Formula injection characters to strip from start of cell values.
# Note: '-' is intentionally NOT stripped (negative currency like -$468.33).
FORMULA_INJECTION_CHARS = {"=", "+", "@", "\t", "\r"}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def detect_file_format(file_bytes: bytes) -> str:
    """Detect whether file is XLSX or CSV from magic bytes.

    XLSX/ZIP files start with PK\\x03\\x04. Everything else treated as CSV.
    """
    if file_bytes[:4] == b"PK\x03\x04":
        return "xlsx"
    return "csv"


def sanitize_cell_value(value):
    """Strip formula injection characters from the START of string values.

    Strips =, +, @, tab, carriage return from the beginning.
    Does NOT strip - (negative currency values are legitimate).
    Non-string or None values are returned as-is.
    """
    if not isinstance(value, str) or value is None:
        return value
    while value and value[0] in FORMULA_INJECTION_CHARS:
        value = value[1:]
    return value


def parse_currency(value) -> Decimal | None:
    """Parse currency strings to Decimal.

    Handles: "$3,085.00", "-$468.33", "($468.33)", None, empty string,
    int/float passthrough.
    Returns None on parse failure.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    # Handle parenthetical negatives: ($468.33) -> -468.33
    negative = False
    if value.startswith("(") and value.endswith(")"):
        negative = True
        value = value[1:-1]

    # Handle leading negative sign before or after dollar sign
    if value.startswith("-"):
        negative = True
        value = value[1:]

    # Strip dollar sign, commas, spaces
    value = value.replace("$", "").replace(",", "").replace(" ", "")

    # Handle negative after dollar sign: $-468.33
    if value.startswith("-"):
        negative = True
        value = value[1:]

    if not value:
        return None

    try:
        result = Decimal(value)
        if negative:
            result = -result
        return result
    except (InvalidOperation, ValueError):
        return None


def parse_yes_no(value) -> bool | None:
    """Parse Yes/No strings to boolean.

    Also accepts true/false, 1/0. Case-insensitive.
    Returns None for None or empty.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if not isinstance(value, str):
        return None

    value = value.strip().lower()
    if not value:
        return None

    if value in ("yes", "true", "1"):
        return True
    if value in ("no", "false", "0"):
        return False

    return None


def parse_percentage(value) -> int | None:
    """Parse percentage value to integer.

    Handles: "104%" -> 104, "-16%" -> -16.
    Handles float from XLSX: if abs(value) <= 10, multiply by 100
    (e.g., 1.04 -> 104, -0.16 -> -16).
    Returns None for None/empty.
    """
    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if abs(value) <= 10:
            return round(value * 100)
        return round(value)

    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    # Strip % sign
    value = value.replace("%", "").strip()

    try:
        num = float(value)
        if abs(num) <= 10:
            return round(num * 100)
        return round(num)
    except (ValueError, TypeError):
        return None


def parse_months_remaining(value) -> str:
    """Parse months remaining field.

    Returns 'infinite' for 'infinite' (case-insensitive).
    Numeric values formatted as string with up to 6 decimal places
    (trailing zeros stripped).
    Returns empty string for None/empty.
    """
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        if isinstance(value, int):
            return str(value)
        # Format float with up to 6 decimal places, strip trailing zeros
        formatted = f"{value:.6f}".rstrip("0").rstrip(".")
        return formatted

    if not isinstance(value, str):
        return ""

    value = value.strip()
    if not value:
        return ""

    if value.lower() == "infinite":
        return "infinite"

    # Try to parse as numeric
    try:
        num = float(value)
        if num == int(num):
            return str(int(num))
        formatted = f"{num:.6f}".rstrip("0").rstrip(".")
        return formatted
    except (ValueError, TypeError):
        return value


# ---------------------------------------------------------------------------
# Column mapping and row parsing
# ---------------------------------------------------------------------------


def build_column_index(headers: list[str]) -> tuple[dict, list[str]]:
    """Map header positions to field names using SMARTSHEET_COLUMN_MAP.

    Each header is normalized with .strip().lower().
    Columns in SKIP_COLUMNS are ignored.
    Columns mapped to None in SMARTSHEET_COLUMN_MAP are ignored.

    Returns:
        (index_map, unrecognized_columns) where:
        - index_map: {col_position: field_name}
        - unrecognized_columns: headers not found in the map
    """
    index_map = {}
    unrecognized = []

    for i, header in enumerate(headers):
        normalized = header.strip().lower()

        if normalized in SKIP_COLUMNS:
            continue

        if normalized in SMARTSHEET_COLUMN_MAP:
            field_name = SMARTSHEET_COLUMN_MAP[normalized]
            if field_name is not None:
                index_map[i] = field_name
        else:
            if normalized:  # Don't report empty headers
                unrecognized.append(header.strip())

    return index_map, unrecognized


def parse_row(row_values: list, column_index: dict) -> dict:
    """Parse a single data row using the column index.

    For each position in column_index, extracts the value from row_values
    (handles index out of range as None). Applies sanitize_cell_value
    to string values, then type-specific parsing based on field name.

    Returns dict of {field_name: parsed_value}.
    """
    result = {}

    for pos, field_name in column_index.items():
        # Extract value (handle index out of range)
        if pos < len(row_values):
            value = row_values[pos]
        else:
            value = None

        # Sanitize string values
        if isinstance(value, str):
            value = sanitize_cell_value(value)

        # Type-specific parsing
        if field_name.startswith("_"):
            # Matching keys: just sanitize and strip as string
            if isinstance(value, str):
                result[field_name] = value.strip()
            else:
                result[field_name] = str(value).strip() if value is not None else ""
        elif field_name in CURRENCY_FIELDS:
            result[field_name] = parse_currency(value)
        elif field_name in BOOLEAN_FIELDS:
            result[field_name] = parse_yes_no(value)
        elif field_name in PERCENTAGE_FIELDS:
            result[field_name] = parse_percentage(value)
        elif field_name == MONTHS_REMAINING_FIELD:
            result[field_name] = parse_months_remaining(value)
        else:
            result[field_name] = value

    return result


# ---------------------------------------------------------------------------
# File parsing (XLSX and CSV)
# ---------------------------------------------------------------------------


def parse_xlsx(file_bytes: bytes) -> tuple[list[str], list[list]]:
    """Parse XLSX file into headers and data rows.

    Uses openpyxl in read_only/data_only mode for efficiency.
    Returns (headers, data_rows).
    """
    import openpyxl

    wb = openpyxl.load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return [], []

    # First row is headers
    headers = [str(cell) if cell is not None else "" for cell in rows[0]]
    data_rows = [list(row) for row in rows[1:]]

    return headers, data_rows


def parse_csv(file_bytes: bytes) -> tuple[list[str], list[list]]:
    """Parse CSV file into headers and data rows.

    Decodes with utf-8-sig to handle BOM.
    Returns (headers, data_rows).
    """
    text = file_bytes.decode("utf-8-sig")
    reader = csv.reader(StringIO(text))

    rows = list(reader)
    if not rows:
        return [], []

    headers = rows[0]
    data_rows = rows[1:]

    return headers, data_rows


# ---------------------------------------------------------------------------
# User matching
# ---------------------------------------------------------------------------


def match_users(parsed_rows: list[dict]) -> tuple[list[tuple], list[dict]]:
    """Match parsed rows to DonorCRM users by first + last name.

    Pre-fetches all active users into a dict keyed by
    (first_name.lower().strip(), last_name.lower().strip()).
    Detects and warns about duplicate name keys.

    Returns:
        (matched, unmatched) where:
        - matched: [(user, row_data_without_underscored_keys), ...]
        - unmatched: [{row: N, first_name: X, last_name: Y}, ...]
        Row numbers start at 2 (header is row 1).
    """
    from apps.users.models import User

    # Pre-fetch all active users
    users = User.objects.filter(is_active=True)
    user_lookup = {}
    duplicates = set()

    for user in users:
        key = (user.first_name.lower().strip(), user.last_name.lower().strip())
        if key in user_lookup:
            duplicates.add(key)
            logger.warning(
                "Duplicate user name key: %s %s (IDs: %s, %s)",
                key[0],
                key[1],
                user_lookup[key].id,
                user.id,
            )
        else:
            user_lookup[key] = user

    if duplicates:
        logger.warning("Found %d duplicate name keys in users", len(duplicates))

    matched = []
    unmatched = []

    for i, row_data in enumerate(parsed_rows):
        row_num = i + 2  # Header is row 1

        first_name = row_data.get("_first_name", "").lower().strip()
        last_name = row_data.get("_last_name", "").lower().strip()
        key = (first_name, last_name)

        # Skip rows with ambiguous (duplicate) name keys
        if key in duplicates:
            logger.warning(
                "Row %d: ambiguous name match for %s %s (multiple users)",
                row_num,
                first_name,
                last_name,
            )
            unmatched.append(
                {
                    "row": row_num,
                    "first_name": row_data.get("_first_name", ""),
                    "last_name": row_data.get("_last_name", ""),
                    # Financial fields for admin visibility in results dialog
                    "current_mpd_cap": (
                        str(row_data.get("current_mpd_cap", ""))
                        if row_data.get("current_mpd_cap") is not None
                        else None
                    ),
                    "latest_roll_forward_balance": (
                        str(row_data.get("latest_roll_forward_balance", ""))
                        if row_data.get("latest_roll_forward_balance") is not None
                        else None
                    ),
                    "months_remaining_rf": row_data.get("months_remaining_rf", ""),
                }
            )
            continue

        user = user_lookup.get(key)
        if user:
            # Build snapshot kwargs (exclude keys starting with _)
            snapshot_data = {k: v for k, v in row_data.items() if not k.startswith("_")}
            matched.append((user, snapshot_data))
        else:
            unmatched.append(
                {
                    "row": row_num,
                    "first_name": row_data.get("_first_name", ""),
                    "last_name": row_data.get("_last_name", ""),
                    # Financial fields for admin visibility in results dialog
                    "current_mpd_cap": (
                        str(row_data.get("current_mpd_cap", ""))
                        if row_data.get("current_mpd_cap") is not None
                        else None
                    ),
                    "latest_roll_forward_balance": (
                        str(row_data.get("latest_roll_forward_balance", ""))
                        if row_data.get("latest_roll_forward_balance") is not None
                        else None
                    ),
                    "months_remaining_rf": row_data.get("months_remaining_rf", ""),
                }
            )

    return matched, unmatched


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def process_mpd_upload(file_bytes: bytes, filename: str, uploaded_by) -> MPDUpload:
    """Process an MPD Smartsheet report upload end-to-end.

    Steps:
    1. Detect file format (CSV/XLSX)
    2. Create MPDUpload record (status=processing)
    3. Parse file
    4. Build column index from headers
    5. Parse all data rows
    6. Match users
    7. Bulk create MPDSnapshot records
    8. Update MPDUpload with counts and status
    9. Return the MPDUpload instance

    On error, marks upload as failed and re-raises.
    """
    # Step 1: Detect format
    file_format = detect_file_format(file_bytes)
    logger.info("MPD upload started: %s (format: %s)", filename, file_format)

    # Step 2: Create upload record
    upload = MPDUpload.objects.create(
        uploaded_by=uploaded_by,
        filename=filename,
        file_format=file_format,
        status="processing",
    )

    try:
        # Step 3: Parse file
        if file_format == "xlsx":
            headers, data_rows = parse_xlsx(file_bytes)
        else:
            headers, data_rows = parse_csv(file_bytes)

        logger.info("Parsed %d data rows from %s", len(data_rows), filename)

        # Step 4: Build column index
        column_index, unrecognized = build_column_index(headers)

        if unrecognized:
            logger.warning("Unrecognized columns in %s: %s", filename, unrecognized)

        if not column_index:
            upload.status = "failed"
            upload.error_message = "No recognized columns found in file headers."
            upload.save()
            return upload

        logger.info("Mapped %d columns from headers", len(column_index))

        # Step 5: Parse all data rows
        parsed_rows = [parse_row(row, column_index) for row in data_rows]
        logger.info("Parsed %d rows", len(parsed_rows))

        # Step 6: Match users
        matched, unmatched = match_users(parsed_rows)
        logger.info("User matching: %d matched, %d unmatched", len(matched), len(unmatched))

        # Step 7: Bulk create MPDSnapshot records
        snapshots = [
            MPDSnapshot(
                user=user,
                upload=upload,
                **snapshot_data,
            )
            for user, snapshot_data in matched
        ]

        snapshot_count = 0
        if snapshots:
            try:
                created = MPDSnapshot.objects.bulk_create(snapshots)
                snapshot_count = len(created)
            except IntegrityError:
                # Fall back to one-by-one creation if bulk fails
                # (e.g., same user appears twice in file)
                logger.warning(
                    "Bulk create failed for %s, falling back to individual creates", filename
                )
                for snapshot in snapshots:
                    try:
                        snapshot.save()
                        snapshot_count += 1
                    except IntegrityError:
                        logger.warning(
                            "Duplicate snapshot skipped: user=%s upload=%s",
                            snapshot.user_id,
                            upload.id,
                        )

        logger.info("Created %d MPDSnapshot records", snapshot_count)

        # Step 8: Update upload with counts
        upload.total_rows = len(data_rows)
        upload.matched_count = len(matched)
        upload.unmatched_count = len(unmatched)
        upload.unmatched_rows = unmatched
        upload.status = "completed"
        upload.save()

        return upload

    except Exception as e:
        logger.error("MPD upload failed for %s: %s", filename, e)
        upload.status = "failed"
        upload.error_message = str(e)
        upload.save()
        raise
