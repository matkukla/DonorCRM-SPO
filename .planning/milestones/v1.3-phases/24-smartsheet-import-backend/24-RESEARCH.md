# Phase 24: Smartsheet MPD Report Import Backend - Research

**Researched:** 2026-02-19
**Domain:** Django file upload, Excel/CSV parsing, model design, financial data storage
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Admin uploads a monthly Smartsheet MPD Dashboard Report (CSV or XLSX export)
- Each row is a MISSIONARY (a DonorCRM User), NOT a donor/contact
- System matches rows to existing users by First Name + Last Name (case-insensitive)
- Creates MPDSnapshot records storing ~20 financial columns per missionary
- Snapshots accumulate historically (monthly uploads create NEW records, never overwrite)
- MPDUpload model tracks each upload (audit trail: timestamp, admin, filename, row counts)
- Single-step upload: admin uploads file, backend parses/matches/creates snapshots, returns results
- No column mapping step needed (columns are known/fixed from the Smartsheet report)
- File format auto-detected from magic bytes (CSV vs XLSX)
- Formula injection characters stripped before storage
- File size limit: 10 MB (realistic: ~10-50 rows per file)
- Synchronous processing (no async/Celery needed)
- Columns to SKIP: coaching columns (Will be a Coach, Coaching Contract, supervisor decisions)
- `months_remaining_rf` stored as CharField (can be "infinite")

### Claude's Discretion
- How to handle unmatched rows (skip and report, or let admin map manually)
- Whether column names should be hardcoded or semi-flexible (auto-detect by known names)

### Deferred Ideas (OUT OF SCOPE)
_(None captured during discussion)_
</user_constraints>

## Summary

This phase adds a specialized import pipeline for the organization's monthly Smartsheet MPD Dashboard Report. Unlike the existing SPO CSV imports which handle donors/contacts/donations, this feature processes a financial summary report where each row represents a **missionary** (DonorCRM User). The system auto-detects file format (CSV vs XLSX), matches rows to existing users by name, and creates historical MPDSnapshot records storing ~20 financial metrics.

The implementation builds on the existing `apps/imports` infrastructure (ImportRun audit trail, formula injection prevention, file upload patterns) but requires a new Django app or model additions since the data model (MPDSnapshot linked to User) is fundamentally different from the existing import types (Contacts, Donations, Pledges linked to Contact).

**Primary recommendation:** Create MPDUpload and MPDSnapshot models in the existing `apps/imports` app, add a new service module (`mpd_services.py`) for parsing/matching/import logic, and a new view (`MPDImportView`) following the existing import view patterns. Use `openpyxl` (new dependency) for XLSX parsing and the existing `csv` stdlib for CSV parsing. Hardcode column names with a mapping dict for resilience against minor column name variations.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openpyxl | 3.1.x (latest: 3.1.4) | Parse .xlsx files | Pure Python, no external deps, read_only mode for efficiency, standard for Django Excel import |
| csv (stdlib) | Python 3.12 built-in | Parse .csv files | Already used extensively in existing import infrastructure |
| decimal (stdlib) | Python 3.12 built-in | Parse currency strings to Decimal | Already used in existing `_parse_amount()` in services.py |
| io (stdlib) | Python 3.12 built-in | BytesIO/StringIO for in-memory file handling | Already used in existing import views |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Django 4.2 | 4.2.27 (installed) | Models, views, ORM | Core framework - already installed |
| DRF | 3.16.1 (installed) | API views, MultiPartParser | Already used for all import endpoints |
| pytest | 7.4.4 (installed) | Testing | Already configured in pyproject.toml |
| factory_boy | 3.3.3 (installed) | Test fixtures | Already used for UserFactory |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openpyxl | pandas | pandas is overkill (heavy NumPy dep) for simple row-by-row parsing of ~50 rows |
| openpyxl | xlrd | xlrd only supports .xls (not .xlsx since v2.0) - wrong format |
| Manual magic bytes check | python-magic / filetype library | Unnecessary dependency - XLSX starts with `PK\x03\x04` (ZIP header) which is a 4-byte check |

### Installation

```bash
pip install "openpyxl>=3.1,<4.0"
```

**Note:** openpyxl is NOT currently installed. This is the only new dependency needed.

## Architecture Patterns

### Recommended Project Structure
```
apps/imports/
├── models.py              # ADD: MPDUpload, MPDSnapshot models
├── mpd_services.py        # NEW: MPD-specific parsing, matching, import logic
├── views.py               # ADD: MPDImportView
├── urls.py                # ADD: mpd-import endpoint
├── admin.py               # ADD: MPDUpload, MPDSnapshot admin registrations
├── migrations/
│   └── 0002_mpd_models.py # NEW: migration for MPDUpload + MPDSnapshot
└── tests/
    └── test_mpd_import.py # NEW: MPD import tests
```

### Pattern 1: File Format Auto-Detection via Magic Bytes
**What:** Detect CSV vs XLSX from the first 4 bytes of file content, not from file extension.
**When to use:** Always - file extensions can be wrong, magic bytes are reliable.
**Confidence:** HIGH

```python
def detect_file_format(file_bytes: bytes) -> str:
    """Detect file format from magic bytes."""
    # XLSX files are ZIP archives: first 4 bytes are PK\x03\x04
    if file_bytes[:4] == b'PK\x03\x04':
        return 'xlsx'
    # Otherwise assume CSV (text files have no reliable magic bytes)
    return 'csv'
```

**Key insight:** XLSX files are ZIP archives with a well-known 4-byte signature (`50 4B 03 04`). CSV files are plain text with no magic bytes, so CSV is the fallback. No third-party library needed for this detection.

### Pattern 2: Hardcoded Column Mapping with Normalization
**What:** Map known Smartsheet column names to model field names using a static dict, with string normalization for resilience.
**When to use:** When the import source has a known, stable column format (as with this Smartsheet report).
**Confidence:** HIGH (recommendation for Claude's Discretion item)

```python
# Column name -> model field name mapping
SMARTSHEET_COLUMN_MAP = {
    'Full Name': None,  # Skip - derived from First + Last
    'First Name': 'first_name',  # matching key, not stored
    'Last Name': 'last_name',    # matching key, not stored
    'Active Recurring Gifts': 'active_recurring_gifts',
    'Annual Gifts': 'annual_gifts',
    'Monthly Average': 'monthly_average',
    'Annual MPD Estimate': 'annual_mpd_estimate',
    'MPD Standard': 'mpd_standard',
    '$ Amount Below MPD Standard': 'amount_below_mpd_standard',
    '% Standard to Max': 'pct_standard_to_max',
    'Met MPD Standard': 'met_mpd_standard',
    'MPD Maximum': 'mpd_maximum',
    'Met MAXIMUM': 'met_maximum',
    'Amount Above/Below Maximum': 'amount_above_below_maximum',
    'Match Met': 'match_met',
    'Match Met for Rest of Fiscal Year (Based on RFB)': 'match_met_rest_fy',
    'Latest Roll Forward Balance': 'latest_roll_forward_balance',
    'Current MPD Cap': 'current_mpd_cap',
    'Months Remaining in RF': 'months_remaining_rf',
    'Proj. Monthly Deduction from RFB (Cap - Rec.Gifts)': 'proj_monthly_deduction_rfb',
    'PAY FORECAST Over 12 Months': 'pay_forecast_12_months',
    'Pay Forecast Over Fiscal Year': 'pay_forecast_over_fy',
    'Total One-Time Gifts - April': 'total_one_time_gifts_april',
}

# Columns to explicitly skip (coaching - not stored)
SKIP_COLUMNS = {
    'Will be a Coach in 2022 MPD Season?',
    'Do you understand the Coaching Contract?',
    'Have you made these decisions w/ your supervisor?',
}

def normalize_column_name(name: str) -> str:
    """Normalize column name for fuzzy matching."""
    return name.strip().lower()

def build_column_index(headers: list) -> dict:
    """Build column index mapping header positions to field names.
    Uses normalized comparison for resilience against minor variations."""
    normalized_map = {normalize_column_name(k): v for k, v in SMARTSHEET_COLUMN_MAP.items()}
    normalized_skip = {normalize_column_name(s) for s in SKIP_COLUMNS}

    index = {}
    unrecognized = []
    for i, header in enumerate(headers):
        norm = normalize_column_name(header)
        if norm in normalized_skip:
            continue  # Skip coaching columns
        if norm in normalized_map:
            field = normalized_map[norm]
            if field is not None:
                index[i] = field
        else:
            unrecognized.append(header)

    return index, unrecognized
```

**Why hardcode, not auto-detect:** This is a specific known report format. The column names come from a specific Smartsheet template the organization uses. Hardcoding is simpler, more predictable, and less error-prone than fuzzy matching. The normalization layer handles minor case/whitespace variations.

### Pattern 3: Currency String Parsing (Reuse + Extend Existing)
**What:** Extend the existing `_parse_amount()` pattern to handle negative currency values and empty strings gracefully.
**When to use:** For all Smartsheet financial columns.
**Confidence:** HIGH

```python
def parse_currency(value) -> Decimal | None:
    """Parse currency string like '$3,085.00' or '-$468.33' to Decimal.

    Returns None for empty/blank values (not an error for MPD data).
    Handles: "$3,085.00", "-$468.33", "$0.00", empty string, None.

    NOTE: Unlike existing _parse_amount(), this allows negative values
    (e.g., "$ Amount Below MPD Standard" can be negative) and allows
    zero (e.g., "$0.00" for roll forward balance).
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        # openpyxl may return numeric values directly from XLSX
        return Decimal(str(value))

    cleaned = str(value).strip()
    if not cleaned:
        return None

    # Remove currency symbols and formatting
    cleaned = cleaned.replace('$', '').replace(',', '').replace(' ', '')

    # Handle negative formats: "-$468.33" -> "-468.33" (already handled by above)
    # Handle parenthetical negatives: "($468.33)" -> "-468.33"
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]

    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None  # Return None rather than error - individual cell parse failures
```

**Key difference from existing `_parse_amount()`:** The existing function rejects negatives and zeros. MPD financial data has legitimate negative values (e.g., "$ Amount Below MPD Standard": "-$468.33") and zero values ("$0.00" for roll forward balance). Also handles `None` from openpyxl cells.

### Pattern 4: User Matching by Name
**What:** Match Smartsheet rows to DonorCRM users by case-insensitive First Name + Last Name.
**When to use:** For every data row in the upload.
**Confidence:** HIGH

```python
def match_users(rows: list[dict]) -> tuple[list[tuple], list[dict]]:
    """Match parsed rows to existing DonorCRM users.

    Returns (matched, unmatched) where:
    - matched: list of (user, row_data) tuples
    - unmatched: list of {row_number, first_name, last_name} dicts
    """
    from apps.users.models import User

    # Pre-fetch all active users into a lookup dict
    # Key: (lower_first, lower_last) -> User
    users_by_name = {}
    for user in User.objects.filter(is_active=True):
        key = (user.first_name.lower().strip(), user.last_name.lower().strip())
        users_by_name[key] = user

    matched = []
    unmatched = []

    for row_num, row in enumerate(rows, start=2):
        first = row.get('first_name', '').strip().lower()
        last = row.get('last_name', '').strip().lower()
        key = (first, last)

        user = users_by_name.get(key)
        if user:
            matched.append((user, row))
        else:
            unmatched.append({
                'row': row_num,
                'first_name': row.get('first_name', ''),
                'last_name': row.get('last_name', ''),
            })

    return matched, unmatched
```

**Important notes:**
- There is NO unique constraint on User.first_name + User.last_name. Two users could theoretically have the same name. The current pre-fetch approach takes the last one found. For a small org (~10-50 missionaries), this is extremely unlikely, but the implementation should warn if duplicate names are detected.
- Only matches against `is_active=True` users.
- The User model has `first_name` (CharField, max_length=150) and `last_name` (CharField, max_length=150) - matches the Smartsheet columns.

### Pattern 5: openpyxl In-Memory XLSX Parsing
**What:** Parse XLSX from Django's uploaded file bytes using BytesIO.
**When to use:** When file format is detected as XLSX.
**Confidence:** HIGH

```python
from openpyxl import load_workbook
from io import BytesIO

def parse_xlsx(file_bytes: bytes) -> tuple[list[str], list[list]]:
    """Parse XLSX file bytes into headers and row data."""
    wb = load_workbook(
        filename=BytesIO(file_bytes),
        read_only=True,   # Memory-efficient, lazy loading
        data_only=True     # Read computed values, not formulas
    )
    ws = wb.active  # Use first/active sheet

    rows = list(ws.iter_rows(values_only=True))
    wb.close()  # Must explicitly close in read_only mode

    if not rows:
        return [], []

    headers = [str(cell) if cell is not None else '' for cell in rows[0]]
    data_rows = rows[1:]  # Skip header row

    return headers, data_rows
```

**Critical notes:**
- `read_only=True` reduces memory usage significantly (though for ~50 rows it barely matters, it's good practice).
- `data_only=True` returns the cached computed value rather than the formula string.
- `wb.close()` is REQUIRED in read_only mode.
- Cell values from openpyxl may be `int`, `float`, `str`, or `None` - the currency parser must handle all types.
- For XLSX, percentage values like "104%" may come as `1.04` (numeric) rather than the string "104%".

### Anti-Patterns to Avoid

- **Anti-pattern: Reusing the existing ImportRun model for MPD uploads.** The existing ImportRun is typed by `ImportType` (funds, entities, transactions, pledges) and tracks created/updated counts that don't map to the MPD workflow (snapshots are always created, never updated). Use a dedicated `MPDUpload` model instead.

- **Anti-pattern: Storing percentage as a string.** The `% Standard to Max` column contains values like "104%" and "-16%". Parse to integer (or Decimal) and store as `IntegerField`. This enables future comparisons/sorting. The "%" is display formatting.

- **Anti-pattern: Using `read_only=False` with openpyxl.** For import-only operations, always use `read_only=True`. The full mode loads the entire workbook DOM into memory, which is unnecessary for row reading.

- **Anti-pattern: Matching on Full Name string.** The Smartsheet has `Full Name`, `First Name`, and `Last Name` columns. Match on `First Name` + `Last Name` separately (as CONTEXT.md specifies), NOT on the combined `Full Name` string, because "Mary Jane Smith" could split differently.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XLSX parsing | Custom ZIP/XML parser | `openpyxl` | XLSX is a complex ZIP-of-XML format with shared strings, styles, etc. |
| Currency string parsing | Regex-based parser | Simple `str.replace()` chain + `Decimal()` | The format is consistent (`$X,XXX.XX`), regex adds complexity for no benefit |
| File format detection | `python-magic` library | 4-byte magic bytes check | XLSX = `PK\x03\x04`, CSV = everything else. No dependency needed for a 1-line check |
| Formula injection | Custom sanitizer | Extend existing `sanitize_csv_value()` | Already handles `=`, `+`, `-`, `@` prefix detection |

**Key insight:** This import has a fixed, known format. The complexity is in the data model and matching, not in parsing. Keep parsing simple and invest effort in robust model design and clear error reporting.

## Common Pitfalls

### Pitfall 1: openpyxl Returns Different Types for XLSX vs CSV Parsing for Same Column
**What goes wrong:** When parsing XLSX, openpyxl returns numeric values as `int` or `float` directly. When parsing CSV, all values are strings (e.g., `"$3,085.00"`). The currency parser must handle both.
**Why it happens:** Excel stores numbers natively; CSV stores everything as text.
**How to avoid:** Write the currency parser to accept `int`, `float`, `str`, and `None` inputs. Test with both file formats.
**Warning signs:** Tests pass with CSV but fail with XLSX (or vice versa).

### Pitfall 2: "infinite" in Months Remaining Field
**What goes wrong:** The `Months Remaining in RF` column can contain the string "infinite" (see sample row for Simon Peter). Trying to parse this as a Decimal will fail.
**Why it happens:** When a missionary's recurring gifts equal or exceed their cap, the months remaining is mathematically infinite.
**How to avoid:** Store as `CharField(max_length=20)` as specified in CONTEXT.md. Parse numeric values to string with consistent decimal formatting, pass "infinite" through unchanged.
**Warning signs:** Import fails on rows with "infinite" value.

### Pitfall 3: Percentage Column Has Different Representation in XLSX vs CSV
**What goes wrong:** In CSV, `% Standard to Max` appears as "104%" (string). In XLSX, it may appear as `1.04` (float) or `0.104` depending on cell formatting.
**Why it happens:** Excel stores percentages as decimals internally (104% = 1.04) and only displays the "%" sign via formatting.
**How to avoid:** Parse percentage as integer, handling both formats: if numeric and < 10, multiply by 100. If string with "%" suffix, strip "%" and parse.
**Warning signs:** Percentages showing as "1%" instead of "104%" when imported from XLSX.

### Pitfall 4: Negative Currency Values with Various Formats
**What goes wrong:** The sample data shows negative values formatted as `-$468.33` and `"-$3,368.33"` (with quotes in CSV due to comma). Some spreadsheets use parenthetical notation `($468.33)`.
**Why it happens:** Smartsheet/Excel export may use different negative formats.
**How to avoid:** Handle both `-$X` and `($X)` formats in the currency parser.
**Warning signs:** Negative values parsing as None or causing errors.

### Pitfall 5: Empty Cells in Optional Columns
**What goes wrong:** The `Total One-Time Gifts - April` column is empty for most rows. openpyxl returns `None` for empty XLSX cells; CSV returns empty string `""`.
**Why it happens:** Not all missionaries have one-time gifts in a given month.
**How to avoid:** All financial fields should be nullable (`null=True, blank=True`) in the model. The currency parser should return `None` for empty values.
**Warning signs:** IntegrityError on import due to NOT NULL constraint on optional fields.

### Pitfall 6: Duplicate User Names
**What goes wrong:** If two DonorCRM users have the same first + last name, the matching is ambiguous.
**Why it happens:** No uniqueness constraint on User.first_name + User.last_name.
**How to avoid:** During matching, detect if the name-lookup dict encounters a collision (two users with same name). Report it as a matching error for that row rather than silently picking one.
**Warning signs:** Data assigned to wrong user silently.

### Pitfall 7: UTF-8 BOM in CSV Files
**What goes wrong:** Excel CSV exports include a UTF-8 BOM (`\xef\xbb\xbf`) that corrupts the first column header.
**Why it happens:** Standard Excel behavior when saving as CSV.
**How to avoid:** Decode CSV with `utf-8-sig` encoding (already done in existing import views for fund/entity/transaction imports).
**Warning signs:** First column not recognized, "First Name" becomes "\ufeffFirst Name".

### Pitfall 8: Snapshot Deduplication
**What goes wrong:** Admin accidentally uploads the same file twice, creating duplicate snapshots.
**Why it happens:** The spec says "uploads do not overwrite" so there's no natural deduplication.
**How to avoid:** Consider a unique constraint on `(user, upload)` pair in MPDSnapshot, so the same upload cannot create two snapshots for the same user. Across uploads, duplicates are allowed (monthly accumulation).
**Warning signs:** Same missionary has two identical snapshot records from the same upload.

## Code Examples

### MPDUpload Model
```python
class MPDUpload(TimeStampedModel):
    """Audit trail for each Smartsheet MPD report upload."""
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='mpd_uploads',
    )
    filename = models.CharField(max_length=255)
    file_format = models.CharField(max_length=10)  # 'csv' or 'xlsx'

    # Row counts
    total_rows = models.IntegerField(default=0)
    matched_count = models.IntegerField(default=0)
    unmatched_count = models.IntegerField(default=0)

    # Unmatched row details (JSON list of {row, first_name, last_name})
    unmatched_rows = models.JSONField(default=list, blank=True)

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=[
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='processing',
    )
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'mpd_uploads'
        ordering = ['-created_at']
```

### MPDSnapshot Model
```python
class MPDSnapshot(TimeStampedModel):
    """Monthly MPD financial snapshot for a missionary."""
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='mpd_snapshots',
    )
    upload = models.ForeignKey(
        MPDUpload,
        on_delete=models.CASCADE,
        related_name='snapshots',
    )

    # Financial fields (all nullable for partial data)
    active_recurring_gifts = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    annual_gifts = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monthly_average = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    annual_mpd_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mpd_standard = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_below_mpd_standard = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mpd_maximum = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_above_below_maximum = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    latest_roll_forward_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_mpd_cap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proj_monthly_deduction_rfb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pay_forecast_12_months = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pay_forecast_over_fy = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_one_time_gifts_april = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Percentage field (stored as integer: 104 for "104%", -16 for "-16%")
    pct_standard_to_max = models.IntegerField(null=True, blank=True)

    # Boolean fields (Yes/No columns)
    met_mpd_standard = models.BooleanField(null=True)
    met_maximum = models.BooleanField(null=True)
    match_met = models.BooleanField(null=True)
    match_met_rest_fy = models.BooleanField(null=True)

    # Special field: can be numeric string or "infinite"
    months_remaining_rf = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        db_table = 'mpd_snapshots'
        ordering = ['-upload__created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'upload'],
                name='unique_snapshot_per_user_per_upload'
            ),
        ]
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
```

### Formula Injection Sanitization (extends existing pattern)
```python
# Reuse from existing services.py
FORMULA_PREFIXES = ('=', '+', '-', '@')

def sanitize_cell_value(value):
    """Strip formula injection characters from imported cell values.

    Unlike sanitize_csv_value() which adds a quote prefix for export,
    this strips dangerous prefixes entirely for import storage.
    """
    if value and isinstance(value, str):
        # Strip leading formula characters
        while value and value[0] in ('=', '+', '@', '\t', '\r'):
            value = value[1:]
        # Note: '-' is NOT stripped here because negative currency values
        # like "-$468.33" are legitimate data. Formula injection with '-'
        # requires '=' or '+' to follow. The currency parser handles '-'.
    return value
```

**Important nuance:** The existing `sanitize_csv_value()` prefixes with a quote for CSV export safety. For import/storage, we strip dangerous characters entirely. However, `-` (minus) must NOT be stripped because negative currency values like `-$468.33` are legitimate MPD data. Only strip `=`, `+`, `@`, `\t`, `\r` from the start of string values.

### View Pattern (follows existing import views)
```python
class MPDImportView(APIView):
    """POST: Upload Smartsheet MPD Dashboard Report (admin only)."""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if 'file' not in request.FILES:
            return Response(
                {'detail': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {'detail': 'File too large (max 10 MB)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Read raw bytes for format detection
        file_bytes = file.read()
        file_format = detect_file_format(file_bytes)

        # Parse file based on detected format
        # ... (parse, match users, create snapshots, return results)
```

### Yes/No Boolean Parsing
```python
def parse_yes_no(value) -> bool | None:
    """Parse Yes/No string to boolean."""
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ('yes', 'true', '1'):
        return True
    if s in ('no', 'false', '0'):
        return False
    return None
```

### Percentage Parsing
```python
def parse_percentage(value) -> int | None:
    """Parse percentage value to integer.

    Handles:
    - String: "104%", "-16%"
    - Float from XLSX: 1.04 (104%), -0.16 (-16%)
    - Integer: 104
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        # XLSX may return 1.04 for 104% or 104 for 104%
        # Heuristic: if abs(value) <= 10, it's a decimal ratio
        if abs(value) <= 10:
            return int(round(value * 100))
        return int(round(value))

    s = str(value).strip().rstrip('%').strip()
    if not s:
        return None

    try:
        return int(round(float(s)))
    except (ValueError, TypeError):
        return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| xlrd for .xlsx | openpyxl for .xlsx | xlrd 2.0 (2020) dropped .xlsx support | Must use openpyxl for .xlsx files |
| Full workbook load | `read_only=True` mode | openpyxl 2.4+ | Constant memory for large files |
| File extension check | Magic bytes detection | Best practice always | More reliable format detection |
| `FloatField` for money | `DecimalField` for money | Django best practice | Avoids floating-point precision issues |

**Deprecated/outdated:**
- `xlrd` (v2.0+): Only supports `.xls` format. Do not use for `.xlsx`.
- `pandas` for simple row parsing: Overkill dependency for reading ~50 rows.

## Open Questions

1. **Handling unmatched rows (Claude's Discretion)**
   - What we know: Unmatched rows must be reported to admin (IMP-04). CONTEXT.md says Claude decides between "skip and report" or "let admin map manually".
   - Recommendation: **Skip and report.** Return unmatched rows in the API response with row number, first name, and last name. Store them in `MPDUpload.unmatched_rows` JSON field. Manual mapping adds UI complexity for a rare edge case (new missionary not yet in system). Admin can add the user to DonorCRM and re-upload.

2. **Column name flexibility (Claude's Discretion)**
   - What we know: CONTEXT.md asks whether to hardcode or semi-flex. The report is from a specific Smartsheet template.
   - Recommendation: **Hardcode with case-insensitive normalization.** The column names are stable across exports of the same Smartsheet. Add `strip()` and `lower()` normalization for resilience. If a required column is missing, fail with a clear error listing expected vs found columns.

3. **What "report_month" means for time-series**
   - What we know: CONTEXT.md mentions `report_month` or `upload_date` for time-series queries.
   - What's unclear: The sample data doesn't contain a month/date column. The "month" is implied by when the admin uploads.
   - Recommendation: Use `upload.created_at` for time-series. The `MPDSnapshot` inherits `created_at` from `TimeStampedModel`, and `upload.created_at` groups all snapshots from the same upload. No separate `report_month` field is needed unless the admin should specify it during upload (adds complexity).

4. **Should we create a new Django app or add to `apps/imports`?**
   - What we know: MPDUpload and MPDSnapshot are import-related but store different data than existing import models.
   - Recommendation: **Add to `apps/imports`** to avoid a new app. The import app already handles file uploads, and adding 2 models + 1 service file keeps things cohesive. The alternative (new `apps/mpd` app) is over-engineering for 2 models.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `apps/imports/services.py` - established patterns for CSV parsing, currency parsing, formula injection
- Existing codebase: `apps/imports/views.py` - established patterns for file upload views
- Existing codebase: `apps/imports/models.py` - ImportRun model pattern
- Existing codebase: `apps/users/models.py` - User model with first_name, last_name fields
- Sample data file: `test_data/Sample Smartsheet MPD Dashboard Report.xlsx - MPD Dashboard 2025-2026.csv`
- [openpyxl documentation (v3.1.4)](https://openpyxl.readthedocs.io/en/latest/) - load_workbook API, read_only mode, data_only flag
- [openpyxl PyPI](https://pypi.org/project/openpyxl/) - current version 3.1.4, Python >=3.8

### Secondary (MEDIUM confidence)
- [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection) - formula characters: =, +, -, @
- [Smartsheet Export Documentation](https://help.smartsheet.com/articles/770623-exporting-sheets-reports-from-smartsheet) - export behavior
- [Django DecimalField best practices](https://deepintodjango.com/keeping-accurate-amounts-in-django-with-currencyfield) - max_digits=10, decimal_places=2

### Tertiary (LOW confidence)
- Smartsheet column name stability across exports - no official documentation found confirming this. Observed from sample data that names are descriptive and consistent with a template structure.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - openpyxl is the clear standard for .xlsx in Python, all other dependencies already in project
- Architecture: HIGH - follows established patterns in existing `apps/imports` with minor extensions
- Data model: HIGH - column list verified against actual sample file, field types derived from real data
- Pitfalls: HIGH - derived from actual sample data analysis and openpyxl documentation
- User matching: MEDIUM - first_name + last_name matching works for small orgs but has edge cases (duplicates, name variations)

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable domain, openpyxl unlikely to change significantly)
