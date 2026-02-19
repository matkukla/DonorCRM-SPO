# Phase 24: Smartsheet Import Backend - Research

**Researched:** 2026-02-19
**Domain:** File parsing (Excel/CSV), column auto-mapping, row validation, formula injection prevention
**Confidence:** HIGH

## Summary

Phase 24 adds a two-step Smartsheet import workflow to the existing `apps/imports` Django app: (1) upload a file, parse it, detect headers, auto-map columns, and return mappings with confidence tiers; (2) commit the import using confirmed mappings and a user-chosen duplicate strategy. The backend already has mature CSV import infrastructure (`services.py` with 1372 lines covering 4 import types, `ImportRun`/`ImportRowError` models, formula injection constants, date/amount parsing helpers). Phase 24 extends this by adding Excel (.xlsx) support via openpyxl, magic-bytes-based format detection, fuzzy column matching via rapidfuzz, a new `ImportSession` model for storing parsed data between steps, and a unified validation pipeline that works across all three target models (Contact, Donation, Pledge).

The critical architectural decision is to build Phase 24 as NEW service functions and endpoints alongside the existing import code, not to refactor the existing SPO-specific CSV importers. The existing `parse_funds_csv`, `parse_entities_csv`, `parse_transactions_csv`, and `parse_pledges_csv` functions are tightly coupled to their specific column schemas and should remain untouched. The new Smartsheet import pipeline is fundamentally different: it supports user-defined column mappings (the old pipeline assumes fixed column names), multiple record types per file, and a two-step workflow with session persistence.

**Primary recommendation:** Use openpyxl (read_only mode) for .xlsx parsing, Python csv module for .csv parsing, magic bytes (first 4 bytes = `PK` for xlsx vs text heuristic for csv) for format detection, rapidfuzz for column auto-matching, and a new `ImportSession` model with JSONField for storing parsed rows between upload and commit steps. All new code goes in the existing `apps/imports` app as new service functions -- do not modify existing import functions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Column Mapping:**
- Confidence scores use three tiers: Green (exact/high confidence), Yellow (partial/fuzzy match), Red (no match)
- Green = exact alias match, Yellow = fuzzy/partial match, Red = unmapped
- Full scope: Contact fields + Donation fields + Pledge fields
- Contact: first_name, last_name, email, phone, address, city, state, zip, external_id, notes, tags
- Donation: amount, date, fund, payment_method, external_id
- Pledge: amount, frequency, start_date, end_date, status, external_id
- A single spreadsheet can create records across all three models

**Validation & Error Handling:**
- Collect ALL errors across all rows -- no early stopping or threshold
- Every row is validated regardless of how many errors have accumulated
- Partial import allowed -- user can choose to import only valid rows
- Rejected rows available as downloadable error CSV
- Full model validation -- same rules as form entry (email format, phone format, valid state codes, amount > 0, date parsing, required fields)
- Uses Django model-level validation to stay consistent
- Error CSV format: Row Number, Field Name, Error Message (one row per error)

**Import Workflow:**
- Two-step: (1) Upload -> parse -> return headers + auto-detected mappings, (2) Commit -> validate -> import valid rows -> return results + error CSV
- Parse immediately on upload, store as JSON in database (ImportSession model)
- Original file not retained after parsing
- 25 MB / ~50k rows maximum
- Processing is synchronous (no background jobs)
- ImportSession tracks: timestamp, user, filename, row counts, status (pending_mapping, pending_commit, completed, failed)

**Duplicate Handling:**
- Contact duplicate detection: email only
- User chooses per-import: Skip, Update, or Flag for Review

**Security:**
- Strip/escape formula injection characters (=, +, -, @, \t, \r) from cell values

### Claude's Discretion

- Column matching strategy (fuzzy vs alias-based vs hybrid)
- UX for Red/unmapped columns (top-N suggestions vs leave blank)
- Donation/Pledge duplicate detection approach

### Deferred Ideas (OUT OF SCOPE)
_(None captured during discussion)_
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openpyxl | 3.1.5 | Parse .xlsx files | De facto Python Excel library; read_only mode for memory efficiency; MIT license; used internally by pandas |
| defusedxml | >=0.7 | Protect against XML bomb attacks in xlsx | openpyxl docs explicitly recommend it; prevents billion laughs / quadratic blowup attacks |
| rapidfuzz | >=3.0 | Fuzzy string matching for column auto-mapping | 16x faster than thefuzz; MIT license (vs GPL for thefuzz); C++ core; drop-in API compatible |
| csv (stdlib) | builtin | Parse CSV files | Already used throughout `apps/imports/services.py`; no external dependency needed |
| io (stdlib) | builtin | BytesIO/StringIO for in-memory file handling | Already used throughout existing import code |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| charset-normalizer | >=3.0 | Detect CSV file encoding | When CSV file is not UTF-8; more accurate than chardet; already a dependency of `requests` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openpyxl | pandas + openpyxl engine | pandas adds unnecessary overhead -- we only need row iteration, not DataFrames; pandas is not in requirements |
| rapidfuzz | thefuzz (fuzzywuzzy) | GPL license, 16x slower, no C++ acceleration; rapidfuzz is strictly better |
| python-magic | filetype | python-magic requires libmagic system dependency; filetype is pure Python but unnecessary since xlsx detection is trivial (PK magic bytes) |
| charset-normalizer | chardet | chardet is slower on large files and less accurate on modern datasets |

### Installation
```bash
pip install openpyxl>=3.1.5 defusedxml>=0.7 rapidfuzz>=3.0
```

Add to `requirements/base.txt`:
```
openpyxl>=3.1,<4.0
defusedxml>=0.7,<1.0
rapidfuzz>=3.0,<4.0
```

## Architecture Patterns

### Recommended Project Structure
All new code lives in the existing `apps/imports/` app:
```
apps/imports/
  models.py          # Add ImportSession model (alongside existing ImportRun)
  services.py        # Existing SPO import functions (DO NOT MODIFY)
  smartsheet.py      # NEW: All Smartsheet import logic (parsing, mapping, validation, commit)
  views.py           # Add new endpoints for upload + commit
  urls.py            # Add new URL patterns
  tests/
    test_smartsheet.py  # NEW: Tests for Smartsheet import pipeline
```

### Pattern 1: Two-Step Import with ImportSession
**What:** Upload creates an ImportSession with parsed rows stored as JSON; commit reads the session, validates, and imports.
**When to use:** Whenever the import workflow requires user interaction between parsing and committing.

```python
# Step 1: Upload endpoint
class SmartsheetUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        file = request.FILES['file']
        # 1. Detect format (xlsx vs csv)
        # 2. Parse to list of dicts (rows)
        # 3. Extract headers
        # 4. Auto-map columns with confidence scores
        # 5. Store parsed rows in ImportSession
        # 6. Return headers + mappings + session_id

# Step 2: Commit endpoint
class SmartsheetCommitView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        session_id = request.data['session_id']
        mappings = request.data['mappings']       # {source_col: target_field}
        duplicate_strategy = request.data['duplicate_strategy']
        # 1. Load ImportSession
        # 2. Apply mappings to transform rows
        # 3. Validate ALL rows (collect all errors)
        # 4. Import valid rows based on duplicate_strategy
        # 5. Generate error CSV for invalid rows
        # 6. Update ImportSession status + counts
        # 7. Return results
```

### Pattern 2: File Format Detection Without External Libraries
**What:** Detect xlsx vs csv by reading the first few bytes of the uploaded file.
**When to use:** Always -- avoids needing python-magic or filetype as dependencies.

```python
def detect_file_format(file_obj) -> str:
    """Detect file format from magic bytes. Returns 'xlsx' or 'csv'."""
    # Read first 4 bytes
    header = file_obj.read(4)
    file_obj.seek(0)  # Reset for subsequent reads

    # XLSX files are ZIP archives: magic bytes = PK\x03\x04
    if header[:4] == b'PK\x03\x04':
        return 'xlsx'

    # Everything else, try as CSV (CSV has no magic bytes)
    return 'csv'
```

### Pattern 3: Hybrid Column Mapping (Aliases + Fuzzy Fallback)
**What:** First try exact alias matching (high confidence), then fall back to fuzzy matching for unmatched columns.
**When to use:** For the auto-detection step in upload response.

```python
# Alias registry: each target field has a list of known aliases
COLUMN_ALIASES = {
    'first_name': ['first name', 'first_name', 'firstname', 'fname', 'given name', 'given_name'],
    'last_name': ['last name', 'last_name', 'lastname', 'lname', 'surname', 'family name', 'family_name'],
    'email': ['email', 'email address', 'e-mail', 'email_address', 'emailaddress'],
    'phone': ['phone', 'phone number', 'telephone', 'tel', 'phone_number', 'mobile'],
    'street_address': ['address', 'street', 'street address', 'street_address', 'address1', 'mailing address'],
    'city': ['city', 'town'],
    'state': ['state', 'province', 'st', 'region'],
    'postal_code': ['zip', 'zip code', 'zipcode', 'postal code', 'postal_code', 'zip_code'],
    'external_id': ['external id', 'external_id', 'ext_id', 'id', 'donor id', 'donor_id', 'entity_id'],
    'notes': ['notes', 'comments', 'memo', 'description'],
    # Donation fields
    'amount': ['amount', 'gift amount', 'donation amount', 'gift_amount', 'donation_amount', 'total'],
    'date': ['date', 'gift date', 'donation date', 'gift_date', 'donation_date', 'posted_date'],
    'fund': ['fund', 'fund name', 'fund_name', 'account', 'campaign'],
    'payment_method': ['payment method', 'payment_method', 'method', 'pay method', 'payment type'],
    # Pledge fields
    'frequency': ['frequency', 'cadence', 'schedule', 'recurrence', 'pledge frequency'],
    'start_date': ['start date', 'start_date', 'begin date', 'effective date'],
    'end_date': ['end date', 'end_date', 'expiry date', 'expiration date'],
    'status': ['status', 'pledge status', 'state'],
}

def auto_map_columns(source_headers: list[str]) -> list[dict]:
    """
    Auto-map source headers to target fields.
    Returns list of {source, target, confidence} dicts.
    """
    mappings = []
    used_targets = set()

    for header in source_headers:
        normalized = header.strip().lower().replace('_', ' ')

        # Phase 1: Exact alias match -> GREEN
        match = _try_alias_match(normalized, used_targets)
        if match:
            mappings.append({'source': header, 'target': match, 'confidence': 'green'})
            used_targets.add(match)
            continue

        # Phase 2: Fuzzy match -> YELLOW (score >= 80)
        match, score = _try_fuzzy_match(normalized, used_targets)
        if match and score >= 80:
            mappings.append({'source': header, 'target': match, 'confidence': 'yellow'})
            used_targets.add(match)
            continue

        # Phase 3: No match -> RED (with top-3 suggestions)
        suggestions = _get_suggestions(normalized, used_targets)
        mappings.append({'source': header, 'target': None, 'confidence': 'red', 'suggestions': suggestions})

    return mappings
```

### Pattern 4: Formula Injection Sanitization on Import
**What:** Strip dangerous formula prefix characters from every cell value during parsing.
**When to use:** Always, on every text value parsed from the uploaded file.

```python
# Characters that trigger formula execution in spreadsheet apps
FORMULA_CHARS = {'=', '+', '-', '@', '\t', '\r', '\n'}

def sanitize_cell_value(value: str) -> str:
    """Strip formula injection characters from cell values per OWASP guidelines."""
    if not value or not isinstance(value, str):
        return value
    # Strip leading formula characters (may be chained: "==cmd")
    while value and value[0] in FORMULA_CHARS:
        value = value[1:]
    return value.strip()
```

Note: The existing codebase in `services.py` uses `FORMULA_PREFIXES = ('=', '+', '-', '@')` and the `sanitize_csv_value()` function prefixes with a single quote on EXPORT. For IMPORT, we should STRIP the characters rather than prefix, since we're ingesting data into our database, not outputting to a spreadsheet.

### Pattern 5: Unified Row Validation
**What:** Validate rows against the target model's rules, reusing existing validation helpers.
**When to use:** During the commit step, after mappings are applied.

```python
def validate_row(row: dict, mappings: dict, row_num: int) -> list[dict]:
    """
    Validate a single mapped row. Returns list of errors.
    Each error: {'row_number': int, 'field_name': str, 'error_message': str}
    """
    errors = []
    # Reuse existing helpers from services.py:
    # - _validate_email(email) for email format
    # - _parse_amount(amount_str) for donation/pledge amounts
    # - _parse_date(date_str) for date fields
    # Add: required field checks, max length checks, enum validation
    return errors
```

### Anti-Patterns to Avoid
- **Modifying existing service functions:** The existing `parse_entities_csv`, `parse_transactions_csv`, etc. are tightly coupled to SPO column schemas. Do NOT refactor them to share code with Smartsheet import. Duplicate validation helpers if needed.
- **Storing the original file:** The context says "Original file is not retained after parsing." Parse to JSON immediately, store in ImportSession.
- **Loading entire xlsx into memory without read_only:** Always use `load_workbook(file, read_only=True)` to avoid memory bloat on large files.
- **Using pandas:** The project does not have pandas in requirements. openpyxl directly is lighter and sufficient for row iteration.
- **Relying on file extension for format detection:** Use magic bytes (PK header) for xlsx detection, not `.xlsx` extension. Fall back to csv for anything that isn't a zip archive.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom Levenshtein implementation | `rapidfuzz.fuzz.token_sort_ratio` + `rapidfuzz.process.extractOne` | Handles word reordering ("last name" vs "name last"), C++ performance, edge cases |
| Excel parsing | Custom XML/ZIP extraction | `openpyxl.load_workbook(read_only=True)` | Handles merged cells, date formats, number formats, shared strings |
| XML bomb protection | Custom XML parser | `defusedxml` (installed alongside openpyxl) | Prevents billion laughs, quadratic blowup, XXE attacks |
| CSV encoding detection | Custom charset guessing | `charset-normalizer` or try utf-8-sig then latin-1 | Handles BOM, Windows-1252, edge cases |
| Date parsing | New date parser | Reuse existing `_parse_date()` from `services.py` | Already handles 5 date formats, tested in production |
| Amount parsing | New amount parser | Reuse existing `_parse_amount()` from `services.py` | Already handles $, commas, negative, max value |
| Email validation | New regex | Reuse existing `_validate_email()` from `services.py` | Already validated pattern, tested |

**Key insight:** The existing `services.py` already has well-tested validation helpers (`_parse_date`, `_parse_amount`, `_validate_email`, `FORMULA_PREFIXES`). Import these into the new `smartsheet.py` module rather than duplicating them.

## Common Pitfalls

### Pitfall 1: openpyxl Returns None for Empty Cells
**What goes wrong:** Iterating rows with openpyxl in read_only mode, empty cells return `None` instead of empty string. Code does `cell.value.strip()` and gets `AttributeError: 'NoneType' object has no attribute 'strip'`.
**Why it happens:** openpyxl represents truly empty cells as None, not as empty strings like csv.DictReader does.
**How to avoid:** Always coerce cell values: `str(cell.value).strip() if cell.value is not None else ''`
**Warning signs:** Tests pass with dense data but fail when users upload files with empty columns.

### Pitfall 2: openpyxl Date Cells Return datetime Objects, Not Strings
**What goes wrong:** Excel stores dates as serial numbers with a date format. openpyxl returns `datetime.datetime` objects for date-formatted cells, not strings. The validation pipeline that expects string input (like `_parse_date()`) gets a datetime and fails or double-parses.
**Why it happens:** openpyxl automatically converts Excel date serial numbers to Python datetime objects based on cell number format.
**How to avoid:** Check cell value type during parsing: if it's already a `datetime.date` or `datetime.datetime`, convert to ISO string or pass through directly. Only call `_parse_date()` on string values.
**Warning signs:** Dates work in CSV imports but break or produce wrong values in Excel imports.

### Pitfall 3: Excel Number Cells Return float/int, Not Strings
**What goes wrong:** Amount column in Excel returns `100.0` (float) instead of `"100.00"` (string). The `_parse_amount()` function expects a string and may handle the float incorrectly, or the `$` stripping logic fails.
**Why it happens:** Excel stores numbers as numeric types. openpyxl returns the native Python type.
**How to avoid:** Normalize all cell values to strings during the parsing phase: `str(cell.value)` for non-None values. Or handle both types in the validation functions.
**Warning signs:** Works with CSV (all strings) but amounts are wrong or cause errors with Excel files.

### Pitfall 4: CSV Files with BOM (Byte Order Mark)
**What goes wrong:** User exports from Excel to CSV. The file starts with `\ufeff` (UTF-8 BOM). The first column header becomes `\ufefffirst_name` instead of `first_name`. Column mapping fails to match the first column.
**Why it happens:** Excel on Windows adds a BOM when saving as "CSV UTF-8". The existing import code uses `utf-8-sig` encoding in FundImportView and EntityImportView but `utf-8` in ContactImportView and DonationImportView (inconsistency in existing code).
**How to avoid:** Always decode with `utf-8-sig` which strips the BOM if present and works identically to `utf-8` if no BOM. The existing codebase already does this in some views.
**Warning signs:** First column never matches in mapping despite appearing correct visually.

### Pitfall 5: JSON Storage Size for Large Files
**What goes wrong:** Storing 50,000 rows as JSON in a Django JSONField can produce a very large database row (potentially hundreds of MB if rows have many columns). PostgreSQL handles JSONB well but the serialization/deserialization in Python can be slow.
**Why it happens:** The context specifies 25MB/50k rows max and JSON storage in the database. At 50k rows with 15 columns, the JSON could be 50-100MB.
**How to avoid:** Store only the cell values (not metadata) in a compact format. Use a list of lists (not list of dicts) to avoid repeating header names 50k times. Store headers separately. For 50k rows x 15 cols at ~50 bytes/cell avg = ~37MB which is within PostgreSQL's tolerance.
**Warning signs:** Commit step is very slow for large files; database response times increase.

### Pitfall 6: Contact UniqueConstraint Complications
**What goes wrong:** Contact model has `UniqueConstraint(fields=['owner', 'email'], condition=~Q(email=''))`. When using email-based duplicate detection with "Update" strategy, `update_or_create` may fail or create duplicates if the email is empty.
**Why it happens:** The conditional unique constraint means empty emails are allowed to duplicate. The duplicate detection (email-only per context) must handle the case where imported rows have no email -- they should always create new contacts since there's nothing to match on.
**How to avoid:** Only apply duplicate detection when the imported row has a non-empty email. Rows with no email always create new contacts (skip/update/flag strategies don't apply).
**Warning signs:** Duplicate detection works for rows with emails but throws IntegrityError or creates unexpected duplicates for rows without.

### Pitfall 7: Concurrent ImportSession Access
**What goes wrong:** User uploads file (creates session), then opens same page in another tab and uploads again. Both sessions are "pending_mapping". User commits from Tab 1 successfully, then commits from Tab 2 -- double import of the same data.
**Why it happens:** No guard against committing an already-committed session.
**How to avoid:** Check session status before committing. Only allow commit if status is `pending_mapping` or `pending_commit`. Use `select_for_update()` to prevent race conditions. Transition to `completed` atomically.
**Warning signs:** Users report duplicate records appearing after import.

## Code Examples

### Example 1: Parsing Excel File with openpyxl (read_only mode)

```python
from openpyxl import load_workbook
import io

def parse_xlsx(file_bytes: bytes) -> tuple[list[str], list[list[str]]]:
    """
    Parse xlsx file bytes into headers and rows.
    Returns (headers, rows) where rows is list of list of string values.
    """
    wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    try:
        ws = wb.active
        rows_iter = ws.iter_rows()

        # First row = headers
        header_row = next(rows_iter, None)
        if not header_row:
            return [], []
        headers = [str(cell.value).strip() if cell.value is not None else '' for cell in header_row]

        # Remaining rows = data
        rows = []
        for row in rows_iter:
            values = []
            for cell in row:
                if cell.value is None:
                    values.append('')
                elif isinstance(cell.value, (int, float)):
                    # Preserve numeric precision
                    values.append(str(cell.value))
                elif hasattr(cell.value, 'isoformat'):
                    # datetime/date objects -> ISO string
                    values.append(cell.value.isoformat())
                else:
                    values.append(str(cell.value).strip())
            rows.append(values)

        return headers, rows
    finally:
        wb.close()
```

### Example 2: Parsing CSV with Encoding Detection

```python
import csv
import io

def parse_csv(file_bytes: bytes) -> tuple[list[str], list[list[str]]]:
    """
    Parse CSV file bytes into headers and rows.
    Tries utf-8-sig first (handles BOM), falls back to latin-1.
    """
    # Try UTF-8 with BOM handling first
    try:
        content = file_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        content = file_bytes.decode('latin-1')

    reader = csv.reader(io.StringIO(content))
    header_row = next(reader, None)
    if not header_row:
        return [], []

    headers = [h.strip() for h in header_row]
    rows = []
    for row in reader:
        # Pad short rows, trim long rows to match header count
        padded = row + [''] * (len(headers) - len(row))
        rows.append([v.strip() for v in padded[:len(headers)]])

    return headers, rows
```

### Example 3: Fuzzy Column Matching with rapidfuzz

```python
from rapidfuzz import fuzz, process

def _try_fuzzy_match(normalized_header: str, used_targets: set) -> tuple[str | None, int]:
    """
    Try fuzzy matching against all target field aliases.
    Returns (target_field, score) or (None, 0).
    """
    # Build choices from all aliases of unused targets
    choices = {}
    for target, aliases in COLUMN_ALIASES.items():
        if target not in used_targets:
            for alias in aliases:
                choices[alias] = target

    if not choices:
        return None, 0

    result = process.extractOne(
        normalized_header,
        choices.keys(),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=70  # Minimum score to consider
    )

    if result:
        matched_alias, score, _ = result
        return choices[matched_alias], score

    return None, 0

def _get_suggestions(normalized_header: str, used_targets: set, limit: int = 3) -> list[str]:
    """Get top-N target field suggestions for an unmatched column."""
    available = [t for t in COLUMN_ALIASES.keys() if t not in used_targets]
    if not available:
        return []

    # Score each available target by best alias match
    scored = []
    for target in available:
        best = max(
            fuzz.token_sort_ratio(normalized_header, alias)
            for alias in COLUMN_ALIASES[target]
        )
        scored.append((target, best))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in scored[:limit]]
```

### Example 4: ImportSession Model

```python
from django.db import models
from apps.core.models import TimeStampedModel

class ImportSessionStatus(models.TextChoices):
    PENDING_MAPPING = 'pending_mapping', 'Pending Mapping'
    PENDING_COMMIT = 'pending_commit', 'Pending Commit'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'

class ImportSession(TimeStampedModel):
    """Stores parsed spreadsheet data between upload and commit steps."""
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='import_sessions'
    )
    filename = models.CharField(max_length=255)
    file_format = models.CharField(max_length=10)  # 'xlsx' or 'csv'
    status = models.CharField(
        max_length=20,
        choices=ImportSessionStatus.choices,
        default=ImportSessionStatus.PENDING_MAPPING
    )

    # Parsed data (stored as JSON to avoid re-parsing)
    headers = models.JSONField(default=list)        # ["First Name", "Last Name", ...]
    rows = models.JSONField(default=list)            # [[val, val, ...], [val, val, ...]]
    auto_mappings = models.JSONField(default=list)   # [{source, target, confidence}, ...]

    # Confirmed mappings (set during commit)
    confirmed_mappings = models.JSONField(default=dict, blank=True)
    duplicate_strategy = models.CharField(max_length=20, blank=True)

    # Row counts
    total_rows = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'import_sessions'
        ordering = ['-created_at']
```

## Discretionary Decisions (Claude's Recommendations)

### Column Matching Strategy: Hybrid (Alias + Fuzzy)
**Recommendation:** Use a two-phase approach -- exact alias matching first (GREEN), then rapidfuzz fuzzy matching for unmatched columns (YELLOW), then leave remaining as RED with top-3 suggestions.

**Rationale:** Pure fuzzy matching has false positives (e.g., "status" matching "state" at 83%). Pure alias matching misses creative column names. The hybrid approach gives high confidence for known patterns and reasonable guesses for unknown ones. The alias registry can grow over time as users encounter new column naming patterns.

**Fuzzy scorer:** Use `fuzz.token_sort_ratio` (not `fuzz.ratio` or `fuzz.partial_ratio`). Token sort handles word reordering: "Last Name" vs "Name, Last" both score high. Set threshold at 80 for YELLOW confidence.

### UX for Red/Unmapped Columns: Top-3 Suggestions
**Recommendation:** For unmapped columns, provide the top 3 closest target field suggestions sorted by fuzzy score. The frontend can present these as a dropdown pre-populated with suggestions, with the option to select "Skip this column" or choose any target field.

**Rationale:** Leaving blank provides no guidance. Top-N suggestions are lightweight to compute and help users who have unusual column names. Three suggestions is enough to be helpful without being overwhelming.

### Donation/Pledge Duplicate Detection: External ID Only
**Recommendation:** For donations and pledges, use `external_id` as the sole duplicate detection key. If no external_id is provided in the import, treat every row as a new record (no dedup).

**Rationale:** Financial records are dangerous to deduplicate on fuzzy criteria. Two $100 donations on the same date to the same contact could be legitimate separate transactions. External ID is the only safe, deterministic key. The existing codebase already uses `external_id` with conditional unique constraints on both Donation and Pledge models. This is consistent with how `import_transactions` and `import_pledges` already work.

For contacts: use email (per locked decision). For donations/pledges: use external_id. If neither is available, always create new.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| fuzzywuzzy (Python-only) | rapidfuzz (C++ backend) | 2021+ | 16x faster fuzzy matching; MIT license |
| chardet for encoding | charset-normalizer | 2022+ | Better accuracy, actively maintained |
| Store uploaded file on disk | Parse immediately, store as JSON | Current best practice | No file storage needed, simpler cleanup |
| Manual engine specification | Magic bytes detection | Standard practice | Users don't need to choose file format |

**Deprecated/outdated:**
- `fuzzywuzzy`: Renamed to `thefuzz`, but both are superseded by `rapidfuzz`
- `xlrd` for .xlsx: xlrd dropped xlsx support in v2.0 (2020); only reads .xls now
- `python-magic` for simple format detection: Requires libmagic system dependency; overkill for xlsx-vs-csv

## Open Questions

1. **Session Cleanup / Expiry**
   - What we know: ImportSession stores parsed rows as JSON. Abandoned sessions (user uploads but never commits) will accumulate.
   - What's unclear: When to clean up abandoned sessions. The context doesn't specify.
   - Recommendation: Add a `expires_at` field set to 24 hours after creation. A future cron job or management command can clean up expired sessions. For Phase 24, just set the field -- cleanup can be a later task.

2. **"Flag for Review" Duplicate Strategy Implementation**
   - What we know: User can choose "Flag for Review" for contacts with matching emails.
   - What's unclear: Where do flagged records go? Are they stored in ImportSession? A separate table? How does the user review them later?
   - Recommendation: For Phase 24 (backend only), flagged rows should be stored as ImportRowError records with a special error type like "duplicate_flagged". They are NOT imported. The error CSV includes them with a message like "Duplicate contact (email: x@y.com) -- flagged for review." The actual review UI is a future phase concern. This keeps the backend simple and consistent with the existing error CSV pattern.

3. **Tags Field on Contact Import**
   - What we know: The CONTEXT lists "tags" as a Contact target field. The Contact model has a M2M `groups` field.
   - What's unclear: How to handle tags in import -- create Groups on the fly? Match existing Group names?
   - Recommendation: Match existing Group names (case-insensitive). If a tag doesn't match an existing Group, report as a validation warning but still import the contact. Comma-separated tags in a single cell.

4. **Multi-Model Import from Single Spreadsheet**
   - What we know: "A single spreadsheet can create records across all three models."
   - What's unclear: How the user signals which rows are contacts vs donations vs pledges. Are they inferred from the mappings? Does the user choose?
   - Recommendation: Infer from confirmed mappings. If the user maps columns to Contact fields (first_name, last_name), the system creates Contacts. If they also map amount + date, it creates Donations linked to those Contacts. If they map frequency + start_date, it creates Pledges. The key is: Contact fields create/match contacts; Donation fields create donations linked to those contacts; Pledge fields create pledges linked to those contacts. Each row can produce up to 3 records (1 contact + 1 donation + 1 pledge).

## Existing Codebase Integration Points

### Reusable from `apps/imports/services.py`
- `_validate_email()` - Email format validation
- `_parse_amount()` - Amount string parsing with currency/comma handling
- `_parse_date()` - Multi-format date parsing (5 formats)
- `FORMULA_PREFIXES` - Formula injection character tuple
- `sanitize_csv_value()` - Export sanitization (reference for import approach)
- `VALID_DONATION_TYPES`, `VALID_PAYMENT_METHODS`, `VALID_PLEDGE_FREQUENCIES`, `VALID_PLEDGE_STATUSES` - Enum value lists
- `DATE_FORMATS` - Accepted date format strings

### Reusable Models
- `ImportRun` - Can optionally be created during commit step for audit trail (alongside ImportSession)
- `ImportRowError` - Can store per-row errors during commit for error CSV download
- `Fund` - Referenced by donation/pledge imports; match by name or external_id

### Settings to Update
- `DATA_UPLOAD_MAX_MEMORY_SIZE` in `config/settings/base.py`: Currently 10MB, needs to increase to 25MB per context
- `FILE_UPLOAD_MAX_MEMORY_SIZE` in `config/settings/base.py`: Currently 10MB, needs to increase to 25MB per context
- `MAX_UPLOAD_SIZE` in `apps/imports/views.py`: Currently 10MB, new Smartsheet endpoints should use 25MB

### URL Patterns
New endpoints to add to `apps/imports/urls.py`:
```python
path('smartsheet/upload/', SmartsheetUploadView.as_view(), name='smartsheet-upload'),
path('smartsheet/commit/', SmartsheetCommitView.as_view(), name='smartsheet-commit'),
path('smartsheet/sessions/<uuid:session_id>/', SmartsheetSessionView.as_view(), name='smartsheet-session'),
path('smartsheet/sessions/<uuid:session_id>/errors/csv/', SmartsheetErrorCSVView.as_view(), name='smartsheet-errors-csv'),
```

## Sources

### Primary (HIGH confidence)
- [openpyxl official docs - Optimised Modes](https://openpyxl.readthedocs.io/en/stable/optimized.html) - read_only mode, iter_rows, memory usage
- [openpyxl official docs - Tutorial](https://openpyxl.readthedocs.io/en/3.1/tutorial.html) - load_workbook API, BytesIO support
- [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection) - Formula injection characters (=, +, -, @, \t, \r), mitigation approaches
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) - API, scorers, process.extractOne
- [RapidFuzz PyPI](https://pypi.org/project/RapidFuzz/) - v3.14.3, MIT license, Python >=3.9
- [openpyxl PyPI](https://pypi.org/project/openpyxl/) - v3.1.5, MIT license, Python >=3.8

### Secondary (MEDIUM confidence)
- Existing codebase: `apps/imports/services.py` - 1372 lines of production-tested import logic
- Existing codebase: `apps/imports/models.py` - ImportRun, ImportRowError, Fund models
- Existing codebase: `apps/imports/views.py` - View patterns, MultiPartParser usage, error response format
- [CWE-1236: Improper Neutralization of Formula Elements in CSV](https://cwe.mitre.org/data/definitions/1236.html) - Formula injection CWE reference

### Tertiary (LOW confidence)
- [Django Forum: DATA_UPLOAD_MAX_MEMORY_SIZE vs FILE_UPLOAD_MAX_MEMORY_SIZE](https://forum.djangoproject.com/t/why-does-django-throw-a-data-upload-max-memory-size-error-even-when-uploading-files-not-setting-file-upload-max-memory-size/41194) - Setting interaction details

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - openpyxl and rapidfuzz are well-established, verified via official docs and PyPI
- Architecture: HIGH - Two-step import pattern is well-defined by CONTEXT.md; ImportSession model follows existing codebase conventions
- Pitfalls: HIGH - Verified against existing codebase (found real inconsistencies like BOM handling), cross-referenced with prior pitfalls research
- Column mapping: MEDIUM - Alias + fuzzy hybrid is a sound approach but optimal thresholds (80 for YELLOW) may need tuning with real user data

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable domain, no fast-moving dependencies)
