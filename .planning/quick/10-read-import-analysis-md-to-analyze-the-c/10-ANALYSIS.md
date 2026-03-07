# Import Analysis: CSV Formats vs DonorCRM Backend

**Date:** 2026-03-07
**Analyst:** Claude (quick task 10)
**Scope:** test_constituents.csv, test_solicitors.csv, test_gifts.csv, test_recurring_gifts.csv vs Phase 44 SPO import pipeline

---

## 1. What the 4 CSV Files Represent

### 1.1 test_constituents.csv

**Type:** Raiser's Edge (RE) Constituent export. 100 data rows.

**Structure:**
- Row 1: Type-label row with value "Constituent" (stripped by `skip_re_type_label_row()`)
- Row 2: Column headers

**Fields confirmed:**
| CSV Column | Sample Values |
|---|---|
| Constituent Date Last Changed | Date string (not used) |
| Constituent ID | 6-digit integer, e.g. `100001` |
| First Name | Personal name or blank for org rows |
| Last Name | Personal name or blank for org rows |
| Organization Name | Present for org-type rows; blank for individuals |
| Address Line 1 | Street address |
| Address Line 2 | Suite/unit |
| City | City name |
| State | 2-letter code |
| ZIP | Postal code |
| Country | e.g. "USA" |
| Phone | Phone number |
| Email | Email address |

**Key characteristics:**
- `Constituent ID` is the primary foreign key. Gift and recurring gift CSVs reference it.
- Mixed individual rows (First Name + Last Name) and organization rows (Organization Name populated, First/Last blank).
- No phone_secondary column in test data.

**Relationship:** Source of Contact records in DonorCRM. One constituent = one Contact.

---

### 1.2 test_solicitors.csv

**Type:** SPO Solicitor export. 25 data rows.

**Structure:**
- Row 1: Type-label row with value "Solicitor"
- Row 2: Single column header "Name"

**Fields confirmed:**
| CSV Column | Sample Values |
|---|---|
| Name | "Peter Anderson", "O'Brien, Pat" |

**Key characteristics:**
- Names appear in both "First Last" and "Last, First" formats.
- No numeric ID. No email. No phone.
- Sole purpose: establish the missionary User population before gift import.
- 25 unique names corresponding to 25 missionary accounts.

**Relationship:** Each name maps to a User (role=missionary) + Solicitor record in DonorCRM.

---

### 1.3 test_gifts.csv

**Type:** RE Gift export. 100 data rows.

**Structure:**
- Row 1: Type-label row with value "Gift"
- Row 2: Column headers

**Fields confirmed:**
| CSV Column | Sample Values | Notes |
|---|---|---|
| Gift ID | 200001–200100 | Unique per gift |
| Gift Date Last Changed | Date string | Not imported |
| Gift Date | Date string | Imported as gift_date |
| Gift Type | "Gift" | Not used |
| Fund ID | "Staff MPD" | Fund name string (not numeric ID) |
| Fund Split Amount | "$100.00" | Per-gift amount |
| Constituent ID | References constituent CSV | FK to Contact |
| Gift Is Anonymous | "Yes" / "No" | |
| Solicitor Name | Missionary name | Matches solicitors CSV |
| Solicitor Amount | Dollar string | Credit amount |
| Gift Payment Type | "EFT", "Check", "Credit Card", "Direct Debit", "Cash" | |
| Gift Specific Attributes Prayer Requests Description | Prayer text or empty | |
| Soft Credit Recipient ID | ID or blank | Not imported |

**Key characteristics:**
- No split-fund rows in test data. All gifts go to a single "Staff MPD" fund entry.
- `Fund Split Amount` (not "Gift Amount") is the canonical dollar column — the header alias was added in a post-UAT fix (commit 1779430).
- Payment types include "EFT" and "Cash" which require mapping to app enum values.

**Relationship:** Each row = one Gift. Solicitor Name links to User/Solicitor. Constituent ID links to Contact (or Anonymous Donor if is_anonymous=Yes or blank).

---

### 1.4 test_recurring_gifts.csv

**Type:** RE Recurring Gift export. 100 data rows.

**Structure:**
- Row 1: Type-label row with value "Recurring Gift"
- Row 2: Column headers

**Fields confirmed:**
| CSV Column | Sample Values | Notes |
|---|---|---|
| Gift ID | 300001–300100 | Unique per recurring gift |
| Gift Date Last Changed | Date string | Not imported |
| Gift Date | Installment start date | Imported as start_date |
| Gift Type | "Recurring Gift" | Not used |
| Gift First Installment Due | Empty in test data | |
| Last Installment/Payment Date Due | Empty in test data | End date candidate |
| Gift Installment Frequency | "Monthly", "Quarterly", "Annually" | |
| Number of Installments Scheduled | Empty in test data | |
| Gift First Installment Due_1 | Empty in test data | Duplicate-ish field |
| Fund ID | "Staff MPD" | Fund name string |
| Constituent ID | References constituent CSV | FK to Contact |
| Gift Is Anonymous | "Yes" / "No" | |
| Solicitor Name | Missionary name | |
| Solicitor Amount | Dollar string | Credit amount |
| Gift Payment Type | "EFT", "Direct Debit", "Check", "Cash" | |
| Gift Status | "Active", "Held", "Completed" | |
| Gift Status Date | Date string | Status change date, not imported |
| Gift Specific Attributes Prayer Requests Description | Prayer text or empty | |
| Soft Credit Recipient ID | ID or blank | Not imported |

**Key characteristics:**
- `Gift Date` maps to `start_date` on RecurringGift (the field for first payment date).
- End date columns are empty in test data; mapped via `Last Installment/Payment Date Due` alias.
- `Gift Status` values "Active", "Held", "Completed" map directly to RecurringGiftStatus enum.
- Prayer requests present in this CSV but NOT extracted by `import_re_recurring_gifts()`.

---

## 2. Current Application Structure

### 2.1 Data Models

**Contact** (`apps/contacts/models.py`)
- Represents a donor or prospect. Scoped by `owner` FK to User.
- `external_id`: generic external system ID (SPO-style, per owner)
- `external_constituent_id`: RE-specific constituent ID (global unique — no owner scoping)
- `organization_name`: handles org-type constituents
- Full address, phone, email fields present
- No `phone_secondary` column in model (field not in test data either)

**Solicitor** (`apps/gifts/models.py`)
- Links a missionary User to their gift credit attribution
- `normalized_name`: "last, first" lowercase
- `user` FK to User (nullable)
- `external_solicitor_id`: RE solicitor ID (unused by SPO pipeline — SPO has no numeric IDs)

**Gift** (`apps/gifts/models.py`)
- `donor_contact` FK to Contact (required)
- `fund` FK to Fund (nullable)
- `external_gift_id`: idempotency key
- `amount_cents`: integer cents
- `gift_date`: DateField
- `payment_type`: TextChoices (credit_card, direct_deposit, check)
- `description`: TextField

**GiftCredit** (`apps/gifts/models.py`)
- Junction table: Gift × Solicitor with `amount_cents`
- Unique constraint on (gift, solicitor)

**RecurringGift** (`apps/gifts/models.py`)
- `donor_contact` FK to Contact (required)
- `fund` FK to Fund (nullable)
- `external_gift_id`: idempotency key
- `amount_cents`, `frequency`, `start_date`, `end_date`, `status`, `description`
- Status choices: active, held, completed, cancelled, terminated
- Frequency choices: monthly, quarterly, semi_annually, annually, bimonthly, biweekly, weekly, irregular

**RecurringGiftCredit** (`apps/gifts/models.py`)
- Junction table: RecurringGift × Solicitor with `amount_cents`

**Fund** (`apps/imports/models.py`)
- `external_id`: unique fund identifier (maps to CSV "Fund ID" string like "Staff MPD")
- `name`: display name
- `owner` FK to User (nullable; null = org-wide)

**ImportBatch** (`apps/imports/models.py`)
- Universal import tracking with SHA256 dedup per import_type
- Types: RE_CONSTITUENT, RE_SOLICITOR, RE_GIFT, RE_RECURRING_GIFT, SPO_MISSIONARY, SPO_GIFT, SPO_PRAYER
- Stores counts and JSON summary

**MissionaryAlias** (`apps/imports/models.py`)
- Maps SPO name variants to User accounts
- `user=None` = admin-flagged unresolvable (not just unseen)

### 2.2 Import Pipelines

**RE Pipeline** (re_services.py):
- `import_re_constituents(file_bytes, filename, uploaded_by, owner)` — imports constituents with explicit owner assignment
- `import_re_solicitors(file_bytes, filename, uploaded_by)` — imports RE solicitors with numeric IDs
- `import_re_gifts(file_bytes, filename, uploaded_by, owner)` — imports gifts with fund linkage, payment_type mapping, prayer extraction
- `import_re_recurring_gifts(file_bytes, filename, uploaded_by, owner)` — imports recurring gifts with fund linkage, solicitor credits; does NOT extract prayer requests

**SPO Pipeline** (spo_services.py):
- `reconcile_missionaries(file_bytes, filename, uploaded_by)` — three-level name matching; creates User + Solicitor per name
- `import_spo_gifts(file_bytes, filename, uploaded_by)` — contact lookup via constituent_id or anonymous fallback; creates Gift + GiftCredit; extracts prayer intentions inline
- `import_spo_prayers(file_bytes, filename, uploaded_by)` — prayer-only rerun pass; separate dedup namespace

**The 4 CSV files feed two different pipelines:**
- `test_constituents.csv` → RE pipeline (`import_re_constituents`)
- `test_solicitors.csv` → SPO pipeline (`reconcile_missionaries`)
- `test_gifts.csv` → SPO pipeline (`import_spo_gifts` / `import_spo_prayers`)
- `test_recurring_gifts.csv` → RE pipeline (`import_re_recurring_gifts`)

---

## 3. Discrepancies Found

### 3.1 Discrepancy Table

| # | CSV Expectation | Current App Structure | Problem | Recommended Fix | Severity |
|---|---|---|---|---|---|
| D1 | Gift payment types: "EFT", "Direct Debit", "Cash", "Credit Card", "Check" | PaymentType choices: credit_card, direct_deposit, check. `_normalize_payment_type()` in re_services.py maps these. | `import_spo_gifts()` does NOT call `_normalize_payment_type()` — Gift is created without payment_type. | Add `payment_type=_normalize_payment_type(_get(row, 'payment_type'))` to the Gift.objects.create() call in spo_services.py. Header alias for "gift payment type" is NOT in SPO_GIFT_HEADER_ALIAS_MAP — add it. | Bug |
| D2 | Fund ID column "Staff MPD" present in gifts and recurring gifts CSVs | Gift.fund FK exists. Fund record must exist with external_id="Staff MPD". | `import_spo_gifts()` creates Gift without `fund=` argument. Fund FK is always null for SPO-imported gifts. RE pipeline (`import_re_gifts`) DOES link fund via fund_lookup. | Add "fund id" and "fund split amount" (for fund name) to SPO_GIFT_HEADER_ALIAS_MAP; look up Fund by external_id and pass `fund=matched_fund` to Gift.objects.create(). | Gap |
| D3 | Soft Credit Recipient ID present in gifts and recurring gifts CSVs | No Soft Credit model or field exists | Soft credit data is silently discarded on import | Acceptable limitation: soft credits require a separate model (two-sided attribution). Log a warning in summary but do not block import. No model change needed now. | Acceptable |
| D4 | Recurring gifts imported by RE pipeline; gifts imported by SPO pipeline | Two separate pipelines with different behaviors | For the same data batch (4 CSVs from RE), the recurring gift import requires an explicit `--owner` flag while the gift import uses missionary-based contact lookup. Contact scoping differs between the two. | Document in CLI help. For multi-missionary orgs, run `import_re_constituents` once per missionary with the correct owner. Then SPO gifts auto-route by solicitor name. Recurring gifts use the same constituent_id → contact lookup after constituents are imported. | Design decision (acceptable) |
| D5 | Contact lookup by constituent_id for gift import | `import_spo_gifts()` looks up Contact via `external_constituent_id` globally (no owner filter) | Contact.external_constituent_id has a global unique constraint — correct. But if constituents are NOT pre-imported, named non-anonymous gifts are skipped with `contact_not_found`. | Ensure constituents are imported BEFORE gifts. No code change needed; enforce via import order. | Process gap |
| D6 | Prayer requests in recurring_gifts CSV | `import_re_recurring_gifts()` processes `prayer_description` header alias is in RECURRING_GIFT_HEADER_ALIASES but no prayer extraction code exists in the recurring gift processing loop | Prayer intentions from recurring gift rows are silently discarded — no call to `_maybe_create_prayer_intention()` | Add prayer extraction to the recurring gift processing loop, after RecurringGiftCredit creation. Use `first_row.get('prayer_description', '')` and call `_maybe_create_prayer_intention()` (which accepts a Gift, not RecurringGift — adaptation needed). | Bug |
| D7 | Gift Date Last Changed column present | No `date_last_changed` field on Gift or RecurringGift | Change tracking date from RE is discarded | Acceptable limitation: audit trail via `ImportBatch.created_at`. No field needed. | Acceptable |
| D8 | `import_re_recurring_gifts()` requires `start_date` to be non-null | RE CSV uses "Gift Date" as start date. RECURRING_GIFT_HEADER_ALIASES maps "gift date" to "start_date". | In test_recurring_gifts.csv, "Gift Date" is present and non-empty. However, the dedicated "Gift First Installment Due" columns are empty. The correct start date is "Gift Date". | Current alias mapping is correct. No change needed. | No issue |
| D9 | Organization constituents: First Name/Last Name blank, Organization Name present | Contact model has `organization_name` field. `import_re_constituents()` checks `has_org = bool(org_name)` and creates contact using organization_name | RE constituent import correctly handles org rows. | No change needed. | No issue |
| D10 | Gift amount column is "Fund Split Amount" (not "Gift Amount") | `SPO_GIFT_HEADER_ALIAS_MAP` originally only had "Gift Amount". Post-UAT fix (commit 1779430) added "Fund Split Amount" as alias for `gift_amount`. | Fixed in commit 1779430. | No further action needed. | Resolved |

---

### 3.2 Critical Gaps (Bugs)

**D1 — Payment type not set on SPO-imported gifts:**

In `import_spo_gifts()` (spo_services.py line ~740):
```python
gift = Gift.objects.create(
    donor_contact=contact,
    amount_cents=amount_cents,
    gift_date=gift_date,
    external_gift_id=gift_id,
    # payment_type is NOT set
)
```
The `_get(row, 'payment_type')` call would return empty string because `payment_type` is not in `SPO_GIFT_HEADER_ALIAS_MAP`. Two separate fixes required:
1. Add `'gift payment type': 'payment_type'` to `_SPO_GIFT_HEADER_ALIASES_NESTED` in spo_services.py
2. Pass `payment_type=_normalize_payment_type(_get(row, 'payment_type'))` to Gift.objects.create()

**D6 — Prayer requests in recurring gifts not extracted:**

In `import_re_recurring_gifts()`, the RECURRING_GIFT_HEADER_ALIASES dict includes aliases for `prayer_description`. The header mapping correctly identifies the column. But the processing loop (lines ~1791–1834) never reads `first_row.get('prayer_description')` and never calls `_maybe_create_prayer_intention()`.

Complication: `_maybe_create_prayer_intention()` signature is `(gift: Gift, prayer_text: str, contact: Contact, seen_prayers: dict)`. It expects a Gift object, but we have a RecurringGift. The function creates a PrayerIntention linked to a Contact only (the gift M2M link is optional when gift=None). The prayer-only path in `import_spo_prayers()` already demonstrates the pattern for creating PrayerIntentions without a gift object. The simplest fix is to call `_maybe_create_prayer_intention(None, prayer_text, contact, seen_prayers)` — but `_maybe_create_prayer_intention()` currently requires a non-None gift for the M2M relationship. An alternative is to create the PrayerIntention directly (without a gift link) using the same logic as the `gift is None` branch in `import_spo_prayers()`.

---

## 4. Recommended Target Structure

The core model set is well-designed. No new models are required for the 4 CSV formats.

### 4.1 Models Sufficient As-Is

| Model | Assessment |
|---|---|
| Contact | Sufficient. external_constituent_id (global unique) handles RE FK lookup correctly. organization_name handles org rows. |
| Solicitor | Sufficient for SPO. external_solicitor_id unused by SPO pipeline (no numeric IDs in test_solicitors.csv) — acceptable. |
| Gift | Sufficient. payment_type field exists but not set by SPO pipeline (D1). |
| GiftCredit | Sufficient. |
| RecurringGift | Sufficient. description field can hold prayer text as a fallback. |
| RecurringGiftCredit | Sufficient. |
| Fund | Sufficient. external_id maps to "Staff MPD" string. Fund must be pre-created or auto-created on import. |
| ImportBatch | Sufficient. |
| MissionaryAlias | Sufficient. |

### 4.2 Models Needing Behavioral Changes (No Schema Changes)

**Gift import via SPO pipeline:** Set `payment_type` field (D1) and `fund` FK (D2).

**RecurringGift import via RE pipeline:** Extract prayer intentions from the `prayer_description` column (D6).

### 4.3 Fields Worth Adding (Optional, Not Blocking)

| Field | Model | Rationale |
|---|---|---|
| `date_last_changed` | Gift, RecurringGift | Tracks RE modification timestamp for incremental sync. Not needed for initial bulk import. |
| `soft_credit_recipient_id` | Gift, RecurringGift | Stores the raw soft-credit ID for future processing. One varchar column, no new model needed. |

No new models are recommended. Soft credits as a full feature would require a new model (out of scope).

---

## 5. Recommended Import Workflow

### 5.1 Correct Order

```
1. test_solicitors.csv     → reconcile_missionaries()        [SPO pipeline]
2. test_constituents.csv   → import_re_constituents()        [RE pipeline, per-missionary owner]
3. test_gifts.csv          → import_spo_gifts()              [SPO pipeline]
4. test_gifts.csv          → import_spo_prayers()            [SPO pipeline, optional rerun]
5. test_recurring_gifts.csv → import_re_recurring_gifts()   [RE pipeline, per-missionary owner]
```

### 5.2 Dependency Graph

```
solicitors ──────────────────────────────────────────────┐
                                                          ↓
constituents ──────────────────────────────────────────► gifts (SPO)
                                                          │
                                                          ↓
                                                      prayers (SPO)

constituents ──────────────────────────────────────────► recurring_gifts (RE)
```

**Why this order:**

- **Solicitors first:** `reconcile_missionaries()` creates User + Solicitor records. `import_spo_gifts()` looks up Solicitor by name to create GiftCredit. If Solicitor does not exist, the gift row is skipped with `unmatched_unresolved`.
- **Constituents second:** `import_spo_gifts()` resolves named (non-anonymous) donors via `Contact.external_constituent_id`. If constituents are not imported first, all non-anonymous gifts fail with `contact_not_found` and are skipped.
- **Gifts third:** After contacts and solicitors exist, all rows should resolve cleanly.
- **Prayers fourth (optional):** `import_spo_prayers()` can rerun against the same gifts CSV after gifts are imported. Uses a separate dedup namespace (SPO_PRAYER).
- **Recurring gifts last:** Depends on constituents (Contact lookup by external_constituent_id) and solicitors (RecurringGiftCredit lookup by normalized_name).

### 5.3 Multi-Missionary Scoping

Each missionary's contact population is scoped by `Contact.owner`. `import_re_constituents()` requires an explicit `--owner` (email or user ID) parameter. In a real deployment:
- Run constituent import once per missionary with `--owner missionary@example.org`
- SPO gift import routes contacts to the correct missionary via solicitor name match
- RE recurring gift import also requires `--owner` to scope the constituent lookup

### 5.4 Anonymous Donors

`import_spo_gifts()` handles anonymous gifts correctly:
- `Gift Is Anonymous = Yes` OR blank `Constituent ID` → uses per-missionary Anonymous Donor contact
- Created via `_get_or_create_anonymous_contact(missionary)` with stable `external_id=spo_anonymous_{user_id}`
- Idempotent across re-runs

---

## 6. Exact Implementation Plan

### 6.1 Bug Fixes Required

**Fix 1: Add payment_type to SPO gift import** (D1)
- File: `apps/imports/spo_services.py`
- Changes:
  1. In `_SPO_GIFT_HEADER_ALIASES_NESTED`, add `'payment_type': ['Gift Payment Type', 'payment_type']`
  2. In `import_spo_gifts()`, add `payment_type_raw = _get(row, 'payment_type')` after gift_date_raw
  3. Pass `payment_type=_normalize_payment_type(payment_type_raw)` to `Gift.objects.create()`
- Impact: SPO-imported gifts will have payment_type set. No schema migration needed.
- Existing test: `test_spo_gifts_import` will need update to assert payment_type on created gifts.

**Fix 2: Extract prayer intentions from recurring gift import** (D6)
- File: `apps/imports/re_services.py`
- Changes:
  1. Add `seen_prayers: dict = {}` before the processing loop
  2. After `RecurringGiftCredit` creation loop (line ~1834), add:
     ```python
     prayer_text = first_row.get('prayer_description', '')
     if prayer_text:
         # PrayerIntention without gift M2M linkage (recurring gifts have no Gift object)
         from apps.prayers.models import PrayerIntention, PrayerIntentionStatus
         _create_prayer_from_text(prayer_text, contact, seen_prayers)
     ```
  3. Extract the gift-free prayer creation logic from `import_spo_prayers()` into a shared helper `_create_prayer_from_text(prayer_text, contact, seen_prayers)` in re_services.py
- Impact: Prayer intentions from recurring gift rows will be created. No schema migration needed.
- Existing tests: Add test case for recurring gift prayer extraction.

### 6.2 Gaps Acceptable As-Is

**Gap: Fund not linked on SPO gifts** (D2)
- SPO gifts are created without `fund=` assignment
- RE gifts DO link to Fund via `fund_lookup`
- To fix: Pre-create Fund with `external_id="Staff MPD"`, add fund lookup to `import_spo_gifts()`
- Assessment: Acceptable limitation for initial import. Fund data is present but the linkage is cosmetic for current reporting. If Fund-level reporting is required, this becomes a bug.

**Gap: Soft Credit Recipient ID discarded** (D3)
- No model for soft credits. Column silently ignored.
- Assessment: Acceptable. Soft credits require a separate model design decision. Log in summary for awareness.

**Gap: Gift Date Last Changed not tracked** (D7)
- Assessment: Acceptable. ImportBatch.created_at provides import timestamp. RE's "last changed" date is useful for incremental sync but not needed for initial bulk import.

### 6.3 Files to Change

| File | Change Required | Priority |
|---|---|---|
| `apps/imports/spo_services.py` | Add payment_type header alias and field assignment in import_spo_gifts() | High (bug) |
| `apps/imports/re_services.py` | Add prayer extraction to import_re_recurring_gifts() | High (data loss) |
| `apps/imports/tests/test_spo_services.py` | Add assertions for payment_type on SPO-imported gifts | Medium |
| `apps/imports/tests/test_re_services.py` | Add test for prayer extraction in recurring gift import | Medium |

### 6.4 Phase 44 Coverage Verdict

| Requirement Area | Phase 44 Coverage |
|---|---|
| Constituent CSV → Contact model | Covered (import_re_constituents via RE pipeline) |
| Solicitor CSV → User + Solicitor reconciliation | Covered (reconcile_missionaries, three-level matching) |
| Gift CSV → Gift + GiftCredit creation | Covered |
| Gift CSV → prayer extraction inline | Covered |
| Gift CSV → payment_type mapping | NOT COVERED (bug — spo_services.py omits payment_type) |
| Gift CSV → Fund linkage | NOT COVERED (SPO pipeline omits fund= on Gift creation) |
| Recurring Gift CSV → RecurringGift + RecurringGiftCredit | Covered (import_re_recurring_gifts via RE pipeline) |
| Recurring Gift CSV → prayer extraction | NOT COVERED (prayer_description header mapped but never read) |
| Soft Credit Recipient ID | NOT COVERED (acceptable — no model exists) |
| SHA256 dedup | Covered |
| Anonymous donor handling | Covered |
| Force re-import | Covered (force=True on SPO pipeline; RE pipeline lacks force flag) |
| Organization constituents | Covered (import_re_constituents checks organization_name) |
| Idempotent contact lookup by external_constituent_id | Covered |
| Import audit trail (ImportBatch) | Covered |

**Summary:** Phase 44 correctly implements the structural pipeline. Two bugs exist (payment_type omission, recurring gift prayer extraction) and one design gap (SPO fund linkage). None of these block data import from succeeding. All four CSV formats are parseable and will import without errors when run in the correct order with constituents pre-loaded.

---

## Appendix: Key Utility Functions

| Function | Location | Purpose |
|---|---|---|
| `decode_csv_bytes()` | re_services.py | UTF-8-sig / UTF-8 / Windows-1252 cascade |
| `skip_re_type_label_row()` | re_services.py | Strips RE type-label row before headers |
| `_build_header_mapping()` | re_services.py | Alias → canonical column mapping |
| `normalize_solicitor_name()` | re_services.py | "Last, First" lowercase normalization |
| `_normalize_payment_type()` | re_services.py | Maps RE strings to PaymentType choices |
| `_parse_amount_to_cents()` | re_services.py | "$1,234.56" → integer cents |
| `_parse_date()` | re_services.py | Multi-format date parsing |
| `_maybe_create_prayer_intention()` | re_services.py | Dedup-safe prayer creation (requires Gift) |
| `check_duplicate_import()` | re_services.py | SHA256 per import_type dedup |
| `_match_missionary_name()` | spo_services.py | Three-level name matching (exact/normalized/alias) |
| `_get_or_create_anonymous_contact()` | spo_services.py | Stable anonymous donor per missionary |
