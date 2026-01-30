# Architecture Research: CSV Import Pipeline Integration

**Domain:** CSV data import for Django/React CRM
**Researched:** 2026-01-30
**Confidence:** HIGH

## Executive Summary

CSV import pipelines in Django/React applications follow a multi-stage architecture: **Upload → Validate → Preview → Import → Audit**. For DonorCRM's SPO-compatible import, the architecture must integrate with existing owner-scoped data models, preserve referential integrity across 4 CSV types (Funds → Entities → Transactions → Pledges), and provide idempotent upserts via external IDs.

The existing DonorCRM codebase already has foundational import infrastructure (apps/imports with synchronous contact/donation import). The v1.1 milestone extends this with:
1. **New models** (Fund, ImportRun, ImportRowError)
2. **External ID fields** on Contact, Donation, Pledge for idempotency
3. **Multi-file workflow** with dependency ordering
4. **Enhanced validation** with row-level error tracking

**Key architectural decision:** Keep synchronous imports for MVP (Celery infrastructure exists but disabled in production). Django's atomic transactions provide rollback guarantees, and row-level error collection enables user-friendly validation reports.

## Existing Architecture Analysis

### Current Django Backend Structure

```
apps/
├── core/
│   ├── models.py              # TimeStampedModel base (UUID PK, timestamps)
│   ├── permissions.py         # IsAdmin, IsFinanceOrAdmin, IsContactOwnerOrReadAccess
│   └── pagination.py          # StandardPagination
├── imports/                   # ✅ EXISTING import infrastructure
│   ├── services.py            # parse_contacts_csv, parse_donations_csv, import_contacts
│   ├── views.py               # ContactImportView, DonationImportView (sync + async modes)
│   ├── tasks.py               # Celery tasks (import_contacts_async, import_donations_async)
│   └── urls.py                # /api/v1/imports/contacts/, /api/v1/imports/donations/
├── contacts/
│   └── models.py              # Contact (owner-scoped, giving stats, no external_id yet)
├── donations/
│   └── models.py              # Donation (has external_id, import_batch, imported_at)
├── pledges/
│   └── models.py              # Pledge (no external_id yet)
└── users/
    └── models.py              # User (email-based, role: staff/admin/finance)
```

### Current Frontend Structure

```
frontend/src/
├── pages/
│   └── imports/
│       └── ImportExport.tsx   # ✅ EXISTING import UI (tabs: Import/Export)
├── components/
│   └── imports/
│       ├── ImportCard.tsx     # File upload + validation UI
│       └── ExportCard.tsx     # Download CSV UI
└── hooks/
    └── useImports.ts          # React Query mutations for import/export
```

### Current Import Flow (Contacts/Donations)

```
User uploads CSV → ImportCard component
    ↓
POST /api/v1/imports/contacts/ with FormData
    ↓ (validate_only=true for preview)
ContactImportView.post()
    ↓
parse_contacts_csv(content, user)
    → Returns (valid_records, errors)
    → Validates: required fields, email format, duplicates, field lengths
    → Checks uniqueness: Contact.objects.filter(owner=user, email=email).exists()
    ↓ (if validate_only=false)
import_contacts(valid_records, user)
    → Creates Contact instances via Contact.objects.create()
    → Returns (count, created_contacts)
    ↓
Response: {imported_count, error_count, errors[:20]}
```

**Key observation:** Existing imports app already implements the **Upload → Validate → Import** pattern. Missing pieces for v1.1:
- Preview step (currently validate_only=true returns errors but no preview grid)
- Idempotent upserts (currently always creates new records)
- ImportRun audit model (currently uses import_batch string on Donation)
- Row-level error persistence (currently returns errors in API response only)

## Standard Django CSV Import Architecture

### Multi-Stage Import Pipeline

Based on research of [django-csvimport](https://github.com/edcrewe/django-csvimport), [django-csv-admin](https://github.com/huddlej/django-csv-admin), and [django-import-export](https://django-import-export.readthedocs.io/en/latest/advanced_usage.html), the standard architecture has 5 stages:

```
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 1: Upload & Parse                                          │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────┐        ┌──────────┐        ┌──────────┐            │
│  │ User    │ ──────>│ Frontend │ ──────>│ API      │            │
│  │ Browser │  CSV   │ Upload   │  POST  │ Endpoint │            │
│  └─────────┘        └──────────┘        └──────────┘            │
│                                              │                   │
│                                              ↓                   │
│                                         Parse CSV                │
│                                         (csv.DictReader)         │
├──────────────────────────────────────────────────────────────────┤
│ STAGE 2: Row-Level Validation                                    │
├──────────────────────────────────────────────────────────────────┤
│  For each row:                                                    │
│    - Type validation (amount → Decimal, date → Date)             │
│    - Business rules (amount > 0, date not in future)             │
│    - Foreign key existence (contact_email → Contact.id)          │
│    - Uniqueness (external_id not already used)                   │
│                                                                   │
│  Returns: (valid_records[], invalid_rows[])                      │
│                                                                   │
│  invalid_rows = [{row: 2, errors: ["No contact..."], data: {}}]  │
├──────────────────────────────────────────────────────────────────┤
│ STAGE 3: Preview (Optional)                                      │
├──────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐      │
│  │ Frontend displays:                                      │      │
│  │ - Valid rows count                                      │      │
│  │ - Sample valid records (first 10)                       │      │
│  │ - Error rows with messages                              │      │
│  │ - "Confirm Import" button (if valid_rows > 0)           │      │
│  └────────────────────────────────────────────────────────┘      │
├──────────────────────────────────────────────────────────────────┤
│ STAGE 4: Atomic Import                                           │
├──────────────────────────────────────────────────────────────────┤
│  with transaction.atomic():                                       │
│    import_run = ImportRun.objects.create(...)                    │
│    for record in valid_records:                                  │
│      Model.objects.update_or_create(                             │
│        defaults={...record},                                     │
│        external_id=record['external_id']  # Idempotent           │
│      )                                                            │
│    import_run.status = 'completed'                               │
│    import_run.save()                                             │
├──────────────────────────────────────────────────────────────────┤
│ STAGE 5: Audit Trail                                             │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ ImportRun                                                 │    │
│  │ - type: "funds"                                           │    │
│  │ - status: "completed"                                     │    │
│  │ - total_rows: 150                                         │    │
│  │ - created_count: 45, updated_count: 103, skipped: 2       │    │
│  │ - uploaded_by: User                                       │    │
│  └──────────────────────────────────────────────────────────┘    │
│                         │                                         │
│                         ↓                                         │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ ImportRowError (for each failed row)                      │    │
│  │ - import_run: FK → ImportRun                              │    │
│  │ - row_number: 23                                          │    │
│  │ - error_messages: ["Amount is required"]                  │    │
│  │ - row_data: {"contact_email": "...", "amount": ""}        │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | DonorCRM Implementation |
|-----------|----------------|-------------------------|
| **Parser Service** | Read CSV, convert to dict records | `services.py`: `parse_{type}_csv()` — uses csv.DictReader |
| **Validator** | Row-level validation, collect errors | `services.py`: `_parse_amount()`, `_parse_date()`, FK lookups |
| **Importer Service** | Atomic database writes, update stats | `services.py`: `import_{type}()` — uses Model.objects.create() |
| **API View** | Handle upload, orchestrate stages | `views.py`: `{Type}ImportView` — MultiPartParser, validate_only param |
| **ImportRun Model** | Audit trail, batch metadata | **NEW** — tracks type, status, counts, user |
| **ImportRowError Model** | Row-level error persistence | **NEW** — FK to ImportRun, stores row_number + errors + data |
| **External ID Fields** | Idempotency via unique constraint | **NEW** on Contact/Pledge — existing on Donation |
| **Frontend Upload** | File selection, preview, confirm | `ImportCard.tsx` — drag-drop, validation, error display |

## Integration with Existing DonorCRM Architecture

### New Models Required

```python
# apps/imports/models.py (NEW FILE)

class ImportType(models.TextChoices):
    FUNDS = 'funds', 'Funds'
    ENTITIES = 'entities', 'Entities'
    TRANSACTIONS = 'transactions', 'Transactions'
    PLEDGES = 'pledges', 'Pledges'

class ImportStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    VALIDATING = 'validating', 'Validating'
    VALIDATED = 'validated', 'Validated'
    IMPORTING = 'importing', 'Importing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'

class ImportRun(TimeStampedModel):
    """Audit trail for each CSV import operation."""
    type = models.CharField(max_length=20, choices=ImportType.choices, db_index=True)
    status = models.CharField(max_length=20, choices=ImportStatus.choices, default=ImportStatus.PENDING)

    # File metadata
    filename = models.CharField(max_length=255)
    total_rows = models.IntegerField(default=0)

    # Results
    created_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)

    # User tracking
    uploaded_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='import_runs')

    # Error summary (JSON field for quick access)
    error_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uploaded_by', '-created_at']),
            models.Index(fields=['type', 'status']),
        ]

class ImportRowError(TimeStampedModel):
    """Individual row errors for failed import rows."""
    import_run = models.ForeignKey(ImportRun, on_delete=models.CASCADE, related_name='row_errors')
    row_number = models.IntegerField()
    error_messages = models.JSONField()  # List of error strings
    row_data = models.JSONField()        # Original CSV row as dict

    class Meta:
        ordering = ['row_number']
        indexes = [
            models.Index(fields=['import_run', 'row_number']),
        ]

class Fund(TimeStampedModel):
    """Represents a fund/account/campaign from SPO."""
    external_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default='active')  # active, inactive, closed

    # Optional: owner-scoped for multi-org
    owner = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['external_id'],
                name='unique_fund_external_id'
            )
        ]
```

### Modified Models (Add External ID Fields)

```python
# apps/contacts/models.py
class Contact(TimeStampedModel):
    # ... existing fields ...

    # NEW: External ID for idempotent imports
    external_id = models.CharField(
        'external ID',
        max_length=100,
        blank=True,
        db_index=True,
        help_text='Entity ID from external system (e.g., SPO)'
    )

    class Meta:
        # ... existing meta ...
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'email'],
                name='unique_contact_email_per_owner',
                condition=~models.Q(email='')
            ),
            # NEW: Unique external_id per owner
            models.UniqueConstraint(
                fields=['owner', 'external_id'],
                name='unique_contact_external_id_per_owner',
                condition=~models.Q(external_id='')
            )
        ]

# apps/pledges/models.py
class Pledge(TimeStampedModel):
    # ... existing fields ...

    # NEW: External ID for idempotent imports
    external_id = models.CharField(
        'external ID',
        max_length=100,
        blank=True,
        db_index=True,
        help_text='Pledge ID from external system'
    )

    # NEW: Fund FK
    fund = models.ForeignKey(
        'imports.Fund',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pledges'
    )

    class Meta:
        # ... existing meta ...
        constraints = [
            # NEW: Unique external_id globally
            models.UniqueConstraint(
                fields=['external_id'],
                name='unique_pledge_external_id',
                condition=~models.Q(external_id='')
            )
        ]

# apps/donations/models.py — ALREADY HAS external_id with unique constraint ✅
# ADD Fund FK:
class Donation(TimeStampedModel):
    # ... existing fields ...

    # NEW: Fund FK
    fund = models.ForeignKey(
        'imports.Fund',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donations'
    )
```

### Data Flow: SPO CSV Import Workflow

```
User navigates to Import Center → 4 tiles (Funds, Entities, Transactions, Pledges)
    ↓
STEP 1: Upload Funds CSV
    ↓
POST /api/v1/imports/funds/?validate_only=true
    → parse_funds_csv() validates columns, checks duplicates
    → Returns: {valid_count: 45, errors: [...]}
    ↓ (Frontend displays preview)
User clicks "Confirm Import"
    ↓
POST /api/v1/imports/funds/
    → import_run = ImportRun.objects.create(type='funds', status='importing', ...)
    → with transaction.atomic():
        for record in valid_records:
          Fund.objects.update_or_create(
            defaults={'name': record['name'], 'status': record['status']},
            external_id=record['fund_id']
          )
    → import_run.status = 'completed'
    → Returns: {import_run_id, created_count, updated_count, errors: [...]}
    ↓
STEP 2: Upload Entities CSV
    ↓
POST /api/v1/imports/entities/?validate_only=true
    → parse_entities_csv() validates + checks if entity_id exists as Contact.external_id
    → For each row: Contact.objects.update_or_create(
        defaults={...parsed_contact_data},
        owner=user,
        external_id=record['entity_id']
      )
    ↓
STEP 3: Upload Transactions CSV
    → Validates: fund_id exists in Fund, entity_id exists in Contact
    → Donation.objects.update_or_create(
        defaults={'contact': contact, 'fund': fund, 'amount': ...},
        external_id=record['transaction_id']
      )
    ↓
STEP 4: Upload Pledges CSV
    → Validates: entity_id exists in Contact, fund_id exists in Fund
    → Pledge.objects.update_or_create(
        defaults={'contact': contact, 'fund': fund, 'amount': ...},
        external_id=record['pledge_id']
      )
```

**Dependency ordering enforced by:**
1. Frontend displays 4 tiles in order (Funds → Entities → Transactions → Pledges)
2. Validation checks foreign key existence (entity_id must exist before transaction import)
3. User receives error messages if trying to import transactions before entities

## Architectural Patterns

### Pattern 1: Idempotent Upsert via External ID

**What:** Use Django's `update_or_create()` with external_id to enable re-importing the same CSV without duplicates.

**When to use:** All import operations where external system provides stable IDs.

**Trade-offs:**
- ✅ Allows users to fix errors and re-upload
- ✅ Supports incremental imports (new rows update, existing rows don't duplicate)
- ❌ Requires unique constraint on external_id (may conflict with manual data entry)

**Example:**
```python
# apps/imports/services.py
def import_funds(records: List[dict], import_run: ImportRun):
    created_count = 0
    updated_count = 0

    for record in records:
        fund, created = Fund.objects.update_or_create(
            external_id=record['fund_id'],
            defaults={
                'name': record['name'],
                'status': record['status'],
            }
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    import_run.created_count = created_count
    import_run.updated_count = updated_count
    import_run.save()

    return created_count, updated_count
```

### Pattern 2: Atomic Import with Validation-First

**What:** Separate validation pass from import pass. Validate ALL rows first, only import if ALL rows valid.

**When to use:** When referential integrity matters (e.g., transactions must reference valid entities).

**Trade-offs:**
- ✅ User-friendly: see all errors at once, not one-at-a-time
- ✅ Database stays consistent (no partial imports)
- ❌ Requires two passes over data (validation then import)
- ❌ Higher memory usage (store valid_records in memory)

**Example:**
```python
# apps/imports/views.py
class TransactionImportView(APIView):
    def post(self, request):
        content = request.FILES['file'].read().decode('utf-8')

        # PASS 1: Validate all rows
        valid_records, errors = parse_transactions_csv(content, request.user)

        if request.query_params.get('validate_only') == 'true':
            return Response({
                'valid_count': len(valid_records),
                'error_count': len(errors),
                'errors': errors
            })

        # PASS 2: Import only if validation passed
        if errors:
            return Response(
                {'detail': 'Validation errors found', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            import_run = ImportRun.objects.create(
                type='transactions',
                status='importing',
                filename=request.FILES['file'].name,
                total_rows=len(valid_records),
                uploaded_by=request.user
            )

            created, updated = import_transactions(valid_records, import_run)

            import_run.status = 'completed'
            import_run.save()

        return Response({
            'import_run_id': str(import_run.id),
            'created_count': created,
            'updated_count': updated
        })
```

### Pattern 3: Row-Level Error Collection

**What:** Continue validation through all rows, collecting errors per row, rather than raising exception on first error.

**When to use:** User-facing imports where fixing all errors at once is valuable.

**Trade-offs:**
- ✅ Better UX: user sees all problems in one pass
- ✅ Enables "Download Errors CSV" feature
- ❌ More complex validation code (must handle exceptions gracefully)

**Example:**
```python
# apps/imports/services.py
def parse_entities_csv(content: str, user) -> Tuple[List[dict], List[dict]]:
    reader = csv.DictReader(io.StringIO(content))
    valid_records = []
    errors = []

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Validate each field, collecting errors
        entity_id = row.get('entity_id', '').strip()
        if not entity_id:
            row_errors.append('entity_id is required')
        elif len(entity_id) > 100:
            row_errors.append('entity_id exceeds max length')

        amount, amount_error = _parse_amount(row.get('amount', ''))
        if amount_error:
            row_errors.append(amount_error)

        # Don't stop on first error — continue checking all fields

        if row_errors:
            errors.append({
                'row': row_num,
                'errors': row_errors,
                'data': dict(row)
            })
        else:
            valid_records.append({
                'entity_id': entity_id,
                'amount': amount,
                # ... other validated fields
            })

    return valid_records, errors
```

### Pattern 4: Synchronous Import for MVP (Async Optional)

**What:** Process CSV imports synchronously in the API request for files < 1000 rows. Optionally queue large files to Celery.

**When to use:**
- Synchronous: MVP, admin-only imports, < 1000 rows
- Async: Large files (> 1000 rows), user-facing imports, long-running validations

**Trade-offs:**
- ✅ Sync: Simpler code, immediate feedback, easier error handling
- ✅ Async: Handles large files, doesn't block web workers, better scalability
- ❌ Sync: Request timeout risk (> 30s for large files)
- ❌ Async: Complex polling UI, delayed feedback, requires Celery infrastructure

**Recommendation for DonorCRM v1.1 MVP:** Start with synchronous imports only. Celery infrastructure exists but is disabled in production. Add async support post-MVP if admins report timeouts with large files.

## Build Order Recommendation

Based on dependency analysis and integration complexity:

### Phase 1: Foundation (Models + Database)
1. Create `imports/models.py` with ImportRun, ImportRowError, Fund
2. Add external_id to Contact model with unique constraint
3. Add external_id to Pledge model with unique constraint
4. Add fund FK to Donation and Pledge models
5. Run migrations, verify schema changes

**Why first:** All subsequent work depends on these models existing.

### Phase 2: Fund Import (Simplest CSV)
1. Create `parse_funds_csv()` in services.py
2. Create `import_funds()` in services.py
3. Create `FundImportView` in views.py
4. Create `FundSerializer` in serializers.py
5. Add `/api/v1/imports/funds/` endpoint
6. Test with sample funds.csv

**Why second:** Funds have no dependencies, simplest validation logic. Proves out the upload → validate → import flow.

### Phase 3: Entity Import (Contact Upsert)
1. Create `parse_entities_csv()` in services.py
2. Modify existing `import_contacts()` to use update_or_create with external_id
3. Create `EntityImportView` in views.py
4. Add `/api/v1/imports/entities/` endpoint
5. Test entity import creates/updates Contact records

**Why third:** Entities must exist before transactions/pledges can reference them.

### Phase 4: Transaction Import (Donation with FK)
1. Create `parse_transactions_csv()` in services.py
2. Add validation for entity_id existence (Contact lookup)
3. Add validation for fund_id existence (Fund lookup)
4. Create `TransactionImportView` in views.py
5. Modify `import_donations()` to support fund FK
6. Test transaction import with entity/fund references

**Why fourth:** Requires Funds and Entities to exist first.

### Phase 5: Pledge Import (Similar to Transaction)
1. Create `parse_pledges_csv()` in services.py
2. Add validation for entity_id and fund_id
3. Create `PledgeImportView` in views.py
4. Modify `import_pledges()` to use update_or_create with external_id
5. Test pledge import

**Why fifth:** Similar to transactions, depends on entities and funds.

### Phase 6: Frontend Import Center
1. Create `ImportCenter.tsx` with 4 tiles
2. Modify `ImportCard.tsx` to support preview mode
3. Create `ImportPreview.tsx` component (validation results grid)
4. Create `ImportResults.tsx` component (import summary)
5. Add React Query hooks for fund/entity/transaction/pledge imports
6. Wire up upload → preview → confirm flow

**Why last:** Backend must be working before frontend can be built.

## Anti-Patterns

### Anti-Pattern 1: Partial Import on Error

**What people do:** Import valid rows even if some rows have errors, leaving database in partial state.

**Why it's wrong:**
- User thinks import succeeded but data is incomplete
- Hard to track which rows were imported vs skipped
- Re-uploading creates duplicates for valid rows

**Do this instead:**
- Validate ALL rows first
- Return ALL errors to user
- Only import if 100% of rows are valid
- Use atomic transactions to rollback on failure

### Anti-Pattern 2: No Idempotency for Re-Imports

**What people do:** Always create new records, causing duplicates when user re-uploads CSV.

**Why it's wrong:**
- User fixes one row error and re-uploads entire file
- All valid rows from first import are duplicated
- No way to update existing records from external system

**Do this instead:** Use `update_or_create()` with external_id as lookup key.

### Anti-Pattern 3: Synchronous Import Without Timeout Protection

**What people do:** Process large CSV files (10,000+ rows) synchronously in web request without timeout handling.

**Why it's wrong:**
- Web server timeout (30-60s) kills request mid-import
- Database left in partial state (if not using transaction.atomic())
- User sees timeout error, doesn't know if import succeeded

**Do this instead:**
- Set row threshold (e.g., 1000 rows)
- Queue large imports to Celery
- Return 202 Accepted with import_run_id
- Provide polling endpoint for status

## Sources

- [django-csvimport](https://github.com/edcrewe/django-csvimport) - Generic CSV import tool with admin interface and logging
- [django-csv-admin](https://github.com/huddlej/django-csv-admin) - CSV validation and import as form data
- [django-import-export documentation](https://django-import-export.readthedocs.io/en/latest/advanced_usage.html) - Row-level error tracking and validation patterns
- [Django idempotency patterns](https://dev.to/ck3130/idempotence-and-post-requests-in-django-2bbf) - Idempotent POST requests and upsert patterns
- [Django + React file upload](https://joetatusko.com/2024/01/29/how-to-send-file-objects-from-a-react-frontend-to-django-backend/) - File upload architecture for React + Django
- [Celery + Django REST Framework](https://www.mindbowser.com/celery-django-rest-framework/) - Async task optimization patterns
- [Real Python: Asynchronous Tasks with Django and Celery](https://realpython.com/asynchronous-tasks-with-django-and-celery/) - Celery architecture for Django
- [TestDriven.io: Django and Celery](https://testdriven.io/blog/django-and-celery/) - Celery setup and task patterns

---
*Architecture research for: DonorCRM CSV Import Pipeline*
*Researched: 2026-01-30*
*Confidence: HIGH (verified with existing codebase + official Django patterns)*
