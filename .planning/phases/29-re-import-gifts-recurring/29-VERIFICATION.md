---
phase: 29-re-import-gifts-recurring
verified: 2026-02-20T04:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: null
gaps: []
human_verification: []
---

# Phase 29: RE Import Gifts and Recurring Gifts Verification Report

**Phase Goal:** Admins can import RE Gift and Recurring Gift CSV files with correct multi-row grouping, credit splitting, and prayer intention auto-creation
**Verified:** 2026-02-20T04:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | RE Gift CSV groups rows by Gift ID, creates one Gift per group with multiple GiftCredit records | VERIFIED | `_group_rows_by_id()` groups by `gift_id`; `Gift.objects.create` + `GiftCredit.objects.create` per row with solicitor (re_services.py L1149, L1242, L1275) |
| 2  | Gift amount comes from dedicated amount column on first row, NOT summed from credits | VERIFIED | `first_row.get('amount', '')` passed to `_parse_amount_to_cents()` (re_services.py L1200); credit creation is separate per-row loop |
| 3  | Gift groups referencing a Constituent ID not in DonorCRM are skipped entirely with a descriptive error | VERIFIED | `Contact.objects.filter(external_constituent_id=constituent_id).first()` — if `not contact`: appends error with all row numbers and calls `savepoint_rollback` + `continue` (re_services.py L1176-1191) |
| 4  | Gift descriptions containing prayer-relevant text automatically create PrayerIntention records linked to donor contact | VERIFIED | `_maybe_create_prayer_intention(gift, prayer_text, contact, seen_prayers)` called after gift creation (re_services.py L1282-1288); PrayerIntention.gifts M2M confirmed active |
| 5  | Same prayer text from multiple gifts for same donor produces one PrayerIntention linked to all those gifts via M2M | VERIFIED | `seen_prayers` dedup dict with key `(contact.id, normalized)` — on collision, calls `existing.gifts.add(gift)` (re_services.py L963-966); DB fallback via `description__iexact` |
| 6  | Re-uploading same Gift CSV returns cached ImportBatch without reprocessing | VERIFIED | `check_duplicate_import(file_bytes, ImportBatchType.RE_GIFT)` called first; returns early with `status=DUPLICATE` (re_services.py L1083-1087) |
| 7  | Individual row errors do not stop processing | VERIFIED | Savepoint-per-group pattern: `transaction.savepoint()`, exception rollback, `continue` to next group (re_services.py L1169-1302) |
| 8  | RE Recurring Gift CSV groups rows by Recurring Gift ID, creates one RecurringGift per group with multiple RecurringGiftCredit records | VERIFIED | Same `_group_rows_by_id()` pattern; `RecurringGift.objects.create` + `RecurringGiftCredit.objects.create` (re_services.py L1539, L1685, L1721) |
| 9  | Recurring gift amount comes from dedicated amount column on first row | VERIFIED | `first_row.get('amount', '')` (re_services.py L1591); separate credit loop |
| 10 | Recurring gift frequency and status are mapped from RE string values to RecurringGiftFrequency and RecurringGiftStatus choices | VERIFIED | `FREQUENCY_MAP` (17 entries) and `STATUS_MAP` (6 entries); confirmed all 8 frequency choices and all 5 status choices covered via shell verification |
| 11 | Recurring gift groups with missing Constituent ID are skipped entirely | VERIFIED | Same pattern as Gift import — `Contact.objects.filter(external_constituent_id=...)` check with savepoint rollback (re_services.py L1562-1580) |
| 12 | Re-uploading same Recurring Gift CSV returns cached ImportBatch without reprocessing | VERIFIED | `check_duplicate_import(file_bytes, ImportBatchType.RE_RECURRING_GIFT)` at top of `import_re_recurring_gifts` (re_services.py L1473-1477) |
| 13 | Individual recurring gift row errors do not stop processing | VERIFIED | Savepoint-per-group pattern identical to gift import (re_services.py L1557-1741) |

**Score:** 13/13 truths verified

### Required Artifacts

#### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/prayers/models.py` | PrayerIntention with gifts M2M field | VERIFIED | `gifts = models.ManyToManyField('gifts.Gift', ...)` at L35; `gift` FK absent. Shell confirms fields include `gifts`, exclude `gift` |
| `apps/prayers/migrations/0002_remove_prayerintention_gift_prayerintention_gifts.py` | Migration converting FK to M2M | VERIFIED | Exists; removes `gift` field, adds `gifts` M2M field to `gifts.gift`. Applied — `makemigrations --check` returns "No changes detected" |
| `apps/imports/re_services.py` | import_re_gifts orchestrator, GIFT_HEADER_ALIASES, shared helpers | VERIFIED | All 8 exports present and importable: `import_re_gifts`, `GIFT_HEADER_ALIASES` (36 entries), `_parse_amount_to_cents`, `_parse_date`, `_build_fund_lookup`, `_build_solicitor_lookup`, `_group_rows_by_id`, `_maybe_create_prayer_intention`, `PRAYER_STOPLIST` |
| `apps/imports/views.py` | REGiftImportView API endpoint | VERIFIED | `REGiftImportView(APIView)` at L1103; imports `import_re_gifts`; calls it with `file_bytes, file.name, uploaded_by=request.user, owner=request.user` |
| `apps/imports/urls.py` | re/gifts/ URL pattern | VERIFIED | `path('re/gifts/', REGiftImportView.as_view(), name='import-re-gifts')` at L48 |
| `apps/imports/management/commands/import_re_gifts.py` | import_re_gifts management command | VERIFIED | Command registered; `--owner` required arg; calls `import_re_gifts()`; prints prayer_count and unmatched_solicitors |

#### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/imports/re_services.py` | import_re_recurring_gifts, RECURRING_GIFT_HEADER_ALIASES, FREQUENCY_MAP, STATUS_MAP | VERIFIED | All present: `RECURRING_GIFT_HEADER_ALIASES` (38 entries), `FREQUENCY_MAP` (17 entries, covers all 8 choices), `STATUS_MAP` (6 entries, covers all 5 choices) |
| `apps/imports/views.py` | RERecurringGiftImportView API endpoint | VERIFIED | `RERecurringGiftImportView(APIView)` at L1150; imports and calls `import_re_recurring_gifts()` |
| `apps/imports/urls.py` | re/recurring-gifts/ URL pattern | VERIFIED | `path('re/recurring-gifts/', RERecurringGiftImportView.as_view(), name='import-re-recurring-gifts')` at L49 |
| `apps/imports/management/commands/import_re_recurring_gifts.py` | import_re_recurring_gifts management command | VERIFIED | Command registered; `--owner` required arg; calls `import_re_recurring_gifts()`; prints unmatched_solicitors |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `apps/imports/re_services.py` | `apps/gifts/models.py` | `Gift.objects.create, GiftCredit.objects.create` | WIRED | Both calls present at re_services.py L1242 and L1275; `Gift`, `GiftCredit` imported at top of file |
| `apps/imports/re_services.py` | `apps/prayers/models.py` | `PrayerIntention.objects.create + gifts.add()` | WIRED | `PrayerIntention.objects.create(...)` at re_services.py L986; `prayer.gifts.add(gift)` at L992; `existing.gifts.add(gift)` at L965, L975 |
| `apps/imports/re_services.py` | `apps/contacts/models.py` | `Contact.objects.filter(external_constituent_id=)` | WIRED | `Contact.objects.filter(external_constituent_id=constituent_id).first()` at re_services.py L1177 (gifts) and L1565 (recurring gifts) |
| `apps/imports/views.py` | `apps/imports/re_services.py` | `import_re_gifts` | WIRED | Imported at views.py L21; called at views.py L1130 |
| `apps/imports/re_services.py` | `apps/gifts/models.py` | `RecurringGift.objects.create, RecurringGiftCredit.objects.create` | WIRED | Both calls present at re_services.py L1685 and L1721; `RecurringGift`, `RecurringGiftCredit` imported at top of file |
| `apps/imports/views.py` | `apps/imports/re_services.py` | `import_re_recurring_gifts` | WIRED | Imported at views.py L21; called at views.py L1177 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| IMP-03 | 29-01-PLAN.md | RE Gift import with multi-row grouping by Gift ID, GiftCredit creation per solicitor, and Contact linking | SATISFIED | `import_re_gifts()` fully implements: two-pass grouping via `_group_rows_by_id()`, `GiftCredit` per solicitor row, `Contact.objects.filter(external_constituent_id=)` lookup |
| IMP-04 | 29-02-PLAN.md | RE Recurring Gift import with same grouping pattern, installment fields, and status tracking | SATISFIED | `import_re_recurring_gifts()` fully implements: same grouping, `RecurringGift` with frequency/status/start_date/end_date fields, `RecurringGiftCredit` per solicitor |
| IMP-10 | 29-01-PLAN.md | Prayer intention auto-creation from RE gift description field during gift import | SATISFIED | `_maybe_create_prayer_intention()` called in `import_re_gifts()` with `prayer_description` field from first row; stoplist filtering, case-insensitive dedup, and M2M linking all implemented |

**No orphaned requirements found.** REQUIREMENTS.md Traceability section maps IMP-03, IMP-04, and IMP-10 exclusively to Phase 29.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `apps/imports/re_services.py` | 930 | `'xxx'` in PRAYER_STOPLIST set literal | Info | **Not a code anti-pattern.** `'xxx'` is a legitimate stoplist entry for filtering low-value prayer descriptions. The string appears inside a data set definition, not as a code marker. |

**No actual blockers or warnings found.**

### Human Verification Required

None. All critical behaviors are verifiable programmatically:

- Multi-row grouping logic is implemented in code (not a UI behavior)
- PrayerIntention M2M confirmed via Django model introspection
- FREQUENCY_MAP and STATUS_MAP coverage confirmed via set comparison
- All management commands confirmed callable via `--help`
- Migrations confirmed applied via `makemigrations --check`

### Gaps Summary

No gaps found. All 13 observable truths are verified, all artifacts exist and are substantive and wired, all key links are confirmed, all 3 requirement IDs are satisfied.

---

## Technical Summary

**What was verified in code (not just claimed in SUMMARY):**

1. `PrayerIntention.gifts` is a live `ManyToManyField` to `gifts.Gift` — confirmed via `PrayerIntention._meta.get_fields()` shell call. The old `gift` ForeignKey is absent.

2. Migration `0002_remove_prayerintention_gift_prayerintention_gifts.py` is applied — `makemigrations --check` returns "No changes detected".

3. `import_re_gifts` and `import_re_recurring_gifts` are both importable from `apps.imports.re_services` with no errors.

4. All 36 `GIFT_HEADER_ALIASES` entries present including the locked CONTEXT.md alias: `'gift specific attributes prayer requests description': 'prayer_description'`.

5. `FREQUENCY_MAP` covers all 8 `RecurringGiftFrequency` choices (annually, bimonthly, biweekly, irregular, monthly, quarterly, semi_annually, weekly) — `RecurringGiftFrequency.values` is a subset of `FREQUENCY_MAP.values()`.

6. `STATUS_MAP` covers all 5 `RecurringGiftStatus` choices (active, cancelled, completed, held, terminated).

7. Both management commands (`import_re_gifts --help` and `import_re_recurring_gifts --help`) are registered and respond correctly.

8. URL patterns `re/gifts/` and `re/recurring-gifts/` exist in `apps/imports/urls.py` at L48-49.

9. All 4 task commits (c234124, 6c8d3df, 0a2e594, d704e55) are present in git log.

10. Prayer dedup: `seen_prayers` dict with key `(contact.id, normalized)` in `_maybe_create_prayer_intention` — same prayer text from multiple gifts adds to existing M2M, does not create a duplicate record.

---

_Verified: 2026-02-20T04:00:00Z_
_Verifier: Claude (gsd-verifier)_
