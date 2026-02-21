# Phase 30: Data Migration & Backend Cutover - Research

**Researched:** 2026-02-20
**Domain:** Django data migration, model replacement, backend service refactoring
**Confidence:** HIGH

## Summary

Phase 30 migrates all existing Donation records to Gift and all existing Pledge records to RecurringGift, then rewires every backend service, view, serializer, filter, signal, Celery task, and URL endpoint to query the new models exclusively. Finally, the old Donation and Pledge models (including their Django apps) are removed from the codebase.

This is the most structurally impactful phase in v2.0. The Donation and Pledge models are referenced across 40+ files spanning 8 Django apps (donations, pledges, contacts, dashboard, insights, imports, users, events). The migration itself is straightforward -- both old and new models inherit from `TimeStampedModel` with UUID PKs, and the field mappings are deterministic. The challenge is the breadth of the cutover: every query, serializer, filter, signal, export view, Celery task, management command, URL route, and admin registration that touches Donation or Pledge must be updated.

Key architectural difference: old models use `DecimalField` for money, new models use `PositiveBigIntegerField` (cents). The migration must multiply amounts by 100 and round. The new Gift model is leaner than Donation (no `donation_type`, `payment_method`, `thanked`, `thanked_at`, `thanked_by`, `imported_at`, `import_batch` fields), and RecurringGift is leaner than Pledge (no `last_fulfilled_date`, `next_expected_date`, `total_expected`, `total_received`, `is_late`, `days_late`, `late_notified_at` fields). Features depending on removed fields (thank-you tracking, late pledge detection, pledge fulfillment) must be addressed or deferred.

**Primary recommendation:** Execute in three discrete plans: (1) data migration script with verification, (2) backend service cutover for all query/write paths, (3) old model removal and cleanup. Each plan must preserve all existing test coverage.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MIG-01 | Migrate existing Donation records to Gift model with field mapping and UUID preservation | Field-by-field mapping documented below; UUID PK preservation confirmed via TimeStampedModel; amount conversion from Decimal to cents is deterministic (multiply by 100) |
| MIG-02 | Migrate existing Pledge records to RecurringGift model | Field-by-field mapping documented below; frequency/status enum value mapping is direct for shared values; Pledge has 4 frequencies vs RecurringGift has 8 -- all 4 old values exist in new enum |
| MIG-03 | Update Contact stats (totalGiven, lastGiftDate, lastGiftAmount) to query Gift model | Contact.update_giving_stats() currently queries `self.donations` -- must change to `self.gifts`; amount conversion from cents to Decimal needed for display fields |
| MIG-04 | Remove old Donation and Pledge models after migration verification | Complete app removal: models, views, serializers, filters, admin, signals, urls, tasks, export_views, factories, tests across apps/donations/ and apps/pledges/ directories |
| MIG-05 | Update all backend services (dashboard, insights, analytics) to use Gift/RecurringGift | 13 service functions in insights/services.py query Donation; 8 service functions in dashboard/services.py query Donation/Pledge; contacts/views.py has ContactDonationsView and ContactPledgesView; users/views.py and users/serializers.py query Pledge for active_pledge_count |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 | ORM, migrations, data migration framework | Already in project; `RunPython` in migration files is the standard approach |
| PostgreSQL | 15 | Database engine | Already in project; raw SQL for bulk data migration if needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-filter | 24.3 | FilterSet classes for new gift/recurring_gift endpoints | Already in project; must use 24.3 (not 25.2) per project constraints |
| factory-boy | 3.3 | Test factories for Gift/RecurringGift | Already installed; new factories needed to replace DonationFactory/PledgeFactory |
| drf-spectacular | 0.27 | API schema for new endpoints | Already in project; schema tags need updating |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Django RunPython migration | Management command | RunPython is atomic, reversible, and part of migration chain; management command runs outside migration framework. Use RunPython for the actual data copy. |
| Incremental service-by-service cutover | Big-bang all-at-once | Incremental is safer for production but this is a dev environment with no live data. Big-bang within a single plan is cleaner for this project. |

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Execution Order

```
Plan 1: Data Migration
  Task 1: Write Django data migration (Donation -> Gift, Pledge -> RecurringGift)
  Task 2: Write verification management command, run migration, verify counts

Plan 2: Backend Cutover (all services switch to Gift/RecurringGift)
  Task 1: Rewrite all service functions, views, serializers, filters, signals, tasks, exports
  Task 2: Update URL routes, admin, Contact model properties, user serializers

Plan 3: Old Model Removal
  Task 1: Remove apps/donations/ and apps/pledges/ directories and all references
  Task 2: Update settings, URL config, Celery beat, and run final verification
```

### Pattern 1: Data Migration via RunPython

**What:** Django data migration that copies Donation rows to Gift rows and Pledge rows to RecurringGift rows.
**When to use:** For the actual data transfer in MIG-01 and MIG-02.
**Key details:**

```python
# In a new migration file in apps/gifts/migrations/
from django.db import migrations

def migrate_donations_to_gifts(apps, schema_editor):
    Donation = apps.get_model('donations', 'Donation')
    Gift = apps.get_model('gifts', 'Gift')

    gifts_to_create = []
    for d in Donation.objects.all().iterator():
        gifts_to_create.append(Gift(
            id=d.id,  # Preserve UUID
            donor_contact_id=d.contact_id,
            fund_id=d.fund_id,
            external_gift_id=d.external_id,
            amount_cents=int(d.amount * 100),
            gift_date=d.date,
            description=d.notes,
            created_at=d.created_at,
            updated_at=d.updated_at,
        ))
    Gift.objects.bulk_create(gifts_to_create, batch_size=1000, ignore_conflicts=True)

class Migration(migrations.Migration):
    dependencies = [...]
    operations = [
        migrations.RunPython(migrate_donations_to_gifts, migrations.RunPython.noop),
    ]
```

### Pattern 2: Service Function Rewrite Pattern

**What:** Every service function querying Donation must switch to Gift with cents-to-dollars conversion.
**When to use:** For MIG-05 cutover of insights/services.py and dashboard/services.py.
**Key details:**

```python
# OLD: insights/services.py
def _scope_donations(user):
    if user.role in ['admin', 'finance', 'read_only']:
        return Donation.objects.all()
    return Donation.objects.filter(contact__owner=user)

# NEW: Replace with Gift model
def _scope_gifts(user):
    if user.role in ['admin', 'finance', 'read_only']:
        return Gift.objects.all()
    return Gift.objects.filter(donor_contact__owner=user)

# IMPORTANT: All Sum('amount') must become Sum('amount_cents') / 100
# Use ExpressionWrapper or post-query conversion
```

### Pattern 3: Contact Stats Recalculation

**What:** Contact.update_giving_stats() must query Gift instead of Donation.
**When to use:** For MIG-03.
**Key details:**

```python
# OLD: self.donations.all()
# NEW: self.gifts.all()
# amount field: Gift.amount_cents (integer) -> need Decimal conversion
gifts = self.gifts.all()
agg = gifts.aggregate(
    total_cents=Sum('amount_cents'),
    count=Count('id'),
    first=Min('gift_date'),
    last=Max('gift_date')
)
self.total_given = Decimal(agg['total_cents'] or 0) / Decimal(100)
self.gift_count = agg['count'] or 0
self.first_gift_date = agg['first']
self.last_gift_date = agg['last']
if agg['last']:
    last_gift = gifts.order_by('-gift_date').first()
    self.last_gift_amount = Decimal(last_gift.amount_cents) / Decimal(100)
```

### Anti-Patterns to Avoid
- **Partial cutover:** Do NOT have some services querying Gift and others still querying Donation. This creates inconsistent data during the transition. All services must switch in the same plan.
- **Forgetting cents conversion:** Every place that previously returned `donation.amount` (Decimal) must now return `gift.amount_cents / 100` or use the `amount_dollars` property. Forgetting this produces 100x inflation in displayed values.
- **Breaking UUID preservation:** The migration MUST preserve UUIDs. If any existing frontend bookmarks, API responses, or cross-model references use Donation UUIDs, those must continue to work with the same UUID now pointing to a Gift.
- **Deleting old tables before verification:** Always verify row counts, total amounts, and sample spot-checks before removing old models.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data migration | Custom script outside Django | `RunPython` in migration | Atomic, reversible, part of migration chain |
| Bulk data copy | Row-by-row ORM create | `bulk_create` with `batch_size` | Orders of magnitude faster for thousands of rows |
| Amount conversion | Manual float arithmetic | `int(Decimal * 100)` with Decimal context | Avoids floating-point rounding errors |
| Verification | Manual spot-checks only | Programmatic count + sum comparison | Catches systematic errors that spot-checks miss |

**Key insight:** The migration is conceptually simple (copy rows with field renaming and amount * 100), but the cutover surface area is enormous. The risk is not in the migration itself but in missing one of the 40+ files that reference the old models.

## Common Pitfalls

### Pitfall 1: Decimal-to-Cents Rounding Errors
**What goes wrong:** `float(amount) * 100` introduces floating-point errors (e.g., `29.99 * 100 = 2998.9999...`).
**Why it happens:** Python float arithmetic is imprecise for base-10 fractions.
**How to avoid:** Always use `int(Decimal(amount) * 100)` where `amount` is already a `Decimal` from the DecimalField. Django's `DecimalField` returns `Decimal` objects, so `int(d.amount * 100)` is safe.
**Warning signs:** Gift amounts that are off by 1 cent after migration.

### Pitfall 2: Related Name Confusion
**What goes wrong:** Donation uses `contact` FK with `related_name='donations'`; Gift uses `donor_contact` FK with `related_name='gifts'`. Code that does `contact.donations.all()` must become `contact.gifts.all()`.
**Why it happens:** The FK field name changed from `contact` to `donor_contact`, and the related_name changed from `donations` to `gifts`.
**How to avoid:** Search for ALL occurrences of `.donations` and `contact__owner` patterns. In Gift, the FK is `donor_contact`, so owner filtering becomes `donor_contact__owner`.
**Warning signs:** `AttributeError: 'Contact' object has no attribute 'donations'` after model removal.

### Pitfall 3: Missing Service Cutover Points
**What goes wrong:** One service function still queries Donation after models are removed, causing ImportError.
**Why it happens:** Donation/Pledge are referenced in 40+ files across 8 apps. Easy to miss one.
**How to avoid:** Use comprehensive grep to find ALL `from apps.donations` and `from apps.pledges` imports before cleanup. The complete list is documented in the inventory section below.
**Warning signs:** ImportError or ModuleNotFoundError in any endpoint after Phase 30 cleanup.

### Pitfall 4: Pledge Features Lost Without Replacement
**What goes wrong:** RecurringGift lacks `is_late`, `days_late`, `last_fulfilled_date`, `next_expected_date`, `total_expected`, `total_received` fields that Pledge has. Celery tasks and dashboard services depend on these.
**Why it happens:** RecurringGift was designed as a leaner model focused on RE import data. The fulfillment tracking features were on Pledge.
**How to avoid:** The Celery task `check_late_pledges` and related dashboard widgets (`late_donations`, `support_progress`) must either be removed, deferred, or reimplemented with a different approach. These features cannot simply be ported because the underlying fields don't exist on RecurringGift.
**Warning signs:** Celery errors, dashboard widgets showing no data or errors.

### Pitfall 5: Contact Properties Still Referencing Pledges
**What goes wrong:** `Contact.has_active_pledge` and `Contact.monthly_pledge_amount` properties reference `self.pledges`.
**Why it happens:** These are convenience properties on the Contact model.
**How to avoid:** Update these properties to reference `self.recurring_gifts` and adapt to RecurringGift's schema (no `monthly_equivalent` property exists yet on RecurringGift).
**Warning signs:** AttributeError on contact detail pages.

### Pitfall 6: Signal Handlers Missing
**What goes wrong:** Donation's post_save signal (`update_contact_stats_on_save`) auto-updates Contact stats and creates Events. If removed without replacement, creating Gifts won't update Contact stats.
**Why it happens:** The signal is in `apps/donations/signals.py` and registered in `apps/donations/apps.py`.
**How to avoid:** Create equivalent signal handlers in `apps/gifts/` that trigger Contact stat recalculation when Gift objects are created/updated/deleted.
**Warning signs:** Contact.total_given stays at 0 after new gifts are added.

## Complete Inventory: Files Referencing Donation/Pledge

### apps/donations/ (ENTIRE APP TO REMOVE)
- `models.py` - Donation, DonationType, PaymentMethod
- `views.py` - DonationListCreateView, DonationDetailView, DonationThankView, DonationSummaryView, DonationByMonthView
- `serializers.py` - DonationSerializer, DonationCreateSerializer, DonationSummarySerializer, DonationImportSerializer
- `filters.py` - DonationFilterSet
- `export_views.py` - DonationExportCSVView
- `signals.py` - update_contact_stats_on_save, update_contact_stats_on_delete
- `urls.py` - 6 URL patterns
- `admin.py` - DonationAdmin
- `apps.py` - DonationsConfig
- `tests/` - factories.py (DonationFactory), test_views.py, test_models.py

### apps/pledges/ (ENTIRE APP TO REMOVE)
- `models.py` - Pledge, PledgeFrequency, PledgeStatus
- `views.py` - PledgeListCreateView, PledgeDetailView, PledgePauseView, PledgeResumeView, PledgeCancelView, LatePledgesView, PledgeSummaryView
- `serializers.py` - PledgeSerializer, PledgeCreateSerializer, PledgeSummarySerializer
- `filters.py` - PledgeFilterSet
- `export_views.py` - PledgeExportCSVView
- `signals.py` - track_pledge_status_change, handle_pledge_status_change
- `urls.py` - 8 URL patterns
- `admin.py` - PledgeAdmin
- `apps.py` - PledgesConfig
- `tasks.py` - check_late_pledges (Celery task)
- `tests/` - factories.py (PledgeFactory), test_views.py, test_models.py

### apps/contacts/ (REFERENCES TO UPDATE)
- `models.py` - `update_giving_stats()` queries `self.donations`; `has_active_pledge` and `monthly_pledge_amount` query `self.pledges`
- `views.py` - `ContactDonationsView`, `ContactPledgesView` (lines 135-177)
- `urls.py` - routes for contact-donations and contact-pledges

### apps/dashboard/ (REFERENCES TO UPDATE)
- `services.py` - imports Donation and Pledge; 8 functions reference them:
  - `get_needs_attention()` - queries late pledges
  - `get_late_donations()` - queries late pledges
  - `get_support_progress()` - queries active pledges
  - `get_recent_gifts()` - queries Donation
  - `get_giving_summary()` - queries Donation and Pledge
  - `get_monthly_gifts()` - queries Donation
  - `get_dashboard_summary()` - aggregates all above
- `views.py` - imports PledgeSerializer and DonationSerializer
- `tests/test_services.py` - imports DonationFactory and PledgeFactory

### apps/insights/ (REFERENCES TO UPDATE)
- `services.py` - imports Donation and Pledge; functions referencing them:
  - `_scope_donations()` / `_scope_pledges()` - scope helpers
  - `get_donations_by_month()` - monthly aggregation
  - `get_donations_by_year()` - yearly aggregation
  - `get_monthly_commitments()` - active pledge summary
  - `get_late_donations()` - late pledges
  - `get_transactions()` - full ledger
  - `get_dashboard_overview()` - donation summary in admin dashboard
  - `get_user_performance()` - per-user donation totals
  - `get_team_trends()` - weekly donation counts
  - `get_user_trends()` - weekly donation counts per user
  - `get_user_drilldown()` - donation stats for user panel
- `tests/` - 4 test files import DonationFactory

### apps/users/ (REFERENCES TO UPDATE)
- `views.py` - CurrentUserView queries Pledge for `_active_pledge_count` annotation
- `serializers.py` - `get_active_pledge_count()` queries Pledge

### apps/imports/ (REFERENCES TO UPDATE)
- `services.py` - imports Donation, DonationType, PaymentMethod, Pledge, PledgeFrequency, PledgeStatus for old SPO CSV import
- `views.py` - ExportDonationsView queries Donation
- `tasks.py` - import_donations_async references Donation

### apps/events/ (REFERENCES TO UPDATE)
- `models.py` - EventType has DONATION_RECEIVED, FIRST_DONATION, PLEDGE_CREATED, PLEDGE_UPDATED, PLEDGE_LATE, PLEDGE_CANCELLED

### config/ (REFERENCES TO UPDATE)
- `settings/base.py` - INSTALLED_APPS includes 'apps.donations' and 'apps.pledges'; SPECTACULAR_SETTINGS has donation/pledge tags
- `api_urls.py` - URL includes for apps.donations.urls and apps.pledges.urls
- `celery.py` - check-late-pledges-daily Celery beat schedule

### apps/core/ (REFERENCES TO UPDATE)
- `management/commands/generate_sample_data.py` - generates sample Donations and Pledges

## Field Mapping: Donation -> Gift

| Donation Field | Gift Field | Transformation |
|---------------|------------|----------------|
| `id` (UUID) | `id` (UUID) | **Preserve exactly** |
| `contact` (FK) | `donor_contact` (FK) | Same target table, different FK name |
| `fund` (FK) | `fund` (FK) | Direct copy |
| `amount` (Decimal) | `amount_cents` (BigInt) | `int(amount * 100)` |
| `date` (DateField) | `gift_date` (DateField) | Direct copy |
| `external_id` (CharField) | `external_gift_id` (CharField) | Direct copy |
| `notes` (TextField) | `description` (TextField) | Direct copy |
| `created_at` (DateTime) | `created_at` (DateTime) | Preserve |
| `updated_at` (DateTime) | `updated_at` (DateTime) | Preserve |
| `donation_type` | -- | **DROPPED** (no equivalent on Gift) |
| `payment_method` | -- | **DROPPED** |
| `pledge` (FK) | -- | **DROPPED** (Gift doesn't link to RecurringGift) |
| `thanked` | -- | **DROPPED** |
| `thanked_at` | -- | **DROPPED** |
| `thanked_by` | -- | **DROPPED** |
| `imported_at` | -- | **DROPPED** |
| `import_batch` | -- | **DROPPED** |

## Field Mapping: Pledge -> RecurringGift

| Pledge Field | RecurringGift Field | Transformation |
|-------------|---------------------|----------------|
| `id` (UUID) | `id` (UUID) | **Preserve exactly** |
| `contact` (FK) | `donor_contact` (FK) | Same target table, different FK name |
| `fund` (FK) | `fund` (FK) | Direct copy |
| `amount` (Decimal) | `amount_cents` (BigInt) | `int(amount * 100)` |
| `frequency` (CharField) | `frequency` (CharField) | Map: 'semi_annual' -> 'semi_annually'; others direct |
| `status` (CharField) | `status` (CharField) | Map: 'paused' -> 'held'; others direct |
| `start_date` (DateField) | `start_date` (DateField) | Direct copy |
| `end_date` (DateField) | `end_date` (DateField) | Direct copy |
| `external_id` (CharField) | `external_gift_id` (CharField) | Direct copy |
| `notes` (TextField) | `description` (TextField) | Direct copy |
| `created_at` (DateTime) | `created_at` (DateTime) | Preserve |
| `updated_at` (DateTime) | `updated_at` (DateTime) | Preserve |
| `last_fulfilled_date` | -- | **DROPPED** |
| `next_expected_date` | -- | **DROPPED** |
| `total_expected` | -- | **DROPPED** |
| `total_received` | -- | **DROPPED** |
| `is_late` | -- | **DROPPED** |
| `days_late` | -- | **DROPPED** |
| `late_notified_at` | -- | **DROPPED** |

## Frequency Mapping

| PledgeFrequency | RecurringGiftFrequency | Notes |
|----------------|----------------------|-------|
| `monthly` | `monthly` | Direct |
| `quarterly` | `quarterly` | Direct |
| `semi_annual` | `semi_annually` | Value changes from `semi_annual` to `semi_annually` |
| `annual` | `annually` | Value changes from `annual` to `annually` |

## Status Mapping

| PledgeStatus | RecurringGiftStatus | Notes |
|-------------|-------------------|-------|
| `active` | `active` | Direct |
| `paused` | `held` | RE uses "Held" instead of "Paused" |
| `completed` | `completed` | Direct |
| `cancelled` | `cancelled` | Direct |
| -- | `terminated` | New in RecurringGift, no Pledge equivalent |

## Features Affected by Dropped Fields

### Thank-You Tracking (from Donation)
The Donation model has `thanked`, `thanked_at`, `thanked_by` fields. Gift does not. The `DonationThankView` and related signal logic that marks contacts as needing thank-you will be lost. However, the Contact model still has `needs_thank_you` and `last_thanked_at` fields. Thank-you tracking at the individual gift level is dropped; contact-level tracking persists via the Contact model.

### Late Pledge Detection (from Pledge)
The Pledge model has `is_late`, `days_late`, `next_expected_date`, `last_fulfilled_date` fields. RecurringGift does not. The Celery task `check_late_pledges` and the `LatePledgesView`, `get_late_donations()` services depend on these. These features must be removed or reimplemented differently. For Phase 30, remove them -- they can be rebuilt in a future phase if needed.

### Pledge Fulfillment Tracking (from Pledge)
The Pledge model has `total_expected`, `total_received`, `record_fulfillment()`, `fulfillment_percentage`, `check_late_status()`. RecurringGift does not. These are dropped along with the signals that link Donation.pledge FK to fulfillment updates.

### Support Progress (from Dashboard)
`get_support_progress()` depends on `Pledge.monthly_equivalent` property. RecurringGift does not have this yet. Must be implemented as a property on RecurringGift using the same multiplier logic from the expanded frequency set.

## Code Examples

### Example 1: Verified Migration RunPython Pattern

```python
# apps/gifts/migrations/XXXX_migrate_donation_pledge_data.py
from decimal import Decimal
from django.db import migrations

def migrate_donations_to_gifts(apps, schema_editor):
    Donation = apps.get_model('donations', 'Donation')
    Gift = apps.get_model('gifts', 'Gift')

    batch = []
    for d in Donation.objects.all().iterator(chunk_size=1000):
        batch.append(Gift(
            id=d.id,
            donor_contact_id=d.contact_id,
            fund_id=d.fund_id,
            external_gift_id=d.external_id or '',
            amount_cents=int(d.amount * 100),
            gift_date=d.date,
            description=d.notes or '',
            created_at=d.created_at,
            updated_at=d.updated_at,
        ))
        if len(batch) >= 1000:
            Gift.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        Gift.objects.bulk_create(batch, ignore_conflicts=True)

def migrate_pledges_to_recurring_gifts(apps, schema_editor):
    Pledge = apps.get_model('pledges', 'Pledge')
    RecurringGift = apps.get_model('gifts', 'RecurringGift')

    FREQ_MAP = {'semi_annual': 'semi_annually', 'annual': 'annually'}
    STATUS_MAP = {'paused': 'held'}

    batch = []
    for p in Pledge.objects.all().iterator(chunk_size=1000):
        batch.append(RecurringGift(
            id=p.id,
            donor_contact_id=p.contact_id,
            fund_id=p.fund_id,
            external_gift_id=p.external_id or '',
            amount_cents=int(p.amount * 100),
            frequency=FREQ_MAP.get(p.frequency, p.frequency),
            status=STATUS_MAP.get(p.status, p.status),
            start_date=p.start_date,
            end_date=p.end_date,
            description=p.notes or '',
            created_at=p.created_at,
            updated_at=p.updated_at,
        ))
        if len(batch) >= 1000:
            RecurringGift.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        RecurringGift.objects.bulk_create(batch, ignore_conflicts=True)
```

### Example 2: Contact Stats Update (New)

```python
# In Contact.update_giving_stats() -- query Gift instead of Donation
from decimal import Decimal

gifts = self.gifts.all()
agg = gifts.aggregate(
    total_cents=models.Sum('amount_cents'),
    count=models.Count('id'),
    first=models.Min('gift_date'),
    last=models.Max('gift_date')
)

self.total_given = Decimal(agg['total_cents'] or 0) / Decimal(100)
self.gift_count = agg['count'] or 0
self.first_gift_date = agg['first']
self.last_gift_date = agg['last']

if agg['last']:
    last_gift = gifts.order_by('-gift_date').first()
    self.last_gift_amount = Decimal(last_gift.amount_cents) / Decimal(100) if last_gift else None
```

### Example 3: RecurringGift.monthly_equivalent Property (New)

```python
# Must be added to RecurringGift model for support progress calculation
@property
def monthly_equivalent(self):
    """Calculate monthly equivalent amount in dollars."""
    from decimal import Decimal
    multipliers = {
        'monthly': Decimal('1'),
        'quarterly': Decimal('1') / Decimal('3'),
        'semi_annually': Decimal('1') / Decimal('6'),
        'annually': Decimal('1') / Decimal('12'),
        'bimonthly': Decimal('1') / Decimal('2'),
        'biweekly': Decimal('26') / Decimal('12'),  # 26 biweekly periods / 12 months
        'weekly': Decimal('52') / Decimal('12'),     # 52 weeks / 12 months
        'irregular': Decimal('1'),  # Default to monthly
    }
    return round(self.amount_dollars * multipliers.get(self.frequency, Decimal('1')), 2)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DecimalField for money | PositiveBigIntegerField (cents) | Phase 27 | All amount fields use cents internally; display via `amount_dollars` property |
| Single-owner Donation | Multi-solicitor Gift with credits | Phase 27 | GiftCredit junction table enables split attribution |
| 4 pledge frequencies | 8 recurring gift frequencies | Phase 27 | Supports bimonthly, biweekly, weekly, irregular in addition to original 4 |
| Pledge fulfillment tracking | Lean RecurringGift (status only) | Phase 27 | Late detection and fulfillment features deferred/removed |

**Deprecated/outdated:**
- `Donation` model: Replaced by `Gift`
- `Pledge` model: Replaced by `RecurringGift`
- `DonationType`, `PaymentMethod` enums: No equivalent on Gift (not needed for RE imports)
- `PledgeFrequency`, `PledgeStatus` enums: Replaced by `RecurringGiftFrequency`, `RecurringGiftStatus`
- Old SPO CSV import (imports/services.py): Uses Donation/Pledge; must be updated or removed

## Open Questions

1. **Old SPO CSV Import Service**
   - What we know: `apps/imports/services.py` has import functions (`parse_donations_csv`, etc.) that create Donation objects. These are the original v1.0 import pipeline.
   - What's unclear: Whether these old import functions are still used or if the new RE import pipeline (Phase 28-29) fully replaces them.
   - Recommendation: Remove the old SPO import functions since Phase 28-29 built the RE import pipeline. If generic CSV import is needed later, Phase 35 (IMP-08, IMP-09) will handle it.

2. **EventType Names**
   - What we know: EventType enum has `DONATION_RECEIVED`, `FIRST_DONATION`, `PLEDGE_CREATED`, `PLEDGE_UPDATED`, `PLEDGE_LATE`, `PLEDGE_CANCELLED`.
   - What's unclear: Whether to rename these to GIFT_RECEIVED etc. or keep them for backward compatibility with existing Event records.
   - Recommendation: Keep existing EventType values unchanged. They are stored in the Event table and changing them would orphan existing events. Add new GIFT_RECEIVED / RECURRING_GIFT_CREATED values if needed, but the old names can coexist.

3. **generate_sample_data Command**
   - What we know: Management command generates sample Donations and Pledges.
   - What's unclear: Whether this is actively used.
   - Recommendation: Update to generate Gift and RecurringGift objects instead, or defer if not actively needed.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `apps/donations/models.py`, `apps/pledges/models.py`, `apps/gifts/models.py` -- direct field comparison
- Codebase analysis: `apps/insights/services.py`, `apps/dashboard/services.py` -- every Donation/Pledge query mapped
- Codebase analysis: `apps/contacts/models.py` -- Contact.update_giving_stats() implementation
- Codebase analysis: Complete grep of `from apps.donations` and `from apps.pledges` across all apps

### Secondary (MEDIUM confidence)
- Phase 27 Research: `.planning/phases/27-foundation-models/27-RESEARCH.md` -- design decisions for Gift/RecurringGift
- STATE.md: Project decisions including "REPLACE Donation/Pledge with Gift/RecurringGift (full data migration + 77+ file updates)"

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pure Django migration and ORM, no external tools
- Architecture: HIGH - field mappings are deterministic, all query points fully inventoried
- Pitfalls: HIGH - based on direct codebase analysis of every reference point

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (stable -- internal models, no external dependencies)
