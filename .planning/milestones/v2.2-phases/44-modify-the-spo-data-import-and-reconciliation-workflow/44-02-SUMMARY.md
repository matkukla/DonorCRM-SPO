---
phase: 44-modify-the-spo-data-import-and-reconciliation-workflow
plan: "02"
subsystem: imports
tags: [spo, missionary-reconciliation, three-level-matching, solicitor, anonymous-contact, tri-source, tdd]
dependency_graph:
  requires:
    - phase: 44-01
      provides: MissionaryAlias model, SPO ImportBatchType choices, test stub scaffold
  provides:
    - reconcile_missionaries() service — Step 1 SPO pipeline entry point
    - _match_missionary_name() — exact/normalized/alias three-level matching
    - _build_user_lookup() / _build_alias_lookup() — O(1) lookup dicts
    - _auto_create_missionary_user() — placeholder email with collision suffix
    - _get_or_create_missionary_solicitor() — Solicitor record per resolved missionary
    - _get_or_create_anonymous_contact() — per-missionary Anonymous Donor contact
    - _build_tri_source_comparison() — 7-way CSV/MPD/DB set categorization
  affects:
    - 44-03 (import_spo_gifts uses _get_or_create_missionary_solicitor via Solicitor FK)
    - 44-04 (management commands invoke reconcile_missionaries)
tech-stack:
  added: []
  patterns:
    - Three-level name matching (exact → normalized punctuation-stripped → alias table → create/flag)
    - force=True dedup bypass: delete old ImportBatch then re-create (avoids UniqueConstraint)
    - csv.writer in test helpers to properly quote names containing commas
    - _strip_punctuation uses unicodedata.normalize NFD + regex to remove apostrophes for fuzzy match
    - Per-missionary Solicitor record ensured at reconciliation time (not at gift import time)

key-files:
  created:
    - apps/imports/spo_services.py
  modified:
    - apps/imports/tests/test_spo_services.py
    - apps/imports/tests/test_missionary_alias.py

key-decisions:
  - "csv.writer used in test helper _make_solicitor_csv to properly quote names with commas — naive newline join caused CSV field-splitting on 'OBrien, Pat'"
  - "force=True deletes existing ImportBatch before re-creating — UniqueConstraint on (import_type, sha256_hash) prevents simple re-insert"
  - "user_lookup built from ALL active users (not just missionaries) to avoid creating duplicate accounts for existing non-missionary users"
  - "_strip_punctuation keeps commas so 'last, first' structure is preserved after punctuation removal"
  - "Solicitor record created at reconcile time (not gift import time) so import_spo_gifts can rely on Solicitor.user FK existing"

patterns-established:
  - "Three-level match: normalize_solicitor_name exact → _strip_punctuation fuzzy → MissionaryAlias table → auto-create/unresolved"
  - "Merge-only user field update: fill blank first_name/last_name from CSV, never overwrite existing values"
  - "Tri-source comparison returns sets (later JSON-serialized as sorted lists) for CSV/MPD/DB name analysis"

requirements-completed:
  - SPO-RECONCILE

duration: ~16min
completed: 2026-03-07
---

# Phase 44 Plan 02: reconcile_missionaries() Service Summary

**Three-level missionary name matching (exact/normalized/alias/create/flag) with Solicitor record creation, tri-source CSV-MPD-DB comparison, and full TDD test coverage — the gate-keeping Step 1 of the SPO import pipeline.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-03-07T19:35:33Z
- **Completed:** 2026-03-07T19:52:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Implemented `reconcile_missionaries()` with three-level name matching, SHA256 dedup, force bypass, and per-missionary Solicitor record creation ensuring Step 2 GiftCredit attribution works
- Implemented `_match_missionary_name()` covering all five outcomes: exact, normalized (punctuation-stripped), alias (resolved), alias (unresolved/flagged), new (auto-create)
- Implemented `_build_tri_source_comparison()` categorizing names into 7 buckets (csv_only, mpd_only, db_only, all_three, csv_and_mpd_not_db, csv_and_db_not_mpd, mpd_and_db_not_csv) with full summary inclusion
- Implemented `_get_or_create_anonymous_contact()` and `_get_or_create_missionary_solicitor()` as idempotent helpers
- Filled 43 previously-stub tests across `TestReconcileMissionaries`, `TestMatchMissionaryName`, `TestBuildTriSourceComparison`, `TestGetOrCreateMissionarySolicitor`, `TestGetOrCreateAnonymousContact`, `TestImportSpoGifts` (anonymous contact assertions), and `TestMissionaryAliasModel`

## Task Commits

1. **Task 1 RED: failing tests** — `66a1cfa` (test)
2. **Task 1 GREEN: spo_services.py implementation** — `edff3f1` (feat)
3. **Task 2: TestImportSpoGifts anonymous contact + Task 2 verification** — `4044279` (feat)

## Files Created/Modified

- `apps/imports/spo_services.py` — New service module with all helpers (180 lines)
- `apps/imports/tests/test_spo_services.py` — Filled all 40 stubs with real assertions
- `apps/imports/tests/test_missionary_alias.py` — Filled all 3 stubs with real assertions

## Decisions Made

- **csv.writer in test helper**: The naive `'\n'.join(names)` approach caused CSV field-splitting on "OBrien, Pat" — comma was treated as delimiter. Using `csv.writer` correctly quotes fields containing commas.
- **force=True deletes old ImportBatch**: The `unique_import_batch_hash_per_type` UniqueConstraint prevents inserting a new batch with the same (import_type, sha256_hash). Force mode deletes the old batch before re-processing.
- **user_lookup from ALL active users**: Only filtering `role='missionary'` would miss existing non-missionary users with the same name, creating duplicate accounts. Including all active users prevents this.
- **_strip_punctuation keeps commas**: Commas are structurally significant in the "last, first" normalized form. Removing them would make "obrien, pat" and "obrien pat" identical, causing false matches across different first names.
- **Solicitor created at reconcile time**: Rather than creating Solicitor records lazily during gift import, we create them eagerly here. This makes `import_spo_gifts` simpler — it can assume the Solicitor FK exists for any resolved missionary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed CSV field-splitting on names with commas in test helper**
- **Found during:** Task 1 GREEN phase (test_normalized_match test run)
- **Issue:** `_make_solicitor_csv("OBrien, Pat")` produced unquoted CSV; csv.DictReader split "OBrien, Pat" into two columns — "OBrien" for the "Name" header and "Pat" discarded. This caused the test missionary name to be parsed as last="OBrien", first="" and auto-created rather than normalized-matched.
- **Fix:** Replaced `'\n'.join(lines)` with `csv.writer` which properly quotes values containing commas.
- **Files modified:** `apps/imports/tests/test_spo_services.py`
- **Committed in:** edff3f1 (Task 1 GREEN commit)

**2. [Rule 1 - Bug] Fixed UniqueConstraint violation on force=True re-import**
- **Found during:** Task 1 GREEN phase (test_force_bypasses_dedup test run)
- **Issue:** `force=True` skipped the dedup check but then tried to create a new ImportBatch with the same (import_type, sha256_hash), violating the UniqueConstraint.
- **Fix:** When `force=True` and an existing batch is found, delete the old batch before proceeding.
- **Files modified:** `apps/imports/spo_services.py`
- **Committed in:** edff3f1 (Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs — both in test infrastructure / dedup logic)
**Impact on plan:** Both fixes necessary for test correctness and service correctness. No scope creep.

## Issues Encountered

- The `test_donorcrm` test database was left locked after a background process, causing `EOFError: EOF when reading a line` on subsequent test runs. Resolved by dropping the database via psycopg2 directly.

## Self-Check: PASSED

- `apps/imports/spo_services.py` exists on disk
- `apps/imports/tests/test_spo_services.py` exists on disk
- `apps/imports/tests/test_missionary_alias.py` exists on disk
- Task commits: 66a1cfa (RED), edff3f1 (GREEN), 4044279 (Task 2) all in git log
- 67 tests pass in `apps.imports.tests` (no regressions)

## Next Phase Readiness

- `reconcile_missionaries()` returns `ImportBatch` with populated `summary['per_missionary']` for each resolved/created name
- Every resolved missionary User has a `Solicitor` record — `import_spo_gifts` (Plan 03) can look up `Solicitor.objects.get(user=missionary)` without creating new ones
- `_get_or_create_anonymous_contact()` ready for Plan 03 to call on each anonymous-donor gift row
- MissionaryAlias admin UI (from Plan 01) supports resolving unresolved names before re-running reconcile

---
*Phase: 44-modify-the-spo-data-import-and-reconciliation-workflow*
*Completed: 2026-03-07*
