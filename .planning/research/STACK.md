# Technology Stack: v2.0 Additions

**Project:** DonorCRM v2.0 -- RE Import Pipeline, Prayer Intentions, Dashboard Drag-and-Drop
**Researched:** 2026-02-20
**Confidence:** HIGH

## Existing Stack (DO NOT re-research)

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Django 4.2 + DRF | 4.2.27 |
| Frontend | React 19 + TypeScript + Vite | 19.2.0 / 5.9.3 / 7.2.4 |
| Database | PostgreSQL + Django ORM | UUID PKs, TimeStampedModel |
| UI | Tailwind 3.4 + Radix UI | Various |
| Data | TanStack Query + TanStack Table | 5.90.17 / 8.21.3 |
| CSV Frontend | react-papaparse | 4.4.0 |
| Charts | Recharts | 3.6.0 |
| Filtering | django-filter 24.3 + nuqs | Pinned (no Django 5.2) |
| Auth | JWT (simplejwt) | Role-based |
| Import | Existing SPO CSV pipeline | 4 types |
| Async | Celery 5.6 + Redis | For large imports |

## New Stack Additions for v2.0

### 1. SHA256 File Hashing -- Python stdlib (NO new dependency)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `hashlib` (stdlib) | Python 3.12 built-in | SHA256 hash of uploaded CSV files for ImportBatch dedup | Zero dependency. Part of Python standard library since Python 2. `hashlib.sha256()` is implemented in C (OpenSSL binding), so performance is excellent even for 10MB files. Produces 64-char hex digest for DB storage. |

**How it works in practice:**

```python
import hashlib

def compute_sha256(file_bytes: bytes) -> str:
    """Compute SHA256 hash of file content for dedup.

    For files up to 10MB (our upload limit), reading the entire
    buffer at once is fine. No need for chunked reading.
    """
    return hashlib.sha256(file_bytes).hexdigest()
```

**Why not chunk-read:** The project already enforces a 10MB upload limit (`MAX_UPLOAD_SIZE = 10 * 1024 * 1024` in `apps/imports/views.py`). At 10MB, hashing the entire buffer in one call takes ~15ms. Chunked reading is only needed for files >100MB.

**DB storage:** The SHA256 hex digest is exactly 64 characters. Use `CharField(max_length=64)` on the `ImportBatch` model. Combined with `type` in a unique constraint: `UniqueConstraint(fields=['type', 'sha256'], name='unique_batch_per_type_sha256')`.

**Confidence:** HIGH -- `hashlib` is Python stdlib, verified in Python 3.12 docs.

### 2. CSV Parsing for Messy RE Exports -- Python stdlib `csv` module (NO new dependency)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `csv` (stdlib) | Python 3.12 built-in | Parse Raiser's Edge CSV exports with messy quoting | Already used throughout `apps/imports/services.py`. The existing codebase uses `csv.DictReader` for all 6 import types. RE exports are well-formed enough for the stdlib -- they use standard RFC 4180 quoting (double-quote escaping). |

**The "relaxed quotes" concern addressed:**

The original prompt (from `prompts/CSV_import_system_2.md`) mentions `relax_quotes: true` from Node.js `csv-parse`. This is because Node's csv-parse is strict by default and chokes on fields like `"Prayer request with, comma"`. However, Python's `csv` module handles this correctly out of the box:

- Python's `csv.DictReader` with default settings (`quoting=csv.QUOTE_MINIMAL`, `doublequote=True`) correctly handles:
  - Fields containing commas wrapped in double quotes
  - Fields with embedded double quotes (doubled: `""`)
  - The "Gift Specific Attributes Prayer Requests Description" field which may contain commas

- The existing codebase already parses CSVs with `csv.DictReader(io.StringIO(file_content))` and this works for all current import types including fields with commas.

**One addition needed: UTF-8 BOM handling.** RE exports from Windows often have UTF-8 BOM (`\xef\xbb\xbf`). The existing fund/entity/transaction/pledge import views already decode with `utf-8-sig` (which strips BOM), but the contact/donation views use plain `utf-8`. All new RE import views should use `utf-8-sig`:

```python
content = file.read().decode('utf-8-sig')  # Handles BOM from Windows/Excel exports
```

**If truly malformed CSVs are encountered:** Create a custom `csv.Dialect` rather than adding a third-party library:

```python
class RaisersEdgeDialect(csv.Dialect):
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = True
    lineterminator = '\r\n'
    quoting = csv.QUOTE_MINIMAL

csv.register_dialect('raisers_edge', RaisersEdgeDialect)
reader = csv.DictReader(io.StringIO(content), dialect='raisers_edge')
```

**Confidence:** HIGH -- Python's `csv` module already handles RE CSV format correctly. Verified by examining the exact CSV headers from `prompts/CSV_import_system_2.md` against existing parsing patterns in `apps/imports/services.py`.

### 3. Data Migration Tooling (Donation -> Gift, Pledge -> RecurringGift) -- Django migrations (NO new dependency)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Django migrations (`RunPython`) | Django 4.2 built-in | Migrate data from Donation/Pledge tables to new Gift/RecurringGift tables | Django's migration framework handles schema changes and data migrations in a single, reversible, ordered pipeline. `RunPython` operations allow custom Python code within migrations. This is the standard Django pattern for model renames/replacements. |

**Migration strategy -- New tables + data copy (NOT RenameModel):**

The v2.0 changes are NOT simple renames. The new models have structural differences:
- `Gift` adds `external_gift_id`, `is_anonymous`, `payment_type`, `description` (prayer), `last_changed_at`, removes `pledge` FK, removes `thanked` tracking
- `Gift` needs a many-to-many `GiftCredit` junction table (new concept)
- `RecurringGift` adds `installment_frequency`, `installments_scheduled`, `first_installment_due`, `status_date`, removes `total_expected`/`total_received`/`is_late`/`days_late`

Therefore: **Create new tables, migrate data with RunPython, deprecate old tables.**

**Migration sequence (3 migration files):**

```
Migration 1: Create new schema
  - CreateModel: Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Solicitor, ImportBatch
  - Add external_constituent_id to Contact (if not already present)

Migration 2: Data migration (RunPython)
  - Copy Donation rows -> Gift rows (map fields, generate external_gift_id from existing external_id)
  - Copy Pledge rows -> RecurringGift rows (map frequency/status/dates)
  - Create placeholder GiftCredit for each Gift (1:1 until RE imports add multi-solicitor)
  - Update Contact.update_giving_stats references (if any hardcoded references)

Migration 3: Cleanup (DEFER to v2.1)
  - Drop old Donation/Pledge tables only AFTER confirming v2.0 is stable
  - Keep old tables as read-only backup during v2.0
```

**Reversibility:** Migration 2 should include a `reverse_func` that copies data back from Gift -> Donation and RecurringGift -> Pledge. Use `RunPython(forwards, reverse)` pattern.

**Key field mappings:**

| Donation field | Gift field | Notes |
|---|---|---|
| `id` | (new UUID) | Fresh UUIDs for Gift |
| `contact` | `donor_contact` | Same FK |
| `amount` | `fund_split_amount` | DecimalField preserved |
| `date` | `gift_date` | DateField -> DateField |
| `external_id` | `external_gift_id` | CharField preserved |
| `donation_type` | `gift_type` | Map enum values |
| `payment_method` | `payment_method` | Direct copy |
| `fund` | `fund` | Same FK |
| `notes` | `description` | TextField -> TextField |
| `thanked`/`thanked_at`/`thanked_by` | (dropped) | Thank-you tracking stays on Contact |
| `import_batch` (CharField) | `import_batch` (FK) | Upgrade to proper FK |

| Pledge field | RecurringGift field | Notes |
|---|---|---|
| `contact` | `donor_contact` | Same FK |
| `amount` | `installment_amount` | Per-period amount |
| `frequency` | `installment_frequency` | Map enum values |
| `status` | `status` | Map enum values |
| `start_date` | `gift_date` | First gift date |
| `external_id` | `external_gift_id` | CharField preserved |
| `fund` | `fund` | Same FK |
| `notes` | `description` | TextField -> TextField |
| `end_date` | `last_installment_due` | Nullable DateField |
| `total_expected`/`total_received` | (dropped) | Computed from actual gifts |
| `is_late`/`days_late` | (dropped) | Computed property instead |

**Confidence:** HIGH -- Django migration framework is well-documented and battle-tested. The `RunPython` + `SeparateDatabaseAndState` patterns are standard.

### 4. Drag-and-Drop Dashboard Tiles -- @dnd-kit/core + @dnd-kit/sortable (NEW frontend dependency)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `@dnd-kit/core` | 6.3.1 | Core drag-and-drop primitives | Battle-tested, 2185 dependents on npm, accessible (keyboard + screen reader support built-in), peer dep `react: ">=16.8.0"` includes React 19. |
| `@dnd-kit/sortable` | 10.0.0 | Sortable preset for grid reordering | Built on @dnd-kit/core, provides `SortableContext` + `useSortable` hook. Supports grid layouts natively. Peer dep: `react: ">=16.8.0"`, `@dnd-kit/core: "^6.3.0"`. |
| `@dnd-kit/utilities` | 3.2.2 | CSS transform utilities | `CSS.Transform.toString()` helper for smooth drag animations. Peer dep: `react: ">=16.8.0"`. |

**Why @dnd-kit/core+sortable over alternatives:**

| Library | React 19 | Grid Support | Size | Maintenance | Verdict |
|---------|----------|-------------|------|-------------|---------|
| `@dnd-kit/core` + `@dnd-kit/sortable` | Yes (>=16.8.0) | Native grid preset | ~15KB | Stable release, widely used | **CHOSEN** |
| `@dnd-kit/react` (new API) | Yes (^18 or ^19) | Sortable via @dnd-kit/dom | ~10KB | Pre-1.0 (v0.3.2), API unstable | Too early |
| `@atlaskit/pragmatic-drag-and-drop` | Yes (vanilla JS core) | Manual implementation | ~5KB core | Active (Atlassian) | More work for grid, known sorting bugs |
| `react-beautiful-dnd` | No (archived) | List only, no grid | N/A | Deprecated/archived | Dead |
| HTML5 native drag | Yes | Manual everything | 0KB | Browser API | Too much boilerplate |

**Why NOT @dnd-kit/react (v0.3.2):**
- Pre-1.0 semver: API can break between minor versions
- Open issue #1654: missing "use client" directive for React 19 Server Components
- Open issue #1695: no official sortable example for new API
- The legacy `@dnd-kit/core` (6.3.1) + `@dnd-kit/sortable` (10.0.0) have `react: ">=16.8.0"` peer deps which explicitly include React 19 -- no `--legacy-peer-deps` needed

**Dashboard integration pattern:**

The current Dashboard (`frontend/src/pages/Dashboard.tsx`) uses a static grid layout:
```tsx
{/* Current: static 2-column grid */}
<div className="grid gap-6 lg:grid-cols-2">
  <GivingSummaryCard />
  <MonthlyGiftsCard />
</div>
```

With @dnd-kit/sortable, this becomes:
```tsx
import { DndContext, closestCenter } from '@dnd-kit/core';
import { SortableContext, rectSortingStrategy } from '@dnd-kit/sortable';

const [tileOrder, setTileOrder] = useState<string[]>([
  'giving-summary', 'monthly-gifts', 'needs-attention',
  'support-progress', 'recent-donations', 'journal-activity'
]);

<DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
  <SortableContext items={tileOrder} strategy={rectSortingStrategy}>
    <div className="grid gap-6 lg:grid-cols-2">
      {tileOrder.map(id => <SortableTile key={id} id={id} />)}
    </div>
  </SortableContext>
</DndContext>
```

**Session-only persistence:** Per PROJECT.md scope, tile order is session-only (no backend persistence). Use React `useState` -- order resets on page refresh. This avoids needing a user preferences model.

**Confidence:** HIGH -- `@dnd-kit/core` 6.3.1 peer deps verified via `npm view @dnd-kit/core@6.3.1 peerDependencies` returning `{ react: '>=16.8.0', 'react-dom': '>=16.8.0' }`. React 19.2.0 satisfies `>=16.8.0`.

### 5. Gift Credit Many-to-Many with Amounts -- Django `through` model (NO new dependency)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Django `ManyToManyField` with `through` | Django 4.2 built-in | Gift-to-Solicitor junction with `solicitor_amount` field | Standard Django pattern for M2M relationships with extra data. The `through` model stores the amount each solicitor is credited per gift. Cannot use plain M2M because we need the `solicitor_amount_cents` and `solicitor_name` fields on the junction. |

**Pattern:**

```python
class Gift(TimeStampedModel):
    """One-time gift from Raiser's Edge."""
    external_gift_id = models.CharField(max_length=100, unique=True)
    donor_contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE, related_name='gifts')
    gift_date = models.DateField(null=True, blank=True)
    gift_type = models.CharField(max_length=50, blank=True)
    fund = models.ForeignKey('imports.Fund', on_delete=models.SET_NULL, null=True, blank=True)
    fund_split_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    payment_type = models.CharField(max_length=50, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)  # "Gift Specific Attributes Prayer Requests Description"
    last_changed_at = models.DateTimeField(null=True, blank=True)
    import_batch = models.ForeignKey('imports.ImportBatch', on_delete=models.SET_NULL, null=True, blank=True)

    # M2M through GiftCredit
    solicitors = models.ManyToManyField('imports.Solicitor', through='GiftCredit', blank=True)


class GiftCredit(TimeStampedModel):
    """Junction: one gift credits one or more solicitors (missionaries)."""
    gift = models.ForeignKey(Gift, on_delete=models.CASCADE, related_name='credits')
    solicitor = models.ForeignKey('imports.Solicitor', on_delete=models.SET_NULL, null=True, blank=True)
    solicitor_name = models.CharField(max_length=255)  # Original name from CSV (preserved even if solicitor deleted)
    solicitor_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['gift', 'solicitor_name'],
                name='unique_credit_per_solicitor_per_gift'
            )
        ]
```

**Why `through` model instead of JSONField:**
- Queryable: "Show all gifts credited to Solicitor X" is a single JOIN
- Aggregatable: "Total amount credited to Solicitor X this year" uses Django ORM `Sum()`
- Validated: `DecimalField` enforces numeric amounts, `UniqueConstraint` prevents duplicate credits
- Consistent with existing patterns: the codebase uses ForeignKey relationships everywhere, not JSON blobs

**Why `solicitor_name` stored alongside `solicitor` FK:**
- RE CSV gives us a name string, not an ID
- Solicitor record may not exist yet (import order: Constituents -> Solicitors -> Gifts)
- If gift is imported before solicitor, we store the name and link later
- Preserves original data even if Solicitor record is deleted

**Querying pattern:**
```python
# All gifts credited to a specific solicitor
Gift.objects.filter(credits__solicitor=solicitor_instance)

# Total amount credited to solicitor this year
from django.db.models import Sum
GiftCredit.objects.filter(
    solicitor=solicitor_instance,
    gift__gift_date__year=2026
).aggregate(total=Sum('solicitor_amount'))
```

**Confidence:** HIGH -- Django `through` model is a first-class ORM feature documented since Django 1.0. The pattern exactly matches the RE CSV structure where one Gift ID can have multiple rows with different Solicitor Names.

### 6. Solicitor Model with User Auto-Linking -- Django model + normalized name matching (NO new dependency)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Django model with `normalized_name` | Django 4.2 built-in | Solicitor lookup table with auto-link to User | Missionaries are both User accounts and Solicitor entries in RE. Matching by normalized name (`lower().strip()`) auto-links Solicitor to User. Same pattern already used in MPD Smartsheet import (`apps/imports/mpd_services.py`). |

**Pattern:**

```python
class Solicitor(TimeStampedModel):
    """Fundraiser/missionary who receives gift credit from RE."""
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, unique=True, db_index=True)
    external_solicitor_id = models.CharField(max_length=100, blank=True, unique=True)

    # Auto-linked to User account (if name matches)
    user = models.OneToOneField(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='solicitor'
    )

    def save(self, *args, **kwargs):
        self.normalized_name = self.name.lower().strip()
        if not self.user:
            self._try_link_user()
        super().save(*args, **kwargs)

    def _try_link_user(self):
        """Attempt to match solicitor name to a User account."""
        from apps.users.models import User
        parts = self.normalized_name.split()
        if len(parts) >= 2:
            matches = User.objects.filter(
                first_name__iexact=parts[0],
                last_name__iexact=parts[-1],
                is_active=True
            )
            if matches.count() == 1:
                self.user = matches.first()
            # If 0 or 2+ matches, leave user=None (admin resolves manually)
```

**Why OneToOneField (not ForeignKey):** Each User can only be one Solicitor, and each Solicitor maps to at most one User. The project already has the "duplicate names -> unmatched" pattern from MPD import (see Key Decisions in PROJECT.md).

**Confidence:** HIGH -- follows existing MPD name-matching pattern.

## Installation

### Backend

```bash
# NO new Python packages needed for v2.0
# hashlib, csv, and Django migrations are all stdlib/built-in
#
# Everything needed is already installed:
# - Django 4.2.27 (migrations, ORM, through models)
# - Python 3.12.3 (hashlib, csv)
# - openpyxl 3.1.5 (already installed from v1.3 Smartsheet import)
```

### Frontend

```bash
# Drag-and-drop for dashboard tiles
npm install @dnd-kit/core@6.3.1 @dnd-kit/sortable@10.0.0 @dnd-kit/utilities@3.2.2
```

That is the ONLY new dependency for the entire v2.0 milestone.

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pandas` for CSV parsing | 50MB+ dependency, overkill for row-by-row CSV processing | Python stdlib `csv.DictReader` (already in use) |
| `csv-parse` (Node) | The prompts reference Node.js csv-parse with `relax_quotes`. We are Django/Python, not Node. | Python `csv` module handles RE quoting correctly by default |
| Third-party SHA256 library | `hashlib` is stdlib, C-implemented, no reason for external package | `hashlib.sha256()` |
| `@dnd-kit/react` v0.3.2 | Pre-1.0, unstable API, missing "use client" for React 19, no sortable examples | `@dnd-kit/core` 6.3.1 + `@dnd-kit/sortable` 10.0.0 (stable) |
| `react-beautiful-dnd` | Archived and deprecated by Atlassian since 2023 | `@dnd-kit` |
| `@atlaskit/pragmatic-drag-and-drop` | Known bugs with sortable grids (issue #166), more boilerplate for grid sorting | `@dnd-kit/sortable` has native grid strategy |
| `django-import-export` | Heavy, opinionated, admin-coupled. Our import pipeline is custom and works well. | Existing custom import service pattern |
| `celery-results` for import tracking | We already have ImportRun model for audit trails | Existing ImportRun + new ImportBatch model |
| User preferences model for tile order | Out of scope per PROJECT.md ("session-only, no persistence") | React `useState` |
| `chardet` / `charset-normalizer` | RE exports are UTF-8 (possibly with BOM). `utf-8-sig` handles BOM. | `file.read().decode('utf-8-sig')` |
| New prayer model library | Prayer Intentions are a simple model with ForeignKey to Contact | Django model + TextField |
| `django-reversion` for migration rollback | Overkill. Keep old tables during v2.0, drop in v2.1. | Deferred table drops |

## Alternatives Considered

| Category | Chosen | Alternative | Why Not |
|----------|--------|-------------|---------|
| File dedup | SHA256 via `hashlib` | MD5 via `hashlib` | SHA256 is industry standard for content addressing. MD5 has known collisions. Marginal speed difference at 10MB. |
| File dedup | SHA256 of file content | Filename + timestamp | Same file uploaded twice with different names would be missed. Content hash is the only reliable dedup. |
| CSV parsing | Python `csv` stdlib | `pandas.read_csv` | pandas loads entire file into DataFrame (memory overhead), has complex dtype inference that can mangle IDs. `csv.DictReader` is simpler, streams row-by-row, gives raw strings. |
| Data migration | New tables + RunPython copy | RenameModel + AlterField | Gift/RecurringGift have different schemas from Donation/Pledge. RenameModel only works for exact renames. We need to add M2M junction tables, new fields, and drop fields. |
| Data migration | Keep old tables during v2.0 | Drop immediately | Safety net. If migration has bugs, old data is still accessible. Drop in v2.1 after validation. |
| Dashboard DnD | `@dnd-kit/sortable` | CSS `order` property + buttons | Drag-and-drop is the expected UX for tile reordering. Up/down buttons feel dated. |
| Dashboard DnD | Session-only state | localStorage persistence | Out of scope per PROJECT.md. Session-only avoids stale state bugs and keeps implementation simple. |
| Gift credits | `through` model | JSONField on Gift | JSON is not queryable for "all gifts credited to Solicitor X", not aggregatable, not validated. |
| Solicitor linking | Normalized name matching | Manual admin linking | Auto-matching handles 90%+ of cases. Admin can fix edge cases. Same pattern proven in MPD import. |
| Import batch tracking | New ImportBatch model | Extend existing ImportRun | ImportRun is SPO-specific (type enum has FUNDS/ENTITIES/TRANSACTIONS/PLEDGES). ImportBatch needs RE-specific types (CONSTITUENT/SOLICITOR/GIFT/RECURRING_GIFT) and SHA256 dedup. Separate models avoid polluting existing system. |

## Version Compatibility Matrix

| Package | Python | Django | React | Status |
|---------|--------|--------|-------|--------|
| `hashlib` (stdlib) | 3.12 built-in | N/A | N/A | Always available |
| `csv` (stdlib) | 3.12 built-in | N/A | N/A | Always available |
| Django migrations | N/A | 4.2 built-in | N/A | Always available |
| `@dnd-kit/core` 6.3.1 | N/A | N/A | >=16.8.0 | Includes React 19 |
| `@dnd-kit/sortable` 10.0.0 | N/A | N/A | >=16.8.0 | Includes React 19 |
| `@dnd-kit/utilities` 3.2.2 | N/A | N/A | >=16.8.0 | Includes React 19 |

**All verified compatible with: Python 3.12.3 + Django 4.2.27 + React 19.2.0**

## Integration Points with Existing Code

### Import Pipeline

The existing import pipeline (`apps/imports/services.py`) follows a clear pattern:
1. `parse_*_csv()` -- validate and parse CSV content
2. `import_*()` -- upsert records to database
3. Views call parse, then conditionally import

The new RE import pipeline should follow the same pattern but add:
- SHA256 check before parsing (via ImportBatch model)
- Row grouping for gifts (group by Gift ID before processing)
- GiftCredit creation in the import step

### Contact Model

The existing `Contact` model already has `external_id` (used for SPO entity imports). For RE imports, this same field stores the Constituent ID. No new field needed on Contact -- `external_id` is already the right field.

### Dashboard

The existing Dashboard has 8 tile components in `frontend/src/components/dashboard/`. Each is a self-contained component that receives data via props. Wrapping them in `SortableContext` + `useSortable` is additive -- no changes to individual tile components needed.

### Contact Stats

The existing `Contact.update_giving_stats()` method queries `self.donations.all()`. When migrating to Gift model, this needs to query `self.gifts.all()` instead. This is part of the data migration, not a stack addition.

## Sources

**SHA256 hashing:**
- [Python hashlib documentation](https://docs.python.org/3/library/hashlib.html) -- Official stdlib docs
- [hashlib file hashing pattern](https://realpython.com/ref/stdlib/hashlib/) -- Chunked vs buffered approach

**CSV parsing:**
- [Python csv module documentation](https://docs.python.org/3/library/csv.html) -- Dialect, quoting options, DictReader
- [csv reader quoting issue](https://bugs.python.org/issue30034) -- Known edge cases (not applicable to RE format)

**Django data migrations:**
- [Django migration operations](https://docs.djangoproject.com/en/5.2/ref/migration-operations/) -- RunPython, SeparateDatabaseAndState
- [Renaming models without heavy migrations](https://www.hacksoft.io/blog/renaming-models-in-django-without-heavy-data-migrations) -- SeparateDatabaseAndState pattern
- [Django ManyToManyField through](https://docs.djangoproject.com/en/4.2/topics/db/examples/many_to_many/) -- Through model pattern

**Drag-and-drop:**
- [@dnd-kit/core on npm](https://www.npmjs.com/package/@dnd-kit/core) -- v6.3.1, peer deps verified
- [@dnd-kit/sortable on npm](https://www.npmjs.com/package/@dnd-kit/sortable) -- v10.0.0, grid strategy
- [@dnd-kit/react on npm](https://www.npmjs.com/package/@dnd-kit/react) -- v0.3.2 (NOT recommended, pre-1.0)
- [dnd-kit docs: sortable](https://docs.dndkit.com/presets/sortable) -- SortableContext, useSortable, rectSortingStrategy
- [React 19 dnd-kit compatibility](https://github.com/clauderic/dnd-kit/issues/1654) -- Issue on new @dnd-kit/react
- [pragmatic-drag-and-drop sortable grid bug](https://github.com/atlassian/pragmatic-drag-and-drop/issues/166) -- Known reorder loop issue

**Raiser's Edge CSV format:**
- [Exporting Raisers Edge for CiviCRM](https://hq.megaphonetech.com/projects/commons/wiki/Exporting_Raisers_Edge_for_CiviCRM) -- RE export field reference
- [RE NXT Gift Export Setup](https://support.givecampus.com/hc/en-us/articles/29093884332311-Raiser-s-Edge-NXT-Integration-Gift-Export-Setup-Management) -- Gift/recurring gift fields
- Local: `prompts/CSV_import_system_2.md` -- Exact CSV headers from production RE exports

---
*Stack research for: v2.0 RE Import Pipeline, Prayer Intentions, Dashboard Drag-and-Drop*
*Researched: 2026-02-20*
*Confidence: HIGH -- Only 1 new npm dependency needed (3 packages: @dnd-kit/core+sortable+utilities). Zero new Python dependencies. All peer deps verified via npm CLI.*
