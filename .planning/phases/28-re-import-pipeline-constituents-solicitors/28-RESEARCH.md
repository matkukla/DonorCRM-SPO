# Phase 28: RE Import Pipeline (Constituents & Solicitors) - Research

**Researched:** 2026-02-20
**Domain:** Django CSV import services, management commands, DRF file upload endpoints, encoding handling
**Confidence:** HIGH

## Summary

Phase 28 builds the import pipeline for Raiser's Edge Constituent and Solicitor CSV files. It creates a shared service layer consumed by both management commands (`import_re_constituents`, `import_re_solicitors`) and DRF API endpoints (for Phase 32's UI). The pipeline uses the ImportBatch model (created in Phase 27) for SHA256 dedup, row-level error collection, and import tracking.

The codebase already has extensive CSV import infrastructure in `apps/imports/services.py` (6 parse+import function pairs), `apps/imports/views.py` (9 import/export API views), and `apps/imports/mpd_services.py` (a well-structured service orchestrator). These provide strong patterns to follow. The key new requirements beyond existing patterns are: (1) cascading encoding detection (UTF-8-sig -> UTF-8 -> Windows-1252), (2) merge-only contact updates (never overwrite non-blank fields), (3) solicitor name normalization with auto-linking to User accounts, and (4) SHA256-based dedup via ImportBatch.

One critical finding: the Solicitor model currently uses `OneToOneField` to User, but the Phase 28 CONTEXT.md specifies "Multiple Solicitor records can link to the same User account (many-to-one is allowed)." This requires changing the FK to `ForeignKey` before the import service can work correctly.

**Primary recommendation:** Follow the existing service layer pattern from `mpd_services.py` (orchestrator function + helper functions) and the parse/import separation from `services.py`. Create new `re_services.py` in the imports app with a clear service interface that both management commands and API endpoints call. Use Python's built-in `codecs` module for cascading encoding detection (no external library needed).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Contact Matching**: Match hierarchy: external_constituent_id first, then email, then phone. If none match, create new Contact.
- **ID/Email Conflict**: When external_constituent_id matches but email/phone differs from existing Contact: trust the ID match but log a warning flagging the conflict for admin review.
- **Merge-only**: Only fill blank fields on the Contact. Never overwrite existing non-blank values, even if RE has different data.
- **Solicitor Name Normalization**: Handles "Last, First" vs "First Last" format differences (case-insensitive, trimmed, reversed format detection), but no fuzzy matching beyond that.
- **Unlinked Solicitors**: When a solicitor doesn't match any User account: create Solicitor unlinked, and include it in the import summary as "unlinked solicitors" for admin review.
- **Multiple Solicitors per User**: Multiple Solicitor records can link to the same User account (many-to-one is allowed). Admin cleans up later if needed.
- **Row-scoped errors**: Always process every row, collect all errors, report at end. Never abort mid-file for row errors.
- **File-scoped errors**: Can't interpret safely (wrong format, missing required headers, unreadable encoding): abort entire file immediately.
- **Error detail per row**: Row number + error message. No raw row data stored.
- **SHA256 dedup**: Re-uploading same file returns the cached ImportBatch result. No force-reprocess option.
- **Header validation**: Flexible by default (required headers must be present, extras ignored), strict when it protects correctness.
- **Management commands**: `python manage.py import_re_constituents <file>` and `python manage.py import_re_solicitors <file>`.
- **API endpoints**: Build now for Phase 32's UI. Management command and API share the same service layer.
- **Permissions**: Admin/superuser only (is_staff or is_superuser).
- **CLI output**: Show progress indicator while processing, then print summary counts (created, updated, skipped, errors).

### Claude's Discretion
- Minimum data threshold for creating new Contacts from name-only rows
- Solicitor dedup key strategy (external_solicitor_id vs normalized name)
- Exact progress indicator format in management commands
- Service layer architecture (how to structure shared logic between command and API)
- Encoding cascade implementation details (UTF-8-sig, UTF-8, Windows-1252)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IMP-01 | RE Constituent import creates/updates Contacts with externalConstituentId matching, email/phone fallback, merge-only updates | Existing Contact model has `external_constituent_id` (Phase 27), cascading match logic documented, merge-only pattern identified, existing entity import in `services.py` provides update_or_create pattern |
| IMP-02 | RE Solicitor import creates Solicitor records with normalized name dedup and auto-link to User accounts | Solicitor model exists with `normalized_name` and `external_solicitor_id` fields; User model has `first_name`/`last_name` for name matching; name normalization pattern documented |
| IMP-05 | SHA256 idempotency -- re-uploading same file returns cached result without reprocessing | ImportBatch model has `sha256_hash` with `UniqueConstraint(fields=['import_type', 'sha256_hash'])` -- query before processing, return existing batch if found |
| IMP-06 | Row-level error collection -- errors don't stop processing, final report shows all errors with row numbers | Existing parse functions in `services.py` demonstrate row-level error collection pattern; ImportBatch.summary JSON can store error details; decision to NOT store raw row data |
| IMP-07 | Windows-1252 encoding detection with cascading fallback (UTF-8-sig, UTF-8, Windows-1252) | Python `codecs` module handles all three natively; cascading try/except pattern documented; no external library needed |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2.27 | ORM, management commands, migrations | Already in project |
| djangorestframework | 3.16.1 | API endpoints with MultiPartParser | Already in project |
| Python csv module | stdlib | CSV parsing | Already used extensively in `services.py` |
| Python hashlib | stdlib | SHA256 file hashing | Standard library, no dependency needed |
| Python codecs | stdlib | Encoding detection/fallback | Standard library, handles UTF-8-sig, UTF-8, Windows-1252 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| factory-boy | 3.3.3 | Test factories | Already installed; create test fixtures |
| pytest | (installed) | Test framework | Already configured in pyproject.toml |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual cascading decode (codecs) | chardet/cchardet library | chardet adds dependency and is probabilistic; cascading try/except is deterministic and handles the specific RE use case (UTF-8-sig > UTF-8 > Windows-1252) perfectly. Use manual cascade. |
| Storing errors in ImportBatch.summary JSON | Separate ImportBatchError model | Per CONTEXT.md, only row number + error message needed (no raw row data). JSON in summary field is sufficient and avoids a new model. Existing ImportRowError model stores raw row data which we explicitly don't want. |
| New `apps/re_imports/` app | Services in existing `apps/imports/` | Keep in `apps/imports/` -- it already has all import infrastructure. Add `re_services.py` alongside existing `services.py` and `mpd_services.py`. |

**Installation:** No new packages needed. All functionality uses stdlib and existing dependencies.

## Architecture Patterns

### Recommended File Structure
```
apps/imports/
├── models.py                # Existing - ImportBatch already defined
├── services.py              # Existing - SPO import services
├── mpd_services.py          # Existing - Smartsheet MPD import
├── re_services.py           # NEW - RE Constituent + Solicitor import services
├── views.py                 # Existing - add RE import API endpoints
├── urls.py                  # Existing - add RE import URL patterns
├── management/
│   ├── __init__.py          # NEW
│   └── commands/
│       ├── __init__.py      # NEW
│       ├── import_re_constituents.py  # NEW
│       └── import_re_solicitors.py    # NEW
├── tests/
│   ├── test_re_services.py          # NEW - unit tests for service layer
│   └── test_re_import_views.py      # NEW - integration tests for API endpoints
└── admin.py                 # Existing - ImportBatch already registered
```

### Pattern 1: Cascading Encoding Detection
**What:** Try decoding file bytes through UTF-8-sig > UTF-8 > Windows-1252, use first success.
**When to use:** Every RE CSV file read (both management command and API).
**Example:**
```python
def decode_csv_bytes(file_bytes: bytes) -> str:
    """Decode CSV bytes with cascading encoding fallback.

    RE exports may use UTF-8 (modern), UTF-8-sig (Excel), or
    Windows-1252 (legacy with smart quotes, accented names).

    Raises ValueError if no encoding works (should never happen
    since Windows-1252 accepts all byte values 0x00-0xFF).
    """
    for encoding in ('utf-8-sig', 'utf-8', 'windows-1252'):
        try:
            return file_bytes.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    # windows-1252 accepts all single bytes, so this should be unreachable
    raise ValueError('Unable to decode file with any supported encoding')
```
**Confidence:** HIGH -- Python's built-in codecs handle all three encodings. Windows-1252 is a superset of ISO-8859-1 and accepts all byte values, making it the final fallback that always succeeds.

### Pattern 2: SHA256 Dedup Check
**What:** Hash file bytes, check ImportBatch for existing hash+type combo, return cached result if found.
**When to use:** Before any parsing or processing begins.
**Example:**
```python
import hashlib
from apps.imports.models import ImportBatch, ImportBatchType

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
```
**Confidence:** HIGH -- ImportBatch already has UniqueConstraint on (import_type, sha256_hash).

### Pattern 3: Service Orchestrator (following mpd_services.py)
**What:** Single entry-point function that orchestrates the full import pipeline.
**When to use:** Both management command and API endpoint call the same function.
**Example:**
```python
def import_re_constituents(
    file_bytes: bytes,
    filename: str,
    uploaded_by,
    owner,  # Contact owner for new contacts
) -> ImportBatch:
    """Import RE Constituent CSV end-to-end.

    Steps:
    1. SHA256 dedup check
    2. Decode with cascading encoding
    3. Validate headers
    4. Parse rows with error collection
    5. Match/create/update contacts
    6. Create ImportBatch record with results

    Returns ImportBatch (may be existing if duplicate).
    """
    # Step 1: Check for duplicate
    existing = check_duplicate_import(file_bytes, ImportBatchType.RE_CONSTITUENT)
    if existing:
        return existing  # Return cached result

    # Step 2: Decode
    content = decode_csv_bytes(file_bytes)

    # Step 3-6: Parse, validate, import...
    ...
```
**Confidence:** HIGH -- directly follows `process_mpd_upload()` pattern from mpd_services.py.

### Pattern 4: Merge-Only Contact Updates
**What:** When updating an existing Contact, only fill blank/empty fields. Never overwrite non-blank values.
**When to use:** When external_constituent_id or email/phone matches an existing Contact.
**Example:**
```python
def merge_contact_fields(contact: Contact, new_data: dict) -> list[str]:
    """Merge new data into contact, only filling blank fields.

    Returns list of field names that were updated.
    """
    updated_fields = []
    merge_fields = [
        'first_name', 'last_name', 'email', 'phone', 'phone_secondary',
        'street_address', 'city', 'state', 'postal_code', 'country',
        'organization_name',
    ]
    for field in merge_fields:
        current_value = getattr(contact, field, '')
        new_value = new_data.get(field, '')
        if not current_value and new_value:
            setattr(contact, field, new_value)
            updated_fields.append(field)
    return updated_fields
```
**Confidence:** HIGH -- straightforward field-by-field comparison.

### Pattern 5: Solicitor Name Normalization
**What:** Normalize solicitor names to "Last, First" format for consistent matching.
**When to use:** When creating/matching Solicitor records from RE data.
**Example:**
```python
def normalize_solicitor_name(raw_name: str) -> str:
    """Normalize solicitor name to 'Last, First' format.

    Handles:
    - "Last, First" -> "last, first" (already correct format)
    - "First Last" -> "last, first" (reverse)
    - Case-insensitive, trimmed
    """
    name = raw_name.strip()
    if not name:
        return ''

    if ',' in name:
        # Already "Last, First" format
        parts = [p.strip() for p in name.split(',', 1)]
        return f'{parts[0].lower()}, {parts[1].lower()}'.strip(', ')
    else:
        # "First Last" format -- reverse
        parts = name.split()
        if len(parts) >= 2:
            first = ' '.join(parts[:-1])
            last = parts[-1]
            return f'{last.lower()}, {first.lower()}'
        return name.lower()
```
**Confidence:** HIGH -- per CONTEXT.md, only handle "Last, First" vs "First Last" with case-insensitive matching. No fuzzy matching.

### Pattern 6: User Auto-Linking for Solicitors
**What:** Match solicitor normalized name against User.full_name (case-insensitive).
**When to use:** After creating/finding a Solicitor, attempt to link to a User account.
**Example:**
```python
def find_matching_user(normalized_name: str) -> User | None:
    """Find User with exact name match (case-insensitive).

    Builds "last, first" from User first_name + last_name and compares.
    """
    # Pre-build lookup from all active users
    # (batch this for the whole import, not per-solicitor)
    ...
```
**Confidence:** HIGH -- follows the `match_users()` pattern in mpd_services.py.

### Anti-Patterns to Avoid
- **Processing file twice for hash and content:** Hash the raw bytes once before decoding. Don't re-read the file.
- **Overwriting existing Contact data:** This is a merge-only import. Never set a field that already has a value.
- **Using chardet for encoding detection:** Chardet is probabilistic and adds a dependency. The cascading try/except is deterministic for the known RE encoding set.
- **Storing raw row data in errors:** Per CONTEXT.md decision, only store row number + error message. Don't store raw row data.
- **Creating separate ImportBatchError model:** Use ImportBatch.summary JSON field for errors. Keep it simple.
- **Aborting on row errors:** Per CONTEXT.md, always process every row. Only abort for file-level errors (missing headers, unreadable encoding).

## Critical Finding: Solicitor.user Field Type

**Issue:** The Solicitor model (Phase 27) uses `OneToOneField('users.User')`, but Phase 28 CONTEXT.md specifies "Multiple Solicitor records can link to the same User account (many-to-one is allowed)."

**Impact:** The `OneToOneField` enforces a database-level constraint preventing multiple Solicitors from linking to the same User. This will cause `IntegrityError` during import if two solicitor rows resolve to the same User.

**Required fix:** Migration to change `Solicitor.user` from `OneToOneField` to `ForeignKey`. This is a simple field type change that preserves all existing data.

```python
# Change from:
user = models.OneToOneField('users.User', ...)
# To:
user = models.ForeignKey('users.User', ...)
```

**Confidence:** HIGH -- the CONTEXT.md decision is explicit about many-to-one. The migration is non-destructive.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Encoding detection | chardet-based detection library | Cascading `bytes.decode()` with try/except | RE exports use only 3 known encodings; deterministic cascade is simpler and more reliable |
| SHA256 hashing | Custom hash function | `hashlib.sha256(file_bytes).hexdigest()` | Standard library, cryptographically sound |
| CSV parsing | Custom field parser | Python `csv.DictReader` | Handles quoting, escaping, newlines in fields correctly |
| File upload handling | Manual multipart parsing | DRF `MultiPartParser` | Already used by 6+ existing import views |
| Management command framework | Custom CLI tool | Django `BaseCommand` | Integrated with Django settings, DB access, argument parsing |

**Key insight:** The entire import pipeline can be built with Python stdlib (`csv`, `hashlib`, `codecs`) plus Django/DRF infrastructure already in the project. No new dependencies required.

## Common Pitfalls

### Pitfall 1: Encoding Cascade Order Matters
**What goes wrong:** UTF-8 succeeds on Windows-1252 files that happen to have no high-bit characters, but fails on the next file that has smart quotes.
**Why it happens:** ASCII is valid in all three encodings. Files with only ASCII characters will decode successfully with any encoding.
**How to avoid:** Try `utf-8-sig` first (handles BOM), then `utf-8` (most common modern encoding), then `windows-1252` (accepts all byte values as final fallback). This order is correct and deterministic.
**Warning signs:** Tests pass with ASCII-only test data but fail with real RE exports containing accented names or smart quotes.

### Pitfall 2: Merge-Only Logic Must Handle Empty vs Missing
**What goes wrong:** A CSV row has an empty email field (the column exists but value is blank), causing the merge logic to see "new value is empty" and skip it. But what about a CSV that completely lacks an email column?
**Why it happens:** `csv.DictReader` returns empty string `''` for present-but-empty fields, and `None` or missing key for absent columns.
**How to avoid:** Merge logic should only fill blank fields when the NEW data has a non-empty value. Both empty-string and missing-key should be treated as "no new data to merge."
**Warning signs:** Contacts getting their email/phone blanked out after import.

### Pitfall 3: Contact Owner Assignment for New Contacts
**What goes wrong:** RE Constituents imported via management command create Contacts without an owner, or assign the wrong owner.
**Why it happens:** Contact requires an `owner` FK (per Contact model), but RE CSV data doesn't specify which staff member owns the contact.
**How to avoid:** Management command must accept an owner parameter (or use the command-running admin user). API endpoint uses the authenticated user. Document this clearly.
**Warning signs:** `IntegrityError` on Contact.owner (it's a required FK with PROTECT).

### Pitfall 4: SHA256 Hash Must Be on Raw Bytes, Not Decoded String
**What goes wrong:** Same file uploaded with different Python string encoding produces different hashes, defeating dedup.
**Why it happens:** Hashing the decoded string means the hash changes based on which encoding was used to decode.
**How to avoid:** Always hash `file_bytes` (the raw uploaded bytes) before any decoding. This ensures identical files always produce identical hashes regardless of decode path.
**Warning signs:** Same file uploaded twice creates two ImportBatch records instead of returning cached result.

### Pitfall 5: Solicitor OneToOneField Prevents Many-to-One
**What goes wrong:** Second solicitor linking to same User raises IntegrityError.
**Why it happens:** Phase 27 model uses `OneToOneField` but Phase 28 requirements allow many-to-one.
**How to avoid:** Must migrate `Solicitor.user` from `OneToOneField` to `ForeignKey` before import service can work.
**Warning signs:** Import fails when two solicitor CSV rows map to the same staff user.

### Pitfall 6: RE CSV Headers Are Customizable
**What goes wrong:** Import service expects exact RE field codes (e.g., `CnBio_ID`, `CnBio_First_Name`) but the admin exported with custom column headers.
**Why it happens:** RE allows admins to rename export column headers.
**How to avoid:** Accept common RE header variations. Document required headers clearly. Per CONTEXT.md: required headers must be present (flexible on extras). Consider case-insensitive header matching and a small set of aliases.
**Warning signs:** Every RE export from a different organization fails header validation.

## Code Examples

### Management Command Pattern (from existing generate_sample_data.py)
```python
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Import RE Constituent CSV file'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to CSV file')
        parser.add_argument(
            '--owner',
            type=str,
            required=True,
            help='Email of the user who will own new contacts'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate without importing'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
        except FileNotFoundError:
            raise CommandError(f'File not found: {file_path}')

        # Call shared service layer
        batch = import_re_constituents(
            file_bytes=file_bytes,
            filename=file_path,
            uploaded_by=owner_user,
            owner=owner_user,
        )

        # Print summary
        self.stdout.write(self.style.SUCCESS(
            f'Created: {batch.created_count}, Updated: {batch.updated_count}, '
            f'Errors: {batch.error_count}'
        ))
```
**Confidence:** HIGH -- follows Django management command conventions and existing `generate_sample_data.py` pattern.

### API Endpoint Pattern (from existing import views)
```python
class REConstituentImportView(APIView):
    """POST: Import RE Constituent CSV file (admin only)."""
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

        file_bytes = file.read()

        # Call shared service layer
        batch = import_re_constituents(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
            owner=request.user,
        )

        # Return result
        return Response({
            'batch_id': str(batch.id),
            'status': batch.status,
            'is_duplicate': batch.status == 'duplicate',
            'created_count': batch.created_count,
            'updated_count': batch.updated_count,
            'skipped_count': batch.skipped_count,
            'error_count': batch.error_count,
            'summary': batch.summary,
        })
```
**Confidence:** HIGH -- follows existing pattern from EntityImportView, FundImportView, etc.

### RE Constituent CSV Expected Headers
Based on Raiser's Edge export documentation, typical constituent CSV headers include:
```
CnBio_ID (or ConsID, Constituent_ID) -> external_constituent_id
CnBio_First_Name (or FirstName, First Name) -> first_name
CnBio_Last_Name (or LastName, Last Name) -> last_name
CnBio_Org_Name (or OrgName) -> organization_name
CnAdrPrf_Email (or Email, Email Address) -> email
CnPh_1_01_Phone_number (or Phone, Phone Number) -> phone
CnAdrPrf_Addrline1 (or Address, Address Line 1) -> street_address
CnAdrPrf_City (or City) -> city
CnAdrPrf_State (or State) -> state
CnAdrPrf_ZIP (or ZIP, Postal Code) -> postal_code
CnAdrPrf_ContryLongDsc (or Country) -> country
```
**Confidence:** MEDIUM -- RE headers vary by installation and export configuration. Implementation should use case-insensitive matching with a mapping of common aliases.

### RE Solicitor CSV Expected Headers
```
Solicitor_ID (or SolID) -> external_solicitor_id
Solicitor_Name (or Name, Full Name) -> raw name for normalization
```
**Confidence:** MEDIUM -- solicitor export format varies. The critical field is the name for normalization.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single encoding decode (`utf-8-sig`) | Cascading decode fallback | Phase 28 (new) | Handles Windows-1252 RE exports transparently |
| Entity import with `update_or_create` (overwrites) | Merge-only updates (fill blanks only) | Phase 28 (new) | Preserves manually-entered Contact data |
| ImportRun for audit trail | ImportBatch with SHA256 dedup | Phase 27 model | Prevents duplicate file processing |
| No management commands for imports | Management commands + API endpoints | Phase 28 (new) | Admin can import via CLI or future UI |

**Deprecated/outdated:**
- Existing `import_entities()` in services.py uses `update_or_create` which overwrites existing data. Phase 28's RE import must NOT follow this pattern -- it uses merge-only updates per CONTEXT.md.

## Discretion Recommendations

### Minimum Data for New Contact Creation
**Recommendation:** Require at least one of: (a) first_name + last_name, (b) organization_name. A row with only an external_constituent_id and no name/org data should be treated as an error -- there's nothing useful to display to users.
**Rationale:** Contacts with no identifying information are useless in the UI. The existing Contact model requires `first_name`, so we need at least that.

### Solicitor Dedup Key Strategy
**Recommendation:** Use `external_solicitor_id` as primary dedup key when present. Fall back to `normalized_name` when no external ID exists. Within a single file, dedup by the key (first occurrence wins, subsequent rows for same key are skipped with warning).
**Rationale:** External ID is the most reliable identifier. Name-based dedup catches duplicates when RE doesn't export IDs.

### Progress Indicator Format
**Recommendation:** Use a simple counter: `Processing row 50 of 200...` printed with `\r` for in-place updates. Final summary on separate lines.
**Rationale:** Simple, doesn't require external libraries (like `tqdm`). Compatible with all terminals.

### Service Layer Architecture
**Recommendation:** Create `apps/imports/re_services.py` with:
- `decode_csv_bytes(file_bytes)` -- cascading encoding
- `check_duplicate_import(file_bytes, import_type)` -- SHA256 dedup
- `import_re_constituents(file_bytes, filename, uploaded_by, owner)` -- orchestrator
- `import_re_solicitors(file_bytes, filename, uploaded_by)` -- orchestrator
- Helper functions for parsing, validation, matching
**Rationale:** Follows `mpd_services.py` pattern (single file, orchestrator + helpers). Service functions return `ImportBatch` instances.

### Encoding Cascade Implementation
**Recommendation:** Try `utf-8-sig` first (handles BOM from Excel exports), then `utf-8`, then `windows-1252`. Windows-1252 always succeeds (accepts all byte values), so this cascade is exhaustive.
**Rationale:** Deterministic, no external dependencies, covers all known RE export encodings.

## Open Questions

1. **RE CSV header names are installation-specific**
   - What we know: RE allows admins to customize export column headers
   - What's unclear: Whether this specific installation uses RE field codes (`CnBio_ID`) or friendly names (`Constituent ID`)
   - Recommendation: Implement case-insensitive header matching with a mapping of common aliases. First real import will confirm the exact headers; we can add aliases as needed.

2. **Contact owner for RE constituent imports**
   - What we know: Contact requires an `owner` FK, RE CSV doesn't include owner info
   - What's unclear: Whether all imported contacts should be owned by one user or distributed
   - Recommendation: Management command requires `--owner` email flag. API endpoint uses `request.user`. This can be revisited if multi-owner assignment is needed.

3. **Solicitor CSV vs embedded solicitor data in Gift CSV**
   - What we know: Phase 28 imports a standalone Solicitor CSV. Phase 29 imports Gift CSVs that include solicitor columns.
   - What's unclear: Whether the standalone Solicitor CSV has different columns than the solicitor data embedded in Gift exports
   - Recommendation: Phase 28 imports handle the standalone Solicitor file. Phase 29 can reuse the name normalization and matching logic.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `apps/imports/services.py` -- existing parse/import patterns for contacts, donations, entities, funds, transactions, pledges
- Codebase analysis: `apps/imports/mpd_services.py` -- service orchestrator pattern with `process_mpd_upload()`
- Codebase analysis: `apps/imports/models.py` -- ImportBatch model with SHA256 dedup, ImportBatchType enum
- Codebase analysis: `apps/gifts/models.py` -- Solicitor model with normalized_name, external_solicitor_id
- Codebase analysis: `apps/contacts/models.py` -- Contact model with external_constituent_id, address fields
- Codebase analysis: `apps/users/models.py` -- User model with first_name, last_name, full_name property
- Codebase analysis: `apps/imports/views.py` -- existing API endpoint patterns with MultiPartParser
- Python documentation: `codecs` module for encoding handling (UTF-8-sig, UTF-8, Windows-1252)
- Python documentation: `hashlib.sha256` for file hashing
- Python documentation: `csv.DictReader` for CSV parsing

### Secondary (MEDIUM confidence)
- [Blackbaud RE Import Guide](https://help.blackbaud.com/docs/0/assets/guides/re/import.pdf) -- RE CSV field codes and headers
- [Blackbaud RE Query & Export Guide](https://webfiles-sc1.blackbaud.com/files/support/guides/re7ent/queryexp.pdf) -- RE export column configuration
- [Neon One: Exporting from RE](https://support.neonone.com/hc/en-us/articles/4407398875533-Exporting-Data-from-The-Raiser-s-Edge) -- RE export process and field selection
- [chardet documentation](https://chardet.readthedocs.io/en/latest/how-it-works.html) -- encoding detection methodology (decided NOT to use, but informed cascade approach)

### Tertiary (LOW confidence)
- RE CSV header names are installation-specific and may vary. The exact headers for this project's RE installation need to be confirmed with a real export file.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib + existing project dependencies
- Architecture: HIGH -- directly follows existing patterns (mpd_services.py, services.py)
- Pitfalls: HIGH -- all identified from codebase analysis and known RE export behavior
- RE header format: MEDIUM -- headers vary by installation, will need real data to confirm

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (30 days -- stable domain, no fast-moving libraries)
