# Architecture Research: v2.0 Data Model Restructuring

**Domain:** DonorCRM v2.0 -- Gift/RecurringGift/Solicitor/GiftCredit integration with existing architecture
**Researched:** 2026-02-20
**Overall Confidence:** HIGH (based on thorough codebase analysis + Django migration docs)

---

## Executive Summary

The v2.0 restructuring introduces five new models (Gift, RecurringGift, Solicitor, GiftCredit, RecurringGiftCredit) alongside the existing Donation and Pledge models, plus a PrayerIntention model and a revamped RE import pipeline. The critical architectural decision is: **do NOT replace Donation/Pledge -- add new models alongside them**.

The existing Donation/Pledge models serve the manual/SPO import workflow and remain the user-facing data for everyday CRM usage. The new Gift/RecurringGift models are RE-import-specific with different schemas (external IDs, solicitor credits, fund split amounts in cents). Attempting a Donation-to-Gift migration would break 30+ frontend files, all dashboard services, all insight services, and the entire import pipeline -- for no user benefit.

**The correct architecture is a dual-model system** where Gift/RecurringGift coexist with Donation/Pledge, each serving its own import source, with a unified query layer for aggregate stats.

---

## Recommended Architecture

### System Overview

```
                         EXISTING (unchanged)              NEW (v2.0)
                    +--------------------------+    +---------------------------+
                    |                          |    |                           |
User/SPO Import --> | Donation (manual/SPO)    |    | Gift (RE import)          | <-- RE CSV Import
                    | Pledge   (manual/SPO)    |    | RecurringGift (RE import) |
                    |                          |    | Solicitor                 |
                    +-----------+--------------+    | GiftCredit                |
                                |                   | RecurringGiftCredit       |
                                |                   | PrayerIntention           |
                                |                   +------------+--------------+
                                |                                |
                                +------+   +---------------------+
                                       |   |
                                       v   v
                              +------------------+
                              | Contact          |
                              | (unified stats   |
                              |  from BOTH       |
                              |  sources)        |
                              +------------------+
```

### Why NOT Replace Donation with Gift

The RE import prompts describe Gift/RecurringGift using a different schema than Donation/Pledge: `externalGiftId`, `fundSplitAmountCents` (integer cents), multi-row-per-gift solicitor credit grouping. The existing Donation model uses `DecimalField` amounts, `UUID` PKs, and a simpler flat schema. These are fundamentally different data structures serving different import sources.

**Blast radius of replacing Donation with Gift:**

| Category | Files Affected | Severity |
|----------|---------------|----------|
| Frontend pages (DonationList, DonationDetail, DonationForm) | 6 files | Total rewrite |
| Frontend components (RecentDonations, LateDonations, GivingSummaryCard, MonthlyGiftsCard) | 6 files | Total rewrite |
| API serializers + views + filters | 6 files | Total rewrite |
| Dashboard services (5 functions reference Donation) | 1 file, 5 functions | Heavy modification |
| Insights services (15+ Donation.objects references) | 1 file, 10+ functions | Heavy modification |
| Donation signals (stat recalculation, event creation) | 1 file | Rewrite |
| Import services (donation import pipeline) | 2 files | Rewrite |
| Frontend API layer (donations.ts, pledges.ts, dashboard.ts) | 3 files | Rewrite |
| Admin analytics components | 5 files | Modification |
| **Total** | **~35 files** | **Massive** |

**Risk:** Every existing feature regresses. Every test breaks. For zero user-visible benefit.

**Instead:** Gift/RecurringGift are additive models that only the RE import pipeline writes to, and that contact stat recalculation reads from as an additional data source.

---

## Component Architecture

### New Django Apps

**Do NOT create new apps for every model.** Add models to existing apps based on domain ownership.

| Model | App | Rationale |
|-------|-----|-----------|
| `Gift` | `apps.donations` | Gift is a type of donation -- same domain |
| `RecurringGift` | `apps.pledges` | RecurringGift is a type of pledge -- same domain |
| `Solicitor` | New: `apps.solicitors` | Distinct domain entity, standalone lifecycle, referenced by both donation and pledge apps |
| `GiftCredit` | `apps.donations` | Junction table for Gift-Solicitor, lives with Gift |
| `RecurringGiftCredit` | `apps.pledges` | Junction table for RecurringGift-Solicitor, lives with RecurringGift |
| `PrayerIntention` | New: `apps.prayer` | Distinct feature domain, own UI/API surface, unique UX philosophy |
| `ImportBatch` | `apps.imports` | Extends existing import tracking infrastructure |

**Rationale for `apps.solicitors`:** Solicitor has its own import step, its own matching logic (normalizedName), and is referenced by both GiftCredit and RecurringGiftCredit across two apps. It needs its own app to avoid circular imports between donations and pledges.

**Rationale for `apps.prayer`:** Prayer intentions have their own dedicated page/tab, their own UX philosophy (chapel-like, calming), and their own API endpoints. Putting them in `donations` or `contacts` would muddy domain boundaries.

### New Models: Detailed Schema

#### Gift (in `apps.donations`)

```python
class Gift(TimeStampedModel):
    """
    One-time gift imported from Raiser's Edge.
    Separate from Donation (which serves manual/SPO imports).
    """
    # RE identifiers
    external_gift_id = models.CharField(max_length=100, unique=True, db_index=True)
    external_constituent_id = models.CharField(max_length=100, db_index=True)

    # Link to donor
    donor_contact = models.ForeignKey(
        'contacts.Contact', on_delete=models.CASCADE,
        related_name='re_gifts', null=True, blank=True
    )

    # Gift details
    gift_date = models.DateField(null=True, blank=True, db_index=True)
    last_changed_at = models.DateTimeField(null=True, blank=True)
    gift_type = models.CharField(max_length=100, blank=True)
    fund_id = models.CharField(max_length=100, blank=True)
    fund_split_amount_cents = models.IntegerField(null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    payment_type = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)  # Prayer requests from RE

    # Import tracking
    import_batch = models.ForeignKey(
        'imports.ImportBatch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='gifts'
    )

    class Meta:
        db_table = 'gifts'
        ordering = ['-gift_date', '-created_at']
        indexes = [
            models.Index(fields=['donor_contact', 'gift_date']),
            models.Index(fields=['external_constituent_id']),
        ]

    @property
    def amount_dollars(self):
        """Convert cents to decimal dollars for stat calculations."""
        from decimal import Decimal
        if self.fund_split_amount_cents is None:
            return Decimal('0')
        return Decimal(self.fund_split_amount_cents) / 100
```

#### GiftCredit (in `apps.donations`)

```python
class GiftCredit(TimeStampedModel):
    """
    Junction: one Gift can credit multiple Solicitors.
    RE exports multiple CSV rows per Gift with different solicitors.
    """
    gift = models.ForeignKey(Gift, on_delete=models.CASCADE, related_name='credits')
    solicitor = models.ForeignKey(
        'solicitors.Solicitor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='gift_credits'
    )
    solicitor_name = models.CharField(max_length=255)  # Original name from CSV
    solicitor_amount_cents = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'gift_credits'
        unique_together = [['gift', 'solicitor_name']]
```

#### RecurringGift (in `apps.pledges`)

```python
class RecurringGift(TimeStampedModel):
    """
    Recurring gift/pledge imported from Raiser's Edge.
    Separate from Pledge (which serves manual/SPO imports).
    """
    external_gift_id = models.CharField(max_length=100, unique=True, db_index=True)
    external_constituent_id = models.CharField(max_length=100, db_index=True)

    donor_contact = models.ForeignKey(
        'contacts.Contact', on_delete=models.CASCADE,
        related_name='re_recurring_gifts', null=True, blank=True
    )

    # Gift details
    gift_date = models.DateField(null=True, blank=True)
    last_changed_at = models.DateTimeField(null=True, blank=True)
    gift_type = models.CharField(max_length=100, blank=True)
    fund_id = models.CharField(max_length=100, blank=True)

    # Installment fields
    installment_amount_cents = models.IntegerField(null=True, blank=True)
    installment_frequency = models.CharField(max_length=50, blank=True)
    installments_scheduled = models.IntegerField(null=True, blank=True)
    first_installment_due = models.DateField(null=True, blank=True)
    last_installment_due = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=50, blank=True)
    status_date = models.DateField(null=True, blank=True)

    is_anonymous = models.BooleanField(default=False)
    payment_type = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)  # Prayer requests

    import_batch = models.ForeignKey(
        'imports.ImportBatch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recurring_gifts'
    )

    class Meta:
        db_table = 'recurring_gifts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['donor_contact']),
            models.Index(fields=['external_constituent_id']),
        ]

    @property
    def amount_dollars(self):
        from decimal import Decimal
        if self.installment_amount_cents is None:
            return Decimal('0')
        return Decimal(self.installment_amount_cents) / 100
```

#### RecurringGiftCredit (in `apps.pledges`)

```python
class RecurringGiftCredit(TimeStampedModel):
    """Junction: one RecurringGift can credit multiple Solicitors."""
    recurring_gift = models.ForeignKey(
        RecurringGift, on_delete=models.CASCADE, related_name='credits'
    )
    solicitor = models.ForeignKey(
        'solicitors.Solicitor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recurring_gift_credits'
    )
    solicitor_name = models.CharField(max_length=255)
    solicitor_amount_cents = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'recurring_gift_credits'
        unique_together = [['recurring_gift', 'solicitor_name']]
```

#### Solicitor (in `apps.solicitors`)

```python
class Solicitor(TimeStampedModel):
    """
    Fundraiser/missionary who receives gift credit.
    Imported from RE Solicitor CSV.
    """
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, unique=True, db_index=True)
    external_solicitor_id = models.CharField(
        max_length=100, blank=True, db_index=True
    )

    # Optional link to a User (if this solicitor IS a system user)
    user = models.OneToOneField(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='solicitor_profile'
    )

    class Meta:
        db_table = 'solicitors'
        ordering = ['name']
```

#### ImportBatch (in `apps.imports`)

```python
class ImportBatchStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    STARTED = 'started', 'Started'
    PROCESSING = 'processing', 'Processing'
    SUCCEEDED = 'succeeded', 'Succeeded'
    SUCCEEDED_WITH_ERRORS = 'succeeded_with_errors', 'Succeeded with Errors'
    FAILED = 'failed', 'Failed'

class ImportBatchType(models.TextChoices):
    CONSTITUENT = 'constituent', 'Constituent'
    SOLICITOR = 'solicitor', 'Solicitor'
    GIFT = 'gift', 'Gift'
    RECURRING_GIFT = 'recurring_gift', 'Recurring Gift'

class ImportBatch(TimeStampedModel):
    """
    Track RE import jobs with SHA256 deduplication.
    Parallel to existing ImportRun (which tracks SPO imports).
    """
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='import_batches'
    )
    filename = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64, db_index=True)
    import_type = models.CharField(
        max_length=30, choices=ImportBatchType.choices
    )
    row_count = models.IntegerField(default=0)
    rows_imported = models.IntegerField(default=0)
    rows_skipped = models.IntegerField(default=0)
    rows_errored = models.IntegerField(default=0)
    status = models.CharField(
        max_length=30, choices=ImportBatchStatus.choices,
        default=ImportBatchStatus.PENDING
    )
    error_log = models.TextField(blank=True)
    summary_json = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'import_batches'
        unique_together = [['import_type', 'sha256']]
        ordering = ['-created_at']
```

#### PrayerIntention (in `apps.prayer`)

```python
class PrayerIntention(TimeStampedModel):
    """
    Prayer request associated with a Contact, optionally linked to a Gift.
    Can be auto-populated from RE Gift description field or manually created.
    """
    contact = models.ForeignKey(
        'contacts.Contact', on_delete=models.CASCADE,
        related_name='prayer_intentions'
    )
    owner = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='prayer_intentions'
    )

    # Content
    text = models.TextField()

    # Source tracking
    source_gift = models.ForeignKey(
        'donations.Gift', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='prayer_intentions'
    )
    is_from_import = models.BooleanField(default=False)

    # Prayer tracking
    is_active = models.BooleanField(default=True)
    last_prayed_at = models.DateTimeField(null=True, blank=True)
    pray_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'prayer_intentions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['contact']),
        ]
```

### Contact Model Changes

Add to existing Contact model (4 new fields):

```python
# In apps/contacts/models.py - ADD these fields:

external_constituent_id = models.CharField(
    'RE Constituent ID', max_length=100, blank=True,
    unique=True, null=True, db_index=True,
    help_text='Constituent ID from Raiser\'s Edge'
)
organization_name = models.CharField(
    'organization name', max_length=255, blank=True
)
address_line_2 = models.CharField(
    'address line 2', max_length=255, blank=True
)
re_last_changed_at = models.DateTimeField(
    'RE last changed', null=True, blank=True
)
```

**Note on `external_constituent_id` vs existing `external_id`:** The existing `external_id` is scoped per-owner (unique constraint is `owner + external_id`). The RE `external_constituent_id` is globally unique across the system (one constituent ID per contact regardless of owner). These are different fields serving different import sources. Keep both.

---

## Data Flow

### RE Import Pipeline (New)

```
Admin uploads CSV
      |
      v
POST /api/v1/imports/re/{type}/
      |
      v
REImportView (new view in imports app)
      |
      +---> Compute SHA256 hash
      +---> Check ImportBatch for duplicate (idempotent)
      +---> If already processed, return cached result
      |
      v
RE Import Service (new service module)
      |
      +---> Parse CSV with csv.DictReader
      +---> Validate required headers
      +---> For gifts: GROUP rows by Gift ID (critical!)
      |
      v
Per-row processing:
      |
      +---> [Constituent] Match/create Contact by external_constituent_id
      +---> [Solicitor]   Upsert by normalized_name
      +---> [Gift]        Find Contact by constituent_id, upsert Gift, upsert GiftCredits
      +---> [RecurringGift] Same as Gift pattern
      |
      v
Complete ImportBatch with summary
      |
      v
Trigger contact stat recalculation (for Gift/RecurringGift imports)
      |
      v
Create PrayerIntentions from Gift descriptions (if non-empty)
      |
      v
Return ImportResult JSON
```

### Contact Stat Recalculation After Model Swap (Modified)

The existing `Contact.update_giving_stats()` (line 152-188 in contacts/models.py) queries ONLY `self.donations`. After v2.0, it must also include Gift data.

**Approach: Modify the single existing method to query both sources**

```python
def update_giving_stats(self):
    """
    Recalculate giving statistics from BOTH Donation and Gift sources.
    Called when donations are added/modified OR when RE gifts are imported.
    """
    from decimal import Decimal
    from django.db import transaction
    from django.db.models import Sum, Count, Min, Max, Value, DecimalField
    from django.db.models.functions import Coalesce

    with transaction.atomic():
        Contact.objects.select_for_update().filter(pk=self.pk).first()

        # --- Source 1: Donation (manual/SPO) ---
        donation_agg = self.donations.aggregate(
            total=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()),
            count=Count('id'),
            first=Min('date'),
            last=Max('date')
        )

        # --- Source 2: Gift (RE import) -- convert cents to dollars ---
        gift_agg = self.re_gifts.aggregate(
            total_cents=Coalesce(Sum('fund_split_amount_cents'), Value(0)),
            count=Count('id'),
            first=Min('gift_date'),
            last=Max('gift_date')
        )
        gift_total = Decimal(gift_agg['total_cents']) / 100

        # --- Merge both sources ---
        self.total_given = donation_agg['total'] + gift_total
        self.gift_count = donation_agg['count'] + gift_agg['count']

        # First/last gift across both sources
        all_firsts = [d for d in [donation_agg['first'], gift_agg['first']] if d]
        self.first_gift_date = min(all_firsts) if all_firsts else None

        all_lasts = [d for d in [donation_agg['last'], gift_agg['last']] if d]
        self.last_gift_date = max(all_lasts) if all_lasts else None

        # Last gift amount: compare dates from both sources
        if self.last_gift_date:
            last_donation = self.donations.order_by('-date').first()
            last_gift = self.re_gifts.order_by('-gift_date').first()

            if last_donation and last_gift:
                if last_donation.date >= last_gift.gift_date:
                    self.last_gift_amount = last_donation.amount
                else:
                    self.last_gift_amount = last_gift.amount_dollars
            elif last_donation:
                self.last_gift_amount = last_donation.amount
            elif last_gift:
                self.last_gift_amount = last_gift.amount_dollars

        # Status upgrade
        if self.gift_count > 0 and self.status == ContactStatus.PROSPECT:
            self.status = ContactStatus.DONOR

        self.save(update_fields=[
            'total_given', 'gift_count', 'first_gift_date',
            'last_gift_date', 'last_gift_amount', 'status'
        ])
```

**This is the ONLY change to existing Contact code.** The existing Donation signal (in `apps/donations/signals.py`) still calls `instance.contact.update_giving_stats()` and still works. The method now also includes Gift data, but since Gift imports call it separately (after batch completion), the signal path remains unchanged.

**Gift signal for stat recalc:**
```python
# In apps/donations/signals.py -- ADD (do NOT modify existing signals)

from apps.donations.models import Gift

@receiver(post_save, sender=Gift)
def update_contact_stats_on_gift_save(sender, instance, **kwargs):
    """Update contact stats when RE gift is saved."""
    if _signals_disabled():
        return
    if instance.donor_contact:
        instance.donor_contact.update_giving_stats()

@receiver(post_delete, sender=Gift)
def update_contact_stats_on_gift_delete(sender, instance, **kwargs):
    """Update contact stats when RE gift is deleted."""
    if instance.donor_contact:
        instance.donor_contact.update_giving_stats()
```

### Prayer Intention Data Flow

```
Source 1: RE Gift Import (automatic)
      |
      +---> Gift.description has non-empty prayer text
      +---> After Gift import batch completes:
            post_import_create_prayer_intentions(batch_id):
              For each Gift in batch with non-empty description:
                - Find or create PrayerIntention
                - Link to Contact (via Gift.donor_contact)
                - Link to Gift (via source_gift FK)
                - Set owner = Contact.owner
                - Set is_from_import = True

Source 2: Manual Creation
      |
      +---> POST /api/v1/prayer/intentions/
      +---> Create PrayerIntention linked to Contact
      +---> is_from_import = False

Consumption:
      |
      +---> GET /api/v1/prayer/focus/ (Today's prayer list for owner)
      +---> POST /api/v1/prayer/intentions/{id}/prayed/ (Mark as prayed)
      +---> Prayer page at /prayer with chapel-like UX
```

---

## Integration Points

### What Changes vs. What Stays

#### UNCHANGED (zero modifications)

| Component | Why Unchanged |
|-----------|--------------|
| `apps/donations/models.py` (Donation class) | Donation model stays as-is, Gift is additive |
| `apps/donations/views.py` | Donation CRUD API unchanged |
| `apps/donations/serializers.py` | Donation API shape unchanged |
| `apps/donations/filters.py` | Donation filtering unchanged |
| `apps/pledges/models.py` (Pledge class) | Pledge model stays as-is, RecurringGift is additive |
| `apps/pledges/views.py` | Pledge CRUD API unchanged |
| `apps/pledges/serializers.py` | Pledge API shape unchanged |
| `apps/dashboard/services.py` | Queries Donation/Pledge as before (stats come from Contact) |
| `apps/dashboard/views.py` | Dashboard API unchanged |
| `apps/insights/services.py` | Queries Donation/Pledge directly -- still correct for those sources |
| Frontend: DonationList, DonationDetail, DonationForm | Existing donation UX unchanged |
| Frontend: PledgeList, PledgeDetail, PledgeForm | Existing pledge UX unchanged |
| Frontend: All dashboard components | Read from Contact stats, which are updated transparently |
| Frontend: `api/donations.ts`, `api/pledges.ts` | API layer unchanged |
| **~35 files stay untouched** | |

#### MODIFIED (minimal changes to existing files)

| Component | Change | Reason |
|-----------|--------|--------|
| `apps/contacts/models.py` | Add 4 fields + modify `update_giving_stats()` | RE fields + unified stat calculation |
| `apps/contacts/serializers.py` | Add new fields to ContactSerializer | Expose RE fields in API |
| `apps/donations/signals.py` | Add Gift post_save/post_delete handlers | Trigger stat recalc for RE gifts |
| `apps/imports/models.py` | Add `ImportBatch` model | RE import tracking |
| `apps/imports/urls.py` | Add RE import endpoint routes | New API routes |
| `config/api_urls.py` | Add solicitors + prayer URL includes | Register new app routing |
| `config/settings/base.py` | Add `apps.solicitors`, `apps.prayer` to INSTALLED_APPS | Register new apps |
| Frontend: `App.tsx` | Add RE import page + prayer page routes | New pages |
| Frontend: `Sidebar.tsx` | Add Prayer nav item | Navigation |
| Frontend: `ImportCenter.tsx` | Add RE import tile alongside SPO tiles | New import source |

#### NEW (created from scratch)

| Component | Purpose |
|-----------|---------|
| `apps/solicitors/` (entire app) | Solicitor model, admin, views, serializers, urls |
| `apps/prayer/` (entire app) | PrayerIntention model, views, serializers, urls |
| `apps/donations/models.py` -- Gift, GiftCredit classes | RE gift models (added to existing file) |
| `apps/pledges/models.py` -- RecurringGift, RecurringGiftCredit classes | RE recurring gift models (added to existing file) |
| `apps/imports/re_services.py` | RE import processing (constituent, solicitor, gift, recurring_gift) |
| `apps/imports/re_views.py` | RE import API endpoints |
| `apps/imports/re_utils.py` | SHA256 hashing, CSV parsing, date/currency parsing |
| Frontend: `pages/admin/REImport.tsx` | RE import UI (tab-based, 4 import types) |
| Frontend: `pages/prayer/PrayerPage.tsx` | Prayer intentions UI (chapel-like) |
| Frontend: `api/re-imports.ts` | RE import API client |
| Frontend: `api/prayer.ts` | Prayer API client |

### Import App Restructuring

**Extend the imports app. Do NOT replace it.**

The existing `apps/imports/` handles SPO imports (contacts, donations, pledges, funds, entities, transactions, MPD). The RE import pipeline is a parallel import source with different CSV schemas, different processing logic (row grouping, SHA256 dedup), and different target models (Gift vs Donation).

**Recommended file structure:**

```
apps/imports/
  models.py          # EXISTING: ImportRun, ImportRowError, Fund
                      # ADD: ImportBatch, ImportBatchStatus, ImportBatchType
  services.py         # EXISTING: SPO import services (UNCHANGED)
  re_services.py      # NEW: RE import services (constituent, solicitor, gift, recurring_gift)
  re_views.py         # NEW: RE import API views
  re_utils.py         # NEW: Shared parsing utilities (SHA256, CSV, date, currency)
  views.py            # EXISTING: SPO import views (UNCHANGED)
  urls.py             # MODIFIED: Add RE import routes alongside existing SPO routes
```

**URL structure (added to existing imports/urls.py):**

```python
# Existing SPO routes stay at their current paths (lines 33-56 of imports/urls.py)
# New RE routes added:
path('re/constituents/', REConstituentImportView.as_view(), name='re-import-constituents'),
path('re/solicitors/', RESolicitorImportView.as_view(), name='re-import-solicitors'),
path('re/gifts/', REGiftImportView.as_view(), name='re-import-gifts'),
path('re/recurring-gifts/', RERecurringGiftImportView.as_view(), name='re-import-recurring-gifts'),
path('re/batches/', REImportBatchListView.as_view(), name='re-import-batches'),
path('re/batches/<uuid:pk>/', REImportBatchDetailView.as_view(), name='re-import-batch-detail'),
```

---

## Patterns to Follow

### Pattern 1: Additive Models (No Destructive Migration)

**What:** Add Gift/RecurringGift alongside Donation/Pledge without removing or renaming existing models.

**Why:** The existing models have ~35 files of references across backend and frontend. A rename or replacement requires coordinated changes across every layer of the stack. Additive models require changes only where the new data needs to flow.

**Migration approach:**
```python
# Migration 1: Add new fields to Contact
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='contact',
            name='external_constituent_id',
            field=models.CharField(max_length=100, blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='contact',
            name='organization_name',
            field=models.CharField(max_length=255, blank=True, default=''),
        ),
        # ...
    ]

# Migration 2: Create Gift model
# Migration 3: Create GiftCredit model
# Migration 4: Create RecurringGift model
# etc.
# Standard CreateModel operations. No RunPython data migration needed.
```

### Pattern 2: SHA256 Idempotent Imports

**What:** Hash each uploaded CSV file. Check ImportBatch for existing hash before processing. Return cached result for duplicates.

**When:** All four RE import types (constituent, solicitor, gift, recurring_gift).

**Implementation:**
```python
import hashlib

def compute_sha256(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()

# In the import view:
content = request.FILES['file'].read()
sha256 = compute_sha256(content)
existing = ImportBatch.objects.filter(
    import_type=import_type, sha256=sha256
).first()
if existing and existing.status in ['succeeded', 'succeeded_with_errors']:
    return Response({
        **existing.summary_json,
        'already_processed': True,
    }, status=200)
```

### Pattern 3: Row Grouping for Multi-Solicitor Gifts

**What:** RE exports multiple CSV rows per Gift when a gift credits multiple solicitors. Group all rows by Gift ID before processing.

**When:** Gift and RecurringGift imports.

**Critical detail from RE spec:** A gift can have 2+ solicitors. The CSV has one row per solicitor credit. All rows share the same Gift ID but have different Solicitor Name and Solicitor Amount values.

**Implementation:**
```python
from collections import defaultdict

def process_gift_csv(rows, import_batch):
    gift_groups = defaultdict(list)
    for i, row in enumerate(rows, start=2):
        gift_id = row.get('Gift ID', '').strip()
        if gift_id:
            gift_groups[gift_id].append((i, row))

    for gift_id, group_rows in gift_groups.items():
        row_num, first_row = group_rows[0]

        # Find donor contact
        constituent_id = first_row.get('Constituent ID', '').strip()
        contact = Contact.objects.filter(
            external_constituent_id=constituent_id
        ).first()
        if not contact:
            # Error: skip all rows in this group
            continue

        # Upsert Gift from first row (all rows share same gift data)
        gift, created = Gift.objects.update_or_create(
            external_gift_id=gift_id,
            defaults={...gift fields from first_row...}
        )

        # Upsert GiftCredit for each solicitor row
        for row_num, row in group_rows:
            solicitor_name = row.get('Solicitor Name', '').strip()
            if solicitor_name:
                solicitor = Solicitor.objects.filter(
                    normalized_name=solicitor_name.lower().strip()
                ).first()
                GiftCredit.objects.update_or_create(
                    gift=gift,
                    solicitor_name=solicitor_name,
                    defaults={
                        'solicitor': solicitor,
                        'solicitor_amount_cents': parse_cents(row.get('Solicitor Amount')),
                    }
                )
```

### Pattern 4: Merge-Only Updates (Never Overwrite with Null)

**What:** When updating existing Contact records from RE constituent import, only overwrite fields that have new non-empty values. Never replace existing data with null/empty.

**When:** Constituent import updating existing contacts.

**Implementation:**
```python
def merge_contact_fields(contact, row_data):
    """Update contact fields only where new data is non-empty."""
    field_map = {
        'first_name': row_data.get('First Name', '').strip(),
        'last_name': row_data.get('Last Name', '').strip(),
        'email': normalize_email(row_data.get('Email')),
        'phone': normalize_phone(row_data.get('Phone')),
        # ... etc
    }

    updated_fields = []
    for field_name, new_value in field_map.items():
        if new_value:  # Only update if new value is non-empty
            setattr(contact, field_name, new_value)
            updated_fields.append(field_name)

    if updated_fields:
        contact.save(update_fields=updated_fields)
```

### Pattern 5: Disable Signals During Bulk Import

**What:** The existing `disable_donation_signals()` / `enable_donation_signals()` pattern in `apps/donations/signals.py` prevents N signal fires during bulk operations. Apply the same pattern to Gift imports.

**When:** RE gift import batch processing.

**Implementation:**
```python
# In re_services.py
from apps.donations.signals import disable_donation_signals, enable_donation_signals

def import_gifts_batch(rows, import_batch):
    disable_donation_signals()
    try:
        # Process all rows without triggering per-save signals
        for gift_id, group_rows in gift_groups.items():
            # ... create/update gifts ...
            pass

        # After all gifts processed, do ONE stat recalc per affected contact
        affected_contact_ids = set()
        for gift in Gift.objects.filter(import_batch=import_batch):
            if gift.donor_contact_id:
                affected_contact_ids.add(gift.donor_contact_id)

        for contact_id in affected_contact_ids:
            Contact.objects.get(pk=contact_id).update_giving_stats()
    finally:
        enable_donation_signals()
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Replacing Donation with Gift

**What:** Renaming Donation to Gift, migrating all existing donation data, updating all 35+ referencing files.

**Why bad:** Months of work, total regression risk on every existing feature, zero user-visible benefit. The RE Gift model has a fundamentally different schema (cents vs decimals, external IDs, solicitor credits).

**Instead:** Add Gift alongside Donation. Each serves its own import source. Unified stats come from Contact.update_giving_stats().

### Anti-Pattern 2: Single Giant Migration

**What:** One migration file that creates all 7 new models, modifies Contact, and adds new apps.

**Why bad:** If anything fails, entire migration rolls back. Hard to test incrementally. Hard to debug.

**Instead:** One migration per model or logical group. Run `makemigrations` per-app. Commit migrations separately.

### Anti-Pattern 3: Storing Amounts in Both Cents and Decimals

**What:** This is unavoidable, not a pattern to avoid. Gift uses `fund_split_amount_cents` (integer) per the RE spec. Donation uses `amount` (decimal) per existing convention.

**Mitigation:** Always convert via `Gift.amount_dollars` property (never do inline `/ 100`). Document the convention clearly.

### Anti-Pattern 4: Making Prayer Intentions a Tab on Contact Detail

**What:** Adding prayer as just another tab on the contact detail page.

**Why bad:** The prayer page UX should feel like a chapel, not a CRM screen. The contact detail page is dense, data-heavy, and transactional. Embedding prayer there destroys the intended meditative UX.

**Instead:** Prayer gets its own top-level route (`/prayer`) with its own calming design (amber palette, serif fonts, generous spacing per the prayer spec). Individual prayers link TO contacts via the contact FK, but the primary prayer experience is the dedicated page.

### Anti-Pattern 5: Building RE Import UI Before Backend Is Tested

**What:** Building the 4-tab import wizard UI before the backend import services are tested with real RE CSV files.

**Why bad:** Real RE CSVs have encoding issues, messy quoted fields, inconsistent date formats. Backend parsing edge cases discovered later force UI redesign.

**Instead:** Build and test all 4 import services (constituent, solicitor, gift, recurring_gift) with real RE CSV data first. Then build the UI on a stable backend.

---

## Suggested Build Order (Dependency-Aware)

The build order respects model dependencies (Solicitor before Gift, Contact fields before Constituent import, etc.) and minimizes risk of breaking existing features.

### Phase 1: Foundation Models

**Build:**
1. Create `apps.solicitors` app with Solicitor model + admin + basic serializer
2. Create `apps.prayer` app with PrayerIntention model + admin + basic serializer
3. Add Gift + GiftCredit models to `apps/donations/models.py`
4. Add RecurringGift + RecurringGiftCredit to `apps/pledges/models.py`
5. Add ImportBatch to `apps/imports/models.py`
6. Add Contact fields: `external_constituent_id`, `organization_name`, `address_line_2`, `re_last_changed_at`
7. Register new apps in settings
8. Run migrations

**Why first:** All subsequent phases depend on these models existing. No existing functionality is touched. Pure additive database changes.

**Risk:** LOW. Only creates new tables and adds nullable/blank fields to Contact.

### Phase 2: RE Import Pipeline (Backend Only)

**Build:**
1. Import utilities (`apps/imports/re_utils.py`): SHA256, CSV parsing, date/currency/phone/email normalization, header validation
2. ImportBatch service: check existing, create, complete, fail
3. Constituent importer: match/create Contact by external_constituent_id, merge-only updates
4. Solicitor importer: upsert by normalized_name
5. Gift importer: group by Gift ID, upsert Gift + GiftCredits, link to Contact
6. RecurringGift importer: same pattern as Gift
7. RE import API views + URL routing (all admin-only)
8. Unit tests for utilities, integration tests for each importer with test CSV fixtures

**Depends on:** Phase 1 (models exist)

**Why second:** The import pipeline is the primary way data enters the new models. Everything else (stats, prayer, UI) depends on having data to work with.

**Risk:** MEDIUM. New code, but completely isolated from existing features. No existing files modified except `imports/urls.py` (additive routes).

### Phase 3: Contact Stat Unification

**Build:**
1. Modify `Contact.update_giving_stats()` to query both Donation and Gift tables
2. Add Gift post_save/post_delete signals in `donations/signals.py` (additive, do not modify existing signals)
3. Add management command: `python manage.py recalculate_contact_stats` (for backfill after initial RE import)
4. Tests verifying stats are correct with Donation-only, Gift-only, and combined data

**Depends on:** Phase 2 (gifts can be imported to test against)

**Why third:** Stats must be correct before any UI shows them. Dashboard and insights already read from Contact stats (total_given, last_gift_date, etc.), so updating the calculation method flows through to all existing UI automatically.

**Risk:** MEDIUM. Modifies existing `update_giving_stats()` method. Must not break existing Donation signal flow. The existing signals call this same method, so backward compatibility is guaranteed as long as the new code handles the case where `re_gifts` relation returns 0 results (which it will for contacts without RE data).

### Phase 4: RE Import UI (Frontend)

**Build:**
1. Frontend: RE import page (`/admin/re-import`) with 4 tabs (constituent, solicitor, gift, recurring_gift)
2. Frontend: File upload with drag-drop per tab
3. Frontend: Import result display (success/error/already-processed banners)
4. Frontend: Required/optional header reference per import type
5. Frontend: Import order guidance (constituents first, then solicitors, then gifts)
6. Frontend: Import history list showing past ImportBatch records
7. Add RE import tile to ImportCenter alongside SPO tiles
8. Add route to App.tsx

**Depends on:** Phase 2 (API exists)

**Risk:** LOW. New page, minimal existing code changes (just add route + tile in ImportCenter).

### Phase 5: Prayer Intentions

**Build:**
1. Backend: Prayer API endpoints (CRUD + mark-as-prayed + today's-focus)
2. Backend: Post-import hook in re_services.py to create PrayerIntentions from Gift descriptions
3. Frontend: Prayer page at `/prayer` with chapel-like UX (amber palette, serif fonts, generous spacing)
4. Frontend: Focus mode with keyboard shortcuts
5. Frontend: Completion screen showing prayed count
6. Add Prayer nav item to Sidebar
7. Add route to App.tsx

**Depends on:** Phase 1 (PrayerIntention model) + Phase 2 (gifts with descriptions imported)

**Why fifth:** Prayer is a standalone feature with no dependencies on other v2.0 features. Can be built in parallel with Phase 4.

**Risk:** LOW. Entirely new feature, no existing code modification beyond Sidebar nav item + App.tsx route.

### Phase 6: Dashboard Draggable Tiles

**Build:**
1. Backend: DashboardLayout model or user preference field for tile positions
2. Frontend: Draggable tile grid using @dnd-kit/core (or react-beautiful-dnd)
3. Frontend: Persist tile positions via API on drag-end
4. Frontend: Default layout + "Reset layout" button
5. Frontend: Mobile-responsive fallback (stack vertically, no drag on mobile)

**Depends on:** Nothing. Can be parallel with Phase 5.

**Why last:** Draggable tiles are a UX polish enhancement to the existing dashboard, not a data model change. All existing dashboard widgets remain functional; this just lets users rearrange them.

**Risk:** MEDIUM. Modifies existing Dashboard.tsx layout structure. Must not break existing widget rendering or data fetching. Use a feature flag to allow rollback.

---

## Scalability Considerations

| Concern | At Current Scale | At 10x Scale | At 100x Scale |
|---------|-----------------|-------------|--------------|
| RE Gift import (daily CSV) | Sync processing, <2s for 500 rows | Sync OK up to 5000 rows | Celery async task for >5000 rows |
| Contact stat recalc after import | Batch recalc for affected contacts | Acceptable with disable_signals pattern | Pre-computed materialized view |
| Prayer intention queries | Simple owner-scoped query | Index on (owner, is_active) handles it | Pagination sufficient |
| SHA256 dedup check | Single DB query per upload | Index on (import_type, sha256) is fast | No issue |
| Dashboard with dual stat sources | Transparent via Contact fields | No additional queries | Consider denormalized RE gift total on Contact |

---

## Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Replace Donation with Gift? | **NO** | 35-file blast radius, zero user benefit, different schema |
| New apps or extend existing? | **2 new apps** (solicitors, prayer) + **extend** existing (donations, pledges, imports) | Domain boundaries, avoid circular imports |
| Import app: replace or extend? | **Extend with parallel pipeline** | SPO imports unchanged, RE imports have different schemas/logic |
| ImportBatch vs reuse ImportRun? | **New ImportBatch model** | Different dedup strategy (SHA256 vs row-level), different summary format |
| Contact stat source? | **Unified** from Donation + Gift in single method | Single source of truth for all UI, automatic flow-through to dashboard |
| Amount storage for Gift? | **Cents (integer)** per RE spec | Matches RE export format, conversion via property |
| Prayer: Contact tab or standalone? | **Standalone route** with Contact links | Chapel UX requires dedicated space, not embedded in dense CRM |
| Migration strategy? | **Additive only** | No renames, no data migration, no risk to existing data |
| Build order priority? | **Models -> Import -> Stats -> UI** | Each phase depends on the previous, maximizes backend stability before UI |

---

## Sources

**Django Migration Strategy:**
- [Django Official Docs: Migration Operations](https://docs.djangoproject.com/en/6.0/ref/migration-operations/)
- [HackSoft: Renaming models without heavy data migrations](https://www.hacksoft.io/blog/renaming-models-in-django-without-heavy-data-migrations)
- [CheesecakeLabs: Keeping data integrity with Django migrations](https://cheesecakelabs.com/blog/keeping-data-integrity-django-migrations/)
- [Medium: Switch ForeignKey from one model to another](https://medium.com/@artemivasyuk/switch-foreignkey-from-one-model-to-another-and-keep-old-data-migration-pain-c01db016cf84)

**Codebase Analysis (primary source, HIGH confidence):**
- `apps/donations/models.py` -- Donation model: DecimalField amounts, UUID PKs, Fund FK, Pledge FK, thank-you tracking
- `apps/pledges/models.py` -- Pledge model: fulfillment tracking, late detection, monthly_equivalent calculation
- `apps/contacts/models.py` -- Contact with denormalized stats, `update_giving_stats()` method (lines 152-188)
- `apps/donations/signals.py` -- Donation signal flow: stat recalc, thank-you flag, pledge fulfillment, event creation
- `apps/dashboard/services.py` -- 7 service functions querying Donation/Pledge for dashboard widgets
- `apps/insights/services.py` -- 15+ references to `Donation.objects` for analytics/reporting
- `apps/imports/services.py` -- 1364 lines of existing SPO import pipeline
- `apps/imports/views.py` -- SPO import views for 6 entity types
- `apps/imports/urls.py` -- 30 URL patterns for existing imports
- `prompts/CSV_import_system_1.md` -- RE import spec (model schemas, import logic, CSV headers)
- `prompts/CSV_import_system_2.md` -- RE import detailed implementation spec (Prisma-based, translated to Django)
- `prompts/prayer_intentions.md` -- Prayer feature spec (UX philosophy, verification checklist)
- Frontend analysis: 30 .tsx files reference Donation/Pledge (searched via grep)

---

*Architecture research for: DonorCRM v2.0 Data Model Restructuring*
*Researched: 2026-02-20*
*Confidence: HIGH -- based on complete codebase analysis of 35+ relevant files across backend and frontend*
