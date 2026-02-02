# Phase 11: Pledges CSV Import - Research

**Researched:** 2026-02-02
**Domain:** Django CSV import with foreign key validation for Pledge model (extends Phase 10 Transaction patterns)
**Confidence:** HIGH

## Summary

Phase 11 completes the CSV import pipeline by enabling Pledge imports using the validated patterns from Phases 8-10. The implementation is nearly identical to Phase 10 Transactions, with three key differences: (1) Pledge.external_id is globally unique (like Fund) not owner-scoped (like Contact), (2) fund_id is OPTIONAL for pledges per IMP-08, and (3) CSV column "cadence" maps to Pledge model field "frequency".

The critical insight: Pledge imports do NOT require denormalized stat updates on Contact. The Contact model has computed properties (`has_active_pledge`, `monthly_pledge_amount`) that query the pledge relationship directly, avoiding the denormalized pattern used for donations. This simplifies implementation compared to Phase 10.

The standard approach: (1) parse CSV with same validation patterns as Transactions, (2) pre-validate entity_id (owner-scoped Contact lookup) and fund_id (global Fund lookup, allow NULL), (3) validate cadence and status enums with case-insensitive matching, (4) bulk upsert Pledge records using external_id as unique field with update_or_create (conditional unique constraint pattern from Phase 9/10).

**Primary recommendation:** Clone Phase 10 Transaction import patterns exactly (parse + import_pledges service functions, PledgeImportView API endpoint, ImportRun audit tracking), remove Contact stats update logic, add enum validation for cadence/status, and handle optional fund_id.

## Standard Stack

The established libraries/tools for Pledge CSV import (identical to Phase 10):

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django ORM | 5.x+ | Database operations, bulk upsert, FK validation | Built-in, proven in Phases 8-10 |
| csv module | stdlib | CSV parsing via DictReader | Python standard library, used in all import phases |
| Django REST Framework | 3.x+ | API endpoints for CSV upload | Already in codebase, consistent pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| decimal.Decimal | stdlib | Amount parsing (already in services.py) | Financial calculations requiring precision |
| datetime | stdlib | Date parsing (already in services.py) | start_date field parsing |
| logging | stdlib | Import audit trail | Track import operations for debugging |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual CSV parsing | django-import-export | Too heavyweight for MVP, adds complexity. Manual parsing proven in Phases 8-10. |
| Individual saves | update_or_create | update_or_create IS the pattern (conditional unique constraint). Same as Phases 9-10. |
| Pre-import FK validation | Catching IntegrityError | IntegrityError provides poor UX (no row numbers). Strict mode requires pre-validation. |

**Installation:**
No new packages required - all functionality available in Django stdlib and existing dependencies.

## Architecture Patterns

### Recommended Project Structure
```
apps/imports/
├── services.py                # parse_pledges_csv, import_pledges (NEW)
├── views.py                   # PledgeImportView, PledgeTemplateView (NEW)
├── models.py                  # Fund, ImportRun (already exist)
└── tests/
    └── test_pledge_import.py  # Comprehensive test coverage (NEW)
```

### Pattern 1: Enum Validation with Case-Insensitive Matching

**What:** Validate cadence and status fields against Pledge enum choices, accepting case variations like Phase 8 Fund status validation.

**When to use:** When CSV contains enum fields that map to Django TextChoices (PledgeFrequency, PledgeStatus).

**Example:**
```python
# Source: Phase 8 parse_funds_csv status validation pattern + Pledge model
from apps.pledges.models import PledgeFrequency, PledgeStatus

# Valid enum values for validation
VALID_PLEDGE_FREQUENCIES = [f.value for f in PledgeFrequency]  # ['monthly', 'quarterly', 'semi_annual', 'annual']
VALID_PLEDGE_STATUSES = [s.value for s in PledgeStatus]        # ['active', 'paused', 'completed', 'cancelled']

def parse_pledges_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    # ... CSV parsing setup ...

    for row_num, row in enumerate(reader, start=2):
        # Parse cadence (CSV column) -> frequency (model field)
        cadence = row.get('cadence', '').strip().lower()
        if not cadence:
            row_errors.append('cadence is required')
        elif cadence not in VALID_PLEDGE_FREQUENCIES:
            row_errors.append(
                f'Invalid cadence: "{cadence}". '
                f'Valid options: {", ".join(VALID_PLEDGE_FREQUENCIES)}'
            )

        # Parse status
        status = row.get('status', '').strip().lower()
        if not status:
            row_errors.append('status is required')
        elif status not in VALID_PLEDGE_STATUSES:
            row_errors.append(
                f'Invalid status: "{status}". '
                f'Valid options: {", ".join(VALID_PLEDGE_STATUSES)}'
            )
```

### Pattern 2: Optional Foreign Key Validation

**What:** Validate fund_id references exist only if fund_id is provided (not required for pledges per IMP-08).

**When to use:** When foreign key is optional (fund field is nullable on Pledge model).

**Example:**
```python
# Source: Phase 10 FK validation + IMP-08 requirement
def parse_pledges_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    # First pass: collect FK references
    all_entity_ids = set()
    all_fund_ids = set()

    for row_num, row in enumerate(reader, start=2):
        entity_id = row.get('entity_id', '').strip()
        fund_id = row.get('fund_id', '').strip()

        # entity_id is REQUIRED
        if not entity_id:
            row_errors.append('entity_id is required')
        else:
            all_entity_ids.add(entity_id)

        # fund_id is OPTIONAL - only validate if provided
        if fund_id:
            all_fund_ids.add(fund_id)

        # Store fund_id (may be empty string)
        valid_records.append({
            'pledge_id': pledge_id,
            'entity_id': entity_id,
            'fund_id': fund_id,  # Empty string allowed
            # ...
        })

    # Second pass: validate only non-empty fund_ids
    if all_fund_ids:  # Only check if any fund_ids provided
        existing_fund_ids = set(
            Fund.objects.filter(
                external_id__in=all_fund_ids
            ).values_list('external_id', flat=True)
        )

        missing_fund_ids = all_fund_ids - existing_fund_ids
        if missing_fund_ids:
            # Add FK errors for rows with invalid fund_ids
            for row_num, record in pending_records:
                if record['fund_id'] and record['fund_id'] in missing_fund_ids:
                    row_fk_errors.append(f"fund_id '{record['fund_id']}' not found in Funds")
```

### Pattern 3: Pledge Import Without Contact Stats Update

**What:** Import pledges and update ImportRun, but skip denormalized stat updates because Contact pledge properties are computed on-the-fly.

**When to use:** When related model uses properties instead of denormalized fields (Pledge vs Donation pattern).

**Example:**
```python
# Source: Phase 10 import_transactions + Contact model analysis
def import_pledges(records: List[dict], user, import_run) -> Tuple[int, int]:
    """
    Import pledges from parsed records.

    Note: NO Contact stats update needed. Contact.has_active_pledge and
    Contact.monthly_pledge_amount are computed properties that query
    pledges.filter(status='active') directly.
    """
    # Pre-fetch Contact and Fund objects
    contacts_by_external_id = {
        c.external_id: c
        for c in Contact.objects.filter(
            owner=user,
            external_id__in=entity_ids
        )
    }

    # Only fetch funds if any fund_ids provided
    funds_by_external_id = {}
    if fund_ids:  # List may contain empty strings
        actual_fund_ids = [f for f in fund_ids if f]
        if actual_fund_ids:
            funds_by_external_id = {
                f.external_id: f
                for f in Fund.objects.filter(external_id__in=actual_fund_ids)
            }

    # Upsert pledges
    for record in records:
        fund = None
        if record['fund_id']:  # Only lookup if fund_id provided
            fund = funds_by_external_id.get(record['fund_id'])

        pledge, created = Pledge.objects.update_or_create(
            external_id=record['pledge_id'],
            defaults={
                'contact': contacts_by_external_id[record['entity_id']],
                'fund': fund,  # May be None
                'amount': record['amount'],
                'frequency': record['cadence'],  # CSV 'cadence' -> model 'frequency'
                'status': record['status'],
                'start_date': record['start_date']
            }
        )
        # created/updated count tracking

    # Update import run and return
    # NO update_contact_stats_for_import call needed
    return created_count, updated_count
```

### Pattern 4: CSV Column to Model Field Mapping

**What:** Map SPO CSV terminology to DonorCRM model fields (cadence -> frequency, entity_id -> contact).

**When to use:** When external system uses different terminology than internal model.

**Example:**
```python
# CSV columns: pledge_id, entity_id, fund_id, amount, cadence, status, start_date
# Model fields: external_id, contact, fund, amount, frequency, status, start_date

valid_records.append({
    'pledge_id': pledge_id,      # -> Pledge.external_id
    'entity_id': entity_id,      # -> Pledge.contact (FK lookup)
    'fund_id': fund_id,          # -> Pledge.fund (FK lookup, optional)
    'amount': amount,            # -> Pledge.amount
    'cadence': cadence,          # -> Pledge.frequency (terminology mapping)
    'status': status,            # -> Pledge.status
    'start_date': start_date     # -> Pledge.start_date
})

# During import:
Pledge.objects.update_or_create(
    external_id=record['pledge_id'],
    defaults={
        'frequency': record['cadence'],  # Key mapping here
        # ...
    }
)
```

### Anti-Patterns to Avoid

- **Don't use global Contact lookup for entity_id:** Contact.external_id is owner-scoped. Always filter by owner=user (same as Phase 10).
- **Don't require fund_id:** IMP-08 explicitly allows optional fund_id. Validate only if provided.
- **Don't update Contact denormalized stats:** Pledge data is accessed via computed properties, not denormalized fields. No stats update needed.
- **Don't forget cadence -> frequency mapping:** CSV uses "cadence", model uses "frequency". Map during import.
- **Don't skip enum validation:** Invalid cadence/status must be rejected with clear error messages before import.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing with encoding handling | Custom file reader | csv.DictReader + decode('utf-8-sig') | Handles Excel BOM automatically. Pattern proven in Phases 8-10. |
| Amount validation | Custom decimal parsing | Existing _parse_amount() helper | Handles currency symbols, negatives, max values. Already tested. |
| Date parsing | Custom date parser | Existing _parse_date() helper | Tries multiple formats. Already handles common formats from SPO exports. |
| FK validation errors | Catching database exceptions | Pre-validation with set operations | Provides row numbers, better error messages. Strict mode requirement. |
| Duplicate detection | Manual tracking | Set-based deduplication | O(1) lookup, memory efficient, pattern established in Phases 8-10. |
| Enum validation | String comparison loops | List comprehension with .value | Follows Phase 8 Fund status pattern exactly. |

**Key insight:** Phase 10 Transactions provides the exact template needed. The only new code is enum validation (reuse Phase 8 pattern) and optional fund_id handling (simple conditional). Everything else is copy-paste with model substitution.

## Common Pitfalls

### Pitfall 1: Pledge.external_id Global Uniqueness vs Contact Owner-Scoping

**What goes wrong:** Treating Pledge.external_id as owner-scoped like Contact.external_id, causing conflicts when different users import same pledge_id.

**Why it happens:** Contact.external_id is owner-scoped (Phase 7 decision 07-02-D1), but Pledge.external_id is globally unique (Phase 7 decision 07-02-D2). SPO pledge_ids are unique across entire organization.

**How to avoid:**
- Pledge.external_id unique constraint is GLOBAL, not per-owner
- No need to filter by owner when checking for existing pledge_id
- Single pledge can only belong to one contact (and thus one owner)
- Pre-validation only needs owner-scoping for entity_id lookup, not pledge_id

**Warning signs:**
- Test with two users importing same pledge_id - should error on second user
- Pledge.objects.filter(owner=user, external_id=pledge_id) - WRONG, Pledge has no owner field
- Upsert matching only on external_id (no owner filter needed)

### Pitfall 2: Treating fund_id as Required Field

**What goes wrong:** Rejecting rows with missing fund_id, even though IMP-08 specifies fund_id is optional.

**Why it happens:** Phase 10 Transactions require both entity_id and fund_id. Copy-pasting validation without reading IMP-08 requirement.

**How to avoid:**
- Check `if not fund_id:` → NO error for pledges (fund is nullable)
- Only add fund_id to all_fund_ids set if fund_id is non-empty
- Only validate fund_ids if all_fund_ids has elements
- Set fund=None in upsert if record['fund_id'] is empty

**Warning signs:**
- Error: "fund_id is required" in pledge import tests
- Valid pledge CSV rejected because fund_id column missing or empty
- Import succeeds but all pledges have fund=None even when fund_id provided

### Pitfall 3: Forgetting cadence -> frequency Field Mapping

**What goes wrong:** Using `frequency` as CSV column name or storing `cadence` to wrong model field, causing validation errors or data corruption.

**Why it happens:** SPO exports use "cadence" terminology, DonorCRM Pledge model uses "frequency". Inconsistent naming between systems.

**How to avoid:**
- CSV template: `pledge_id,entity_id,fund_id,amount,cadence,status,start_date`
- Parse as: `cadence = row.get('cadence', '').strip().lower()`
- Store in dict as: `'cadence': cadence` (keep CSV terminology in validated records)
- Map during import: `'frequency': record['cadence']` (translate to model field)

**Warning signs:**
- Missing required column: 'frequency' error (CSV should have 'cadence')
- Pledge created with frequency=None even when CSV has cadence column
- Tests pass but imported pledges have wrong frequency values

### Pitfall 4: Attempting to Update Contact Stats After Pledge Import

**What goes wrong:** Calling update_contact_stats_for_pledges() or similar function, wasting queries on non-existent denormalized fields.

**Why it happens:** Phase 10 requires Contact stats update after donation import. Copy-pasting pattern without understanding Contact model.

**How to avoid:**
- Check Contact model: NO denormalized pledge fields exist
- Contact.has_active_pledge is a @property (queries pledges.filter(status='active').exists())
- Contact.monthly_pledge_amount is a @property (queries pledges.filter(status='active'))
- Properties are computed on-read, no write updates needed

**Warning signs:**
- import_pledges calls update_contact_stats_for_import
- Tests for pledge import include stats update assertions
- Extra database queries during pledge import for Contact updates

### Pitfall 5: PledgeFrequency.SEMI_ANNUAL vs CSV "semi_annual" Format

**What goes wrong:** Validating against 'semi-annual' (hyphenated) when model uses 'semi_annual' (underscored).

**Why it happens:** Human-readable displays use hyphens, database values use underscores per Django convention.

**How to avoid:**
- Check PledgeFrequency enum values: `SEMI_ANNUAL = 'semi_annual', 'Semi-Annual'`
- Database value is 'semi_annual' (underscore)
- Display value is 'Semi-Annual' (hyphen, capitalized)
- CSV should accept 'semi_annual' (database format)
- Validation: `cadence in ['monthly', 'quarterly', 'semi_annual', 'annual']`

**Warning signs:**
- Valid CSV with "semi-annual" rejected as invalid cadence
- Documentation says "semi-annual" but code checks for "semi_annual"
- Inconsistent hyphen/underscore usage in validation messages

## Code Examples

Verified patterns from official sources and existing codebase:

### Enum Values Extraction for Validation
```python
# Source: apps/pledges/models.py + Phase 8 VALID_FUND_STATUSES pattern
from apps.pledges.models import PledgeFrequency, PledgeStatus

# Extract database values for validation
VALID_PLEDGE_FREQUENCIES = [f.value for f in PledgeFrequency]
# Result: ['monthly', 'quarterly', 'semi_annual', 'annual']

VALID_PLEDGE_STATUSES = [s.value for s in PledgeStatus]
# Result: ['active', 'paused', 'completed', 'cancelled']

# Case-insensitive validation (Phase 8 pattern)
cadence = row.get('cadence', '').strip().lower()
if cadence not in VALID_PLEDGE_FREQUENCIES:
    row_errors.append(
        f'Invalid cadence: "{cadence}". '
        f'Valid options: {", ".join(VALID_PLEDGE_FREQUENCIES)}'
    )
```

### Optional FK Handling in Validation
```python
# Source: IMP-08 requirement + Phase 10 FK validation pattern
# Collect fund_ids ONLY if provided
all_fund_ids = set()
for row_num, row in enumerate(reader, start=2):
    fund_id = row.get('fund_id', '').strip()

    # fund_id is OPTIONAL - only collect if non-empty
    if fund_id:
        all_fund_ids.add(fund_id)

# Validate only if any fund_ids were provided
if all_fund_ids:
    existing_fund_ids = set(
        Fund.objects.filter(
            external_id__in=all_fund_ids
        ).values_list('external_id', flat=True)
    )

    missing_fund_ids = all_fund_ids - existing_fund_ids

    if missing_fund_ids:
        # Only report missing fund_id for rows that provided one
        for row_num, record in pending_records:
            if record['fund_id'] and record['fund_id'] in missing_fund_ids:
                row_fk_errors.append(f"fund_id '{record['fund_id']}' not found in Funds")
```

### Optional FK Resolution in Import
```python
# Source: Phase 10 import_transactions + IMP-08 requirement
def import_pledges(records: List[dict], user, import_run) -> Tuple[int, int]:
    # Collect entity_ids (always required)
    entity_ids = [r['entity_id'] for r in records]

    # Collect fund_ids (filter out empty strings)
    fund_ids = [r['fund_id'] for r in records if r['fund_id']]

    # Fetch Contacts (always needed)
    contacts_by_external_id = {
        c.external_id: c
        for c in Contact.objects.filter(
            owner=user,
            external_id__in=entity_ids
        )
    }

    # Fetch Funds only if any fund_ids provided
    funds_by_external_id = {}
    if fund_ids:
        funds_by_external_id = {
            f.external_id: f
            for f in Fund.objects.filter(external_id__in=fund_ids)
        }

    # Upsert with conditional fund lookup
    for record in records:
        fund = None
        if record['fund_id']:
            fund = funds_by_external_id.get(record['fund_id'])

        pledge, created = Pledge.objects.update_or_create(
            external_id=record['pledge_id'],
            defaults={
                'contact': contacts_by_external_id[record['entity_id']],
                'fund': fund,  # None if no fund_id provided
                'amount': record['amount'],
                'frequency': record['cadence'],  # CSV column -> model field mapping
                'status': record['status'],
                'start_date': record['start_date']
            }
        )
```

### PledgeImportView API Endpoint Pattern
```python
# Source: Phase 10 TransactionImportView pattern
class PledgeImportView(APIView):
    """
    POST: Import pledges from CSV file (admin only)

    Query params:
        validate_only: If 'true', only validate without importing
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        # File validation (Phase 8/9/10 pattern)
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided.'}, status=400)

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response({'detail': 'File must be a CSV.'}, status=400)

        # UTF-8-sig handles Excel BOM (Phase 8/9/10 pattern)
        try:
            content = file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            return Response({'detail': 'File encoding error. Please use UTF-8.'}, status=400)

        # Parse CSV
        valid_records, errors = parse_pledges_csv(content, request.user)

        # Validate-only mode (dry run)
        if request.query_params.get('validate_only') == 'true':
            return Response({
                'valid_count': len(valid_records),
                'error_count': len(errors),
                'errors': errors[:20]
            })

        # Create ImportRun audit record (Phase 8/9/10 pattern)
        import_run = ImportRun.objects.create(
            type=ImportType.PLEDGES,
            status=ImportStatus.IMPORTING,
            filename=file.name,
            uploaded_by=request.user
        )

        # Synchronous import (MVP - no Celery)
        if valid_records:
            created_count, updated_count = import_pledges(
                valid_records, request.user, import_run
            )
            # NO update_contact_stats_for_import call (pledges use computed properties)
        else:
            created_count = 0
            updated_count = 0

        return Response({
            'created_count': created_count,
            'updated_count': updated_count,
            'error_count': len(errors),
            'errors': errors[:20],
            'import_run_id': import_run.id
        })
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Denormalized pledge stats on Contact | Computed properties (has_active_pledge, monthly_pledge_amount) | Existing pattern | No stats update needed after pledge import, simpler code |
| Individual save() calls | update_or_create for conditional unique constraint | Django 4.1+ (Phases 9-10 pattern) | Handles Pledge.external_id global unique constraint correctly |
| Hard-coded enum values | Extract from Django TextChoices | Best practice 2023+ | Single source of truth, DRY principle |
| Required all FKs | Optional FK validation | IMP-08 requirement | Handles nullable fund field correctly |
| Catching IntegrityError for validation | Pre-validation with set operations | Best practice 2023+ (Phase 10 pattern) | Better error messages with row numbers, strict mode support |

**Deprecated/outdated:**
- **get_or_create() in loops for upsert:** Replaced by update_or_create pattern (Phases 9-10). More explicit for conditional unique constraints.
- **Hyphenated enum values:** Django TextChoices convention uses underscores ('semi_annual' not 'semi-annual'). Display layer adds hyphens.
- **Manual Contact stats recalculation after pledge changes:** Contact model uses @property decorators for pledge-related stats. Computed on-read, not denormalized.

## Open Questions

Things that couldn't be fully resolved:

1. **Should pledges auto-calculate next_expected_date on import?**
   - What we know: Pledge.save() calls calculate_next_expected_date() for new active pledges (line 223-224)
   - What's unclear: Should imported pledges trigger this, or assume CSV includes all fields?
   - Recommendation: Let Pledge.save() auto-calculate next_expected_date. Don't override in import. This ensures consistency with manual pledge creation. Test that imported active pledges have next_expected_date set correctly.

2. **Should we validate start_date is not in future?**
   - What we know: Phase 10 validates posted_date is not in future (line 239 services.py)
   - What's unclear: Does same rule apply to pledge start_date? SPO may have future-dated pledges.
   - Recommendation: DON'T validate start_date against future. Pledges can legitimately start in future. Document difference from donation date validation in tests.

3. **What about Pledge.end_date field?**
   - What we know: Pledge model has optional end_date field (line 89 models.py)
   - What's unclear: IMP-08 doesn't mention end_date in CSV columns. Should we support it?
   - Recommendation: CSV doesn't include end_date (IMP-08 spec). Import as None (blank). Admins can set manually after import if needed. Keep CSV minimal for MVP.

4. **Should CSV include notes field?**
   - What we know: Pledge model has notes field (line 114 models.py). Transaction CSV doesn't include notes.
   - What's unclear: Is notes valuable for pledge imports from SPO?
   - Recommendation: Skip notes field for MVP (not in IMP-08 spec). Can add in v1.2 if users request it. Keeps CSV aligned with requirement.

## Sources

### Primary (HIGH confidence)
- Existing codebase: apps/pledges/models.py (Pledge model, PledgeFrequency, PledgeStatus enums, lines 1-226)
- Existing codebase: apps/contacts/models.py (Contact properties: has_active_pledge, monthly_pledge_amount, lines 139-150)
- Existing codebase: apps/imports/services.py (parse_transactions_csv, import_transactions, Phases 8-10 patterns)
- .planning/REQUIREMENTS.md (IMP-08 specification, lines 57-62)
- .planning/STATE.md (Phase 7 decisions 07-02-D2: Pledge.external_id globally unique, lines 53)
- .planning/phases/10-transactions-csv-import/10-RESEARCH.md (FK validation patterns, denormalized stats pattern)

### Secondary (MEDIUM confidence)
- Django TextChoices documentation - https://docs.djangoproject.com/en/5.0/ref/models/fields/#enumeration-types
- Django Conditional Unique Constraints - https://docs.djangoproject.com/en/5.0/ref/models/constraints/#uniqueconstraint

### Tertiary (LOW confidence)
- None - all findings verified with existing codebase and official Django documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Identical to Phase 10, proven patterns
- Architecture: HIGH - Direct reuse of Phase 8-10 patterns with minor modifications (enum validation, optional FK)
- Pitfalls: HIGH - All critical differences documented (global unique external_id, optional fund_id, no stats update, cadence mapping)

**Research date:** 2026-02-02
**Valid until:** 30 days (stable Django patterns, existing codebase patterns)

---

## Summary of Key Differences from Phase 10 (Transactions)

| Aspect | Phase 10 Transactions | Phase 11 Pledges |
|--------|----------------------|------------------|
| **FK Scoping** | Contact: owner-scoped, Fund: global | Contact: owner-scoped, Fund: global (SAME) |
| **External ID Scoping** | Donation.external_id: global unique | Pledge.external_id: global unique (SAME) |
| **fund_id Required?** | YES (strict validation) | NO (optional per IMP-08) |
| **Enum Validation** | None (donation_type has defaults) | Required (cadence and status must validate) |
| **CSV -> Model Mapping** | Direct field names | cadence (CSV) -> frequency (model) |
| **Contact Stats Update** | YES (update_contact_stats_for_import) | NO (computed properties only) |
| **Additional Fields** | posted_date | start_date (end_date not in CSV) |
| **Auto-calculation** | None | next_expected_date calculated on save() |

**Bottom line:** Phase 11 is 90% identical to Phase 10. The 10% difference is: enum validation (reuse Phase 8 pattern), optional fund_id (conditional validation), cadence->frequency mapping, and no Contact stats update.
