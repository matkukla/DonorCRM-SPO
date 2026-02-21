# Phase 29: RE Import Pipeline (Gifts & Recurring Gifts) - Research

**Researched:** 2026-02-20
**Domain:** Django CSV import services with multi-row grouping, solicitor credit splitting, and prayer auto-creation
**Confidence:** HIGH

## Summary

Phase 29 builds the Gift and Recurring Gift import pipelines for Raiser's Edge CSV files. It extends the service layer established in Phase 28 (`apps/imports/re_services.py`) with two new orchestrator functions: `import_re_gifts()` and `import_re_recurring_gifts()`. The core complexity is multi-row grouping -- RE exports produce one row per solicitor credit per gift, so rows sharing a Gift ID must be collapsed into one Gift record with multiple GiftCredit records. This same grouping pattern applies to Recurring Gifts.

A secondary but important feature is automatic PrayerIntention creation from the `"Gift Specific Attributes Prayer Requests Description"` column. Per CONTEXT.md decisions, any non-empty value (passing a basic stoplist/sanity check) creates a PrayerIntention linked to the donor contact. This requires a model change: PrayerIntention.gift must change from a ForeignKey to a ManyToManyField so that multiple gifts from the same donor with the same prayer text can share one PrayerIntention record. Prayer dedup is by contact + normalized description text.

The existing Phase 28 infrastructure provides all shared utilities needed: `decode_csv_bytes()`, `check_duplicate_import()`, `_build_header_mapping()`, and the header alias pattern. The Gift and RecurringGift models (Phase 27) are already in place with `external_gift_id`, `amount_cents` (PositiveBigIntegerField for cents), and solicitor credit junction tables. Fund matching uses the existing `Fund` model's `external_id` field.

**Primary recommendation:** Follow the same service orchestrator pattern from Phase 28, adding `import_re_gifts()` and `import_re_recurring_gifts()` to `re_services.py`. The key new pattern is a two-pass approach: first pass groups rows by Gift ID into a dict of gift groups, second pass creates Gift + GiftCredit records per group. Prayer auto-creation runs inline during gift import, not as a separate step.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Multi-row grouping**: Rows sharing a Gift ID are collapsed into one Gift record + multiple GiftCredit records (one per solicitor row)
- **Gift amount source**: Gift amount comes from a dedicated amount column (first row of the group), NOT summed from credits
- **Same grouping for recurring**: Same grouping pattern applies to Recurring Gifts (group by Recurring Gift ID, first row = amount, credits per solicitor) -- Claude adapts based on actual RE CSV format differences
- **Missing contact handling**: If a gift group references a Contact (Constituent ID) not found in DonorCRM: skip the entire gift group, log the error, continue processing remaining rows
- **Reuse Phase 28 infrastructure**: Reuse ImportBatch types (RE_GIFT, RE_RECURRING_GIFT) and the existing SHA256 dedup/error collection infrastructure
- **Prayer column**: The RE CSV column "Gift Specific Attributes Prayer Requests Description" drives auto-creation
- **Prayer creation rule**: Any non-empty value in that column creates a PrayerIntention -- no heavyweight keyword filtering
- **Prayer stoplist**: Apply a stoplist + basic sanity checks (e.g., skip values that are just whitespace, punctuation, or common non-prayer noise)
- **Prayer title**: First ~50-80 chars of the description text, truncated cleanly
- **Prayer description**: Full text from the CSV column
- **Prayer dedup**: Dedupe by contact + normalized description text -- same donor with same prayer text across multiple gifts = one PrayerIntention
- **Model change required**: PrayerIntention.gift FK to M2M relationship with Gift, so multiple gifts can link to one prayer intention
- **Prayer default status**: New PrayerIntentions default to status=ACTIVE

### Claude's Discretion
- Solicitor matching: how to handle gift rows referencing solicitors not in the Solicitor table (auto-create vs skip credit, following Phase 28 patterns)
- Recurring Gift CSV format adaptation: same core pattern as gifts, but adapt field mapping for installment-specific columns (frequency, start_date, end_date, status)
- Stoplist contents for prayer description filtering
- Fund matching/creation from CSV fund columns
- Exact error message wording for row-level failures

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IMP-03 | RE Gift import with multi-row grouping by Gift ID, GiftCredit creation per solicitor, and Contact linking | Gift model has `external_gift_id` with conditional UniqueConstraint, GiftCredit junction table with `unique_gift_solicitor_credit` constraint, Contact.external_constituent_id for linking, multi-row grouping pattern documented below |
| IMP-04 | RE Recurring Gift import with same grouping pattern, installment fields, and status tracking | RecurringGift model has frequency choices (8 options), status choices (5 options), start_date/end_date fields, RecurringGiftCredit junction table, same grouping pattern as Gift |
| IMP-10 | Prayer intention auto-creation from RE gift description field during gift import | PrayerIntention model exists with contact FK (required), gift FK (needs M2M migration), title/description/status fields, ACTIVE default status |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2.27 | ORM, migrations, management commands | Already in project |
| djangorestframework | 3.16.1 | API endpoints with MultiPartParser | Already in project |
| Python csv module | stdlib | CSV parsing with DictReader | Already used in re_services.py |
| Python hashlib | stdlib | SHA256 file hashing | Already used in re_services.py |
| Python codecs | stdlib | Encoding detection/fallback | Already used in re_services.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python re module | stdlib | Prayer stoplist regex checks | For whitespace/punctuation-only detection |
| Python unicodedata | stdlib | Text normalization for prayer dedup | Normalize accented characters in description text |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline prayer creation during gift import | Separate post-import prayer creation step | Inline is simpler, avoids double-iteration over gifts, and keeps the atomic transaction consistent. Use inline. |
| Two-pass grouping (collect then create) | Single-pass with lookahead | Two-pass is clearer and safer -- first pass collects all rows into groups, second pass creates records. Single-pass would need to handle out-of-order Gift IDs and partial group failures. |
| Auto-create missing solicitors | Skip credits for unknown solicitors | Per Phase 28 pattern: solicitors must be imported first via separate RE Solicitor CSV. Skip credit with error for unknown solicitors. |

**Installation:** No new packages needed. All functionality uses stdlib and existing dependencies.

## Architecture Patterns

### Recommended File Structure
```
apps/imports/
├── re_services.py              # MODIFY - add gift + recurring gift import orchestrators
├── views.py                     # MODIFY - add RE Gift + Recurring Gift import views
├── urls.py                      # MODIFY - add re/gifts/ and re/recurring-gifts/ URL patterns
├── management/
│   └── commands/
│       ├── import_re_gifts.py           # NEW - management command
│       └── import_re_recurring_gifts.py # NEW - management command
apps/prayers/
├── models.py                    # MODIFY - PrayerIntention.gift FK -> M2M
├── migrations/
│   └── 0002_alter_prayerintention_gift_m2m.py  # NEW - migration
apps/gifts/
├── models.py                    # EXISTING - no changes needed (models ready from Phase 27)
```

### Pattern 1: Two-Pass Multi-Row Grouping
**What:** Read all CSV rows first, group by Gift ID, then create records per group.
**When to use:** Any RE import where multiple CSV rows map to one parent record (Gift or RecurringGift).
**Example:**
```python
from collections import defaultdict

def _group_rows_by_gift_id(
    reader: csv.DictReader,
    col_map: dict[str, str | None],
    gift_id_field: str,
) -> tuple[dict[str, list[dict]], list[dict], int]:
    """Group CSV rows by Gift ID.

    Returns:
        groups: {gift_id: [row_data_dicts]}
        errors: [{row, error}] for rows with missing gift ID
        total_rows: total CSV data rows processed
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    errors: list[dict] = []
    total_rows = 0

    for row_number, row in enumerate(reader, start=2):
        total_rows += 1
        # Build row_data from col_map
        row_data: dict[str, str] = {}
        for canonical, actual_col in col_map.items():
            if actual_col is not None:
                row_data[canonical] = (row.get(actual_col) or '').strip()

        gift_id = row_data.get(gift_id_field, '')
        if not gift_id:
            errors.append({
                'row': row_number,
                'error': f'Row {row_number}: Missing gift ID',
            })
            continue

        row_data['_row_number'] = str(row_number)  # Track source row
        groups[gift_id].append(row_data)

    return dict(groups), errors, total_rows
```
**Confidence:** HIGH -- this is a standard ETL pattern for denormalized CSV data.

### Pattern 2: Gift Group Processing
**What:** Process a group of rows (same Gift ID) into one Gift + multiple GiftCredits.
**When to use:** For each group after grouping phase.
**Example:**
```python
def _process_gift_group(
    gift_id: str,
    rows: list[dict],
    owner: User,
    solicitor_lookup: dict[str, Solicitor],
) -> tuple[Gift | None, list[dict]]:
    """Process a gift group into Gift + GiftCredit records.

    First row provides gift-level data (amount, date, contact, fund).
    Each row provides one GiftCredit (solicitor + credit amount).

    Returns (gift_or_none, errors).
    """
    errors = []
    first_row = rows[0]

    # Gift-level data from first row
    constituent_id = first_row.get('constituent_id', '')
    contact = Contact.objects.filter(
        external_constituent_id=constituent_id
    ).first() if constituent_id else None

    if not contact:
        # Skip entire group -- per CONTEXT.md decision
        row_nums = ', '.join(r['_row_number'] for r in rows)
        errors.append({
            'row': int(first_row['_row_number']),
            'error': f'Constituent ID "{constituent_id}" not found -- '
                     f'skipping gift group {gift_id} (rows {row_nums})',
        })
        return None, errors

    # Parse amount (cents-based)
    amount_str = first_row.get('amount', '')
    amount_cents = _parse_amount_to_cents(amount_str)

    # Create Gift
    gift = Gift.objects.create(
        external_gift_id=gift_id,
        donor_contact=contact,
        amount_cents=amount_cents,
        gift_date=parsed_date,
        fund=matched_fund,
        description=first_row.get('description', ''),
    )

    # Create GiftCredits -- one per row with a solicitor
    for row in rows:
        solicitor_name = row.get('solicitor_name', '')
        if not solicitor_name:
            continue
        norm_name = normalize_solicitor_name(solicitor_name)
        solicitor = solicitor_lookup.get(norm_name)
        if not solicitor:
            errors.append({
                'row': int(row['_row_number']),
                'error': f'Solicitor "{solicitor_name}" not found -- '
                         f'credit skipped for gift {gift_id}',
            })
            continue
        credit_amount = _parse_amount_to_cents(row.get('credit_amount', ''))
        GiftCredit.objects.create(
            gift=gift,
            solicitor=solicitor,
            amount_cents=credit_amount or amount_cents,
        )

    return gift, errors
```
**Confidence:** HIGH -- follows the data model structure (Gift + GiftCredit) established in Phase 27.

### Pattern 3: Prayer Auto-Creation
**What:** Check prayer description column, create PrayerIntention if non-empty and passes stoplist.
**When to use:** After creating each Gift during import.
**Example:**
```python
PRAYER_STOPLIST = {
    'n/a', 'na', 'none', 'no', 'yes', '-', '--', '...', 'test',
    'x', 'xx', 'xxx', 'general', 'same', 'same as above',
}

def _maybe_create_prayer_intention(
    gift: Gift,
    prayer_text: str,
    contact: Contact,
    seen_prayers: dict[tuple, PrayerIntention],
) -> PrayerIntention | None:
    """Create or link PrayerIntention from gift description.

    Dedup key: (contact.id, normalized_text)
    If same prayer already created for this contact in this import,
    add the gift to the existing M2M relationship.
    """
    text = prayer_text.strip()
    if not text:
        return None

    # Stoplist check
    if text.lower() in PRAYER_STOPLIST:
        return None

    # Sanity: skip if all whitespace/punctuation
    if not any(c.isalnum() for c in text):
        return None

    # Normalize for dedup
    normalized = text.lower().strip()
    dedup_key = (contact.id, normalized)

    if dedup_key in seen_prayers:
        # Same prayer text for same contact -- just link the gift
        existing = seen_prayers[dedup_key]
        existing.gifts.add(gift)  # M2M
        return existing

    # Also check database for existing prayer with same text
    existing_db = PrayerIntention.objects.filter(
        contact=contact,
        description__iexact=text,
    ).first()

    if existing_db:
        existing_db.gifts.add(gift)
        seen_prayers[dedup_key] = existing_db
        return existing_db

    # Create new PrayerIntention
    title = text[:80].rsplit(' ', 1)[0] if len(text) > 80 else text
    prayer = PrayerIntention.objects.create(
        contact=contact,
        title=title,
        description=text,
        status=PrayerIntentionStatus.ACTIVE,
    )
    prayer.gifts.add(gift)  # M2M
    seen_prayers[dedup_key] = prayer
    return prayer
```
**Confidence:** HIGH -- follows CONTEXT.md decisions for prayer creation rules, stoplist, title truncation, and dedup.

### Pattern 4: Amount Parsing (Dollars to Cents)
**What:** Parse a dollar amount string from CSV into cents integer.
**When to use:** All amount fields in Gift and RecurringGift imports.
**Example:**
```python
from decimal import Decimal, InvalidOperation

def _parse_amount_to_cents(amount_str: str) -> int:
    """Parse dollar amount string to cents integer.

    Handles: "$1,234.56", "1234.56", "1,234", "$100"
    Returns 0 for empty/unparseable values.
    """
    if not amount_str:
        return 0
    # Remove dollar signs, commas, whitespace
    cleaned = amount_str.replace('$', '').replace(',', '').strip()
    if not cleaned:
        return 0
    try:
        dollars = Decimal(cleaned)
        return int(dollars * 100)
    except (InvalidOperation, ValueError):
        return 0
```
**Confidence:** HIGH -- standard pattern for cents-based money storage, using Decimal for precision.

### Pattern 5: Fund Matching
**What:** Match CSV fund column to existing Fund records by external_id or name.
**When to use:** During gift/recurring gift import to set the fund FK.
**Example:**
```python
def _build_fund_lookup() -> dict[str, Fund]:
    """Build lookup for fund matching.

    Returns dict mapping lowercased external_id and lowercased name
    to Fund objects for flexible matching.
    """
    lookup: dict[str, Fund] = {}
    for fund in Fund.objects.all():
        if fund.external_id:
            lookup[fund.external_id.lower()] = fund
        lookup[fund.name.lower()] = fund
    return lookup
```
**Confidence:** HIGH -- Fund model has `external_id` and `name` fields, both usable for matching.

### Anti-Patterns to Avoid
- **Single-pass processing without grouping:** Processing rows one at a time and using `get_or_create` for Gift records leads to race conditions and incorrect credit assignment when rows arrive out of order.
- **Summing credit amounts to derive gift amount:** Per CONTEXT.md, gift amount comes from the dedicated amount column, not from summing credits. Credits may not sum to gift amount (e.g., partial credits).
- **Creating PrayerIntentions in a separate post-import step:** Inline creation during import keeps the atomic transaction consistent and avoids a second pass.
- **Auto-creating solicitors during gift import:** Solicitors should be imported first via the RE Solicitor CSV. Gift import should reference existing solicitors and skip credits for unknown ones.
- **Using ForeignKey for PrayerIntention-Gift link:** Must migrate to M2M per CONTEXT.md, since the same prayer text from multiple gifts should reference one PrayerIntention.

## Critical Finding: PrayerIntention Model Change Required

**Issue:** PrayerIntention currently has a `ForeignKey` to `Gift` (nullable, SET_NULL). Per CONTEXT.md, this must change to a `ManyToManyField` so that one PrayerIntention can be linked to multiple gifts.

**Impact:** Requires a Django migration to:
1. Remove the existing `gift` ForeignKey field
2. Add a `gifts` ManyToManyField to Gift

**Current model:**
```python
class PrayerIntention(TimeStampedModel):
    gift = models.ForeignKey(
        'gifts.Gift',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prayer_intentions',
    )
```

**Required change:**
```python
class PrayerIntention(TimeStampedModel):
    gifts = models.ManyToManyField(
        'gifts.Gift',
        blank=True,
        related_name='prayer_intentions',
    )
```

**Migration approach:** Since no PrayerIntention records exist yet (the model is new from Phase 27, no data populated), this can be a simple field replacement. Django will create the junction table `prayer_intention_gifts` automatically.

**Admin update:** PrayerIntentionAdmin currently lists `'gift'` in `list_display` -- this must be removed or changed since M2M fields cannot be in `list_display`.

**Confidence:** HIGH -- the CONTEXT.md decision is explicit. The migration is non-destructive since no data exists yet.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dollar-to-cents conversion | Manual float multiplication | `Decimal` parsing with `int(d * 100)` | Float multiplication introduces rounding errors ($1.10 * 100 = 109.99...). Decimal is exact. |
| CSV multi-row grouping | Custom stateful parser | `defaultdict(list)` grouping in first pass | Standard pattern, clear, testable, handles out-of-order rows |
| Solicitor name matching | Custom fuzzy match | Existing `normalize_solicitor_name()` + dict lookup | Already built and tested in Phase 28 |
| SHA256 dedup | Custom hash check | Existing `check_duplicate_import()` | Already built in Phase 28 |
| Encoding detection | chardet library | Existing `decode_csv_bytes()` | Already built in Phase 28 |
| Header mapping | Hardcoded column indices | Existing `_build_header_mapping()` with alias dict | Already built in Phase 28, handles RE header variations |

**Key insight:** Phase 28 built the entire shared utility layer. Phase 29 only needs to add two new orchestrator functions (gifts, recurring gifts) plus the prayer auto-creation logic. The grouping pattern is the main new technical challenge.

## Common Pitfalls

### Pitfall 1: Gift Amount vs Credit Amount Confusion
**What goes wrong:** Using the wrong column for Gift.amount_cents -- either summing credits or using the credit amount column instead of the gift amount column.
**Why it happens:** RE exports have both a gift-level amount and per-row credit amounts. If rows share a Gift ID, each row may show the credit amount, not the total gift amount.
**How to avoid:** Per CONTEXT.md: "Gift amount comes from a dedicated amount column (first row of the group)." Always use the gift amount column from the first row of the group. GiftCredit amounts come from each row's credit amount column.
**Warning signs:** Gift amounts don't match expected totals; amounts seem too small (because they're per-credit, not total).

### Pitfall 2: Missing Constituent Skips Entire Group
**What goes wrong:** If any row in a gift group has a constituent ID not in DonorCRM, the entire gift group (all rows with that Gift ID) should be skipped.
**Why it happens:** Per CONTEXT.md decision: "If a gift group references a Contact (Constituent ID) not found in DonorCRM: skip the entire gift group."
**How to avoid:** Check constituent existence BEFORE creating any records for the group. All rows in a group reference the same constituent (the donor). If not found, skip all rows and log one error for the group.
**Warning signs:** Orphaned GiftCredit records, IntegrityError on donor_contact FK.

### Pitfall 3: External Gift ID UniqueConstraint on Re-Import
**What goes wrong:** Importing a different CSV file that contains some of the same Gift IDs causes IntegrityError on the `unique_external_gift_id` constraint.
**Why it happens:** Gift.external_gift_id has a conditional UniqueConstraint (non-empty only). A new CSV file with overlapping Gift IDs (but different SHA256 hash, so dedup doesn't catch it) will try to create duplicates.
**How to avoid:** Before creating a Gift, check if `Gift.objects.filter(external_gift_id=gift_id).exists()`. If exists, skip the group (increment skipped_count). This is analogous to the solicitor dedup-against-database pattern in Phase 28.
**Warning signs:** IntegrityError during import, partial imports.

### Pitfall 4: Prayer Dedup Must Be Case-Insensitive
**What goes wrong:** Same prayer text in different cases creates duplicate PrayerIntentions.
**Why it happens:** "Please pray for my family" and "Please Pray For My Family" would be different strings.
**How to avoid:** Normalize text to lowercase for dedup key. Use `description__iexact` for database lookups.
**Warning signs:** Multiple PrayerIntentions with same text for same contact.

### Pitfall 5: PrayerIntention Title Truncation Mid-Word
**What goes wrong:** Title is truncated at exactly 80 characters, splitting a word: "Please pray for my family as we transition to a new ci" (cut mid-"city").
**Why it happens:** Naive `text[:80]` truncation.
**How to avoid:** Find the last space before the 80-char boundary and truncate there. If no space exists (single very long word), truncate at 80 with ellipsis.
**Warning signs:** Titles ending mid-word in the prayer intentions list.

### Pitfall 6: Frequency Mapping for Recurring Gifts
**What goes wrong:** RE uses different frequency labels than the RecurringGiftFrequency choices, causing validation failures.
**Why it happens:** RE exports might say "Monthly" (matching) but could also say "Semi-Annually" with different hyphenation/spacing.
**How to avoid:** Build a case-insensitive mapping from RE frequency strings to RecurringGiftFrequency values. Include common variations: "monthly", "bi-monthly", "bimonthly", "semi-annual", "semi-annually", "semiannually", "bi-weekly", "biweekly", "weekly", "quarterly", "annual", "annually", "yearly", "irregular".
**Warning signs:** All recurring gifts getting skipped with "invalid frequency" errors.

### Pitfall 7: Transaction Atomicity for Gift Groups
**What goes wrong:** A failure creating one GiftCredit in a group leaves the Gift record without all its credits.
**Why it happens:** If the outer transaction wraps all gifts but inner credit creation fails silently.
**How to avoid:** Use `transaction.atomic()` with savepoints. Each gift group should be processed in its own savepoint so that a failure in one group rolls back only that group, not the entire import.
**Warning signs:** Gifts with incomplete credit records.

## Code Examples

### RE Gift CSV Expected Header Aliases
```python
# Based on RE export conventions and Phase 28 alias pattern
GIFT_HEADER_ALIASES: dict[str, str] = {
    # Gift ID
    'gift_id': 'gift_id',
    'gf_id': 'gift_id',
    'gift id': 'gift_id',
    'gf_system_id': 'gift_id',
    'gift system record id': 'gift_id',
    # Constituent ID
    'gf_cnbio_id': 'constituent_id',
    'constituent_id': 'constituent_id',
    'constituent id': 'constituent_id',
    'cnbio_id': 'constituent_id',
    'consid': 'constituent_id',
    # Amount (gift-level)
    'gf_amount': 'amount',
    'gift_amount': 'amount',
    'gift amount': 'amount',
    'amount': 'amount',
    # Date
    'gf_date': 'gift_date',
    'gift_date': 'gift_date',
    'gift date': 'gift_date',
    'date': 'gift_date',
    # Fund
    'gf_fund': 'fund',
    'fund': 'fund',
    'fund_id': 'fund',
    'fund id': 'fund',
    'fund_description': 'fund',
    # Description
    'gf_description': 'description',
    'description': 'description',
    'gift description': 'description',
    # Solicitor name (may repeat with index: CnSol_1_01_Name, CnSol_1_02_Name)
    'solicitor_name': 'solicitor_name',
    'solicitor name': 'solicitor_name',
    'cnsol_1_01_name': 'solicitor_name',
    'gf_cnsol_1_01_name': 'solicitor_name',
    # Credit amount (per-solicitor)
    'credit_amount': 'credit_amount',
    'gf_cnsol_1_01_amount': 'credit_amount',
    # Prayer description
    'gift specific attributes prayer requests description': 'prayer_description',
    'prayer_requests_description': 'prayer_description',
    'prayer requests description': 'prayer_description',
    'prayer description': 'prayer_description',
}
```
**Confidence:** MEDIUM -- RE headers are installation-specific. This alias set covers the most common RE naming conventions and the specific column name from CONTEXT.md. May need expansion based on real exports.

### RE Recurring Gift CSV Expected Header Aliases
```python
RECURRING_GIFT_HEADER_ALIASES: dict[str, str] = {
    # Recurring Gift ID
    'recurring_gift_id': 'gift_id',
    'rg_id': 'gift_id',
    'recurring gift id': 'gift_id',
    'gift_id': 'gift_id',
    'gf_id': 'gift_id',
    # Constituent ID (same aliases as gift)
    'gf_cnbio_id': 'constituent_id',
    'constituent_id': 'constituent_id',
    'constituent id': 'constituent_id',
    'cnbio_id': 'constituent_id',
    'consid': 'constituent_id',
    # Amount (per-installment)
    'gf_amount': 'amount',
    'amount': 'amount',
    'installment_amount': 'amount',
    'installment amount': 'amount',
    # Frequency
    'gf_installment_frequency': 'frequency',
    'installment_frequency': 'frequency',
    'frequency': 'frequency',
    'installment frequency': 'frequency',
    # Start date
    'gf_date': 'start_date',
    'start_date': 'start_date',
    'start date': 'start_date',
    'date_1st_pay': 'start_date',
    # End date
    'gf_end_date': 'end_date',
    'end_date': 'end_date',
    'end date': 'end_date',
    # Status
    'gf_status': 'status',
    'status': 'status',
    'gift status': 'status',
    # Fund
    'gf_fund': 'fund',
    'fund': 'fund',
    'fund_id': 'fund',
    # Solicitor
    'solicitor_name': 'solicitor_name',
    'solicitor name': 'solicitor_name',
    'cnsol_1_01_name': 'solicitor_name',
    # Credit amount
    'credit_amount': 'credit_amount',
    'gf_cnsol_1_01_amount': 'credit_amount',
    # Description
    'description': 'description',
    'gf_description': 'description',
}
```
**Confidence:** MEDIUM -- same caveat as gift headers. Frequency and status columns may use RE-specific naming.

### Frequency Mapping
```python
# Map RE frequency strings to RecurringGiftFrequency choices
FREQUENCY_MAP: dict[str, str] = {
    'monthly': RecurringGiftFrequency.MONTHLY,
    'quarterly': RecurringGiftFrequency.QUARTERLY,
    'semi-annually': RecurringGiftFrequency.SEMI_ANNUALLY,
    'semi-annual': RecurringGiftFrequency.SEMI_ANNUALLY,
    'semiannually': RecurringGiftFrequency.SEMI_ANNUALLY,
    'semi annually': RecurringGiftFrequency.SEMI_ANNUALLY,
    'annually': RecurringGiftFrequency.ANNUALLY,
    'annual': RecurringGiftFrequency.ANNUALLY,
    'yearly': RecurringGiftFrequency.ANNUALLY,
    'bimonthly': RecurringGiftFrequency.BIMONTHLY,
    'bi-monthly': RecurringGiftFrequency.BIMONTHLY,
    'bi monthly': RecurringGiftFrequency.BIMONTHLY,
    'biweekly': RecurringGiftFrequency.BIWEEKLY,
    'bi-weekly': RecurringGiftFrequency.BIWEEKLY,
    'bi weekly': RecurringGiftFrequency.BIWEEKLY,
    'weekly': RecurringGiftFrequency.WEEKLY,
    'irregular': RecurringGiftFrequency.IRREGULAR,
}
```
**Confidence:** HIGH -- maps all RecurringGiftFrequency choices with common string variations.

### Status Mapping for Recurring Gifts
```python
# Map RE status strings to RecurringGiftStatus choices
STATUS_MAP: dict[str, str] = {
    'active': RecurringGiftStatus.ACTIVE,
    'held': RecurringGiftStatus.HELD,
    'completed': RecurringGiftStatus.COMPLETED,
    'cancelled': RecurringGiftStatus.CANCELLED,
    'canceled': RecurringGiftStatus.CANCELLED,  # US vs UK spelling
    'terminated': RecurringGiftStatus.TERMINATED,
}
```
**Confidence:** HIGH -- maps all RecurringGiftStatus choices plus common spelling variation.

### Orchestrator Signature
```python
def import_re_gifts(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    owner: User,
) -> ImportBatch:
    """Import RE Gift CSV end-to-end.

    Steps:
    1. SHA256 dedup check (reuse check_duplicate_import)
    2. Decode with cascading encoding (reuse decode_csv_bytes)
    3. Parse CSV, validate headers, build column mapping
    4. Group rows by Gift ID (two-pass approach)
    5. Build solicitor + fund lookups
    6. Process each gift group:
       a. Find Contact by constituent_id (skip group if not found)
       b. Check external_gift_id dedup against DB (skip if exists)
       c. Create Gift record with amount from first row
       d. Create GiftCredit records for each solicitor row
       e. Check for prayer description column, auto-create PrayerIntention
    7. Create ImportBatch record with results

    Returns ImportBatch (may be existing if duplicate).
    """
```
**Confidence:** HIGH -- directly follows Phase 28 orchestrator pattern.

## Discretion Recommendations

### Solicitor Matching During Gift Import
**Recommendation:** Gift rows referencing solicitors not in the Solicitor table should have their credit SKIPPED (not auto-create the solicitor). Log a row-level error. Include "unmatched solicitors" in the ImportBatch summary for admin review.
**Rationale:** Phase 28 established the pattern of importing solicitors first via a separate CSV. Auto-creating solicitors during gift import would bypass the name normalization and User auto-linking logic. The admin should import solicitors first, then import gifts.

### Recurring Gift CSV Format
**Recommendation:** Same core grouping pattern as gifts (group by Recurring Gift ID, first row = amount, credits per solicitor), with additional field mapping for: `frequency` (mapped via FREQUENCY_MAP), `start_date`, `end_date` (nullable), `status` (mapped via STATUS_MAP, defaults to ACTIVE if missing).
**Rationale:** RecurringGift model already has these fields from Phase 27. The mapping dicts handle RE string variations.

### Stoplist Contents
**Recommendation:** Use a small, conservative stoplist:
```python
PRAYER_STOPLIST = {
    'n/a', 'na', 'none', 'no', 'yes', '-', '--', '---', '...',
    'test', 'x', 'xx', 'xxx', 'general', 'same', 'same as above',
    'see above', 'ditto', 'tbd', 'unknown',
}
```
Plus a sanity check: skip if the text contains no alphanumeric characters (all whitespace/punctuation).
**Rationale:** Per CONTEXT.md: "Apply a stoplist + basic sanity checks." Keep the stoplist small -- the prayer feature has a "chapel, not dashboard" philosophy, so false positives (creating a prayer from noise) are worse than false negatives (missing a real prayer).

### Fund Matching/Creation
**Recommendation:** Build a fund lookup dict at import start. Match CSV fund value against Fund.external_id first (case-insensitive), then Fund.name (case-insensitive). If no match found, set Gift.fund to None and log a warning. Do NOT auto-create funds -- funds should be imported separately.
**Rationale:** Fund model exists in `apps/imports/models.py` with `external_id` and `name` fields. Auto-creating funds would add unvetted data. Missing funds are not fatal -- the gift is still valid without a fund.

### Error Message Wording
**Recommendation:** Follow Phase 28's pattern of `f'Row {row_number}: {descriptive message}'` with these specific messages:
- Missing gift ID: `Row N: Missing gift ID`
- Missing constituent: `Row N: Constituent ID "X" not found -- skipping gift group GID (rows M, N, ...)`
- Duplicate gift: `Gift ID "X" already exists -- skipping group`
- Unknown solicitor: `Row N: Solicitor "X" not found -- credit skipped for gift GID`
- Invalid amount: `Row N: Invalid amount "X" -- cannot parse as dollar value`
- Invalid date: `Row N: Invalid date "X" -- expected YYYY-MM-DD or MM/DD/YYYY`
- Invalid frequency: `Row N: Unknown frequency "X" for recurring gift RID`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-row-per-record import | Multi-row grouping by ID | Phase 29 (new) | Handles RE's denormalized solicitor credit export format |
| PrayerIntention.gift FK | PrayerIntention.gifts M2M | Phase 29 (new) | Enables prayer dedup across multiple gifts from same donor |
| No prayer auto-creation | Inline prayer creation during import | Phase 29 (new) | Surfaces RE prayer data in DonorCRM's prayer feature |

**Key insight from RE export format:** RE exports gifts in a "one row per solicitor credit" format. A gift with 3 solicitor credits appears as 3 CSV rows with the same Gift ID. The gift-level data (amount, date, fund, description) is repeated on each row, but the solicitor name and credit amount differ. This is not documented clearly in Blackbaud's public docs but is the standard behavior of the RE Export tool.

## Open Questions

1. **RE CSV exact header names for this installation**
   - What we know: RE allows admins to customize export column headers. CONTEXT.md specifies the prayer column as "Gift Specific Attributes Prayer Requests Description"
   - What's unclear: Exact headers for other columns (Gift ID, Amount, Date, etc.)
   - Recommendation: Implement case-insensitive alias matching (same as Phase 28). The prayer column name is locked. Other headers will be confirmed with the first real import. The alias dict can be extended easily.
   - Confidence: MEDIUM

2. **Date format in RE exports**
   - What we know: RE can export dates as MM/DD/YYYY, YYYY-MM-DD, or other locale-specific formats
   - What's unclear: Which format this installation uses
   - Recommendation: Support multiple date formats with cascading parse: try `YYYY-MM-DD` first, then `MM/DD/YYYY`, then `M/D/YYYY`. Use Python's `datetime.strptime` with multiple format strings.
   - Confidence: HIGH (the parsing approach is sound regardless of format)

3. **Credit amount vs gift amount column differentiation**
   - What we know: RE rows may have both a gift-level amount and a per-solicitor credit amount in different columns
   - What's unclear: Whether the CSV has separate columns or if the same "Amount" column serves both purposes
   - Recommendation: Support both scenarios: if a separate credit amount column exists, use it for GiftCredit.amount_cents. If not, default the credit amount to the gift amount (full credit to each solicitor).
   - Confidence: MEDIUM

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `apps/imports/re_services.py` -- Phase 28 shared utilities and orchestrator patterns (decode_csv_bytes, check_duplicate_import, _build_header_mapping, normalize_solicitor_name)
- Codebase analysis: `apps/gifts/models.py` -- Gift, GiftCredit, RecurringGift, RecurringGiftCredit models with cents-based amounts and UniqueConstraints
- Codebase analysis: `apps/prayers/models.py` -- PrayerIntention model with FK to Gift (needs M2M migration)
- Codebase analysis: `apps/imports/models.py` -- ImportBatch model with RE_GIFT and RE_RECURRING_GIFT types, SHA256 dedup
- Codebase analysis: `apps/contacts/models.py` -- Contact model with external_constituent_id for gift-to-contact linking
- Codebase analysis: `apps/imports/views.py` -- RE import API endpoint patterns (RESolicitorImportView, REConstituentImportView)
- Phase 28 plans/summaries -- established patterns for service layer, management commands, API endpoints, and header alias mapping

### Secondary (MEDIUM confidence)
- [Megaphone Tech RE Export Guide](https://hq.megaphonetech.com/projects/commons/wiki/Exporting_Raisers_Edge_for_CiviCRM) -- RE gift data structure, GiftSolicitor table, split gift behavior
- [Palante Tech RE Export Guide](https://redmine.palantetech.coop/projects/commons/wiki/Exporting_Raiser's_Edge_for_CiviCRM) -- RE gift export SQL with field names (CONSTIT_ID, DTE, Amount, FUND, INSTALLMENT_FREQUENCY)
- [Blackbaud Gift Records Guide](https://help.blackbaud.com/docs/0/assets/guides/re/gifts.pdf) -- RE gift management documentation (not directly extractable from PDF)

### Tertiary (LOW confidence)
- RE CSV header names are installation-specific. The alias mapping approach handles this, but exact headers need confirmation with real export files.
- RE recurring gift export format may differ from one-time gift export format in ways not documented publicly.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib + existing project dependencies, no new packages
- Architecture: HIGH -- directly extends Phase 28 patterns with well-defined grouping pattern
- Gift import logic: HIGH -- models exist, grouping pattern is standard ETL, CONTEXT.md provides clear decisions
- Recurring gift import logic: HIGH -- same pattern as gifts with additional field mapping
- Prayer auto-creation: HIGH -- CONTEXT.md provides explicit rules, model change is straightforward
- RE header format: MEDIUM -- headers vary by installation, alias approach handles variations
- Pitfalls: HIGH -- identified from data model constraints and CONTEXT.md decisions

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (30 days -- stable domain, no fast-moving libraries)
