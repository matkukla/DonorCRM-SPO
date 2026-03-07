# Phase 44: Modify the SPO Data Import and Reconciliation Workflow - Research

**Researched:** 2026-03-07
**Domain:** Django CSV import pipeline, management commands, multi-source reconciliation
**Confidence:** HIGH

## Summary

Phase 44 builds a three-step SPO import pipeline — missionary reconciliation, gift attribution, and prayer intention routing — on top of a mature import infrastructure that already handles all the generic mechanisms (SHA256 dedup, cascading encoding, alias-based header mapping, savepoint-isolated row processing, ImportBatch audit records). The new work is almost entirely in the domain-specific logic: how a "solicitor" maps to a missionary User, how anonymous donors are handled, and how the audit output is structured.

The codebase has extremely strong patterns to copy: `import_re_solicitors`, `import_re_gifts`, and `import_re_constituents` in `re_services.py` are direct templates for the three new SPO service functions. The management commands (`import_re_solicitors.py`, `import_re_gifts.py`) are 100-line wrappers that call the shared service, print summaries, and are trivially reusable. The `ImportBatch.summary` JSON field is already the standard persistence layer for type-specific audit data.

The primary new engineering surface is `MissionaryAlias` (new model), the three-level name matching logic (exact → normalized → alias → create), anonymous-donor-per-missionary contact creation, and the tri-source Smartsheet comparison. Everything else is wiring existing patterns into new service functions.

**Primary recommendation:** Create `spo_services.py` alongside `re_services.py`, add three management commands and three API views following existing shape exactly, add `MissionaryAlias` model with Django admin, and extend `ImportBatchType` with three new SPO choices.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Missionary Account Creation
- When a solicitor from the CSV doesn't match any existing User: auto-create a User with role=missionary, name from CSV, placeholder email `firstname.lastname@spo.org`, flagged in audit as "created — needs real email"
- Name matching levels: 1) exact full name match, 2) normalized match (lowercase, trimmed, punctuation-stripped), 3) check alias table. If no match after all three: create new User or flag if alias table entry is marked unresolved
- When a solicitor CSV row matches an existing User: fill blank fields only (merge-only pattern from Phase 28) — never overwrite existing values
- Tri-source reconciliation: compare solicitors CSV names, Smartsheet MPD names, and existing User accounts in one pass. Flag missionaries that appear in one source but not another
- Trigger: both a management command (`reconcile_missionaries <file.csv>`) AND an API endpoint (same service layer, same as Phase 28 pattern). Both surface results in ImportBatch history

#### Unresolved Name Review Queue
- Unresolved/ambiguous names: print to terminal AND stored in ImportBatch.summary JSON — survives terminal close, queryable via Django admin
- Donations referencing an unresolved missionary: skip and report — counted explicitly in audit as "unmatched — unresolved solicitor". Admin resolves name, reruns to pick them up
- Alias table: a lightweight `MissionaryAlias` model (source_name, user FK). Admin populates via Django admin to register known name variants. Reconciliation service checks this before attempting normalized matching

#### Anonymous Donor Handling
- Detection: blank/missing donor name field = anonymous (does not require "Anonymous" keyword)
- Strategy: one per-missionary "Anonymous Donor" contact. All anonymous gifts for a given missionary link to their dedicated anonymous contact
- `Contact.owner` for anonymous contacts = the missionary User the donation was credited to (scopes correctly for supervisor/coach visibility)
- Anonymous contacts are auto-created on first anonymous gift for that missionary

#### Multi-Step Pipeline Architecture
- Separate management commands for each step:
  1. `reconcile_missionaries <solicitors.csv>` — creates/verifies 25 missionary accounts
  2. `import_spo_gifts <gifts.csv>` — imports donations, attributes to missionaries
  3. `import_spo_prayers <file>` — routes prayer intentions to correct contact/missionary context
- Each step produces its own ImportBatch record
- Admin runs step 1, reviews audit output, fixes alias table if needed, then runs step 2 with confidence

#### Audit Output
- Terminal output: formatted summary table printed at end of each command
- Stored in ImportBatch.summary JSON (same data, persisted for Import History UI)
- Format: aggregate totals section first, then per-missionary breakdown table
  - Aggregate: total missionaries expected, created, matched, unresolved, total donations processed, imported, skipped, anonymous count, prayer intentions imported
  - Per-missionary: name, match type (exact/normalized/alias/created), gifts imported, total amount, anonymous gifts count
- Missionaries with zero donations explicitly flagged

#### Idempotency / Reruns
- SHA256 dedup reused from existing ImportBatch infrastructure — same file = skip
- Alias table changes allow reruns to pick up previously unresolved names after admin registers the alias (admin must submit a slightly modified file or use a management command `--force` flag to bypass dedup)

### Claude's Discretion
- MissionaryAlias model exact fields and admin registration UX
- Exact terminal output formatting (table vs. structured text)
- Service layer module organization (one file per step vs. shared spo_services.py)
- Smartsheet tri-source comparison implementation details
- Prayer intention detection from gifts CSV (reuse Phase 29 patterns where applicable)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Standard Stack

### Core (all pre-existing, no new packages)
| Component | Location | Purpose | Pattern |
|-----------|----------|---------|---------|
| `ImportBatch` | `apps/imports/models.py` | Universal audit record with SHA256 dedup | Use as-is for all 3 steps |
| `ImportBatchType` | `apps/imports/models.py` | Enum of import types | Extend with SPO_MISSIONARY, SPO_GIFT, SPO_PRAYER |
| `re_services.py` | `apps/imports/` | Shared import utilities | Template for `spo_services.py` |
| `decode_csv_bytes()` | `re_services.py` | Cascading encoding (UTF-8-sig, UTF-8, Windows-1252) | Reuse directly |
| `skip_re_type_label_row()` | `re_services.py` | Strips RE type-label leading row | Reuse — SPO test CSV has "Solicitor / / ,,..." leading rows |
| `_build_header_mapping()` | `re_services.py` | Alias-to-canonical column map | Reuse pattern |
| `normalize_solicitor_name()` | `re_services.py` | "Last, First" normalization | Adapt — SPO CSV uses "First Last" format |
| `_maybe_create_prayer_intention()` | `re_services.py` | Prayer auto-creation from gift description | Reuse directly (same column present in SPO gifts CSV) |
| `_parse_amount_to_cents()` | `re_services.py` | Dollar string → cents | Reuse directly |
| `_parse_date()` | `re_services.py` | Multi-format date parsing (M/D/YY, M/D/YYYY) | Reuse directly |
| `check_duplicate_import()` | `re_services.py` | SHA256 dedup | Reuse directly |
| `merge_contact_fields()` | `re_services.py` | Merge-only field updates | Reuse for User field merging |
| Django management commands | `apps/imports/management/commands/` | CLI interface | Copy shape from `import_re_solicitors.py` / `import_re_gifts.py` |
| Django Admin | `apps/imports/admin.py` | Admin UI registration | Register `MissionaryAlias` here |

### New Components to Build
| Component | Location | Purpose |
|-----------|----------|---------|
| `spo_services.py` | `apps/imports/` | SPO-specific orchestration functions |
| `MissionaryAlias` model | `apps/imports/models.py` | Maps source name variant → User FK |
| `reconcile_missionaries.py` | `apps/imports/management/commands/` | Step 1 management command |
| `import_spo_gifts.py` | `apps/imports/management/commands/` | Step 2 management command |
| `import_spo_prayers.py` | `apps/imports/management/commands/` | Step 3 management command |
| API views (3x) | `apps/imports/views.py` | POST endpoints matching RE pattern |
| `MissionaryAliasAdmin` | `apps/imports/admin.py` | Django admin for alias table |
| Migration | `apps/imports/migrations/` | MissionaryAlias model + new ImportBatchType values |

**No new pip packages required.** All processing uses stdlib `csv`, `hashlib`, `re`, `io`.

---

## Architecture Patterns

### Recommended File Structure
```
apps/imports/
├── re_services.py           # Existing RE services (DO NOT modify)
├── spo_services.py          # New: SPO-specific orchestration
├── models.py                # Add MissionaryAlias, extend ImportBatchType
├── admin.py                 # Add MissionaryAliasAdmin
├── views.py                 # Add 3 SPO API views
├── urls.py                  # Add 3 SPO URL routes
└── management/commands/
    ├── reconcile_missionaries.py    # New: Step 1
    ├── import_spo_gifts.py          # New: Step 2
    └── import_spo_prayers.py        # New: Step 3
```

### Pattern 1: MissionaryAlias Model

**What:** Lightweight mapping from source_name variant to User FK. Admin-managed.
**When to use:** When a CSV name doesn't match any User on exact or normalized match.

```python
class MissionaryAlias(TimeStampedModel):
    """Maps a source name variant to a known missionary User."""
    source_name = models.CharField(
        'source name',
        max_length=255,
        unique=True,
        db_index=True,
        help_text='Name as it appears in SPO CSV export'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='name_aliases',
        null=True,
        blank=True,
        help_text='Resolved missionary. Null = unresolved (still in review queue).'
    )
    notes = models.TextField(blank=True, help_text='Optional admin notes')

    class Meta:
        db_table = 'missionary_aliases'
        verbose_name = 'missionary alias'
        verbose_name_plural = 'missionary aliases'
```

**Key design choice:** `user=null` means "admin saw this name, marked it unresolved" — distinct from "never seen before". The service checks: (a) alias exists with user set → use that user, (b) alias exists with null → flag as unresolved, (c) no alias → try normalized match → create new User.

### Pattern 2: Three-Level Name Matching

**What:** Deterministic matching that never silently merges uncertain records.

```python
def _match_missionary_name(raw_name: str, user_lookup: dict, alias_lookup: dict) -> tuple:
    """
    Returns (user, match_type) where match_type is one of:
    'exact', 'normalized', 'alias', 'unresolved', 'new'

    - 'exact': raw_name.strip() == user.full_name
    - 'normalized': punctuation-stripped lowercase match
    - 'alias': found in MissionaryAlias table with user set
    - 'unresolved': found in MissionaryAlias table with user=None
    - 'new': not found anywhere — caller must auto-create User
    """
```

Normalization: lowercase + strip + collapse whitespace + remove punctuation (`,.-'`).

### Pattern 3: Per-Missionary Anonymous Contact

**What:** One "Anonymous Donor" Contact per missionary. Auto-created on first anonymous gift.

```python
def _get_or_create_anonymous_contact(missionary: User) -> Contact:
    """Get or create the dedicated anonymous donor contact for a missionary."""
    contact, created = Contact.objects.get_or_create(
        owner=missionary,
        first_name='Anonymous',
        last_name='Donor',
        external_id=f'anonymous_{missionary.id}',
        defaults={
            'status': 'donor',
        }
    )
    return contact
```

**Owner scoping:** `owner=missionary` ensures supervisor/coach visibility follows existing permission model without code changes.

### Pattern 4: SPO Gift Import — Contact Lookup

**Critical difference from RE:** SPO gifts CSV has `Solicitor Name` and `Constituent ID` columns.
- `Solicitor Name` = the missionary who gets credit (maps to User via Solicitor FK)
- `Constituent ID` = the donor (maps to Contact via `external_constituent_id`)
- When `Gift Is Anonymous == Yes` OR `Constituent ID` is blank → use anonymous Contact

The RE gift importer looks up `Contact` by `external_constituent_id`. The SPO gift importer must do the same PLUS handle the anonymous case where no constituent ID is provided.

### Pattern 5: SHA256 Dedup with --force Bypass

```python
# Management command adds --force flag
parser.add_argument('--force', action='store_true', help='Bypass SHA256 dedup and reimport')

# Service accepts force parameter
def reconcile_missionaries(file_bytes, filename, uploaded_by, force=False) -> ImportBatch:
    if not force:
        existing = check_duplicate_import(file_bytes, ImportBatchType.SPO_MISSIONARY)
        if existing:
            return existing  # DUPLICATE status
```

### Pattern 6: Tri-Source Comparison (Smartsheet)

**What:** During `reconcile_missionaries`, also read the existing Smartsheet MPD data (MPDSnapshot records) to compare names.

```python
def _build_tri_source_comparison(
    csv_names: set[str],
    smartsheet_names: set[str],
    db_users: QuerySet,
) -> dict:
    """Return dict with categorized name sets for audit output."""
    return {
        'csv_only': csv_names - smartsheet_names - db_names,
        'mpd_only': smartsheet_names - csv_names - db_names,
        'db_only': db_names - csv_names - smartsheet_names,
        'all_three': csv_names & smartsheet_names & db_names,
        'csv_and_mpd_not_db': (csv_names & smartsheet_names) - db_names,
        # etc.
    }
```

Smartsheet names come from `MPDSnapshot.objects.select_related('user')` — already in DB from prior Smartsheet imports.

### Pattern 7: Audit Output Format

**Terminal:** Print aggregates first, then per-missionary table.

```
=== SPO Missionary Reconciliation Complete ===

Aggregate:
  Missionaries in CSV:    25
  Matched (exact):         8
  Matched (normalized):    4
  Matched (alias):         2
  Created (new):           9
  Unresolved:              2

Per-Missionary:
  Name                  Match Type   Status
  ─────────────────────────────────────────
  Anderson, Peter       exact        matched
  Wagner, Ben           normalized   matched
  ...
  Unknown, J            —            UNRESOLVED — needs alias

Unresolved names saved to ImportBatch #{id} summary.
```

**JSON (ImportBatch.summary):**
```json
{
  "missionaries_expected": 25,
  "created": 9,
  "matched_exact": 8,
  "matched_normalized": 4,
  "matched_alias": 2,
  "unresolved": 2,
  "per_missionary": [
    {"name": "Peter Anderson", "match_type": "exact", "user_id": "..."},
    ...
  ],
  "unresolved_names": ["Unknown, J"],
  "needs_real_email": ["Peter Anderson", ...]
}
```

### Anti-Patterns to Avoid

- **Silent merges:** Never auto-merge when name is ambiguous. Flag and skip.
- **Assuming existing Solicitor rows:** SPO missionaries may not be in the `Solicitor` table. The `reconcile_missionaries` step creates/links Users, not Solicitors. The `import_spo_gifts` step uses the Solicitor name column to find the missionary User directly (not via Solicitor FK if that model is RE-specific).
- **Overwriting existing User fields:** Always merge-only (fill blank fields only, never overwrite).
- **One big transaction:** Use per-row savepoints in gift import (same as RE gift importer) so one bad row doesn't roll back everything.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Encoding detection | Custom codec logic | `decode_csv_bytes()` in `re_services.py` | Handles BOM, Windows-1252, null bytes |
| SHA256 dedup | Custom hash storage | `check_duplicate_import()` + `ImportBatch` unique constraint | Already enforced at DB level |
| CSV header flexibility | Hardcoded column names | `_build_header_mapping()` with alias dict | SPO files may have variant column names |
| Prayer auto-creation | Custom prayer logic | `_maybe_create_prayer_intention()` in `re_services.py` | Includes stoplist, dedup, title truncation |
| Date parsing | Custom `strptime` | `_parse_date()` in `re_services.py` | Handles M/D/YY and M/D/YYYY |
| Amount parsing | Custom regex | `_parse_amount_to_cents()` in `re_services.py` | Handles `$`, `,`, `Decimal` |
| Per-row error isolation | Try/except everywhere | Savepoint pattern from `import_re_gifts` | Allows full-file processing with partial errors |
| Audit persistence | Print only | `ImportBatch.summary` JSON | Survives terminal close, queryable in admin |

---

## Common Pitfalls

### Pitfall 1: SPO CSV Has Type-Label Row
**What goes wrong:** `test_solicitors.csv` starts with `"Solicitor"` then `"Name"` on row 2. `csv.DictReader` would read `"Solicitor"` as the only header, `"Name"` as a data row.
**Why it happens:** Same RE export pattern — a leading type-label row.
**How to avoid:** Call `skip_re_type_label_row()` before `csv.DictReader`. Confirmed: test_solicitors.csv has `Solicitor` on row 1, `Name` on row 2 — exactly the RE type-label pattern.
**Warning signs:** `DictReader` produces only one key (`Solicitor`) for all rows.

### Pitfall 2: SPO Names Are "First Last" Not "Last, First"
**What goes wrong:** `normalize_solicitor_name()` already handles both formats, but the existing lookup dict key format (`"anderson, peter"`) must be consistent. SPO CSV names like "Peter Anderson" normalize to `"anderson, peter"` — this is correct.
**How to avoid:** Use the same `normalize_solicitor_name()` function for both user lookup key building and CSV row name normalization.

### Pitfall 3: Contact.email Unique Constraint Per Owner
**What goes wrong:** `Contact` has `UniqueConstraint(fields=['owner', 'email'], condition=~Q(email=''))`. Anonymous contacts have blank email so no conflict. But if creating two contacts for the same donor for different missionaries, a shared email would conflict.
**How to avoid:** Anonymous contacts have blank email. For named donors, use `external_constituent_id` as primary lookup key (not email).

### Pitfall 4: User Email Must Be Unique
**What goes wrong:** Auto-creating 25 missionary Users with `firstname.lastname@spo.org` placeholder emails — two missionaries with same name (e.g., "John Smith") would collide.
**How to avoid:** Add a numeric suffix if collision detected: `john.smith2@spo.org`. Flag in audit.

### Pitfall 5: Gift CSV Contact Lookup vs. Anonymous Detection
**What goes wrong:** The SPO gifts CSV has `Constituent ID` and `Gift Is Anonymous` columns. RE importer always requires `external_constituent_id`. SPO: when `Gift Is Anonymous == Yes` or `Constituent ID` is blank, the contact is the per-missionary anonymous contact (not a DB-lookup failure).
**How to avoid:** Check anonymous flag BEFORE attempting contact lookup. Don't treat anonymous gifts as errors.

### Pitfall 6: SHA256 Dedup Blocks Reruns After Alias Table Update
**What goes wrong:** Admin updates `MissionaryAlias` to resolve unresolved name, then reruns the same CSV file — dedup returns DUPLICATE and skips.
**How to avoid:** Add `--force` flag to management commands (and `force` parameter to API) to bypass SHA256 check. Document this in audit output for unresolved items: "Rerun with --force after adding aliases."

### Pitfall 7: Solicitor Table vs. User Table Confusion
**What goes wrong:** The existing `Solicitor` model (`apps/gifts/models.py`) is for RE gift credit attribution. SPO missionary reconciliation is about `User` accounts. These are different tables with different purposes.
**How to avoid:** Step 1 (`reconcile_missionaries`) operates on `User` table. The SPO gift importer (`import_spo_gifts`) looks up the missionary by solicitor name → User, then creates the gift attributed to that missionary. GiftCredit still uses the `Solicitor` model if desired — or SPO may skip GiftCredit and use a simpler attribution model. Planner must decide: does `import_spo_gifts` create `GiftCredit` records? The CONTEXT.md says "donations, attributes to missionaries" — likely yes, needs a `Solicitor` record for each missionary. Reconcile step could also ensure Solicitor records exist for each matched User.

---

## Code Examples

### Example: New ImportBatchType Values
```python
# Source: apps/imports/models.py — extend ImportBatchType
class ImportBatchType(models.TextChoices):
    # ... existing values ...
    SPO_MISSIONARY = 'spo_missionary', 'SPO Missionary Reconciliation'
    SPO_GIFT = 'spo_gift', 'SPO Gift Import'
    SPO_PRAYER = 'spo_prayer', 'SPO Prayer Import'
```

### Example: Management Command Shape (from existing import_re_solicitors.py)
```python
class Command(BaseCommand):
    help = 'Step 1: Reconcile SPO missionary accounts from Solicitors CSV'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to solicitors CSV')
        parser.add_argument('--owner', type=str, required=True,
                            help='Email of admin running the import')
        parser.add_argument('--force', action='store_true',
                            help='Bypass SHA256 dedup (use after adding aliases)')

    def handle(self, *args, **options):
        # Load owner user, read file, call service
        batch = reconcile_missionaries(
            file_bytes=file_bytes,
            filename=filename,
            uploaded_by=owner_user,
            force=options['force'],
        )
        # Print formatted summary table
        self._print_summary(batch)
```

### Example: Anonymous Contact Lookup Key
```python
# In import_spo_gifts service — build anonymous contact cache
_anonymous_contacts: dict[int, Contact] = {}  # missionary_user_id -> Contact

def _get_anonymous_contact(missionary: User) -> Contact:
    if missionary.id not in _anonymous_contacts:
        contact, _ = Contact.objects.get_or_create(
            owner=missionary,
            external_id=f'spo_anonymous_{missionary.id}',
            defaults={
                'first_name': 'Anonymous',
                'last_name': 'Donor',
                'status': 'donor',
            }
        )
        _anonymous_contacts[missionary.id] = contact
    return _anonymous_contacts[missionary.id]
```

### Example: Normalized Name Matching (existing function, reuse as-is)
```python
# Source: apps/imports/re_services.py — normalize_solicitor_name()
# Input: "Peter Anderson" -> "anderson, peter"
# Input: "Anderson, Peter" -> "anderson, peter"
# Both produce same key for lookup dict
norm = normalize_solicitor_name(raw_name)
matched_user = user_lookup.get(norm)
```

### Example: Gift Is Anonymous Detection (SPO-specific)
```python
# SPO gifts CSV column: "Gift Is Anonymous" = "Yes" or "No"
is_anonymous = row.get('is_anonymous', '').strip().lower() in ('yes', 'true', '1')
constituent_id = row.get('constituent_id', '').strip()

if is_anonymous or not constituent_id:
    contact = _get_anonymous_contact(missionary)
else:
    contact = Contact.objects.filter(
        external_constituent_id=constituent_id
    ).first()
    if not contact:
        errors.append(...)
        continue
```

---

## State of the Art

| Old Pattern | Current Pattern | Impact |
|-------------|-----------------|--------|
| Print-only audit | `ImportBatch.summary` JSON + terminal | Audit survives terminal close |
| Single import command | Management command + API sharing service layer | Consistent output regardless of trigger |
| RE-only import | RE + SPO pipelines in same `imports` app | Shared utilities, consistent admin UI |

**The test_data/ directory already has SPO-format CSV files** (`test_solicitors.csv`, `test_gifts.csv`) which confirm the exact column names and formats the services must handle. The gifts CSV has `Gift ID`, `Constituent ID`, `Gift Is Anonymous`, `Solicitor Name`, `Solicitor Amount`, `Gift Specific Attributes Prayer Requests Description` columns.

---

## Open Questions

1. **Do SPO gifts create Solicitor records for missionaries?**
   - What we know: RE gift import uses `Solicitor` model FK for `GiftCredit`. SPO missionaries are `User` accounts.
   - What's unclear: Should `reconcile_missionaries` also ensure each missionary has a `Solicitor` record? Or should `import_spo_gifts` use a different attribution path?
   - Recommendation: Yes — create a `Solicitor` record for each missionary User during `reconcile_missionaries` so `import_spo_gifts` can use the same `GiftCredit` model. The `Solicitor.user` FK already links Solicitor to User.

2. **Does `import_spo_prayers` operate on the gifts CSV or a separate file?**
   - What we know: CONTEXT.md lists it as step 3 with `<file>` argument. Prayer intentions already extracted in `import_spo_gifts` via `_maybe_create_prayer_intention()`.
   - What's unclear: Is step 3 redundant with gift import? Or is there a separate prayer-only file?
   - Recommendation: Treat `import_spo_prayers` as a targeted re-extraction pass over the gifts CSV for cases where admin wants to import prayers without reimporting gifts (after a --force scenario). Or it could handle a separate prayer-only file format. Planner should decide.

3. **Smartsheet tri-source comparison — does it re-parse Smartsheet CSV or use MPDSnapshot data?**
   - What we know: `MPDSnapshot` records are already in the DB from prior Smartsheet uploads. The test_data/ directory has a Smartsheet CSV file.
   - Recommendation: Query `MPDSnapshot.objects.select_related('user')` for names — no file re-parsing needed. Simpler and more reliable.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` or `pyproject.toml` (check root) |
| Quick run command | `pytest apps/imports/tests/test_spo_services.py -x` |
| Full suite command | `pytest apps/imports/tests/ -x` |

### Phase Requirements → Test Map
| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Missionary exact name match → User linked | unit | `pytest apps/imports/tests/test_spo_services.py::TestReconcileMissionaries::test_exact_match -x` | Wave 0 |
| Normalized name match (punctuation-stripped) | unit | `pytest apps/imports/tests/test_spo_services.py::TestReconcileMissionaries::test_normalized_match -x` | Wave 0 |
| Alias table match → User linked | unit | `pytest apps/imports/tests/test_spo_services.py::TestReconcileMissionaries::test_alias_match -x` | Wave 0 |
| No match → auto-create User with placeholder email | unit | `pytest apps/imports/tests/test_spo_services.py::TestReconcileMissionaries::test_auto_create -x` | Wave 0 |
| Anonymous gift → per-missionary anonymous Contact | unit | `pytest apps/imports/tests/test_spo_services.py::TestSPOGiftImport::test_anonymous_contact -x` | Wave 0 |
| SHA256 dedup returns DUPLICATE | unit | `pytest apps/imports/tests/test_spo_services.py::TestSPOGiftImport::test_dedup -x` | Wave 0 |
| Unresolved solicitor → gift skipped + counted | unit | `pytest apps/imports/tests/test_spo_services.py::TestSPOGiftImport::test_unresolved_skipped -x` | Wave 0 |
| Prayer intention extracted from gift CSV | unit | `pytest apps/imports/tests/test_spo_services.py::TestSPOGiftImport::test_prayer_extraction -x` | Wave 0 |
| Summary JSON persisted to ImportBatch | unit | `pytest apps/imports/tests/test_spo_services.py -k "summary" -x` | Wave 0 |
| Management command --force bypasses dedup | integration | `pytest apps/imports/tests/test_spo_commands.py::test_force_flag -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/imports/tests/test_spo_services.py -x`
- **Per wave merge:** `pytest apps/imports/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/imports/tests/test_spo_services.py` — covers all service-level behaviors
- [ ] `apps/imports/tests/test_spo_commands.py` — covers --force flag and command output

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `apps/imports/re_services.py` — full service pattern, all utility functions
- Direct code inspection: `apps/imports/models.py` — ImportBatch, ImportBatchType, Solicitor constraints
- Direct code inspection: `apps/imports/views.py` — API view shape for RESolicitorImportView, REGiftImportView
- Direct code inspection: `apps/imports/management/commands/import_re_solicitors.py` — management command shape
- Direct code inspection: `apps/imports/management/commands/import_re_gifts.py` — gift command shape
- Direct code inspection: `test_data/test_solicitors.csv` — SPO solicitor CSV format confirmation
- Direct code inspection: `test_data/test_gifts.csv` — SPO gifts CSV column names and format
- Direct code inspection: `apps/users/models.py` — User model fields, role choices
- Direct code inspection: `apps/contacts/models.py` — Contact ownership model, unique constraints

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions — user-locked implementation choices

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all existing, inspected directly
- Architecture patterns: HIGH — directly derived from existing working code
- Pitfalls: HIGH — sourced from actual code inspection of constraints and existing logic
- Open questions: MEDIUM — reasonable inferences, planner should decide

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable Django codebase, internal patterns)
