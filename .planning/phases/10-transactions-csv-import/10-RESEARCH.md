# Phase 10: Transactions CSV Import - Research

**Researched:** 2026-02-02
**Domain:** Django CSV import with foreign key validation and denormalized statistics updates
**Confidence:** HIGH

## Summary

Phase 10 builds on established patterns from Phase 8 (Funds) and Phase 9 (Entities) to enable Donation CSV imports. The critical new challenges are: (1) validating foreign key references BEFORE import to enforce strict mode, and (2) efficiently updating Contact denormalized statistics after bulk import.

Django provides robust tools for this: set-based FK validation using `filter().values_list()`, bulk upsert via `bulk_create()` with `update_conflicts=True`, and aggregate functions (`Sum`, `Count`, `Max`) for recalculating denormalized stats. The existing codebase already demonstrates all required patterns - Phase 8/9 established CSV parsing and bulk upsert, and `Contact.update_giving_stats()` shows the aggregate recalculation pattern.

The standard approach: (1) parse CSV with existing validation patterns, (2) pre-validate ALL entity_id and fund_id references exist using set intersection, (3) bulk upsert Donation records using external_id as unique field, (4) identify affected Contact IDs from imported donations, (5) call `update_giving_stats()` on each affected contact to recalculate denormalized fields.

**Primary recommendation:** Follow Phase 8/9 patterns exactly (parse + import_transactions service functions, TransactionImportView API endpoint, ImportRun audit tracking), add pre-import FK validation using set operations, and update Contact stats by iterating affected contacts after bulk import completes.

## Standard Stack

The established libraries/tools for Django CSV import with FK validation:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django ORM | 5.x+ | Database operations, bulk upsert, aggregates | Built-in, no external dependencies needed |
| csv module | stdlib | CSV parsing via DictReader | Python standard library, already used in Phase 8/9 |
| Django REST Framework | 3.x+ | API endpoints for CSV upload | Already in codebase, consistent with existing views |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| decimal.Decimal | stdlib | Amount parsing (already in services.py) | Financial calculations requiring precision |
| datetime | stdlib | Date parsing (already in services.py) | posted_date field parsing |
| logging | stdlib | Import audit trail | Track import operations for debugging |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual CSV parsing | django-import-export | Too heavyweight for MVP, adds complexity. Manual parsing proven in Phase 8/9. |
| Individual saves | bulk_create() | bulk_create() is 10-100x faster for large imports. Essential for performance. |
| Pre-import FK validation | Catching IntegrityError | IntegrityError provides poor UX (no row numbers). Strict mode requires pre-validation. |

**Installation:**
No new packages required - all functionality available in Django stdlib and existing dependencies.

## Architecture Patterns

### Recommended Project Structure
```
apps/imports/
├── services.py                # parse_transactions_csv, import_transactions
├── views.py                   # TransactionImportView, TransactionTemplateView
├── models.py                  # Fund, ImportRun (already exist)
└── tests/
    └── test_transaction_import.py  # Comprehensive test coverage
```

### Pattern 1: Pre-Import Foreign Key Validation (Strict Mode)

**What:** Validate ALL foreign key references exist before importing any records. Reject entire import if any orphan references detected.

**When to use:** When importing child records (Donations) that reference parent records (Contact, Fund). Prevents partial imports and data integrity issues.

**Example:**
```python
# Source: Existing codebase pattern + Django ORM documentation
def parse_transactions_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    """
    Parse transactions CSV and validate foreign key references.

    Expected columns: transaction_id, entity_id, fund_id, amount, posted_date

    Returns:
        Tuple of (valid_records, errors)
    """
    reader = csv.DictReader(io.StringIO(file_content))

    valid_records = []
    errors = []
    seen_transaction_ids = set()

    # Collect all entity_ids and fund_ids for batch validation
    all_entity_ids = set()
    all_fund_ids = set()

    # First pass: validate row format, collect FK references
    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        transaction_id = row.get('transaction_id', '').strip()
        entity_id = row.get('entity_id', '').strip()
        fund_id = row.get('fund_id', '').strip()

        # Validate transaction_id
        if not transaction_id:
            row_errors.append('transaction_id is required')
        elif transaction_id in seen_transaction_ids:
            row_errors.append(f'Duplicate transaction_id in file: {transaction_id}')
        else:
            seen_transaction_ids.add(transaction_id)

        # Validate entity_id and fund_id present
        if not entity_id:
            row_errors.append('entity_id is required')
        else:
            all_entity_ids.add(entity_id)

        if not fund_id:
            row_errors.append('fund_id is required')
        else:
            all_fund_ids.add(fund_id)

        # Parse amount and date (reuse existing _parse_amount and _parse_date)
        amount, amount_error = _parse_amount(row.get('amount', ''))
        if amount_error:
            row_errors.append(amount_error)

        posted_date, date_error = _parse_date(row.get('posted_date', ''))
        if date_error:
            row_errors.append(date_error)

        if row_errors:
            errors.append({'row': row_num, 'errors': row_errors, 'data': dict(row)})
        else:
            valid_records.append({
                'transaction_id': transaction_id,
                'entity_id': entity_id,
                'fund_id': fund_id,
                'amount': amount,
                'posted_date': posted_date
            })

    # Second pass: Batch validate foreign key references
    if valid_records:
        # Validate entity_ids exist in Contact.external_id for this owner
        existing_entity_ids = set(
            Contact.objects.filter(
                owner=user,
                external_id__in=all_entity_ids
            ).values_list('external_id', flat=True)
        )

        missing_entity_ids = all_entity_ids - existing_entity_ids

        # Validate fund_ids exist in Fund.external_id (globally unique)
        existing_fund_ids = set(
            Fund.objects.filter(
                external_id__in=all_fund_ids
            ).values_list('external_id', flat=True)
        )

        missing_fund_ids = all_fund_ids - existing_fund_ids

        # If any orphan references, add errors with row numbers
        if missing_entity_ids or missing_fund_ids:
            for record in valid_records:
                row_errors = []
                if record['entity_id'] in missing_entity_ids:
                    row_errors.append(f"entity_id '{record['entity_id']}' not found in Contacts")
                if record['fund_id'] in missing_fund_ids:
                    row_errors.append(f"fund_id '{record['fund_id']}' not found in Funds")

                if row_errors:
                    # Find original row number
                    row_num = next(i+2 for i, r in enumerate(valid_records) if r == record)
                    errors.append({
                        'row': row_num,
                        'errors': row_errors,
                        'data': record
                    })

            # Clear valid_records if any orphan references (strict mode)
            valid_records = []

    return valid_records, errors
```

### Pattern 2: Bulk Upsert with Foreign Key Lookups

**What:** Efficiently create or update Donation records using bulk_create() while resolving foreign key references to Contact and Fund models.

**When to use:** When importing large batches of transaction records with external_id as unique identifier.

**Example:**
```python
# Source: Phase 8 import_funds pattern + Django ORM bulk_create documentation
def import_transactions(records: List[dict], user, import_run) -> Tuple[int, int]:
    """
    Import transactions from parsed records using bulk upsert.

    Args:
        records: List of validated transaction dicts
        user: User performing import (for owner-scoped Contact lookup)
        import_run: ImportRun instance to update with results

    Returns:
        Tuple of (created_count, updated_count)
    """
    if not records:
        import_run.created_count = 0
        import_run.updated_count = 0
        import_run.status = ImportStatus.COMPLETED
        import_run.save()
        return 0, 0

    # Pre-fetch all Contact and Fund objects in batch
    entity_ids = [r['entity_id'] for r in records]
    fund_ids = [r['fund_id'] for r in records]

    # Build lookup dicts for FK resolution
    contacts_by_external_id = {
        c.external_id: c
        for c in Contact.objects.filter(
            owner=user,
            external_id__in=entity_ids
        )
    }

    funds_by_external_id = {
        f.external_id: f
        for f in Fund.objects.filter(external_id__in=fund_ids)
    }

    # Get existing transaction_ids to calculate created vs updated
    transaction_ids = [r['transaction_id'] for r in records]
    existing_transaction_ids = set(
        Donation.objects.filter(
            external_id__in=transaction_ids
        ).values_list('external_id', flat=True)
    )

    # Prepare Donation objects for bulk upsert
    donation_objects = [
        Donation(
            external_id=record['transaction_id'],
            contact=contacts_by_external_id[record['entity_id']],
            fund=funds_by_external_id[record['fund_id']],
            amount=record['amount'],
            date=record['posted_date'],
            donation_type=DonationType.ONE_TIME,
            payment_method=PaymentMethod.OTHER
        )
        for record in records
    ]

    # Bulk upsert using external_id as unique field
    Donation.objects.bulk_create(
        donation_objects,
        update_conflicts=True,
        unique_fields=['external_id'],
        update_fields=['contact', 'fund', 'amount', 'date']
    )

    # Calculate counts
    created_count = sum(1 for r in records if r['transaction_id'] not in existing_transaction_ids)
    updated_count = sum(1 for r in records if r['transaction_id'] in existing_transaction_ids)

    # Update import run
    import_run.created_count = created_count
    import_run.updated_count = updated_count
    import_run.status = ImportStatus.COMPLETED
    import_run.save()

    return created_count, updated_count
```

### Pattern 3: Update Denormalized Statistics After Bulk Import

**What:** Recalculate Contact denormalized fields (total_given, gift_count, last_gift_date) after bulk importing donations.

**When to use:** After any bulk donation import or modification that affects Contact giving statistics.

**Example:**
```python
# Source: Existing Contact.update_giving_stats() + batch processing pattern
def update_contact_stats_for_import(records: List[dict], user):
    """
    Update denormalized giving stats for all contacts affected by import.

    Args:
        records: List of imported transaction dicts
        user: User who owns the contacts
    """
    # Identify unique contact external_ids affected by this import
    affected_entity_ids = set(r['entity_id'] for r in records)

    # Fetch affected Contact objects
    affected_contacts = Contact.objects.filter(
        owner=user,
        external_id__in=affected_entity_ids
    )

    # Update stats for each affected contact
    for contact in affected_contacts:
        contact.update_giving_stats()  # Existing method from Contact model

    logger.info(f'Updated giving stats for {affected_contacts.count()} contacts')
```

The existing `Contact.update_giving_stats()` method already handles the aggregate calculation:
```python
# Source: apps/contacts/models.py lines 152-181
def update_giving_stats(self):
    """Recalculate giving statistics from donations."""
    donations = self.donations.all()
    agg = donations.aggregate(
        total=models.Sum('amount'),
        count=models.Count('id'),
        first=models.Min('date'),
        last=models.Max('date')
    )

    self.total_given = agg['total'] or 0
    self.gift_count = agg['count'] or 0
    self.first_gift_date = agg['first']
    self.last_gift_date = agg['last']

    if agg['last']:
        last_donation = donations.order_by('-date').first()
        self.last_gift_amount = last_donation.amount if last_donation else None

    # Update status based on giving history
    if self.gift_count > 0 and self.status == ContactStatus.PROSPECT:
        self.status = ContactStatus.DONOR

    self.save(update_fields=[
        'total_given', 'gift_count', 'first_gift_date',
        'last_gift_date', 'last_gift_amount', 'status'
    ])
```

### Anti-Patterns to Avoid

- **Don't catch IntegrityError for FK validation:** Poor UX, no row numbers, hard to debug. Use pre-validation instead.
- **Don't use individual save() for bulk imports:** 10-100x slower than bulk_create(). Always use bulk operations for >10 records.
- **Don't update denormalized stats inside the import loop:** N+1 query problem. Batch update after import completes.
- **Don't use global Contact lookup for entity_id:** Contact.external_id is owner-scoped. Always filter by owner=user.
- **Don't skip ImportRun audit trail:** Phase 8/9 established this pattern. Required for import history and debugging.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing with encoding handling | Custom file reader | csv.DictReader + decode('utf-8-sig') | Handles Excel BOM automatically. Pattern proven in Phase 8/9. |
| Amount validation | Custom decimal parsing | Existing _parse_amount() helper | Handles currency symbols, negatives, max values. Already tested. |
| Date parsing | Custom date parser | Existing _parse_date() helper | Tries multiple formats. Already handles common formats from SPO exports. |
| FK validation errors | Catching database exceptions | Pre-validation with set operations | Provides row numbers, better error messages. Strict mode requirement. |
| Denormalized stats calculation | Manual SQL or loops | Contact.update_giving_stats() | Already implements Sum, Count, Max aggregates with status updates. |
| Duplicate detection | Manual tracking | Set-based deduplication | O(1) lookup, memory efficient, pattern established in Phase 8/9. |

**Key insight:** Phase 8 and 9 established comprehensive validation patterns. Reusing these patterns ensures consistency, reduces bugs, and speeds development. The only new code needed is FK validation logic and calling update_giving_stats() on affected contacts.

## Common Pitfalls

### Pitfall 1: Contact.external_id Owner Scoping vs Fund.external_id Global Uniqueness

**What goes wrong:** Using Contact.objects.filter(external_id=entity_id) without owner filter returns wrong contact or raises MultipleObjectsReturned error.

**Why it happens:** Fund.external_id is globally unique (Phase 7 decision 07-01-D1), but Contact.external_id is owner-scoped (Phase 7 decision 07-02-D1). Different owners can have contacts with same external_id.

**How to avoid:**
- Always filter Contact by owner: `Contact.objects.filter(owner=user, external_id=entity_id)`
- Fund queries don't need owner: `Fund.objects.filter(external_id=fund_id)`
- Pre-validation must use owner-scoped lookup for entity_ids

**Warning signs:**
- MultipleObjectsReturned exception when looking up contacts
- Wrong contact linked to donation (different owner)
- ImportRun errors: "Multiple contacts found with entity_id X"

### Pitfall 2: N+1 Queries When Updating Contact Stats

**What goes wrong:** Calling update_giving_stats() inside the import loop causes 1 query per contact update, plus aggregate queries. For 1000 donations affecting 200 contacts = 200+ extra queries.

**Why it happens:** Django doesn't batch method calls automatically. Each contact.update_giving_stats() is a separate transaction.

**How to avoid:**
- Collect affected contact external_ids FIRST
- Fetch affected contacts in single query: `Contact.objects.filter(owner=user, external_id__in=affected_ids)`
- Iterate fetched queryset to call update_giving_stats() - still N queries but prefetched
- Consider bulk_update() for very large imports (1000+ affected contacts)

**Warning signs:**
- Import taking >10 seconds for 100 records
- Django Debug Toolbar shows hundreds of queries
- Database CPU spikes during imports

### Pitfall 3: Missing FK Validation Before Bulk Create Causes Silent Failures

**What goes wrong:** bulk_create() with update_conflicts=True silently skips records with invalid foreign keys. No error message, partial import succeeds, missing records hard to track.

**Why it happens:** Django's bulk_create() doesn't validate ForeignKey constraints before insert. Database rejects invalid FKs, but with update_conflicts=True, the operation continues.

**How to avoid:**
- ALWAYS pre-validate FK references exist using set intersection
- Reject entire import if any orphan references found (strict mode)
- Return clear error messages with row numbers: "Row 42: entity_id 'E123' not found in Contacts"
- Test with invalid FK references to verify rejection

**Warning signs:**
- Import returns success but created_count < total valid rows
- Missing donations in database after "successful" import
- No error messages but records silently dropped

### Pitfall 4: Forgetting UTF-8 BOM Handling from Excel Exports

**What goes wrong:** Excel exports include UTF-8 BOM (Byte Order Mark: \ufeff). Standard decode('utf-8') includes BOM in first column name, causing "missing required column" error.

**Why it happens:** Excel adds BOM to signal UTF-8 encoding. Python's decode('utf-8') doesn't strip it, so column header becomes '\ufefftransaction_id' instead of 'transaction_id'.

**How to avoid:**
- Use decode('utf-8-sig') instead of decode('utf-8')
- Pattern already established in Phase 8/9 FundImportView and EntityImportView
- Test with actual Excel-exported CSV to verify BOM handling

**Warning signs:**
- "Missing required column: transaction_id" error on valid-looking CSV
- First column validation fails but other columns work
- Error only occurs with Excel exports, not manually created CSVs

## Code Examples

Verified patterns from official sources and existing codebase:

### Set-Based Foreign Key Validation
```python
# Source: Django ORM documentation + Phase 8/9 pattern
# Efficient batch validation of FK references

# Collect all unique FK values from CSV
all_entity_ids = set(record['entity_id'] for record in valid_records)
all_fund_ids = set(record['fund_id'] for record in valid_records)

# Query existing values in single database hit
existing_entity_ids = set(
    Contact.objects.filter(
        owner=user,
        external_id__in=all_entity_ids
    ).values_list('external_id', flat=True)
)

existing_fund_ids = set(
    Fund.objects.filter(
        external_id__in=all_fund_ids
    ).values_list('external_id', flat=True)
)

# Calculate missing references using set difference
missing_entity_ids = all_entity_ids - existing_entity_ids
missing_fund_ids = all_fund_ids - existing_fund_ids

# Reject import if any orphan references
if missing_entity_ids:
    raise ValidationError(
        f"Missing entity_ids: {', '.join(sorted(missing_entity_ids))}"
    )
if missing_fund_ids:
    raise ValidationError(
        f"Missing fund_ids: {', '.join(sorted(missing_fund_ids))}"
    )
```

### Bulk FK Lookup for Upsert
```python
# Source: Django ORM documentation
# Build lookup dicts to resolve FKs efficiently

# Single query to fetch all needed Contact objects
contacts_by_external_id = {
    c.external_id: c
    for c in Contact.objects.filter(
        owner=user,
        external_id__in=entity_ids
    )
}

# Single query to fetch all needed Fund objects
funds_by_external_id = {
    f.external_id: f
    for f in Fund.objects.filter(external_id__in=fund_ids)
}

# Use dicts to resolve FKs during object creation
donation = Donation(
    contact=contacts_by_external_id[record['entity_id']],
    fund=funds_by_external_id[record['fund_id']],
    external_id=record['transaction_id'],
    amount=record['amount'],
    date=record['posted_date']
)
```

### Aggregate Statistics Calculation
```python
# Source: apps/contacts/models.py lines 152-181 + Django Aggregation docs
# Recalculate denormalized fields using Django aggregates

from django.db.models import Sum, Count, Min, Max

donations = self.donations.all()
agg = donations.aggregate(
    total=Sum('amount'),
    count=Count('id'),
    first=Min('date'),
    last=Max('date')
)

self.total_given = agg['total'] or 0
self.gift_count = agg['count'] or 0
self.first_gift_date = agg['first']
self.last_gift_date = agg['last']

# Get last donation details
if agg['last']:
    last_donation = donations.order_by('-date').first()
    self.last_gift_amount = last_donation.amount if last_donation else None

self.save(update_fields=[
    'total_given', 'gift_count', 'first_gift_date',
    'last_gift_date', 'last_gift_amount'
])
```

### TransactionImportView API Endpoint Pattern
```python
# Source: Phase 8 FundImportView + Phase 9 EntityImportView pattern
# Consistent API endpoint structure for CSV imports

class TransactionImportView(APIView):
    """
    POST: Import transactions from CSV file (admin only)

    Query params:
        validate_only: If 'true', only validate without importing
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        # File validation (Phase 8/9 pattern)
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided.'}, status=400)

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response({'detail': 'File must be a CSV.'}, status=400)

        # UTF-8-sig handles Excel BOM (Phase 8/9 pattern)
        try:
            content = file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            return Response({'detail': 'File encoding error. Please use UTF-8.'}, status=400)

        # Parse CSV
        valid_records, errors = parse_transactions_csv(content, request.user)

        # Validate-only mode (dry run)
        if request.query_params.get('validate_only') == 'true':
            return Response({
                'valid_count': len(valid_records),
                'error_count': len(errors),
                'errors': errors[:20]
            })

        # Create ImportRun audit record (Phase 8/9 pattern)
        import_run = ImportRun.objects.create(
            type=ImportType.TRANSACTIONS,
            status=ImportStatus.IMPORTING,
            filename=file.name,
            uploaded_by=request.user
        )

        # Synchronous import (MVP - no Celery)
        if valid_records:
            created_count, updated_count = import_transactions(
                valid_records, request.user, import_run
            )

            # Update Contact denormalized stats
            update_contact_stats_for_import(valid_records, request.user)
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
| Individual save() calls | bulk_create() with update_conflicts | Django 4.1+ | 10-100x performance improvement for bulk imports |
| Catching IntegrityError for validation | Pre-validation with set operations | Best practice 2023+ | Better error messages with row numbers, strict mode support |
| Manual SQL for aggregates | Django aggregate() functions | Django 1.0+ but best practices evolved | Database-agnostic, more maintainable, leverages ORM optimizations |
| django-import-export library | Custom service functions | Project decision (Phase 8) | Simpler codebase, more control, less dependencies |
| Signals for denormalized updates | Explicit update_giving_stats() calls | Project decision (Phase 1-7) | More predictable, better performance, no signal overhead |

**Deprecated/outdated:**
- **get_or_create() in loops for upsert:** Replaced by bulk_create() with update_conflicts=True (Django 4.1+). The loop approach is 50-100x slower.
- **F() expressions for denormalized updates:** While F() can increment values, Contact stats require full recalculation from donations. Using aggregate() is correct pattern.
- **django-import-export for simple CSV imports:** Adds 3rd party dependency and complexity. Manual parsing with DictReader is simpler and more maintainable for this use case.

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal batch size for Contact stats updates**
   - What we know: Iterating 200 contacts to call update_giving_stats() is acceptable for MVP
   - What's unclear: At what scale (1000+ affected contacts?) should we switch to bulk_update() pattern
   - Recommendation: Start with simple iteration. Add bulk_update() optimization if Phase 10 verification shows slow performance (>10 seconds for typical imports)

2. **Transaction isolation for concurrent imports**
   - What we know: Two admins importing transactions simultaneously could cause race conditions on Contact denormalized stats
   - What's unclear: How likely is concurrent import scenario? Does MVP need locking?
   - Recommendation: Skip select_for_update() for MVP. Add transaction locking in Phase 11 if concurrent imports become a real use case. Document assumption in tests.

3. **Error reporting when ALL records have orphan FKs**
   - What we know: Strict mode rejects entire import if any orphan references. Error response includes row numbers.
   - What's unclear: Should we return ALL orphan FK errors or limit to first 20 (like other errors)?
   - Recommendation: Return first 20 orphan FK errors with summary count. Prevents huge error payloads for badly malformed files. Consistent with Phase 8/9 error limiting pattern.

## Sources

### Primary (HIGH confidence)
- Django Aggregation documentation - https://docs.djangoproject.com/en/6.0/topics/db/aggregation/
- Existing codebase: apps/imports/services.py (parse_funds_csv, import_funds, parse_entities_csv, import_entities patterns)
- Existing codebase: apps/contacts/models.py (Contact.update_giving_stats method, lines 152-181)
- Existing codebase: apps/imports/views.py (FundImportView, EntityImportView patterns)
- Django QuerySet documentation on bulk_create (WebFetch)

### Secondary (MEDIUM confidence)
- [Boosting Upsert Performance in Django ORM](https://medium.com/@remidenoyer/django-orm-bulk-operations-optimization-notes-1fd9b3c8cf58) - bulk_create performance patterns
- [Django bulk insert with Foreign Key](https://gist.github.com/Attila03/4c491b336117cb86f524cb2d1ed42ab1) - FK resolution in bulk operations
- [Running a bulk update with Django](https://www.sankalpjonna.com/learn-django/running-a-bulk-update-with-django) - bulk_update patterns
- [Import donations - Microsoft for Nonprofits](https://learn.microsoft.com/en-us/industry/nonprofit/fundraising-engagement-gifts-import-data) - Donation CSV import best practices
- [How to Aggregate + Count - Django Forum](https://forum.djangoproject.com/t/how-to-aggregate-count/25864) - Aggregate function patterns

### Tertiary (LOW confidence)
- WebSearch: Django bulk_create with update_conflicts and foreign keys - Known issue with ignore_conflicts and FKs in Django 3.2+. Not applicable to this implementation (using update_conflicts, not ignore_conflicts).
- WebSearch: CSV Data Validation and Storage System - Third-party Django CSV import examples. Not using these libraries, but patterns informative.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Django ORM, stdlib csv, DRF already in use. No new dependencies needed.
- Architecture: HIGH - Patterns established in Phase 8/9. Direct reuse with FK validation addition.
- Pitfalls: HIGH - Contact.external_id owner-scoping documented in Phase 7 decisions. UTF-8 BOM handling verified in Phase 8 tests.

**Research date:** 2026-02-02
**Valid until:** 30 days (stable Django patterns, no fast-moving dependencies)
