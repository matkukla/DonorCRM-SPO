# Phase 8: Funds CSV Import - Research

**Researched:** 2026-01-30
**Domain:** Django CSV import with validation, upsert patterns, and security
**Confidence:** HIGH

## Summary

Phase 8 implements the first CSV import type (Funds) following established Django/DRF patterns already proven in the codebase for Contact and Donation imports. The research confirms that Python's stdlib csv module paired with Django 4.2's bulk_create with update_conflicts provides the optimal stack for idempotent upserts on PostgreSQL.

The existing codebase already has the complete import infrastructure (models.py with Fund, ImportRun, ImportRowError; views.py pattern with MultiPartParser; services.py parse/import pattern). The research focused on three critical areas: (1) PostgreSQL-specific bulk upsert patterns for idempotency, (2) CSV security (injection attacks via formula prefixes), and (3) validation patterns for enum fields and required columns.

**Primary recommendation:** Follow the existing ContactImportView/parse_contacts_csv pattern exactly, adapting validation logic for Fund-specific fields (fund_id as external_id, status enum, no foreign keys). Use bulk_create with update_conflicts=True for PostgreSQL-native upserts, and sanitize all CSV output (not input) to prevent formula injection attacks.

## Standard Stack

The established libraries/tools for Django CSV import:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python csv | stdlib | CSV parsing with DictReader | Industry standard, built-in, handles RFC 4180 format |
| Django ORM | 4.2 | Database operations with bulk_create | Native bulk upsert via update_conflicts (Django 4.1+) |
| PostgreSQL | 12+ | Database backend | Supports ON CONFLICT DO UPDATE for upserts |
| Django REST Framework | 3.14+ | API endpoints with MultiPartParser | Existing codebase standard for all endpoints |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-import-export | 3.3+ | Advanced import with admin UI | NOT recommended - adds complexity for simple use case |
| pandas | 2.x | Large CSV processing | NOT needed - stdlib csv handles < 10k rows efficiently |
| chardet | 5.x | Encoding detection | Optional - only if users upload non-UTF8 files frequently |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| csv.DictReader | pandas.read_csv | Pandas adds 100MB dependency for features we don't need |
| bulk_create(update_conflicts=True) | update_or_create() in loop | 10-100x slower for bulk operations, no atomicity |
| Python stdlib | django-csvimport package | Adds dependency for functionality already implemented |

**Installation:**
```bash
# No new dependencies required - using stdlib csv + Django 4.2 features
# Existing: Django==4.2.27, djangorestframework, psycopg2-binary
```

## Architecture Patterns

### Recommended Project Structure
```
apps/imports/
├── models.py              # Fund, ImportRun, ImportRowError (EXISTING)
├── services.py            # parse_funds_csv, import_funds (NEW)
├── views.py               # FundImportView (NEW), existing Contact/Donation patterns
├── urls.py                # Add /api/v1/imports/funds/ (NEW)
└── admin.py               # Fund, ImportRun admin (OPTIONAL)
```

### Pattern 1: Parse-Validate-Import Pipeline
**What:** Three-stage CSV processing: (1) Parse CSV to dicts, (2) Validate each row collecting errors, (3) Atomic bulk import if validation passes.

**When to use:** All CSV import operations. Existing codebase uses this for Contact and Donation imports.

**Example:**
```python
# Source: Existing DonorCRM apps/imports/services.py (Contact import pattern)
def parse_funds_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    """
    Parse funds CSV and return (valid_records, errors).

    Expected columns: fund_id, name, status
    """
    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except csv.Error as e:
        return [], [{'row': 1, 'errors': [f'Invalid CSV format: {e}'], 'data': {}}]

    valid_records = []
    errors = []
    seen_fund_ids = set()

    # Validate required columns present
    if reader.fieldnames:
        required_cols = {'fund_id', 'name', 'status'}
        missing_cols = required_cols - set(reader.fieldnames)
        if missing_cols:
            return [], [{'row': 1, 'errors': [f'Missing required columns: {", ".join(missing_cols)}'], 'data': {}}]

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Required field validation
        fund_id = row.get('fund_id', '').strip()
        if not fund_id:
            row_errors.append('fund_id is required')
        elif len(fund_id) > 100:
            row_errors.append('fund_id exceeds max length of 100 characters')
        elif fund_id in seen_fund_ids:
            row_errors.append(f'Duplicate fund_id in file: {fund_id}')
        else:
            seen_fund_ids.add(fund_id)

        name = row.get('name', '').strip()
        if not name:
            row_errors.append('name is required')
        elif len(name) > 255:
            row_errors.append('name exceeds max length of 255 characters')

        # Enum validation
        status = row.get('status', '').strip().lower()
        valid_statuses = ['active', 'inactive', 'closed']
        if status and status not in valid_statuses:
            row_errors.append(f'Invalid status: "{status}". Valid options: {", ".join(valid_statuses)}')

        if row_errors:
            errors.append({'row': row_num, 'errors': row_errors, 'data': dict(row)})
        else:
            valid_records.append({
                'fund_id': fund_id,
                'name': name,
                'status': status or 'active',
            })

    return valid_records, errors
```

### Pattern 2: Idempotent Bulk Upsert (Django 4.2 + PostgreSQL)
**What:** Use bulk_create with update_conflicts=True to insert new records or update existing ones based on external_id uniqueness.

**When to use:** All imports where external system provides stable IDs. Enables re-uploading CSV without duplicates.

**Example:**
```python
# Source: Django 4.2 docs + verified PostgreSQL pattern
from django.db import transaction
from apps.imports.models import Fund, ImportRun

def import_funds(records: List[dict], import_run: ImportRun) -> Tuple[int, int]:
    """
    Import funds using bulk upsert pattern.

    Returns: (created_count, updated_count)
    """
    # Track existing fund_ids to calculate created vs updated
    existing_fund_ids = set(
        Fund.objects.filter(
            external_id__in=[r['fund_id'] for r in records]
        ).values_list('external_id', flat=True)
    )

    fund_objects = [
        Fund(
            external_id=record['fund_id'],
            name=record['name'],
            status=record['status'],
            owner=None  # Org-wide funds have null owner
        )
        for record in records
    ]

    with transaction.atomic():
        Fund.objects.bulk_create(
            fund_objects,
            update_conflicts=True,
            update_fields=['name', 'status'],  # external_id is lookup key
            unique_fields=['external_id']  # Must match unique constraint
        )

    created_count = len([r for r in records if r['fund_id'] not in existing_fund_ids])
    updated_count = len(records) - created_count

    import_run.created_count = created_count
    import_run.updated_count = updated_count
    import_run.status = 'completed'
    import_run.save()

    return created_count, updated_count
```

**Critical notes:**
- Requires PostgreSQL 9.5+ or SQLite 3.24+ (DonorCRM uses PostgreSQL)
- unique_fields must match a unique constraint on the model
- update_fields must NOT include fields in unique_fields
- Cannot use ForeignKey fields in update_fields (not applicable for Fund)

### Pattern 3: API View with Validate-Only Mode
**What:** DRF APIView with MultiPartParser that supports ?validate_only=true query param for preview before import.

**When to use:** All import endpoints. Existing pattern in ContactImportView and DonationImportView.

**Example:**
```python
# Source: Existing DonorCRM apps/imports/views.py (ContactImportView pattern)
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

class FundImportView(APIView):
    """
    POST: Import funds from CSV file (admin only)

    Query params:
        validate_only: If 'true', only validate without importing
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        # File validation
        if 'file' not in request.FILES:
            return Response(
                {'detail': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response(
                {'detail': 'File must be a CSV.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Read and decode with BOM handling
        try:
            content = file.read().decode('utf-8-sig')  # Handles UTF-8 BOM from Excel
        except UnicodeDecodeError:
            return Response(
                {'detail': 'File encoding error. Please use UTF-8.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse and validate
        valid_records, errors = parse_funds_csv(content, request.user)

        # Validate-only mode (dry run)
        if request.query_params.get('validate_only') == 'true':
            return Response({
                'valid_count': len(valid_records),
                'error_count': len(errors),
                'errors': errors[:20]  # Limit errors in response
            })

        # Import if validation passed
        if errors:
            return Response(
                {'detail': 'Validation errors found', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        if valid_records:
            import_run = ImportRun.objects.create(
                type='funds',
                status='importing',
                filename=file.name,
                total_rows=len(valid_records),
                uploaded_by=request.user
            )
            created, updated = import_funds(valid_records, import_run)
        else:
            return Response({'detail': 'No valid records to import'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'import_run_id': str(import_run.id),
            'created_count': created,
            'updated_count': updated,
            'error_count': 0
        })
```

### Anti-Patterns to Avoid
- **Partial imports on validation error:** Don't import valid rows if ANY row fails validation. User must fix all errors and re-upload (idempotent upsert makes this safe).
- **No encoding BOM handling:** Excel exports CSV with UTF-8 BOM. Use `decode('utf-8-sig')` not `decode('utf-8')`.
- **update_or_create in loop:** For bulk operations, use bulk_create with update_conflicts instead of looping update_or_create (100x performance difference).
- **Missing column validation:** Always validate required columns present BEFORE iterating rows. Prevents confusing errors when column name is misspelled.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing with encoding detection | Custom file decoder with chardet | decode('utf-8-sig') | Handles 99% of Excel/Google Sheets exports, simpler code |
| Bulk upsert logic | Loop with try/update_or_create | bulk_create(update_conflicts=True) | 10-100x faster, atomic, PostgreSQL-native |
| File upload API | Custom file handling | DRF MultiPartParser | Handles chunked uploads, memory limits, existing pattern |
| Import audit trail | Custom logging | ImportRun + ImportRowError models | Already implemented, queryable, supports error CSV download |
| CSV injection sanitization | Custom regex cleaner | Built-in approach on export only | Security best practice - sanitize output not input |

**Key insight:** The existing DonorCRM codebase already solved all CSV import infrastructure problems (models, views, services pattern). Phase 8 is 90% copy-paste from ContactImportView with Fund-specific validation logic. Don't re-architect - follow the proven pattern.

## Common Pitfalls

### Pitfall 1: CSV Injection Vulnerability
**What goes wrong:** User uploads CSV with cell starting with `=`, `+`, `-`, or `@`. When admin exports data to CSV and opens in Excel, formula executes (can leak data or execute commands).

**Why it happens:** Spreadsheet applications auto-execute formulas. CSV format has no concept of "text vs formula" - it's just data.

**How to avoid:**
- Sanitize on EXPORT (not import). Prepend single quote (') to any cell starting with `=+-@`
- Only needed for export_funds_csv function, not import
- Pattern: `value if not value.startswith(('=', '+', '-', '@')) else f"'{value}"`

**Warning signs:** Security audit flags CSV export functions without sanitization.

**Sources:**
- [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection)
- [Cyber Chief: CSV Formula Injection Best Practices](https://www.cyberchief.ai/2024/09/csv-formula-injection-attacks.html)
- [Sourcery Security Database: CSV Injection](https://www.sourcery.ai/vulnerabilities/csv-injection-vulnerabilities)

### Pitfall 2: Missing UTF-8 BOM Handling
**What goes wrong:** User exports CSV from Excel (which adds UTF-8 BOM marker), uploads to Django, sees weird characters (ï»¿) in first column header or fund_id.

**Why it happens:** Excel adds 3-byte BOM (EF BB BF) to UTF-8 files to signal encoding. Standard decode('utf-8') treats BOM as data, not metadata.

**How to avoid:** Use `file.read().decode('utf-8-sig')` instead of `decode('utf-8')`. The -sig variant strips BOM if present, passes through if absent.

**Warning signs:** User reports "Missing required columns" error despite CSV having correct headers. First fund_id in database has invisible characters.

**Sources:**
- [Python Discussions: UTF-8 BOM Not Being Consumed](https://discuss.python.org/t/utf-8-bom-not-being-consumed-when-opening-file/74870)
- [Elias Dorneles: How to Avoid BOM Issues](https://eliasdorneles.com/til/posts/utf8-sig/)

### Pitfall 3: Enum Validation Case Sensitivity
**What goes wrong:** CSV has status="Active" (capitalized), validation expects "active" (lowercase), import fails with "Invalid status" error.

**Why it happens:** Django TextChoices values are case-sensitive. Common pattern is lowercase for consistency.

**How to avoid:**
- Normalize user input: `status = row.get('status', '').strip().lower()`
- Validate against lowercase enum values: `if status not in ['active', 'inactive', 'closed']`
- Document in CSV template that status should be lowercase (or handle both cases)

**Warning signs:** Users report status validation errors despite using correct values. Different case than enum definition.

### Pitfall 4: bulk_create with update_conflicts on Wrong Fields
**What goes wrong:** bulk_create raises IntegrityError or updates wrong records because unique_fields don't match database constraint.

**Why it happens:** update_conflicts requires unique_fields parameter matching an actual unique constraint. If mismatch, PostgreSQL can't determine which row to update.

**How to avoid:**
- unique_fields must exactly match a UniqueConstraint or unique=True field
- For Fund: `unique_fields=['external_id']` (matches Fund.external_id unique=True)
- Verify with: `Fund._meta.constraints` or check migrations

**Warning signs:** IntegrityError: ON CONFLICT DO UPDATE command cannot affect row a second time. Or updates wrong records silently.

**Sources:**
- [Django Ticket #31685: bulk_create update_conflicts](https://code.djangoproject.com/ticket/31685)
- [Greg Kaleka: Bulk Update or Create in Django 4.1](https://gregkaleka.com/blog/bulk-update-or-create-django-41/)

### Pitfall 5: Forgetting Column Presence Validation
**What goes wrong:** User uploads CSV with typo in column name (fund_name instead of name). Parser iterates rows, every row fails validation with "name is required".

**Why it happens:** csv.DictReader silently creates dict with column names from header row. Missing expected column returns empty string for row.get('name').

**How to avoid:** Validate fieldnames BEFORE iterating rows:
```python
if reader.fieldnames:
    required_cols = {'fund_id', 'name', 'status'}
    missing_cols = required_cols - set(reader.fieldnames)
    if missing_cols:
        return [], [{'row': 1, 'errors': [f'Missing required columns: {", ".join(missing_cols)}'], 'data': {}}]
```

**Warning signs:** User gets 100 identical "field is required" errors when problem is misspelled column header.

## Code Examples

Verified patterns from official sources:

### Enum Field Validation
```python
# Source: Django 4.2 TextChoices pattern + existing DonorCRM models.py
from django.db import models

class Fund(models.Model):
    # Status choices using TextChoices (Django 3.0+)
    class StatusChoices(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        CLOSED = 'closed', 'Closed'

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE
    )

# Validation in parse_funds_csv:
valid_statuses = [choice.value for choice in Fund.StatusChoices]
status = row.get('status', '').strip().lower()
if status and status not in valid_statuses:
    row_errors.append(
        f'Invalid status: "{status}". Valid options: {", ".join(valid_statuses)}'
    )
```

**Sources:**
- [Django Documentation: Model Field Choices](https://docs.djangoproject.com/en/6.0/ref/models/fields/)
- [Adam Johnson: Moving to Django 3.0 Field.choices Enumeration Types](https://adamj.eu/tech/2020/01/27/moving-to-django-3-field-choices-enumeration-types/)

### CSV Formula Injection Prevention (Export Only)
```python
# Source: OWASP + Fluid Attacks best practices
def sanitize_csv_value(value: str) -> str:
    """Prevent CSV injection by escaping formula prefixes."""
    if not value:
        return value

    # Check if value starts with dangerous characters
    if value[0] in ('=', '+', '-', '@'):
        return f"'{value}"  # Prepend single quote to force text treatment

    return value

def export_funds_csv(queryset) -> str:
    """Export funds to CSV string with injection prevention."""
    output = io.StringIO()
    fieldnames = ['fund_id', 'name', 'status']

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for fund in queryset:
        writer.writerow({
            'fund_id': sanitize_csv_value(fund.external_id),
            'name': sanitize_csv_value(fund.name),
            'status': fund.status,  # Enum safe, no user input
        })

    return output.getvalue()
```

**Sources:**
- [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection)
- [Fluid Attacks: CSV Injection in Python](https://docs.fluidattacks.com/criteria/fixes/python/090/)

### Import with ImportRun Audit Trail
```python
# Source: Existing DonorCRM architecture + Django transaction pattern
from django.db import transaction
from apps.imports.models import ImportRun, ImportRowError

def import_funds_with_audit(records: List[dict], file_name: str, user):
    """Import funds with full audit trail."""
    import_run = ImportRun.objects.create(
        type='funds',
        status='importing',
        filename=file_name,
        total_rows=len(records),
        uploaded_by=user
    )

    try:
        with transaction.atomic():
            created, updated = import_funds(records, import_run)
            import_run.status = 'completed'
            import_run.save()
    except Exception as e:
        import_run.status = 'failed'
        import_run.error_summary = {'error': str(e)}
        import_run.save()
        raise

    return import_run, created, updated
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| update_or_create() in loop | bulk_create(update_conflicts=True) | Django 4.1 (Aug 2022) | 10-100x performance improvement for bulk upserts |
| Custom upsert SQL | Native Django ORM | Django 4.1+ | Portable across PostgreSQL/SQLite, simpler code |
| decode('utf-8') | decode('utf-8-sig') | Python 3.x best practice | Handles Excel UTF-8 BOM exports automatically |
| Manual duplicate checking | unique_fields in bulk_create | Django 4.1+ | Database enforces uniqueness, atomic operation |
| CharField(choices=TUPLE) | TextChoices enum class | Django 3.0 (Dec 2019) | Type safety, autocomplete, better error messages |

**Deprecated/outdated:**
- django-csvimport package: Adds complexity for features already in codebase
- pandas for simple CSV: Massive dependency (100MB+) for features stdlib provides
- ignore_conflicts=True: Loses track of created vs updated counts, use update_conflicts instead

## Open Questions

Things that couldn't be fully resolved:

1. **Fund.owner scoping**
   - What we know: Fund model has nullable owner FK for org-wide vs user-specific funds
   - What's unclear: Requirements don't specify if imported SPO funds should be owner-scoped or org-wide
   - Recommendation: Start with owner=None (org-wide) for all imported funds. Add owner-scoping in future phase if multi-org support needed.

2. **CSV file size limits**
   - What we know: Django default FILE_UPLOAD_MAX_MEMORY_SIZE is 2.5MB (holds in memory). Larger files write to temp disk.
   - What's unclear: Expected SPO fund CSV size (10 rows? 10,000 rows?)
   - Recommendation: No changes needed for MVP. Monitor production import sizes. Add Celery async import if admins report >5000 row files.

3. **Error CSV download**
   - What we know: ImportRowError model stores row_data for failed rows
   - What's unclear: Should Phase 8 implement "Download Errors CSV" endpoint?
   - Recommendation: Defer to Phase 9+ (Entities Import). Not critical for Funds since validation is simple (no foreign keys).

## Sources

### Primary (HIGH confidence)
- Django 4.2 Documentation: bulk_create with update_conflicts - https://docs.djangoproject.com/en/4.2/ref/models/querysets/#bulk-create
- Django 4.2 Documentation: TextChoices - https://docs.djangoproject.com/en/6.0/ref/models/fields/
- OWASP CSV Injection - https://owasp.org/www-community/attacks/CSV_Injection
- Existing DonorCRM codebase: apps/imports/services.py, views.py, models.py

### Secondary (MEDIUM confidence)
- [Greg Kaleka: Bulk Update or Create in Django 4.1](https://gregkaleka.com/blog/bulk-update-or-create-django-41/) - Verified update_conflicts pattern
- [Cyber Chief: CSV Formula Injection Best Practices](https://www.cyberchief.ai/2024/09/csv-formula-injection-attacks.html) - Sanitization patterns
- [Elias Dorneles: UTF-8 BOM Handling](https://eliasdorneles.com/til/posts/utf8-sig/) - Encoding best practices
- [Adam Johnson: Django Field.choices Enumeration Types](https://adamj.eu/tech/2020/01/27/moving-to-django-3-field-choices-enumeration-types/) - TextChoices migration guide

### Tertiary (LOW confidence)
- [Python Discussions: UTF-8 BOM](https://discuss.python.org/t/utf-8-bom-not-being-consumed-when-opening-file/74870) - Community discussion
- [Django Forum: bulk_create update_conflicts](https://forum.djangoproject.com/t/doubt-in-the-usage-of-bulk-create-with-update-conflicts-true/26362) - Implementation examples

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified Django 4.2 + PostgreSQL capabilities in official docs, existing codebase uses identical stack
- Architecture: HIGH - Patterns proven in existing Contact/Donation imports, direct code reuse possible
- Pitfalls: HIGH - CSV injection and BOM handling verified in OWASP/official sources, enum validation tested in codebase

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (30 days - stable Django/PostgreSQL ecosystem, no fast-moving dependencies)
