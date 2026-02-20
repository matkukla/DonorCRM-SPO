# Phase 27: Foundation Models - Research

**Researched:** 2026-02-20
**Domain:** Django ORM model design for nonprofit gift/solicitor/import tracking
**Confidence:** HIGH

## Summary

Phase 27 creates 7 new models and updates 1 existing model to replace the current Donation/Pledge system with a Raiser's Edge-compatible Gift/RecurringGift system. This is pure infrastructure: models, migrations, and admin registration only. No API endpoints, no import logic, no UI.

The critical design decisions are: (1) switching from `DecimalField` to integer cents (`PositiveBigIntegerField`) for money fields on new models, (2) implementing junction tables (GiftCredit, RecurringGiftCredit) that carry per-credit amounts for solicitor gift splitting, (3) designing ImportBatch with SHA256 hash uniqueness per import type, and (4) adding a Solicitor model that bridges external RE data to internal User accounts.

The existing codebase provides strong patterns to follow: `TimeStampedModel` base class with UUID PKs, `TextChoices` enums for status fields, conditional `UniqueConstraint` for external IDs, and composite indexes on frequently-queried field pairs.

**Primary recommendation:** Follow existing codebase patterns exactly (TimeStampedModel, TextChoices, conditional UniqueConstraints, db_table naming) while introducing integer cents for all new money fields. Keep the old Donation/Pledge models untouched -- Phase 30 handles migration.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- PrayerIntention.contact is required (not nullable) -- every prayer intention must be tied to a donor contact
- Gift.donor_contact is required (not nullable) -- every gift must link to a Contact; imports must match or create the contact first
- ImportBatch should track ALL import types (RE, generic CSV, Smartsheet) -- it is the universal import tracking model

### Claude's Discretion
Claude has broad flexibility on this phase since it is pure infrastructure. Key discretion areas:
- Whether to replace ImportRun or coexist: based on codebase analysis
- Error storage pattern (separate table vs JSON field): based on query patterns and data volume
- Summary storage (JSON field vs integer columns): based on codebase patterns
- Whether GiftCredits are required on a Gift: based on how RE data works
- Solicitor delete behavior on GiftCredits: pick the safest approach
- RecurringGift status values: based on RE export data and existing Pledge statuses
- RecurringGift frequency format: based on what RE exports provide
- Contact address field granularity: based on RE constituent export format
- PrayerIntention status timestamps (answered_at, archived_at): based on display usefulness

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODEL-01 | Gift model with externalGiftId, donorContact FK, solicitor credit support, cents-based amounts | Codebase patterns for TimeStampedModel, FK design, conditional UniqueConstraint; research on PositiveBigIntegerField for cents; RE gift export field analysis |
| MODEL-02 | GiftCredit junction model linking Gift to Solicitor with per-credit amount | RE solicitor credit research showing multi-row gift splitting pattern; Django through-table patterns with extra fields |
| MODEL-03 | RecurringGift model with installment fields, status tracking, externalGiftId | Existing Pledge model as template; RE recurring gift installment frequency research; TextChoices enum patterns |
| MODEL-04 | RecurringGiftCredit junction model linking RecurringGift to Solicitor | Same pattern as GiftCredit; mirrors RE gift/solicitor structure |
| MODEL-05 | Solicitor model with normalized name matching and auto-linking to User | RE solicitor export format ("Last, First"); Django OneToOneField pattern; name normalization research |
| MODEL-06 | ImportBatch model with SHA256 file dedup, status tracking, summary JSON | Existing ImportRun model analysis; SHA256 uniqueness constraint pattern; JSON vs integer column tradeoffs |
| MODEL-07 | PrayerIntention model tied to Contact with status tracking | Existing model patterns; TextChoices for status; nullable FK to Gift for auto-creation from RE descriptions |
| MODEL-08 | Contact model updated with externalConstituentId, organizationName, address fields | Existing Contact model analysis; RE constituent export fields; address field already exists -- only need external_constituent_id and organization_name |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 | ORM, migrations, admin | Already in project |
| PostgreSQL | 15 | Database engine | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-extensions | 3.2 | `show_urls`, `shell_plus` for model testing | Already installed, use for verification |
| factory-boy | 3.3 | Test factories for new models | Already installed, create factories for each new model |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PositiveBigIntegerField (cents) | DecimalField(max_digits=10, decimal_places=2) | Existing models use DecimalField; cents avoid floating-point entirely but require conversion in serializers. Requirements specify cents. |
| JSONField for ImportBatch summary | Integer columns (created_count, updated_count, etc.) | Existing ImportRun uses integer columns. JSON is more flexible for varying import types. Recommend: keep integer columns for core counts, add JSON for type-specific metadata. |
| Replacing ImportRun with ImportBatch | Coexistence | ImportRun is referenced by existing import services, views, admin, tasks. Replacing would break Phase 28+ pipeline work. Recommend: add ImportBatch as NEW model, coexist with ImportRun until Phase 30 migration. |

**Installation:** No new packages needed. All dependencies already in requirements/base.txt.

## Architecture Patterns

### Recommended Model Placement

New models go into their most logical existing app or a new app:

```
apps/
├── gifts/                    # NEW APP for Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Solicitor
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py             # Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Solicitor
│   ├── admin.py              # Admin registration for all models
│   └── migrations/
│       └── 0001_initial.py   # Generated by makemigrations
├── imports/
│   ├── models.py             # ADD ImportBatch model (coexist with ImportRun)
│   └── migrations/
│       └── 0003_importbatch.py
├── contacts/
│   ├── models.py             # ADD external_constituent_id, organization_name fields
│   └── migrations/
│       └── 0006_add_constituent_and_org_fields.py
└── prayers/                  # NEW APP for PrayerIntention
    ├── __init__.py
    ├── apps.py
    ├── models.py             # PrayerIntention
    ├── admin.py
    └── migrations/
        └── 0001_initial.py
```

**Rationale for new `gifts` app instead of extending `donations`:**
- Clean separation: Gift/RecurringGift are fundamentally different models (cents vs decimal, solicitor credits, different FK patterns)
- Avoids conflicts: Phase 30 will migrate data from Donation to Gift; keeping them in separate apps avoids circular dependencies
- Follows existing pattern: `donations` and `pledges` are already separate apps

**Rationale for new `prayers` app instead of putting in `contacts`:**
- Follows existing pattern: each domain concept has its own app (journals, tasks, events, etc.)
- Future phases (33) will add views, serializers, URLs -- better to have a clean app structure

### Pattern 1: Money in Integer Cents

**What:** Store all money fields as `PositiveBigIntegerField` representing cents.
**When to use:** All new money fields in Gift, GiftCredit, RecurringGift, RecurringGiftCredit models.
**Why:** Requirements specify cents-based amounts. Eliminates floating-point issues. Aligns with Stripe and industry standard for payment systems.

```python
# Source: PROJECT.md constraint + Django docs
class Gift(TimeStampedModel):
    amount_cents = models.PositiveBigIntegerField(
        'amount (cents)',
        help_text='Gift amount in cents (e.g., 10000 = $100.00)'
    )

    @property
    def amount_dollars(self):
        """Return amount as Decimal dollars for display."""
        from decimal import Decimal
        return Decimal(self.amount_cents) / Decimal(100)
```

**CRITICAL NOTE:** The existing Donation.amount and Pledge.amount use `DecimalField(max_digits=10, decimal_places=2)`. The new Gift/RecurringGift models use integer cents. This means:
- Phase 30 (data migration) will need to convert `Decimal('100.00')` to `10000` cents
- Serializers in later phases must convert cents to dollars for API responses
- Dashboard queries in Phase 31 must use cents consistently

### Pattern 2: Junction Table with Extra Fields (Gift Credits)

**What:** Many-to-many relationship between Gift and Solicitor with per-credit amount.
**When to use:** GiftCredit and RecurringGiftCredit models.
**Why:** RE exports show that a single gift can be credited to multiple solicitors with different amounts (split credit).

```python
class GiftCredit(TimeStampedModel):
    """Links a Gift to a Solicitor with a per-credit amount."""
    gift = models.ForeignKey(
        'Gift',
        on_delete=models.CASCADE,
        related_name='credits',
        db_index=True
    )
    solicitor = models.ForeignKey(
        'Solicitor',
        on_delete=models.PROTECT,  # Don't delete solicitor if credits exist
        related_name='gift_credits',
        db_index=True
    )
    amount_cents = models.PositiveBigIntegerField(
        'credit amount (cents)',
        help_text='Amount credited to this solicitor in cents'
    )

    class Meta:
        db_table = 'gift_credits'
        unique_together = [['gift', 'solicitor']]
```

**Key design decisions:**
- `on_delete=models.PROTECT` for solicitor FK: safest approach -- prevents accidental deletion of solicitors with credit history
- GiftCredits are NOT required on a Gift: RE data shows gifts can exist without solicitor credits (e.g., anonymous or unsolicited gifts)
- `unique_together` prevents duplicate credit entries for same gift+solicitor pair

### Pattern 3: External ID with Conditional UniqueConstraint

**What:** External system IDs that are unique only when non-empty.
**When to use:** external_gift_id, external_solicitor_id, external_constituent_id fields.
**Why:** Existing codebase pattern on Contact.external_id and Donation.external_id.

```python
# Source: apps/contacts/models.py (existing pattern)
external_gift_id = models.CharField(
    'external gift ID',
    max_length=100,
    blank=True,
    db_index=True,
    help_text='Gift ID from Raiser\'s Edge or external system'
)

# In Meta.constraints:
models.UniqueConstraint(
    fields=['external_gift_id'],
    name='unique_external_gift_id',
    condition=~models.Q(external_gift_id='')
)
```

### Pattern 4: SHA256 Import Deduplication

**What:** ImportBatch uses SHA256 hash of file content, unique per import type.
**When to use:** ImportBatch model for file deduplication (IMP-05).
**Why:** Re-uploading the same file should return cached result without reprocessing.

```python
class ImportBatch(TimeStampedModel):
    import_type = models.CharField(max_length=30, choices=ImportBatchType.choices)
    sha256_hash = models.CharField(max_length=64, db_index=True)
    # ... other fields

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['import_type', 'sha256_hash'],
                name='unique_import_batch_hash_per_type'
            )
        ]
```

**Design rationale:** SHA256 is unique per (import_type + file content). The same CSV file uploaded as "constituents" and "gifts" should be allowed (different import types). But uploading the same file twice for the same type should be caught.

### Pattern 5: Solicitor with Optional User Link

**What:** Solicitor model that may or may not map to a DonorCRM User.
**When to use:** Solicitor model (MODEL-05).
**Why:** RE exports include solicitor names that may not correspond to existing app users. Auto-linking happens during import (Phase 28), but the model must support both linked and unlinked states.

```python
class Solicitor(TimeStampedModel):
    normalized_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text='Normalized "last, first" for matching'
    )
    user = models.OneToOneField(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitor_profile',
        help_text='Linked DonorCRM user account (auto-detected or manual)'
    )
    external_solicitor_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text='Solicitor ID from Raiser\'s Edge'
    )
```

**Key decisions:**
- `OneToOneField` to User (not ForeignKey): one solicitor maps to at most one user
- `on_delete=SET_NULL`: if User is deleted, solicitor record persists (historical credit data)
- `normalized_name` format: "Last, First" to match RE export convention (confirmed by research)

### Anti-Patterns to Avoid

- **Don't modify existing Donation/Pledge models:** Phase 30 handles migration. Phase 27 only adds NEW models.
- **Don't create API endpoints or serializers:** Phase 27 is models only. Phase 28+ adds API.
- **Don't use DecimalField for new money fields:** Requirements specify cents-based amounts on new models. Use `PositiveBigIntegerField`.
- **Don't replace ImportRun:** Coexist with new ImportBatch. ImportRun is still used by existing import services until Phase 28 rewrites them.
- **Don't add `amount_cents` to existing Contact stats:** Contact.total_given remains `DecimalField` until Phase 30 (MIG-03) updates it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID primary keys | Custom UUID generation | `TimeStampedModel` base class (apps/core/models.py) | Already provides UUID PK + created_at + updated_at |
| Enum field choices | Raw string constants | `models.TextChoices` subclass | Type-safe, display labels, validated by Django |
| External ID uniqueness | Application-level dedup checks | `UniqueConstraint` with `condition` | Database-level enforcement, existing pattern |
| Many-to-many with extra fields | Custom intermediary queries | Django explicit through-table (GiftCredit model) | ORM support for prefetch, admin inline, clean API |

**Key insight:** This phase is model-only infrastructure. Resist the urge to build helper methods, property calculations, or business logic beyond basic `__str__` and `Meta` configuration. Keep models lean -- business logic belongs in services (Phase 28+).

## Common Pitfalls

### Pitfall 1: Circular Migration Dependencies
**What goes wrong:** New `gifts` app references `contacts.Contact` and `imports.Fund`; if Contact migration also references Gift, circular dependency breaks `makemigrations`.
**Why it happens:** Django migration system resolves dependencies between apps; circular references create unresolvable chains.
**How to avoid:** New models reference existing models (one-way). Contact model changes (adding fields) go in a separate migration that doesn't reference the new `gifts` app.
**Warning signs:** `makemigrations` error: "Circular dependency detected."

### Pitfall 2: Forgetting to Register in INSTALLED_APPS
**What goes wrong:** New `gifts` and `prayers` apps are created but `makemigrations` doesn't detect them.
**Why it happens:** Django only discovers models from apps listed in `INSTALLED_APPS`.
**How to avoid:** Add `'apps.gifts'` and `'apps.prayers'` to `LOCAL_APPS` in `config/settings/base.py` BEFORE running `makemigrations`.
**Warning signs:** `makemigrations` says "No changes detected."

### Pitfall 3: Money Field Inconsistency Between Old and New Models
**What goes wrong:** Dashboard queries join Gift (cents) with Contact.total_given (decimal dollars), producing wildly wrong totals.
**Why it happens:** Phase 27 introduces cents-based fields while existing models use `DecimalField`.
**How to avoid:** Phase 27 only creates models. Phase 30 migrates data and updates Contact stats. Until then, old and new models are completely independent -- no cross-queries.
**Warning signs:** Numbers that are 100x too large or too small.

### Pitfall 4: Conditional UniqueConstraint on CharField Blank vs Empty
**What goes wrong:** `UniqueConstraint` with `condition=~models.Q(field='')` doesn't catch null values.
**Why it happens:** `blank=True` allows empty string, but if field is also `null=True`, NULL values bypass the constraint entirely.
**How to avoid:** Use `blank=True` WITHOUT `null=True` for CharField external IDs (matching existing Contact.external_id pattern). Django stores empty strings as `''`, not NULL.
**Warning signs:** Duplicate external IDs in database despite constraint.

### Pitfall 5: Admin Registration with Missing Model Imports
**What goes wrong:** Admin site throws `ImproperlyConfigured` because new models aren't imported.
**Why it happens:** Forgot to update admin.py with new model imports after creating models.
**How to avoid:** Create admin.py registrations immediately after model creation. Follow existing pattern in `apps/imports/admin.py`.
**Warning signs:** 500 error on Django admin.

### Pitfall 6: ImportBatch vs ImportRun Confusion
**What goes wrong:** Trying to use ImportBatch in existing import views that expect ImportRun.
**Why it happens:** Both models track imports but have different schemas and purposes.
**How to avoid:** ImportBatch is NEW and COEXISTS with ImportRun. Phase 28 will wire ImportBatch into the new RE import pipeline. Existing SPO imports continue using ImportRun until Phase 28 migration.
**Warning signs:** AttributeError on missing fields when mixing models.

## Code Examples

### Complete Gift Model

```python
from django.db import models
from apps.core.models import TimeStampedModel


class Gift(TimeStampedModel):
    """
    Individual gift record linked to a donor contact.
    Replaces Donation model with cents-based amounts and solicitor credit support.
    """
    # Link to donor (required)
    donor_contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        related_name='gifts',
        db_index=True,
        help_text='Donor who made this gift'
    )

    # Link to fund
    fund = models.ForeignKey(
        'imports.Fund',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gifts',
        help_text='Fund/account this gift is attributed to'
    )

    # External ID for idempotent imports
    external_gift_id = models.CharField(
        'external gift ID',
        max_length=100,
        blank=True,
        db_index=True,
        help_text='Gift ID from Raiser\'s Edge or external system'
    )

    # Gift details (cents-based)
    amount_cents = models.PositiveBigIntegerField(
        'amount (cents)',
        help_text='Gift amount in cents (e.g., 10000 = $100.00)'
    )
    gift_date = models.DateField('gift date', db_index=True)
    description = models.TextField('description', blank=True)

    class Meta:
        db_table = 'gifts'
        verbose_name = 'gift'
        verbose_name_plural = 'gifts'
        ordering = ['-gift_date', '-created_at']
        indexes = [
            models.Index(fields=['donor_contact', 'gift_date']),
            models.Index(fields=['gift_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['external_gift_id'],
                name='unique_external_gift_id',
                condition=~models.Q(external_gift_id='')
            )
        ]

    def __str__(self):
        dollars = self.amount_cents / 100
        return f'${dollars:.2f} from {self.donor_contact} on {self.gift_date}'
```

### Complete ImportBatch Model

```python
class ImportBatchType(models.TextChoices):
    """Types of imports tracked by ImportBatch."""
    RE_CONSTITUENT = 're_constituent', 'RE Constituent'
    RE_SOLICITOR = 're_solicitor', 'RE Solicitor'
    RE_GIFT = 're_gift', 'RE Gift'
    RE_RECURRING_GIFT = 're_recurring_gift', 'RE Recurring Gift'
    GENERIC_CONTACTS = 'generic_contacts', 'Generic Contacts'
    GENERIC_DONATIONS = 'generic_donations', 'Generic Donations'
    SMARTSHEET_MPD = 'smartsheet_mpd', 'Smartsheet MPD'


class ImportBatchStatus(models.TextChoices):
    """Processing status for import batches."""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    DUPLICATE = 'duplicate', 'Duplicate (already processed)'


class ImportBatch(TimeStampedModel):
    """
    Universal import tracking model with SHA256 file deduplication.
    Replaces ImportRun for new v2.0 import pipeline.
    """
    import_type = models.CharField(
        'import type',
        max_length=30,
        choices=ImportBatchType.choices,
        db_index=True
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=ImportBatchStatus.choices,
        default=ImportBatchStatus.PENDING
    )

    # File metadata
    filename = models.CharField('filename', max_length=255)
    sha256_hash = models.CharField(
        'SHA256 hash',
        max_length=64,
        db_index=True,
        help_text='SHA256 hash of file content for deduplication'
    )

    # Result counts (integer columns, matching existing ImportRun pattern)
    total_rows = models.PositiveIntegerField('total rows', default=0)
    created_count = models.PositiveIntegerField('created count', default=0)
    updated_count = models.PositiveIntegerField('updated count', default=0)
    skipped_count = models.PositiveIntegerField('skipped count', default=0)
    error_count = models.PositiveIntegerField('error count', default=0)

    # Summary (JSON for type-specific metadata)
    summary = models.JSONField(
        'summary',
        default=dict,
        blank=True,
        help_text='Type-specific import summary metadata'
    )

    # User tracking
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='import_batches',
        verbose_name='uploaded by'
    )

    class Meta:
        db_table = 'import_batches'
        verbose_name = 'import batch'
        verbose_name_plural = 'import batches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uploaded_by', '-created_at']),
            models.Index(fields=['import_type', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['import_type', 'sha256_hash'],
                name='unique_import_batch_hash_per_type'
            )
        ]

    def __str__(self):
        return f'{self.get_import_type_display()} by {self.uploaded_by} ({self.status})'
```

### PrayerIntention Model

```python
class PrayerIntentionStatus(models.TextChoices):
    """Status of a prayer intention."""
    ACTIVE = 'active', 'Active'
    ANSWERED = 'answered', 'Answered'
    ARCHIVED = 'archived', 'Archived'


class PrayerIntention(TimeStampedModel):
    """
    Prayer intention tied to a donor contact.
    Can be manually created or auto-created from RE gift descriptions.
    """
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        related_name='prayer_intentions',
        db_index=True,
        help_text='Contact this prayer intention is for (required)'
    )

    # Optional link to gift (auto-created from RE gift description)
    gift = models.ForeignKey(
        'gifts.Gift',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prayer_intentions',
        help_text='Gift that prompted this prayer intention (if auto-created from import)'
    )

    title = models.CharField('title', max_length=255)
    description = models.TextField('description', blank=True)

    status = models.CharField(
        'status',
        max_length=20,
        choices=PrayerIntentionStatus.choices,
        default=PrayerIntentionStatus.ACTIVE,
        db_index=True
    )

    # Status timestamps for display usefulness
    answered_at = models.DateTimeField('answered at', null=True, blank=True)
    archived_at = models.DateTimeField('archived at', null=True, blank=True)

    class Meta:
        db_table = 'prayer_intentions'
        verbose_name = 'prayer intention'
        verbose_name_plural = 'prayer intentions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contact', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f'{self.title} ({self.contact})'
```

## Discretion Decisions (Researcher Recommendations)

### ImportBatch vs ImportRun: COEXIST

**Recommendation:** Add ImportBatch as a NEW model in `apps/imports/models.py`. Do NOT replace or modify ImportRun.

**Rationale:**
- ImportRun is actively used by `apps/imports/services.py` (6 import functions reference it), `apps/imports/views.py`, `apps/imports/admin.py`, and `apps/imports/tasks.py`
- Replacing it would break all existing import functionality before Phase 28 can rewrite it
- Coexistence allows Phase 28 to gradually migrate import pipelines from ImportRun to ImportBatch
- After Phase 30 migration completes, ImportRun can be removed as dead code

### Error Storage: Reuse ImportRowError Model Pattern

**Recommendation:** ImportBatch should work with a new `ImportBatchError` model (same pattern as ImportRowError) rather than storing errors in a JSON field.

**Rationale:**
- Existing `ImportRowError` has proven the separate-table pattern works well (row_number, error_messages JSON, row_data JSON)
- JSON field for errors would grow unbounded and make querying by row number slow
- Separate table allows pagination of errors in the UI (Phase 32)
- HOWEVER: for Phase 27, just create the ImportBatch model. The error model can be added in Phase 28 when the import pipeline is built (keeping Phase 27 scope focused on the 7+1 models required)

### Summary Storage: Hybrid (Integer Columns + JSON)

**Recommendation:** Use integer columns for universal counts (total_rows, created_count, updated_count, skipped_count, error_count) PLUS a JSON field for type-specific metadata.

**Rationale:**
- Integer columns enable efficient aggregation queries across batches (SUM, AVG)
- Existing ImportRun uses integer columns -- consistency
- JSON field provides flexibility for type-specific data (e.g., RE-specific stats, solicitor match counts)
- Best of both worlds: structured data for common queries, flexible data for edge cases

### GiftCredits: NOT Required on a Gift

**Recommendation:** GiftCredits should be optional. A Gift can exist without any GiftCredit records.

**Rationale:**
- RE exports show that not all gifts have solicitor credits (unsolicited gifts, anonymous gifts)
- Making credits required would break import for gifts without solicitors
- The credit splitting is additive: if solicitors exist, create GiftCredit records; if not, the Gift stands alone
- This matches the RE data model where the GiftSolicitor table is a separate, optional join

### Solicitor Delete Behavior: PROTECT

**Recommendation:** Use `on_delete=models.PROTECT` for Solicitor FK on GiftCredit/RecurringGiftCredit.

**Rationale:**
- Safest approach: prevents accidental deletion of solicitors who have historical credit data
- Credit records are important audit trail for fundraising attribution
- If a solicitor needs to be "deactivated", they can be soft-deleted or marked inactive (future feature) rather than hard-deleted
- This matches the existing pattern of PROTECT on owner FKs throughout the codebase

### RecurringGift Status Values

**Recommendation:** Use the same status choices as existing Pledge model: `active`, `paused`, `completed`, `cancelled` PLUS add `terminated` for RE-specific status.

```python
class RecurringGiftStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    HELD = 'held', 'Held'          # RE uses "Held" instead of "Paused"
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    TERMINATED = 'terminated', 'Terminated'  # RE-specific
```

**Rationale:**
- RE exports use statuses: Active, Held, Completed, Cancelled, Terminated
- "Held" is RE's equivalent of "Paused" -- use RE terminology since this is the RE-compatible model
- "Terminated" is distinct from "Cancelled" in RE (terminated = system-ended vs cancelled = user-ended)
- This gives Phase 28 import direct mapping from RE CSV values

### RecurringGift Frequency Format

**Recommendation:** Use string choices matching RE export values:

```python
class RecurringGiftFrequency(models.TextChoices):
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'
    SEMI_ANNUALLY = 'semi_annually', 'Semi-Annually'
    ANNUALLY = 'annually', 'Annually'
    BIMONTHLY = 'bimonthly', 'Bimonthly'      # RE supports this
    BIWEEKLY = 'biweekly', 'Biweekly'          # RE supports this
    WEEKLY = 'weekly', 'Weekly'                  # RE supports this
    IRREGULAR = 'irregular', 'Irregular'         # For non-standard schedules
```

**Rationale:**
- RE supports more frequencies than the existing Pledge model (which only has monthly, quarterly, semi_annual, annual)
- Adding bimonthly, biweekly, weekly, and irregular covers the full RE export range
- `semi_annually` (not `semi_annual`) to match RE export convention
- Existing Pledge model is NOT changed -- these choices are only for the new RecurringGift model

### Contact Address Fields: Minimal Addition

**Recommendation:** Contact already has `street_address`, `city`, `state`, `postal_code`, `country`. Only add `external_constituent_id` and `organization_name`.

**Rationale:**
- RE constituent exports have address fields that map directly to existing Contact fields
- No need for `address_line_2` or `county` -- RE exports typically concatenate into a single address
- `external_constituent_id` parallels existing `external_id` but is specifically for RE Constituent IDs
- `organization_name` is needed because RE has both individual and organization constituent types

**Implementation note:** `external_constituent_id` could potentially REPLACE `external_id` on Contact, but safer to ADD a new field. The existing `external_id` is used by SPO imports; `external_constituent_id` is for RE imports. Phase 28 can decide whether to unify them.

### PrayerIntention Timestamps: Include Both

**Recommendation:** Include `answered_at` and `archived_at` timestamp fields in addition to the status field.

**Rationale:**
- "When was this prayer answered?" is a meaningful display metric for missionaries
- Timestamps enable filtering by date answered/archived
- Minimal cost (two nullable DateTimeField columns)
- Follows existing codebase pattern: `Journal.archived_at`, `NextStep.completed_at`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DecimalField for money | Integer cents (PositiveBigIntegerField) | Industry standard since Stripe | Eliminates floating-point issues; requires serializer conversion |
| `unique=True` on external_id | `UniqueConstraint` with condition | Django 2.2+ | Allows blank values while enforcing uniqueness on non-blank |
| `unique_together` in Meta | `UniqueConstraint` in Meta.constraints | Django 2.2+ | More expressive, supports conditions |
| ForeignKey for M2M with data | Explicit through-table model | Always Django best practice | Required when junction table has extra fields (amount_cents) |

**Deprecated/outdated:**
- `unique_together`: Still works but `UniqueConstraint` is preferred (more flexible)
- `models.BooleanField(null=True)`: Not deprecated, but avoid for new models -- use `TextChoices` status instead

## Open Questions

1. **Should `external_constituent_id` replace `external_id` on Contact?**
   - What we know: `external_id` is currently used by SPO imports for entity matching
   - What's unclear: Whether RE constituent IDs will be stored in the same field or a separate one
   - Recommendation: Add `external_constituent_id` as a NEW field. Let Phase 28 decide if they should be unified. Lower risk approach.

2. **Should RecurringGift have `installment_amount_cents` separate from base `amount_cents`?**
   - What we know: RE recurring gifts have both a base amount and an installment amount (e.g., $100/month pledge = $100 installment, $1200 total)
   - What's unclear: Whether the total pledge amount is relevant for DonorCRM's use case
   - Recommendation: Store `amount_cents` as the per-installment amount (what the donor gives each period). This matches the existing Pledge.amount pattern and is what users care about for monthly support tracking.

3. **ImportBatch error storage model -- include in Phase 27?**
   - What we know: Phase 27 scope is the 7+1 models listed in requirements
   - What's unclear: Whether ImportBatchError should be created now or in Phase 28
   - Recommendation: Defer ImportBatchError to Phase 28 when the import pipeline is built. Phase 27 creates ImportBatch with the `error_count` integer field and `summary` JSON field, which is sufficient for the model definition.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `apps/core/models.py` -- TimeStampedModel pattern
- Existing codebase: `apps/contacts/models.py` -- Contact fields, external_id pattern, conditional UniqueConstraint
- Existing codebase: `apps/donations/models.py` -- Donation model structure, FK patterns
- Existing codebase: `apps/pledges/models.py` -- Pledge model, frequency/status TextChoices, installment fields
- Existing codebase: `apps/imports/models.py` -- ImportRun, ImportRowError, Fund models
- Existing codebase: `apps/journals/models.py` -- Junction table patterns (JournalContact), through-table design
- Existing codebase: `config/settings/base.py` -- INSTALLED_APPS, LOCAL_APPS
- Existing codebase: `.planning/PROJECT.md` -- v2.0 decisions, cents for money, UUID PKs
- Existing codebase: `.planning/REQUIREMENTS.md` -- MODEL-01 through MODEL-08 specifications
- Existing codebase: `.planning/STATE.md` -- v2.0 key decision: REPLACE Donation/Pledge with Gift/RecurringGift

### Secondary (MEDIUM confidence)
- [Django docs: Model field reference](https://docs.djangoproject.com/en/5.0/ref/models/fields/) -- PositiveBigIntegerField, UniqueConstraint
- [RE NXT Gift IDs and Batch](https://support.omaticsoftware.com/s/article/Gift-IDs-and-Batch-in-Raiser-s-Edge-NXT) -- Gift ID uniqueness in RE
- [RE Split Gift Export feature request](https://renxt.ideas.aha.io/ideas/RENXT-I-8179) -- Multi-row gift export pattern
- [Omatic Blog: Importing Pledge and Installment Information](https://omaticsoftware.com/blog/importing-pledge-and-installment-information-in-the-raisers-edge/) -- RE pledge/recurring gift field structure
- [RE7 Feature Request: Gift Instalment Frequency](https://re7.ideas.aha.io/ideas/RE7-I-5192) -- RE frequency field behavior
- [django-money: Storing money as cents](https://github.com/django-money/django-money/issues/552) -- Industry discussion on cents vs decimal

### Tertiary (LOW confidence)
- RE recurring gift status values: Based on RE documentation references across multiple sources. Exact status string values should be validated against actual RE CSV exports during Phase 28 development.
- RE solicitor name format ("Last, First"): Based on common RE convention but installation-specific. STATE.md already flags this as a concern to confirm before Phase 28 ships.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- using only existing project dependencies
- Architecture: HIGH -- patterns directly derived from existing codebase analysis
- Model design: HIGH -- requirements are specific, codebase patterns are clear
- RE data format: MEDIUM -- based on web research of RE export formats; actual CSV column headers will be confirmed in Phase 28
- Pitfalls: HIGH -- identified from real codebase patterns and Django ORM known issues

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (stable -- model design is framework-level, not fast-moving)
