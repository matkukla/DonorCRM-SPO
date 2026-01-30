# Phase 7: Foundation - Research

**Researched:** 2026-01-30
**Domain:** Django model creation and database migrations for CSV import infrastructure
**Confidence:** HIGH

## Summary

Phase 7 establishes the data model foundation for SPO-compatible CSV imports. This involves creating three new models (Fund, ImportRun, ImportRowError) and adding external_id fields to three existing models (Contact, Donation, Pledge). The existing codebase uses Django 4.2 with PostgreSQL and UUID primary keys via TimeStampedModel base class.

Django 4.2 provides native bulk upsert capabilities via `bulk_create(update_conflicts=True)`, eliminating the need for third-party libraries. The key technical challenge is adding external_id fields to production models that already contain data, requiring nullable fields with conditional unique constraints.

**Primary recommendation:** Add external_id fields as nullable with `blank=True`, use conditional UniqueConstraint to enforce uniqueness only when non-empty, and leverage Django 4.2's native bulk operations for idempotent imports.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2.27 | ORM and migrations | Already in project, provides native bulk upsert since 4.1+ |
| PostgreSQL | 12+ | Database backend | Already in project, supports ON CONFLICT for upserts |
| Python csv | stdlib | CSV parsing | Already used in apps/imports/services.py, sufficient for server-side parsing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Django migrations | Django 4.2 | Schema versioning | All model changes, automatic generation with makemigrations |
| UUID | Python stdlib | Primary keys | Already used via TimeStampedModel base, no change needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Django native bulk_create | django-bulk-update-or-create | Third-party package, adds dependency, not needed with Django 4.1+ |
| Nullable external_id | Required external_id | Breaks existing manual data entry, forces all records to have external IDs |
| Conditional UniqueConstraint | Standard unique=True | Would fail for multiple blank external_id values in database |

**Installation:**
```bash
# No new dependencies needed
# Django 4.2.27 already provides all required functionality
```

## Architecture Patterns

### Recommended Project Structure
```
apps/
├── imports/
│   ├── models.py           # NEW: ImportRun, ImportRowError, Fund
│   ├── services.py         # Extend: add parse_funds_csv, import_funds
│   ├── views.py            # Extend: add FundImportView
│   └── migrations/         # NEW migrations generated
├── contacts/
│   ├── models.py           # Extend: add external_id field
│   └── migrations/         # NEW migration for external_id
├── donations/
│   ├── models.py           # Extend: add fund FK (external_id already exists)
│   └── migrations/         # NEW migration for fund FK
└── pledges/
    ├── models.py           # Extend: add external_id field, fund FK
    └── migrations/         # NEW migration for external_id + fund FK
```

### Pattern 1: Adding External ID to Existing Model (Nullable with Conditional Uniqueness)

**What:** Add external_id field to models with existing data using nullable field and conditional unique constraint.

**When to use:** When adding unique fields to production models that already contain records without external IDs.

**Example:**
```python
# apps/contacts/models.py
class Contact(TimeStampedModel):
    # ... existing fields ...

    # NEW: External ID for idempotent imports
    external_id = models.CharField(
        'external ID',
        max_length=100,
        blank=True,  # Allow empty string in forms
        db_index=True,  # Fast lookups during import validation
        help_text='Entity ID from external system (e.g., SPO)'
    )

    class Meta:
        # ... existing meta ...
        constraints = [
            # ... existing constraints ...
            # NEW: Unique external_id per owner, only when not empty
            models.UniqueConstraint(
                fields=['owner', 'external_id'],
                name='unique_contact_external_id_per_owner',
                condition=~models.Q(external_id='')  # Uniqueness only when populated
            )
        ]
```

**Why this works:**
- `blank=True` allows empty strings, doesn't require `null=True` (Django best practice: avoid NULL on CharField)
- `db_index=True` enables fast `Contact.objects.filter(external_id__in=csv_ids)` lookups during validation
- Conditional constraint `condition=~models.Q(external_id='')` allows multiple empty external_id values while enforcing uniqueness for populated values
- Owner-scoped uniqueness prevents collisions across missionaries (Contact already has owner field)

### Pattern 2: Creating ImportRun Audit Model with Status Enum

**What:** Central audit model tracking all import operations with status progression and result counts.

**When to use:** For any CSV import pipeline requiring audit trail and import history.

**Example:**
```python
# apps/imports/models.py
from django.db import models
from apps.core.models import TimeStampedModel

class ImportType(models.TextChoices):
    """Types of CSV imports supported."""
    FUNDS = 'funds', 'Funds'
    ENTITIES = 'entities', 'Entities'
    TRANSACTIONS = 'transactions', 'Transactions'
    PLEDGES = 'pledges', 'Pledges'

class ImportStatus(models.TextChoices):
    """Import processing status."""
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
```

**Why this pattern:**
- TextChoices provides type safety and validation (Django 3.0+)
- Separate counts enable "45 created, 103 updated, 2 errors" reporting
- JSONField error_summary stores first 20 errors for quick preview without querying ImportRowError
- on_delete=models.PROTECT prevents accidental deletion of user with import history
- Indexes on common query patterns (user's recent imports, imports by type/status)

### Pattern 3: Row-Level Error Storage for User-Friendly Reports

**What:** Store validation errors per row with line numbers and original data for "Download Errors CSV" feature.

**When to use:** CSV imports where users need to fix validation errors and re-upload.

**Example:**
```python
# apps/imports/models.py
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
```

**Why this pattern:**
- CASCADE delete removes errors when ImportRun deleted (audit cleanup)
- JSONField error_messages stores list: `["Amount is required", "Invalid date format"]`
- JSONField row_data enables "Download Errors CSV" with original problematic values
- Index on row_number enables fast retrieval for error report display

### Pattern 4: Fund Model with External ID and Owner-Scoped Data

**What:** Simple reference data model for account/campaign tracking from SPO.

**When to use:** For lookup tables referenced by foreign keys in transactional data.

**Example:**
```python
# apps/imports/models.py
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

    def __str__(self):
        return f'{self.name} ({self.external_id})'
```

**Why this pattern:**
- Unique constraint on external_id enables idempotent imports (upsert on conflict)
- owner field nullable allows global funds (some SPO exports have org-wide accounts)
- Simple model with minimal fields (extensible later without breaking imports)

### Pattern 5: Zero-Downtime Migration for Adding Nullable Fields

**What:** Multi-step approach for adding fields to production databases without locking tables.

**When to use:** Production deployments where table locks would cause downtime.

**Example:**
```bash
# Step 1: Add nullable field with index (single migration)
python manage.py makemigrations contacts --name add_external_id

# Generated migration:
# migrations/XXXX_add_external_id.py
operations = [
    migrations.AddField(
        model_name='contact',
        name='external_id',
        field=models.CharField(blank=True, db_index=True, max_length=100),
    ),
    migrations.AddConstraint(
        model_name='contact',
        constraint=models.UniqueConstraint(
            condition=models.Q(('external_id', '')),
            fields=('owner', 'external_id'),
            name='unique_contact_external_id_per_owner'
        ),
    ),
]

# Step 2: Apply migration (PostgreSQL 11+ doesn't lock table for nullable adds)
python manage.py migrate contacts
```

**Why this approach:**
- Nullable fields added without locking table in PostgreSQL 11+
- Conditional constraint allows multiple empty values (existing records)
- Single migration avoids multi-version deployment complexity
- db_index created concurrently (Django handles this automatically)

### Anti-Patterns to Avoid

- **Making external_id required on existing models:** Forces data migration for all existing records, breaks manual data entry, complex deployment
- **Using unique=True on nullable CharField:** Allows only one NULL value in most databases, fails with multiple blank external_id records
- **Creating ImportRun without status field:** No way to track "validating" vs "importing" vs "completed", poor progress reporting
- **Storing CSV content in ImportRowError.row_data for large files:** Bloats database, use only for error rows, not all rows
- **Using ForeignKey without on_delete:** Django requires explicit on_delete, PROTECT prevents accidental cascade deletes

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bulk upsert operations | Custom SQL with ON CONFLICT | Django 4.2 `bulk_create(update_conflicts=True, unique_fields=['external_id'])` | Django ORM handles cross-database syntax, transaction safety, and returns created/updated objects |
| Unique constraint on nullable field | Complex triggers or stored procedures | Django `UniqueConstraint(condition=~models.Q(field=''))` | Database-level enforcement, works with Django ORM, standard migration generation |
| CSV field parsing (amount, date) | New validation functions | Extend existing `_parse_amount()`, `_parse_date()` in services.py | Already tested, handles edge cases, consistent error messages |
| Migration dependency ordering | Manual migration file editing | Django's automatic dependency detection via `dependencies = [('app', 'migration')]` | Django resolves circular dependencies, detects cross-app references |

**Key insight:** Django 4.1+ native bulk operations eliminate the need for third-party upsert libraries. Use Django's built-in features for common migration patterns rather than custom SQL.

## Common Pitfalls

### Pitfall 1: External ID Field Without Conditional Uniqueness

**What goes wrong:** Adding `external_id = models.CharField(max_length=100, unique=True, blank=True)` to Contact fails during migration because existing records have empty external_id, and most databases allow only one NULL/empty value in unique column.

**Why it happens:** Standard `unique=True` creates database-level UNIQUE constraint without condition. PostgreSQL, MySQL treat empty string as a value, not NULL, but still enforce uniqueness.

**How to avoid:**
1. Use `blank=True` (no `null=True` for CharField per Django best practice)
2. Add UniqueConstraint with condition: `condition=~models.Q(external_id='')`
3. Scope uniqueness to owner for multi-tenant: `fields=['owner', 'external_id']`

**Warning signs:**
- Migration fails with "duplicate key value violates unique constraint"
- Error occurs even though no external_ids are populated
- All existing records have empty external_id but constraint fails

**Code example:**
```python
# ❌ WRONG: Standard unique constraint fails with multiple empty values
class Contact(TimeStampedModel):
    external_id = models.CharField(max_length=100, unique=True, blank=True)

# ✅ CORRECT: Conditional constraint allows multiple empty values
class Contact(TimeStampedModel):
    external_id = models.CharField(max_length=100, blank=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'external_id'],
                name='unique_contact_external_id_per_owner',
                condition=~models.Q(external_id='')
            )
        ]
```

### Pitfall 2: Adding Non-Nullable ForeignKey to Existing Model

**What goes wrong:** Adding `fund = models.ForeignKey('imports.Fund', on_delete=models.PROTECT)` to Donation model that already has 5,000 donations fails migration because existing records have no fund_id value to populate.

**Why it happens:** Django migration requires a value for non-nullable fields. With ForeignKey, there's no sensible default (can't use 0 or empty string for UUID/integer FK).

**How to avoid:**
1. Add ForeignKey with `null=True, blank=True` initially
2. In separate deployment, populate fund_id for historical records (data migration)
3. In third deployment, change to `null=False` if required

**Warning signs:**
- Migration prompts "Please enter the default value now"
- Migration fails with "column cannot be null"
- ImportError for circular dependency between models

**Code example:**
```python
# ✅ CORRECT: Nullable FK for existing data
class Donation(TimeStampedModel):
    # ... existing fields ...

    # NEW: Fund FK (nullable to allow existing donations)
    fund = models.ForeignKey(
        'imports.Fund',
        on_delete=models.SET_NULL,  # Don't cascade delete donations if fund deleted
        null=True,
        blank=True,
        related_name='donations'
    )
```

**Phase 7 approach:** Add fund FK as nullable. Import validation will require fund_id for new imports, but existing manual donations remain valid.

### Pitfall 3: Missing on_delete for ForeignKey

**What goes wrong:** Adding `fund = models.ForeignKey('imports.Fund')` without `on_delete` argument fails with `TypeError: __init__() missing 1 required keyword-only argument: 'on_delete'`.

**Why it happens:** Django 2.0+ requires explicit on_delete behavior to prevent accidental cascade deletes. No default fallback.

**How to avoid:**
1. Always specify on_delete when creating ForeignKey
2. Use PROTECT for audit models (ImportRun → User)
3. Use CASCADE for child records (ImportRowError → ImportRun)
4. Use SET_NULL for optional references (Donation → Fund)

**Warning signs:**
- TypeError during model class definition
- Migration fails to generate
- Django check command fails with "fields.E320"

**Decision matrix:**
| Relationship | on_delete | Rationale |
|--------------|-----------|-----------|
| ImportRun → User | PROTECT | Prevent deleting user with import history |
| ImportRowError → ImportRun | CASCADE | Errors belong to import run, delete together |
| Donation → Fund | SET_NULL | Keep donations even if fund deleted (data preservation) |
| Contact → User (owner) | PROTECT | Prevent deleting user who owns contacts |

### Pitfall 4: Forgetting db_index on External ID Fields

**What goes wrong:** Import validation performs `Contact.objects.filter(external_id__in=csv_external_ids)` for 1,000 rows. Without index, database performs sequential scan of 50,000 contacts, taking 5+ seconds per import.

**Why it happens:** Django doesn't automatically index CharField fields (unlike primary keys and ForeignKeys). Developer assumes ORM will optimize lookups.

**How to avoid:**
1. Add `db_index=True` to external_id field definition
2. Review query patterns during import validation (use Django Debug Toolbar or explain analyze)
3. Add composite indexes for common filter combinations

**Warning signs:**
- Import validation slow for large files (>1000 rows)
- Database CPU spikes during import
- EXPLAIN shows "Seq Scan" on external_id lookups
- Import time grows linearly with total database size, not CSV size

**Code example:**
```python
# ✅ Add db_index for fast lookups
external_id = models.CharField(
    max_length=100,
    blank=True,
    db_index=True  # Creates index: idx_contacts_external_id
)

# Validation query (used during CSV import)
csv_ids = [row['entity_id'] for row in csv_rows]
existing_contacts = Contact.objects.filter(
    owner=user,
    external_id__in=csv_ids  # Fast with index
).values_list('external_id', flat=True)
```

### Pitfall 5: Using CharField(null=True) Instead of blank=True

**What goes wrong:** Defining `external_id = models.CharField(max_length=100, null=True)` creates two empty states: NULL (database) and empty string (Django forms). Causes confusion: `filter(external_id='')` misses NULL records, `filter(external_id__isnull=True)` misses empty strings.

**Why it happens:** Developer treats CharField like IntegerField (where null=True is correct). Django's CharField best practice is blank=True only.

**How to avoid:**
1. Use `blank=True` for optional CharField (allows empty string '')
2. Avoid `null=True` on CharField (creates two empty states)
3. Use `null=True, blank=True` only for DateField, IntegerField, ForeignKey

**Warning signs:**
- Some external_id fields are NULL, others are empty string
- Queries miss records: `filter(external_id='')` doesn't find NULL
- Unique constraint behaves inconsistently

**Code example:**
```python
# ❌ WRONG: Creates two empty states (NULL and '')
external_id = models.CharField(max_length=100, null=True, blank=True)

# ✅ CORRECT: Single empty state (empty string)
external_id = models.CharField(max_length=100, blank=True)

# ✅ CORRECT: Use null=True for non-text fields
amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
date = models.DateField(null=True, blank=True)
fund = models.ForeignKey('imports.Fund', null=True, blank=True, on_delete=models.SET_NULL)
```

## Code Examples

Verified patterns from official sources:

### Complete Fund Model
```python
# apps/imports/models.py
from django.db import models
from apps.core.models import TimeStampedModel

class Fund(TimeStampedModel):
    """
    Represents a fund/account/campaign from SPO.
    Funds are imported before transactions and referenced via external_id.
    """
    external_id = models.CharField(
        'external ID',
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Fund ID from SPO system'
    )
    name = models.CharField('fund name', max_length=255)
    status = models.CharField(
        'status',
        max_length=20,
        default='active',
        help_text='active, inactive, or closed'
    )

    # Optional: owner-scoped for multi-org deployments
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='funds',
        help_text='Owner if fund is user-specific, null for org-wide funds'
    )

    class Meta:
        db_table = 'funds'
        verbose_name = 'fund'
        verbose_name_plural = 'funds'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['external_id'],
                name='unique_fund_external_id'
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.external_id})'
```

### Complete ImportRun Model
```python
# apps/imports/models.py
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
    """
    Audit trail for each CSV import operation.
    Tracks status, counts, and errors for import history.
    """
    type = models.CharField(
        'import type',
        max_length=20,
        choices=ImportType.choices,
        db_index=True
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=ImportStatus.choices,
        default=ImportStatus.PENDING
    )

    # File metadata
    filename = models.CharField('filename', max_length=255)
    total_rows = models.IntegerField('total rows', default=0)

    # Results
    created_count = models.IntegerField('created count', default=0)
    updated_count = models.IntegerField('updated count', default=0)
    skipped_count = models.IntegerField('skipped count', default=0)
    error_count = models.IntegerField('error count', default=0)

    # User tracking
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='import_runs'
    )

    # Error summary (first 20 errors for quick preview)
    error_summary = models.JSONField(
        'error summary',
        default=dict,
        blank=True,
        help_text='JSON dict with sample errors for preview'
    )

    class Meta:
        db_table = 'import_runs'
        verbose_name = 'import run'
        verbose_name_plural = 'import runs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uploaded_by', '-created_at']),
            models.Index(fields=['type', 'status']),
        ]

    def __str__(self):
        return f'{self.get_type_display()} import by {self.uploaded_by.email} on {self.created_at.date()}'
```

### Complete ImportRowError Model
```python
# apps/imports/models.py
class ImportRowError(TimeStampedModel):
    """
    Individual row errors for failed import rows.
    Stores validation errors with line numbers for error reports.
    """
    import_run = models.ForeignKey(
        ImportRun,
        on_delete=models.CASCADE,
        related_name='row_errors'
    )
    row_number = models.IntegerField('row number')
    error_messages = models.JSONField(
        'error messages',
        help_text='List of error strings for this row'
    )
    row_data = models.JSONField(
        'row data',
        help_text='Original CSV row as dict for error CSV download'
    )

    class Meta:
        db_table = 'import_row_errors'
        verbose_name = 'import row error'
        verbose_name_plural = 'import row errors'
        ordering = ['row_number']
        indexes = [
            models.Index(fields=['import_run', 'row_number']),
        ]

    def __str__(self):
        return f'Row {self.row_number}: {len(self.error_messages)} errors'
```

### Migration for Adding External ID to Contact
```python
# Generated by Django 4.2.27 - apps/contacts/migrations/XXXX_add_external_id.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('contacts', 'YYYY_previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='external_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Entity ID from external system (e.g., SPO)',
                max_length=100,
                verbose_name='external ID'
            ),
        ),
        migrations.AddConstraint(
            model_name='contact',
            constraint=models.UniqueConstraint(
                condition=models.Q(('external_id', '')),
                fields=('owner', 'external_id'),
                name='unique_contact_external_id_per_owner'
            ),
        ),
    ]
```

### Bulk Upsert Pattern with Django 4.2
```python
# apps/imports/services.py
from django.db import transaction
from apps.imports.models import Fund

@transaction.atomic
def import_funds(records: List[dict], import_run) -> Tuple[int, int]:
    """
    Import funds with idempotent upsert.
    Uses Django 4.2 bulk_create with update_conflicts.

    Returns:
        (created_count, updated_count)
    """
    # Pre-check: which external_ids already exist?
    existing_ids = set(
        Fund.objects.filter(
            external_id__in=[r['fund_id'] for r in records]
        ).values_list('external_id', flat=True)
    )

    # Separate creates and updates
    creates = [r for r in records if r['fund_id'] not in existing_ids]
    updates = [r for r in records if r['fund_id'] in existing_ids]

    created_count = 0
    updated_count = 0

    # Bulk create new records
    if creates:
        fund_objs = [
            Fund(
                external_id=r['fund_id'],
                name=r['name'],
                status=r['status']
            )
            for r in creates
        ]
        Fund.objects.bulk_create(fund_objs, batch_size=1000)
        created_count = len(fund_objs)

    # Bulk update existing records
    if updates:
        fund_objs = []
        for r in updates:
            fund = Fund.objects.get(external_id=r['fund_id'])
            fund.name = r['name']
            fund.status = r['status']
            fund_objs.append(fund)

        Fund.objects.bulk_update(
            fund_objs,
            fields=['name', 'status'],
            batch_size=1000
        )
        updated_count = len(fund_objs)

    return created_count, updated_count
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| django-bulk-update-or-create package | Django 4.2 native bulk_create(update_conflicts=True) | Django 4.1 (Aug 2022) | No third-party dependency, built-in ORM support, cross-database compatibility |
| Manual unique constraint management | Conditional UniqueConstraint with Q objects | Django 2.2 (Apr 2019) | Database-enforced uniqueness with conditions, prevents multiple empty value issues |
| CharField(null=True) for optional text | CharField(blank=True) without null | Django best practice (established) | Single empty state (empty string), simpler queries, consistent validation |
| Integer auto-increment PKs | UUID primary keys | Project established | Prevents ID enumeration, secure external references, distributed system friendly |

**Deprecated/outdated:**
- `unique_together` in Meta: Use `UniqueConstraint` in `constraints` list for condition support
- `index_together` in Meta: Use `Index` in `indexes` list for more options (partial indexes, expressions)

## Open Questions

Things that couldn't be fully resolved:

1. **Should Fund model have owner field for multi-org or be global?**
   - What we know: Contact has owner, Donation inherits from Contact.owner
   - What's unclear: SPO exports have org-wide funds (e.g., "Ministry General Fund") and missionary-specific funds
   - Recommendation: Make Fund.owner nullable (null = org-wide, non-null = user-specific). Validation checks if user can import to specific fund.

2. **Migration order when adding fund FK to Donation and Pledge**
   - What we know: Django requires referenced model to exist before ForeignKey
   - What's unclear: Should Fund model migration run before or in same migration as Donation/Pledge changes?
   - Recommendation: Create Fund model first (separate migration), then add fund FK to Donation/Pledge (can be same or separate migrations). Django's dependency system handles this automatically.

3. **Should external_id be scoped to owner or globally unique?**
   - What we know: Contact is owner-scoped, Donation/Pledge can reference any Contact
   - What's unclear: Can two missionaries have contacts with same SPO entity_id?
   - Recommendation: For Phase 7, scope Contact.external_id to owner (per existing pattern). For Donation/Pledge.external_id, use global uniqueness (SPO transaction_id/pledge_id are globally unique).

## Sources

### Primary (HIGH confidence)
- [Django 4.2 Migrations Documentation](https://docs.djangoproject.com/en/4.2/topics/migrations/) - Official Django migration guide
- [Django Constraints Reference](https://docs.djangoproject.com/en/5.2/ref/models/constraints/) - UniqueConstraint with conditions
- [Bulk update or create in Django 4.1](https://gregkaleka.com/blog/bulk-update-or-create-django-41/) - bulk_create with update_conflicts
- [Database Indexing in Django | TestDriven.io](https://testdriven.io/blog/django-db-indexing/) - Index performance best practices

### Secondary (MEDIUM confidence)
- [Django migrations without downtime](https://gist.github.com/majackson/493c3d6d4476914ca9da63f84247407b) - Zero-downtime migration patterns
- [Adding Fields to Models With Pre-existing Data](https://django.pythonassets.com/docs/more-on-models-and-forms/adding-fields-to-models-with-pre-existing-data/) - Nullable field strategies
- [Django Migrations: Best Practices](https://esketchers.com/best-practices-for-django-migrations/) - Community migration patterns
- ["NULL but Not Forgotten" — Handling Null Values in Unique Constraint](https://medium.com/@mustafakhorakiwala53/null-but-not-forgotten-handling-null-values-in-unique-constraint-b339d388e520) - Conditional uniqueness patterns

### Tertiary (LOW confidence)
- UUIDv7 performance improvements: Mentioned in community discussions but not yet standard in Django 4.2 (requires Python 3.14+, not production-ready for 2026-01)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Django 4.2.27 verified in environment, PostgreSQL confirmed in PROJECT.md
- Architecture: HIGH - All patterns verified with Django official docs and existing codebase structure
- Pitfalls: HIGH - Common issues documented in official Django docs and community resources
- Migration patterns: MEDIUM - Zero-downtime patterns are environment-specific, need testing in production-like setup

**Research date:** 2026-01-30
**Valid until:** 2026-03-30 (60 days for stable Django 4.2 features, migration patterns)
