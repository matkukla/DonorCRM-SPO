# Pitfalls Research: v2.0 -- Model Replacement, RE Import, Data Migration

**Domain:** Replacing core data models (Donation->Gift, Pledge->RecurringGift) in a live app with 41+ dependent files, building Raiser's Edge CSV import pipeline, SHA256-based dedup, solicitor name matching, prayer intentions
**Researched:** 2026-02-20
**Confidence:** HIGH (verified against actual DonorCRM codebase with full dependency graph analysis)

## Critical Pitfalls

### Pitfall 1: Renaming Donation->Gift Breaks 77+ Dependent References Across 8 Apps

**What goes wrong:**
The `Donation` model is referenced by 36 frontend files and 41 backend files spanning 8 Django apps. Renaming it to `Gift` requires updating:
- **Backend:** `apps/donations/models.py` (model + DonationType + PaymentMethod), `apps/donations/signals.py` (post_save/post_delete receivers), `apps/donations/serializers.py`, `apps/donations/views.py`, `apps/donations/filters.py`, `apps/donations/export_views.py`, `apps/donations/admin.py`, `apps/imports/services.py` (6 references to Donation model), `apps/dashboard/services.py` (9 references to Donation), `apps/insights/services.py` (12 references to Donation), `apps/events/models.py` (EventType.DONATION_RECEIVED), `apps/contacts/models.py` (Contact.update_giving_stats queries `self.donations.all()`), plus all test files
- **Frontend:** `api/donations.ts` (Donation interface, DonationType, endpoints), `hooks/useDonations.ts`, `pages/donations/DonationList.tsx`, `pages/donations/DonationDetail.tsx`, `pages/donations/DonationForm.tsx`, `components/dashboard/RecentDonations.tsx`, `components/dashboard/LateDonations.tsx`, `components/dashboard/MonthlyGiftsCard.tsx`, `pages/insights/DonationsByMonthYear.tsx`, `pages/contacts/ContactDetail.tsx` (donations tab), `lib/filter-presets.ts`, `App.tsx` (routes), `components/layout/Sidebar.tsx` (navigation)

If any reference is missed, the app crashes at runtime. Django migration will rename the table but string references in `related_name='donations'`, `db_table='donations'`, `EventType.DONATION_RECEIVED`, and frontend API paths will break silently.

**Why it happens:**
Developers focus on the model rename and forget the cascading impact: related_names on ForeignKey fields, reverse relation usage in querysets (`self.donations.all()`), signal sender references, EventType enum values, API URL paths, React Query cache keys, and UI string labels. Django's `RenameModel` migration handles the database table and foreign key constraints but NOT string-based references.

**How to avoid:**
Use a phased approach that avoids a "big bang" rename:

Phase A -- Create new Gift model alongside Donation:
```python
# apps/gifts/models.py (NEW app)
class Gift(TimeStampedModel):
    # Copy all fields from Donation
    # Add new fields: credit_type, solicitor, prayer_description
    contact = models.ForeignKey('contacts.Contact', related_name='gifts', ...)
    # Keep external_id for RE import dedup
```

Phase B -- Data migration: copy Donation records to Gift records
```python
def forwards(apps, schema_editor):
    Donation = apps.get_model('donations', 'Donation')
    Gift = apps.get_model('gifts', 'Gift')
    for donation in Donation.objects.all().iterator():
        Gift.objects.create(
            id=donation.id,  # Preserve UUIDs for FK references
            contact=donation.contact,
            amount=donation.amount,
            date=donation.date,
            # ... map all fields
        )
```

Phase C -- Update all dependent code to use Gift instead of Donation
Phase D -- Drop Donation model (after verification period)

Do NOT use Django's `RenameModel` migration because the model is not just being renamed -- it is gaining new fields (credit_type, solicitor FK, prayer_description) and the app name changes from `donations` to `gifts`.

**Warning signs:**
- Planning to do a single migration that renames Donation to Gift
- Not running a full-text search for "donation" (case-insensitive) across the entire codebase
- Not updating `related_name='donations'` on Contact FK
- EventType.DONATION_RECEIVED left unchanged (should become GIFT_RECEIVED or kept for backward compat)
- Frontend API paths `/api/donations/` changed without redirect handling

**Phase to address:**
Phase 1 (New models) -- Create Gift/RecurringGift models in a new app; Phase 2 (Data migration); Phase 3 (Update all dependent code); Phase 4 (Remove old models)

---

### Pitfall 2: Contact.update_giving_stats() Hardcoded to Query self.donations.all()

**What goes wrong:**
`Contact.update_giving_stats()` (contacts/models.py:152-188) aggregates `self.donations.all()` to compute `total_given`, `gift_count`, `first_gift_date`, `last_gift_date`, and `last_gift_amount`. After the model rename, this reverse relation breaks. But even before the rename, if you create Gift records alongside existing Donation records during migration, the stats will be wrong because `update_giving_stats()` only queries the old `donations` relation and ignores the new `gifts` relation.

During the transition period where both models exist, a gift recorded in the new Gift model will NOT update contact stats. The dashboard will show stale/incorrect totals. Missionaries will see wrong "Total Given" amounts.

**Why it happens:**
`update_giving_stats()` is called from `apps/donations/signals.py` on Donation post_save/post_delete. If new Gift records are created through a different signal path (or no signal at all), the contact stats never update. The method itself queries `self.donations.all()` (the reverse relation), which is specific to the Donation model's `related_name`.

**How to avoid:**
1. When creating the Gift model, immediately wire up equivalent signals:
```python
# apps/gifts/signals.py
@receiver(post_save, sender=Gift)
def update_contact_stats_on_gift_save(sender, instance, created, **kwargs):
    instance.contact.update_giving_stats_from_gifts()
```

2. Update `Contact.update_giving_stats()` to query the active model:
```python
def update_giving_stats(self):
    """Recalculate giving stats. Queries Gift model (v2.0+)."""
    from apps.gifts.models import Gift
    gifts = Gift.objects.filter(contact=self)
    agg = gifts.aggregate(
        total=models.Sum('amount'),
        count=models.Count('id'),
        first=models.Min('date'),
        last=models.Max('date')
    )
    # ... same logic
```

3. During the dual-model transition, query BOTH:
```python
def update_giving_stats(self):
    from django.db.models import Sum, Count, Min, Max
    # Query both old and new models during transition
    old_agg = self.donations.aggregate(...)
    new_agg = self.gifts.aggregate(...)
    # Combine: max of maxes, min of mins, sum of sums
```

**Warning signs:**
- Contact "Total Given" showing $0 after importing gifts through the new model
- Dashboard "Recent Gifts" widget empty while gift records exist
- `needs_thank_you` flag never set for gifts created via Gift model
- Event log missing "Gift Received" events

**Phase to address:**
Phase 1 (New models) -- signals and stat update must be wired before any Gift records are created

---

### Pitfall 3: SHA256 Dedup Produces Different Hashes for Identical CSV Content

**What goes wrong:**
The v2.0 plan uses SHA256 hash of uploaded CSV file content for import deduplication (ImportBatch). A user uploads a Raiser's Edge CSV export, SHA256 is computed, stored, and subsequent uploads with the same hash are flagged as duplicates. However, the SAME logical CSV file can produce different SHA256 hashes due to:

1. **BOM markers**: Windows applications (including Excel "Save as CSV") prepend UTF-8 BOM bytes `EF BB BF` to the file. The same content without BOM has a different hash. User exports from RE -> opens in Excel -> saves as CSV (adds BOM) -> uploads. Next time they export directly from RE (no BOM) -> upload -> different hash -> duplicate import.

2. **Line endings**: RE on Windows exports with `\r\n` (CRLF). If the file passes through Git, email, or a text editor, line endings may change to `\n` (LF). Different bytes = different hash.

3. **Trailing newline**: Some exports end with a trailing newline, some don't. One byte difference = completely different SHA256.

4. **Re-encoding**: User opens CSV in Excel, makes no changes, saves. Excel re-encodes from Windows-1252 to UTF-8 (or vice versa). Smart quotes `\x93` `\x94` become `\xe2\x80\x9c` `\xe2\x80\x9d`. Different bytes = different hash.

5. **Column reordering**: RE NXT's new "Single Row Query" feature may export columns in different order than the legacy export. Same data, different CSV, different hash.

**Why it happens:**
SHA256 operates on raw bytes, not semantic content. Developers test with the same file and dedup works. Real-world users transform files between exports and uploads in ways that change bytes without changing meaning.

**How to avoid:**
Do NOT hash the raw file bytes. Normalize content before hashing:

```python
import hashlib
import csv
import io

def compute_import_hash(file_content: bytes) -> str:
    """Compute SHA256 hash of normalized CSV content for dedup."""
    # Step 1: Decode, handling BOM and encoding
    try:
        text = file_content.decode('utf-8-sig')  # Strips BOM
    except UnicodeDecodeError:
        text = file_content.decode('windows-1252')  # RE default encoding

    # Step 2: Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Step 3: Strip trailing whitespace/newlines
    text = text.strip()

    # Step 4: Parse CSV and sort rows for column-order independence
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        return hashlib.sha256(b'').hexdigest()

    # Step 5: Normalize: lowercase header, sort data rows by first column
    headers = [h.strip().lower() for h in rows[0]]
    data_rows = sorted(rows[1:], key=lambda r: r[0] if r else '')

    # Step 6: Rebuild canonical CSV for hashing
    canonical = '\n'.join(
        ','.join(cell.strip() for cell in row)
        for row in [headers] + data_rows
    )

    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

**Warning signs:**
- Using `hashlib.sha256(file.read()).hexdigest()` directly on raw bytes
- Dedup tests pass with identical files but fail when user re-saves the file
- Users reporting "This file was already imported" when the file IS new (false positive from different file with same data)
- Users importing the same data twice because the file was slightly modified (false negative)

**Phase to address:**
Phase 2 (Import pipeline) -- hashing strategy must be decided and tested before any import batch records are created

---

### Pitfall 4: Raiser's Edge CSV Encoding: Windows-1252 Smart Quotes Break UTF-8 Parser

**What goes wrong:**
Raiser's Edge is a Windows application that exports CSV in Windows-1252 encoding. Names with accents (Jose -> Jose), notes with smart quotes ("thank you" with curly quotes), and em-dashes in addresses all use Windows-1252 byte values that are invalid UTF-8. Python's default `file.read().decode('utf-8')` raises `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x92 in position N`. The entire import fails on the first non-ASCII character.

The existing CSV parser in `apps/imports/services.py` line 120 uses `csv.DictReader(io.StringIO(file_content))` where `file_content` is already decoded as a string -- the encoding issue must be handled upstream during file reading.

**Why it happens:**
- RE exports in Windows-1252 by default (confirmed by web research, HIGH confidence)
- The existing `parse_csv()` in `mpd_services.py:379-395` uses `file_bytes.decode('utf-8-sig')` -- this handles BOM but NOT Windows-1252
- Python 3's `str` type is UTF-8 internally; Windows-1252 bytes like `0x92` (right single quote), `0x93`/`0x94` (left/right double quotes), `0x96` (en-dash), `0x97` (em-dash) are invalid in UTF-8
- Developers test with ASCII-only data and never encounter the issue

**How to avoid:**
Use cascading encoding detection in the file reading layer:

```python
def decode_csv_bytes(file_bytes: bytes) -> str:
    """Decode CSV file bytes with cascading encoding detection.

    Priority: UTF-8 with BOM > UTF-8 > Windows-1252 (fallback)
    """
    # Try UTF-8 with BOM first (handles Excel "Save as UTF-8 CSV")
    if file_bytes.startswith(b'\xef\xbb\xbf'):
        return file_bytes.decode('utf-8-sig')

    # Try UTF-8
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        pass

    # Fallback to Windows-1252 (RE default)
    return file_bytes.decode('windows-1252')
```

Apply this in EVERY CSV reading path, not just the new RE import. Update the existing `parse_csv()` in `mpd_services.py` too.

**Warning signs:**
- Import fails with "invalid start byte" on files containing accented names
- `UnicodeDecodeError` in production logs
- Import works in development (ASCII test data) but fails with real RE exports
- Smart quotes appearing as `\x93` or `?` in imported notes

**Phase to address:**
Phase 2 (RE import pipeline) -- encoding handling must be the FIRST layer before any CSV parsing

---

### Pitfall 5: Raiser's Edge Multi-Row Gift Splits Create Duplicate Gift Records

**What goes wrong:**
Raiser's Edge exports "split gifts" as multiple rows. A single $1000 gift split across two funds appears as:

```csv
Gift ID,Constituent ID,Amount,Fund,Date
G-001,C-100,600.00,General Fund,01/15/2026
G-001,C-100,400.00,Mission Fund,01/15/2026
```

If the import pipeline treats each row as a separate gift, the system records two gifts totaling $1000 instead of one $1000 gift with two fund splits. The contact's `total_given` becomes $1000 (correct) but `gift_count` becomes 2 (wrong). Worse, if the Gift model has a unique constraint on `external_id`, the second row fails because `G-001` already exists.

This is the v2.0 "gift credit splitting" feature -- one gift credits multiple missionaries. But the CSV parser must understand that multiple rows with the same Gift ID represent splits of ONE gift, not separate gifts.

**Why it happens:**
RE exports gifts in a denormalized format. Each row represents a gift-fund combination, not a unique gift. The [Blackbaud community](https://renxt.ideas.aha.io/ideas/RENXT-I-8179) confirms that "split gifts would be exported to more than one row." The naive approach of "one row = one gift" does not work for RE data.

**How to avoid:**
Group rows by Gift ID before creating records:

```python
from itertools import groupby
from operator import itemgetter

def process_re_gifts(rows: list[dict]) -> list[dict]:
    """Group RE gift rows by Gift ID, handling split gifts."""
    # Sort by Gift ID for groupby
    sorted_rows = sorted(rows, key=itemgetter('gift_id'))

    gifts = []
    for gift_id, group in groupby(sorted_rows, key=itemgetter('gift_id')):
        split_rows = list(group)

        if len(split_rows) == 1:
            # Simple gift: one row = one gift
            gifts.append(split_rows[0])
        else:
            # Split gift: multiple rows = one gift with credits
            primary = split_rows[0].copy()
            primary['amount'] = sum(Decimal(r['amount']) for r in split_rows)
            primary['splits'] = [
                {'fund': r['fund'], 'amount': r['amount']}
                for r in split_rows
            ]
            gifts.append(primary)

    return gifts
```

**Warning signs:**
- `gift_count` on contacts is higher than expected after RE import
- Unique constraint violation on Gift.external_id during import
- Same gift appearing twice in the gifts list page
- Gift amounts smaller than expected (individual split amounts instead of total)

**Phase to address:**
Phase 2 (RE import pipeline) -- gift row grouping must happen BEFORE validation/creation

---

### Pitfall 6: Solicitor Name Matching Creates False Links to Wrong Missionaries

**What goes wrong:**
RE exports include a "Solicitor" field containing the missionary's name who is credited with the gift. The v2.0 plan auto-links solicitors to User accounts by name matching. Common false matches:

1. **Common names**: "John Smith" in RE matches the wrong "John Smith" user (if org has two)
2. **Name variations**: RE has "Jonathan Smith" but User account has "John Smith" (nickname)
3. **Name format**: RE exports "Smith, John" (last, first) but matching expects "John Smith" (first last)
4. **Middle names**: RE has "John A. Smith" but User has "John Smith"
5. **Married name changes**: RE has "Jane Doe" but User account was updated to "Jane Smith"
6. **Titles**: RE has "Dr. John Smith" but User has "John Smith"
7. **Special characters**: RE has "O'Brien" but matching sees "O" and "Brien" after naive splitting

A false solicitor link silently credits gifts to the wrong missionary. Their dashboard shows inflated giving totals. The correct missionary shows zero. This is a data integrity disaster that is hard to detect and harder to undo.

**Why it happens:**
The existing name matching pattern in `mpd_services.py:402-482` uses exact (first_name.lower(), last_name.lower()) matching. This works for MPD reports where names are controlled. RE data is messier: names come from external donor records, may include titles, middle names, suffixes, and formatting variations. Additionally, the MPD match handles duplicates correctly (skips to unmatched) but does not handle partial matches at all.

**How to avoid:**
1. Use the existing proven pattern: exact match with duplicate detection (from `mpd_services.py`)
2. Add normalization before matching:
```python
import re

def normalize_name(name: str) -> str:
    """Normalize name for matching: strip titles, suffixes, punctuation."""
    if not name:
        return ''
    name = name.strip().lower()
    # Remove common titles
    name = re.sub(r'^(mr|mrs|ms|dr|rev|pastor|sir)\.?\s+', '', name)
    # Remove suffixes
    name = re.sub(r'\s+(jr|sr|ii|iii|iv|phd|md|esq)\.?$', '', name)
    # Remove punctuation (O'Brien -> obrien)
    name = re.sub(r"['\-.]", '', name)
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name
```

3. Handle "Last, First" format from RE:
```python
def parse_solicitor_name(raw_name: str) -> tuple[str, str]:
    """Parse solicitor name from RE, handling 'Last, First' format."""
    if ',' in raw_name:
        parts = raw_name.split(',', 1)
        return parts[1].strip(), parts[0].strip()  # first, last
    parts = raw_name.strip().split()
    if len(parts) >= 2:
        return ' '.join(parts[:-1]), parts[-1]  # first (may include middle), last
    return raw_name.strip(), ''
```

4. CRITICAL: When multiple users match, do NOT auto-link. Send to unmatched queue for admin resolution. This is the pattern already used in MPD matching and documented as a key decision in PROJECT.md: "Duplicate user names -> unmatched."

5. Provide an admin UI to manually link unmatched solicitors to users. Store the manual link in a `SolicitorAlias` table for future auto-matching.

**Warning signs:**
- Using fuzzy matching (Levenshtein, Jaro-Winkler) instead of exact match with normalization
- Setting fuzzy threshold below 90% to "catch more matches"
- No duplicate detection -- silently picking the first match
- Not handling "Last, First" name format from RE
- No admin review queue for unmatched/ambiguous solicitors

**Phase to address:**
Phase 2 (RE import pipeline) -- solicitor matching must be built with the unmatched queue pattern from day one

---

### Pitfall 7: Data Migration Breaks if Gift Model Uses Different PK Type or FK Structure

**What goes wrong:**
The existing Donation model uses UUID primary keys (from TimeStampedModel). The new Gift model also uses UUIDs. During data migration (Donation -> Gift), developers must preserve the original UUID so that:
1. Events referencing the donation via GenericForeignKey still resolve
2. ImportRun records that referenced donation counts still make sense
3. Any external bookmarks or logs referencing the donation UUID still work

If the migration creates NEW UUIDs for Gift records, the Event model's `object_id` (UUIDField) that pointed to Donation records now points to nothing. The "What Changed" dashboard widget shows broken references.

Additionally, the Donation model has FK relationships:
- `contact` FK (CASCADE) -- must be preserved
- `pledge` FK (SET_NULL) -- must be converted to RecurringGift FK
- `fund` FK (SET_NULL) -- must be preserved
- `thanked_by` FK (SET_NULL) -- must be preserved

The `pledge` FK is the dangerous one: it points to the old Pledge model, but Gift should point to RecurringGift. This FK target change cannot be done with a simple data copy.

**Why it happens:**
Developers think of data migration as "copy rows from table A to table B" but forget about:
- GenericForeignKey references in the Event model (content_type + object_id)
- Signal side effects during migration (post_save on Gift triggers contact stat update for EVERY migrated record)
- The pledge->recurring_gift FK target change requiring a mapping table

**How to avoid:**
1. Preserve UUIDs during migration:
```python
def migrate_donations_to_gifts(apps, schema_editor):
    Donation = apps.get_model('donations', 'Donation')
    Gift = apps.get_model('gifts', 'Gift')

    # Disable signals during bulk migration
    from apps.gifts.signals import disable_gift_signals
    disable_gift_signals()

    for donation in Donation.objects.all().iterator(chunk_size=500):
        Gift.objects.create(
            id=donation.id,  # PRESERVE UUID
            contact_id=donation.contact_id,
            # ... other fields
        )

    enable_gift_signals()
```

2. Update GenericForeignKey content_type references:
```python
from django.contrib.contenttypes.models import ContentType

def update_event_content_types(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    old_ct = ContentType.objects.get_for_model(Donation)
    new_ct = ContentType.objects.get_for_model(Gift)
    Event.objects.filter(content_type=old_ct).update(content_type=new_ct)
```

3. Disable signals during migration to prevent N contact stat recalculations
4. Build Pledge->RecurringGift mapping BEFORE migrating gifts that reference pledges

**Warning signs:**
- Migration creates new UUIDs instead of preserving existing ones
- Event log shows broken references after migration
- Contact stats recalculate during migration (N+1 signals firing)
- Migration takes 10+ minutes due to signal side effects
- `pledge` FK on Gift records is NULL because the RecurringGift records don't exist yet

**Phase to address:**
Phase 3 (Data migration) -- must come AFTER both Gift and RecurringGift models exist

---

### Pitfall 8: Dashboard and Insights Services Have 21+ Direct Donation/Pledge References

**What goes wrong:**
`apps/dashboard/services.py` imports and queries `Donation` 9 times and `Pledge` 12 times. `apps/insights/services.py` has `_scope_donations()`, `_scope_pledges()`, and 12+ functions querying these models with complex aggregations (TruncMonth, TruncWeek, Subquery annotations). After the rename, ALL of these must be updated atomically. If even one function still imports `from apps.donations.models import Donation`, the entire dashboard crashes.

The frontend has matching complexity: `api/dashboard.ts` returns data shaped around the Donation/Pledge model (field names like `total_donations`, `late_pledges`, `pledge_count`). Renaming on the backend without updating the API response shape AND the frontend consumers breaks the dashboard completely.

**Why it happens:**
The dashboard and insights services were built to aggregate across Donation/Pledge models. They use the model classes directly in querysets, not through an abstraction layer. There is no service interface or repository pattern that could be swapped.

**How to avoid:**
1. Keep API response field names backward-compatible during transition. The API can return `total_donations` (not renamed to `total_gifts`) initially:
```python
# dashboard/services.py -- during transition
def get_giving_summary(user, year=None):
    # Query Gift model internally
    from apps.gifts.models import Gift
    gifts = Gift.objects.filter(contact__owner=user)
    given = gifts.filter(date__year=year).aggregate(total=Sum('amount'))

    # Return with old field names for API compatibility
    return {
        'given': given,  # field name unchanged
        # ... other fields unchanged
    }
```

2. Create a transition checklist of every function in both service files:

| Function | Model References | Update Strategy |
|----------|-----------------|-----------------|
| `get_recent_gifts()` | `Donation.objects` | Change to `Gift.objects` |
| `get_giving_summary()` | `Donation.objects`, `Pledge.objects` | Change to `Gift.objects`, `RecurringGift.objects` |
| `get_monthly_gifts()` | `Donation.objects` | Change to `Gift.objects` |
| `get_needs_attention()` | `Pledge.objects` | Change to `RecurringGift.objects` |
| `get_late_donations()` | `Pledge.objects` (confusing name!) | Change to `RecurringGift.objects`, rename function |
| `get_support_progress()` | `Pledge.objects` | Change to `RecurringGift.objects` |
| `_scope_donations()` | `Donation.objects` | Change to `Gift.objects` |
| `_scope_pledges()` | `Pledge.objects` | Change to `RecurringGift.objects` |
| `get_donations_by_month()` | `_scope_donations()` | Rename to `get_gifts_by_month()` |
| `get_donations_by_year()` | `_scope_donations()` | Rename to `get_gifts_by_year()` |
| `get_monthly_commitments()` | `_scope_pledges()` | Update scope function |
| `get_late_donations()` (insights) | `_scope_pledges()` | Rename to `get_late_recurring_gifts()` |
| `get_transactions()` | `Donation.objects` | Change to `Gift.objects` |
| `get_dashboard_overview()` | `Donation.objects` | Change to `Gift.objects` |
| `get_user_performance()` | `Donation.objects` (Subquery) | Change to `Gift.objects` |
| `get_team_trends()` | `Donation.objects` | Change to `Gift.objects` |
| `get_user_trends()` | `Donation.objects` | Change to `Gift.objects` |

3. Update all service functions in ONE phase, run the full test suite, then update the frontend

**Warning signs:**
- Updating models without updating service files
- Dashboard showing zero/stale data after migration
- `ImportError: cannot import name 'Donation' from 'apps.donations.models'`
- Frontend showing "undefined" for gift-related fields

**Phase to address:**
Phase 4 (Update dependent features) -- must be a comprehensive sweep, not piecemeal

---

### Pitfall 9: Raiser's Edge Date Format Ambiguity: MM/DD/YYYY vs DD/MM/YYYY

**What goes wrong:**
The existing `_parse_date()` in `services.py:81-100` tries multiple date formats in order: `['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']`. For the date "01/02/2026", it matches `%m/%d/%Y` first (January 2nd) but the RE export intended `%d/%m/%Y` (February 1st). Since RE is a US-centric application, `MM/DD/YYYY` is almost always correct, but organizations using RE internationally may have different locale settings.

The ambiguity is undetectable for dates where both day and month are <= 12 (e.g., "06/07/2026" could be June 7 or July 6). For dates where day > 12 (e.g., "15/01/2026"), only one format works, so it resolves correctly. The silent misparse for ambiguous dates corrupts gift dates without any error.

**Why it happens:**
The format list tries `%m/%d/%Y` before `%d/%m/%Y`. For US-based RE installations, this is correct. But the function doesn't know the data source, so it cannot make an informed choice. RE exports do not include timezone or locale metadata in the CSV.

**How to avoid:**
For RE-specific imports, enforce US date format and do NOT fall through to `%d/%m/%Y`:

```python
RE_DATE_FORMATS = ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y']  # US formats only

def parse_re_date(date_str: str) -> tuple:
    """Parse date from Raiser's Edge export (US locale assumed)."""
    if not date_str:
        return None, 'Date is required'

    cleaned = date_str.strip()

    for fmt in RE_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date(), None
        except ValueError:
            continue

    return None, f'Invalid date: "{date_str}". Expected MM/DD/YYYY or YYYY-MM-DD format.'
```

Keep the original `_parse_date()` with all formats for generic CSV imports. The RE parser should use the RE-specific date parser.

**Warning signs:**
- Gift dates in January-December range that look plausible but are off by months
- Users in non-US locales reporting "wrong dates" after import
- No date format specification in the import UI
- Reusing the generic `_parse_date()` for RE-specific imports

**Phase to address:**
Phase 2 (RE import pipeline) -- RE-specific parsers should use US date formats only

---

### Pitfall 10: Existing Donation Signals Fire During Gift Creation, Double-Counting Stats

**What goes wrong:**
The existing `apps/donations/signals.py` has `post_save` and `post_delete` receivers on the Donation model. If the new Gift model inherits from the same base or if signals are registered with a broad sender, gift creation could trigger donation signals. More subtly: if Gift records are created in the same transaction as Donation deletions (during migration), the signal handlers interact:

1. Donation signal fires `contact.update_giving_stats()` which queries `self.donations.all()`
2. Gift signal fires `contact.update_giving_stats()` which queries `self.gifts.all()`
3. During migration, both fire on the same contact, creating a race condition

The existing signal disabling mechanism (`disable_donation_signals()` / `enable_donation_signals()` using threading.local) works but is NOT used in the data migration. Running the migration without disabling signals means N contacts get N stat recalculations, each taking a database query -- a 5000-record migration fires 5000 signal handlers, each running an aggregate query.

**Why it happens:**
Django signals fire automatically on model save/delete. The migration uses `Gift.objects.create()` which triggers `post_save`. Unless signals are explicitly disabled, every single created record triggers stat recalculation. The existing `disable_donation_signals()` mechanism only covers Donation signals, not Gift signals.

**How to avoid:**
1. Create an equivalent signal disabling mechanism for Gift:
```python
# gifts/signals.py
_signal_state = threading.local()

def disable_gift_signals():
    _signal_state._skip_signals = True

def enable_gift_signals():
    _signal_state._skip_signals = False
```

2. In the data migration, disable BOTH signal sets:
```python
def migrate_donations_to_gifts(apps, schema_editor):
    from apps.donations.signals import disable_donation_signals, enable_donation_signals
    from apps.gifts.signals import disable_gift_signals, enable_gift_signals

    disable_donation_signals()
    disable_gift_signals()

    try:
        # Bulk migrate records
        # ...
        pass
    finally:
        enable_donation_signals()
        enable_gift_signals()

    # After migration, recalculate stats ONCE per affected contact
    for contact in Contact.objects.filter(gifts__isnull=False).distinct():
        contact.update_giving_stats()
```

3. Use `bulk_create()` where possible -- it does NOT trigger signals:
```python
# bulk_create skips signals entirely (Django behavior)
Gift.objects.bulk_create(gift_objects, batch_size=500)
# Then manually recalculate stats once
```

**Warning signs:**
- Migration taking 10+ minutes for a few thousand records
- Database CPU spike during migration
- Contact stats being recalculated multiple times per contact
- Post-migration stats showing double the actual total (if both old and new models are counted)

**Phase to address:**
Phase 3 (Data migration) -- signal management is a prerequisite for the migration script

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keeping both Donation and Gift models permanently | Avoids massive rename effort | Two parallel models, double maintenance, confusing codebase | Never; set a deadline to remove Donation model |
| Hashing raw file bytes instead of normalized content | Simpler dedup code | False negatives (same data, different hash) and false positives | Never; normalize before hashing |
| Using fuzzy matching for solicitor->user linking | Catches more matches | False positives silently credit gifts to wrong missionary | Never; use exact match with normalization + admin review queue |
| Skipping GenericForeignKey content_type migration | Saves one migration step | Event log shows broken references for all historical donations | Never; content_type update is essential |
| Not renaming API endpoints (/api/donations/ -> /api/gifts/) | Frontend works without changes | Confusing API inconsistency, new developers confused | Acceptable temporarily during transition; rename within same milestone |
| Keeping EventType.DONATION_RECEIVED for Gift events | No event system changes needed | Confusing audit trail, grep for "donation" still finds event code | Acceptable; add GIFT_RECEIVED alias pointing to same value |
| Not migrating existing Donation test data to Gift format | Tests pass against old model | New Gift-specific tests don't cover edge cases from old test data | Never; migrate test factories to Gift model |
| Running migration without signal disabling | Simpler migration script | 5000x slower migration, possible race conditions | Never; always disable signals during bulk operations |

## Integration Gotchas

Common mistakes when connecting Raiser's Edge imports to existing infrastructure.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| RE CSV encoding | Assuming UTF-8 | Cascading decode: UTF-8-sig -> UTF-8 -> Windows-1252 |
| RE split gifts | One row = one gift | Group rows by Gift ID, sum split amounts |
| RE solicitor names | Fuzzy matching | Exact match with normalization + "Last, First" format handling |
| RE date formats | Using generic date parser with DD/MM fallback | RE-specific parser with US-only formats (MM/DD/YYYY) |
| RE gift amounts | Treating amount string as-is | Strip `$`, `,`, handle `()` for negative amounts (existing `parse_currency` pattern) |
| SHA256 dedup | Hash raw file bytes | Normalize (strip BOM, normalize line endings, sort rows) then hash |
| Gift->Contact stats | Relying on Donation signals | Wire new Gift signals that call updated `update_giving_stats()` |
| Gift->Event log | Not creating events for new Gift model | Register post_save signal on Gift that creates Event records |
| GenericForeignKey | Forgetting content_type migration | Update Event.content_type from Donation CT to Gift CT |
| DB migration | Creating records one-by-one | Use `bulk_create()` to skip signals, then recalculate stats once per contact |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Signal-per-record during migration | Migration takes 30+ minutes | Disable signals, use bulk_create, recalculate once | >500 donation records |
| update_giving_stats called per gift during import | Import of 200 gifts takes 5 minutes | Collect affected contact IDs, update stats once per contact at end | >50 gifts per import |
| SHA256 hash computation on large CSV | Slow upload response | Compute hash on first 10KB + file size for quick dedup check | >5MB files |
| Contact.monthly_pledge_amount iterates pledges in Python | Slow with many pledges | Use DB annotation with Case/When for monthly_equivalent calculation | >20 active pledges per contact |
| Not indexing Gift.external_id for RE dedup lookups | Full table scan on each import row | Ensure unique index on external_id (already exists on Donation, replicate on Gift) | >10,000 gift records |
| Frontend re-renders entire gift list on stats update | UI flickers after import | Use React Query invalidation targeting specific query keys, not broad invalidation | >100 gifts displayed |

## Security Mistakes

Domain-specific security issues.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Auto-linking solicitor to user without admin review | Gifts credited to wrong missionary; inflated support totals affecting coaching decisions | Exact match only; ambiguous -> unmatched queue; admin confirms |
| RE CSV formula injection in gift notes/descriptions | Data exfiltration when admin exports gifts to CSV | Apply FORMULA_PREFIXES check to ALL imported text fields including prayer_description |
| Exposing solicitor User IDs in API responses | User enumeration via import API | Return solicitor name only, not internal user ID, in import results |
| Not scoping Gift queries by owner | Same owner-scoping bugs as Donation model | Copy owner-scoping pattern from DonationListView.get_queryset() to GiftListView |
| SHA256 hash stored in plaintext | Low risk, but hash reveals if two users imported same file | Acceptable; import dedup is not a security-sensitive feature |

## UX Pitfalls

Common user experience mistakes in model replacement and import.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Renaming "Donations" to "Gifts" everywhere simultaneously | Users confused, can't find familiar features | Change labels gradually: sidebar first, then page titles, then field labels |
| Import error: "Donation with ID X already exists" when user hasn't imported yet | Confusing error from old Donation data conflicting with new Gift dedup | Clear error message: "A gift record with this external ID was imported previously" |
| No progress indicator during RE import with 1000+ rows | User thinks import is frozen, refreshes page, loses progress | Show progress: "Processing row 450 of 1,200..." |
| Prayer intention auto-created with cryptic RE description | User sees "Prayer: GFT-2026-001 ANNUAL FUND" instead of meaningful text | Only auto-create prayer intentions when RE description field contains actual prayer text; require manual review |
| Solicitor match report with no context | Admin sees "John Smith -> User #abc123" with no way to verify | Show matched gift count, total amount, and sample gift dates alongside each match |
| Dashboard shows $0 during migration period | User panics thinking data was lost | Show banner: "System upgrade in progress. Data will be restored shortly." |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Gift model created:** But Contact.update_giving_stats() still queries `self.donations.all()` -- stats show $0
- [ ] **Data migration ran:** But Event.content_type not updated -- "What Changed" shows broken references
- [ ] **RE import works:** But not tested with split gifts (multi-row), Windows-1252 encoding, or "Last, First" solicitor names
- [ ] **SHA256 dedup works:** But not tested with BOM vs no-BOM, CRLF vs LF, or re-encoded files
- [ ] **Solicitor matching works:** But no admin review UI for unmatched/ambiguous matches -- they silently drop
- [ ] **API endpoints updated:** But React Query cache keys still reference old "donation" keys -- stale cache served
- [ ] **Dashboard shows gifts:** But `get_late_donations()` still queries Pledge model instead of RecurringGift
- [ ] **Sidebar renamed:** But browser bookmarks to `/donations` return 404 instead of redirecting to `/gifts`
- [ ] **Gift signals working:** But migration script doesn't disable them -- migration runs 100x slower
- [ ] **Import tests pass:** But only with ASCII data -- no tests with accented names (Jose), smart quotes, or em-dashes
- [ ] **Prayer intentions created:** But no de-duplication -- re-importing same RE file creates duplicate prayer records
- [ ] **Draggable tiles work:** But drag position resets on page navigation (session-only was spec, but user expects persistence)
- [ ] **Export CSV updated:** But export still says "donation_type" in CSV header instead of "gift_type"

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong solicitor auto-linking | HIGH | Identify affected gifts by import batch; unlink solicitor; recalculate missionary stats; admin manually re-links |
| Duplicate gifts from split rows | MEDIUM | Query gifts with same external_id prefix; merge splits; recalculate contact stats |
| Broken Event references after migration | MEDIUM | Run content_type update migration; re-validate Event.object_id points to existing Gift records |
| Double-counted stats during migration | LOW | Run `contact.update_giving_stats()` for all contacts with gifts; one-time management command |
| Wrong dates from DD/MM ambiguity | HIGH | Impossible to auto-fix -- must re-import with correct format; affected records need manual review |
| SHA256 false negatives (same data imported twice) | MEDIUM | De-duplicate by external_id (more reliable); mark duplicates; recalculate stats |
| Windows-1252 characters corrupted to UTF-8 mojibake | MEDIUM | Re-import with correct encoding; or data migration to fix known mojibake patterns (`Ã©` -> `e`) |
| Migration signals causing stat recalculation storm | LOW | Kill migration, disable signals, restart migration, recalculate stats once at end |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| #1 77+ dependent references | Phase 1 (New models) + Phase 4 (Update dependents) | Full-text search for "Donation" and "Pledge" returns zero hits outside migration files |
| #2 Contact stats hardcoded to donations | Phase 1 (New models) | Create a Gift, verify contact.total_given updates correctly |
| #3 SHA256 hash instability | Phase 2 (Import pipeline) | Upload same CSV saved with/without BOM; verify same hash |
| #4 Windows-1252 encoding | Phase 2 (Import pipeline) | Import CSV with accented name "Jose"; verify correct storage |
| #5 Multi-row split gifts | Phase 2 (Import pipeline) | Import CSV with two rows sharing same Gift ID; verify one Gift created |
| #6 Solicitor false matching | Phase 2 (Import pipeline) | Import with ambiguous name; verify sent to unmatched queue, not auto-linked |
| #7 Migration UUID preservation | Phase 3 (Data migration) | Compare Gift.id with original Donation.id for migrated records; verify match |
| #8 Dashboard 21+ references | Phase 4 (Update dependents) | Load every dashboard widget; load every insights page; verify no errors |
| #9 RE date format ambiguity | Phase 2 (Import pipeline) | Import "01/02/2026"; verify parsed as January 2 (US format) |
| #10 Signal storms during migration | Phase 3 (Data migration) | Time migration of 1000 records; verify < 60 seconds with signals disabled |

## Sources

**Raiser's Edge CSV Quirks:**
- [Introducing Single Row Query in Blackbaud RE NXT](https://community.blackbaud.com/discussion/84415/introducing-single-row-query-in-blackbaud-raiser-s-edge-nxt-a-smarter-way-to-export-your-data) -- split gift export behavior, denormalized data
- [Export split gifts to multiple rows (Aha idea)](https://renxt.ideas.aha.io/ideas/RENXT-I-8179) -- confirmation that split gifts produce multi-row exports
- [Why Raiser's Edge Migrations are Difficult (Arkus)](https://www.arkusinc.com/archive/2020/its-not-just-your-org-why-raisers-edge-migrations-are-difficult) -- gift complexity, adjustments, soft credits
- [Exporting RE for CiviCRM (Palante Tech)](https://redmine.palantetech.coop/projects/commons/wiki/Exporting_Raiser's_Edge_for_CiviCRM) -- column group issues, denormalized exports

**Encoding Issues:**
- [Windows-1252 (Wikipedia)](https://en.wikipedia.org/wiki/Windows-1252) -- smart quotes byte values, differences from UTF-8
- [How to Fix CSV Encoding Problems (CSV Viewer)](https://csv-viewer-online.com/blog/fix-csv-encoding-problems) -- cascading encoding detection strategy
- [UTF-8 and Byte Order Marks (CryptoSys)](https://www.cryptosys.net/pki/utf8bom.html) -- BOM bytes silently changing hash values

**SHA256 Dedup Edge Cases:**
- [Resolving SHA256 Hash Mismatch: Line Endings Matter (devgem.io)](https://www.devgem.io/posts/resolving-sha256-hash-mismatch-in-net-tests-line-endings-matter) -- CRLF vs LF hash differences
- [Byte Order Mark (Wikipedia)](https://en.wikipedia.org/wiki/Byte_order_mark) -- BOM as invisible hash-changing prefix
- [Deduplication considerations (Relativity)](https://help.relativity.com/RelativityOne/Content/Relativity/Processing/Deduplication_considerations.htm) -- case sensitivity in hash-based dedup

**Name Matching:**
- [Common Mistakes in Fuzzy Data Matching (WinPure)](https://winpure.com/fuzzy-matching-common-mistakes/) -- threshold calibration, normalization skipping
- [Fuzzy Matching 101 (Data Ladder)](https://dataladder.com/fuzzy-matching-101/) -- false positive management, confidence thresholds
- [The Problem of Name Matching in Sanctions Screening (sanctions.io)](https://www.sanctions.io/blog/the-problem-of-name-matching-in-sanctions-screening) -- cultural name variations, transliteration

**Django Model Migration:**
- [Renaming models in Django without heavy data migrations (HackSoft)](https://www.hacksoft.io/blog/renaming-models-in-django-without-heavy-data-migrations) -- RenameModel vs new model strategy
- [How to Move a Django Model to Another App (Real Python)](https://realpython.com/move-django-model/) -- SeparateDatabaseAndState, content type migration
- [Django Ticket #23577 -- Rename operations should rename indexes](https://code.djangoproject.com/ticket/23577) -- index name conflicts on rename
- [Django Ticket #27092 -- Creating and then renaming FK fails](https://code.djangoproject.com/ticket/27092) -- migration ordering issues

**Existing Codebase (HIGH confidence):**
- `apps/donations/models.py` -- Donation model with 7 fields, 4 indexes, FK to Contact/Pledge/Fund
- `apps/pledges/models.py` -- Pledge model with status transitions, fulfillment tracking, monthly_equivalent
- `apps/contacts/models.py:152-188` -- `update_giving_stats()` queries `self.donations.all()`
- `apps/donations/signals.py` -- post_save/post_delete with threading-based disable mechanism
- `apps/pledges/signals.py` -- pre_save/post_save for status change tracking
- `apps/dashboard/services.py` -- 9 Donation references, 12 Pledge references across 10 functions
- `apps/insights/services.py` -- 12+ Donation/Pledge references with complex aggregation queries
- `apps/imports/services.py` -- existing CSV parsers, date/amount parsing, import infrastructure
- `apps/imports/mpd_services.py:402-482` -- existing name matching pattern with duplicate detection
- `apps/events/models.py` -- EventType.DONATION_RECEIVED, GenericForeignKey to any model

---
*Pitfalls research for: DonorCRM v2.0 -- Model Replacement, RE Import, Data Migration*
*Researched: 2026-02-20*
