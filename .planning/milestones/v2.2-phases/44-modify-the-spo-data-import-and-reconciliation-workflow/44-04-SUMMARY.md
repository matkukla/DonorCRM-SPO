---
phase: 44-modify-the-spo-data-import-and-reconciliation-workflow
plan: "04"
subsystem: imports
tags: [spo, management-commands, api-views, tdd]
dependency_graph:
  requires: [44-03]
  provides: [SPO-CLI, SPO-API]
  affects: [imports, gifts, prayers]
tech_stack:
  added: []
  patterns: [management-command, tdd-red-green, multipart-upload, importbatch-json-shape]
key_files:
  created:
    - apps/imports/management/commands/reconcile_missionaries.py
    - apps/imports/management/commands/import_spo_gifts.py
    - apps/imports/management/commands/import_spo_prayers.py
  modified:
    - apps/imports/views.py
    - apps/imports/urls.py
    - apps/imports/tests/test_spo_commands.py
    - apps/imports/tests/test_spo_views.py
decisions:
  - "force=True not exposed via API — admin must use CLI for force re-imports to prevent accidental web-based reimports"
  - "ZERO DONATIONS marker rendered in _print_summary output for any per_missionary entry with gifts_imported==0"
  - "SPO URL routes grouped under spo/ prefix alongside existing re/ routes in urls.py"
metrics:
  duration: "~9 minutes"
  completed_date: "2026-03-07"
  tasks_completed: 2
  files_modified: 7
---

# Phase 44 Plan 04: SPO CLI Commands and API Views Summary

Three SPO management commands and three API views wired to the spo_services functions from plans 02-03, with zero-donation audit flag and full test coverage.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Three management commands with --force flag, audit output, zero-donation flag | 5cbdc61 | reconcile_missionaries.py, import_spo_gifts.py, import_spo_prayers.py, test_spo_commands.py |
| 2 | Three API views + URL routes + test assertions | 8199671 | views.py, urls.py, test_spo_views.py |

## What Was Built

### Management Commands

Three new management commands in `apps/imports/management/commands/`:

**reconcile_missionaries.py** — Step 1 CLI entry point
- Accepts `file` positional arg, `--owner` (required), `--force` (optional)
- `_print_summary()` prints aggregate counts + per-missionary table
- Zero-donation flag: any `per_missionary` entry with `gifts_imported == 0` shows `ZERO DONATIONS — verify import ran correctly` in the Status column (using `self.style.WARNING`)
- Prints unresolved names list and reminder to rerun with `--force` after adding aliases

**import_spo_gifts.py** — Step 2 CLI entry point
- Prints aggregate counts + per-missionary gift summary table
- Lists contact_not_found constituent IDs and unmatched_unresolved solicitor names

**import_spo_prayers.py** — Step 3 CLI entry point
- Simple aggregate output (prayers_created + skipped)

### API Views

Three new view classes in `apps/imports/views.py`:
- `SPOMissionaryImportView` — POST /api/imports/spo/missionaries/
- `SPOGiftImportView` — POST /api/imports/spo/gifts/
- `SPOPrayerImportView` — POST /api/imports/spo/prayers/

All three:
- `permission_classes = [IsAuthenticated, IsAdmin]`
- `parser_classes = [MultiPartParser]`
- Return same ImportBatch JSON shape as RESolicitorImportView: `{batch_id, status, is_duplicate, created_count, updated_count, skipped_count, error_count, total_rows, summary}`
- No `force` parameter (admin-only CLI operation)

URL routes added to `apps/imports/urls.py` under `spo/` prefix alongside existing `re/` routes.

### SPO ImportBatch Visibility

ImportBatch records created by the three SPO commands/views appear automatically in `GET /api/imports/batches/` via the existing `ImportBatchListView` — no additional work needed.

## Test Results

```
Ran 74 tests in 76.586s  (full apps.imports.tests suite)
OK
```

Tests added:
- `TestReconcileMissionariesCommand` (4 tests): runs successfully, force flag, missing owner error, zero-donation flag in output
- `TestImportSpoGiftsCommand` (2 tests): runs successfully, force flag
- `TestImportSpoPrayersCommand` (2 tests): runs successfully, force flag
- `TestSPOMissionaryImportView` (4 tests): requires admin, returns batch result, no file 400, unauthenticated 401
- `TestSPOGiftImportView` (2 tests): requires admin, returns batch result
- `TestSPOPrayerImportView` (2 tests): requires admin, returns batch result

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `python manage.py reconcile_missionaries --help` shows file, --owner, --force args
- `python manage.py import_spo_gifts --help` shows same
- `python manage.py import_spo_prayers --help` shows same
- `python manage.py test apps.imports.tests --verbosity=1` — 74/74 green, 0 failures
- Zero-donation missionaries show `ZERO DONATIONS` marker in `_print_summary` output (confirmed by `test_zero_donation_flag_in_output`)

## Self-Check: PASSED

- reconcile_missionaries.py: FOUND
- import_spo_gifts.py: FOUND
- import_spo_prayers.py: FOUND
- commit 5cbdc61 (Task 1): FOUND
- commit 8199671 (Task 2): FOUND
