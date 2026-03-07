---
phase: 44-modify-the-spo-data-import-and-reconciliation-workflow
plan: "01"
subsystem: imports
tags: [spo, missionary-alias, model, migration, admin, test-stubs]
dependency_graph:
  requires: []
  provides:
    - MissionaryAlias model (missionary_aliases table)
    - SPO ImportBatchType choices (spo_missionary, spo_gift, spo_prayer)
    - MissionaryAliasAdmin Django admin registration
    - Test stub files for all SPO behaviors (Wave 0 Nyquist)
  affects:
    - apps/imports/models.py
    - apps/imports/admin.py
    - apps/imports/migrations/
tech_stack:
  added: []
  patterns:
    - SimpleListFilter for nullable FK filtering in Django admin
    - TimeStampedModel base class for auto id/created_at/updated_at
    - Nullable ForeignKey with user=None sentinel for unresolved alias state
key_files:
  created:
    - apps/imports/migrations/0004_add_missionary_alias_spo_batch_types.py
    - apps/imports/tests/test_missionary_alias.py
    - apps/imports/tests/test_spo_services.py
    - apps/imports/tests/test_spo_commands.py
    - apps/imports/tests/test_spo_views.py
  modified:
    - apps/imports/models.py
    - apps/imports/admin.py
decisions:
  - "Used SimpleListFilter (UnresolvedAliasFilter) instead of user__isnull in list_filter — Django admin does not support lookup transforms as list_filter values"
  - "user=None on MissionaryAlias means admin-flagged unresolved (distinct from never seen) — prevents repeated auto-create for known-unresolvable names"
metrics:
  duration: "~3 minutes"
  completed_date: "2026-03-07"
  tasks: 2
  files: 7
---

# Phase 44 Plan 01: SPO Data Model Foundation Summary

**One-liner:** MissionaryAlias model with nullable-user sentinel for unresolved names, three SPO ImportBatchType choices, admin with SimpleListFilter, and 36-test Wave 0 stub scaffold.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | MissionaryAlias model + SPO ImportBatchType choices + migration + admin | d920d85 | models.py, admin.py, migration 0004 |
| 2 | Test stub files for all SPO behaviors (Wave 0 Nyquist) | b2c2650 | 4 test stub files (36 tests) |

## What Was Built

**MissionaryAlias model** (`apps/imports/models.py`):
- `source_name`: unique CharField (max 255), indexed — stores name exactly as it appears in SPO CSV export
- `user`: nullable FK to `users.User` with CASCADE, `related_name='name_aliases'`
- `notes`: blank TextField for admin notes
- `db_table = 'missionary_aliases'`
- `__str__` returns `'{source_name} -> {user}'`
- `user=None` sentinel: means admin saw this name and marked it unresolved — prevents auto-create loop for known-unresolvable names

**ImportBatchType additions** (`apps/imports/models.py`):
- `SPO_MISSIONARY = 'spo_missionary', 'SPO Missionary Reconciliation'`
- `SPO_GIFT = 'spo_gift', 'SPO Gift Import'`
- `SPO_PRAYER = 'spo_prayer', 'SPO Prayer Import'`

**MissionaryAliasAdmin** (`apps/imports/admin.py`):
- `list_display = ['source_name', 'user', 'notes', 'created_at']`
- `search_fields = ['source_name']`
- `list_filter = [UnresolvedAliasFilter]` — custom SimpleListFilter for resolved/unresolved
- `raw_id_fields = ['user']` — efficient FK lookup for large user tables
- `readonly_fields = ['id', 'created_at', 'updated_at']`

**Migration** (`0004_add_missionary_alias_spo_batch_types.py`):
- Alters `import_type` field max_length to accommodate new choice values
- Creates `missionary_aliases` table with all columns

**Test stubs** (36 tests, all passing):
- `test_missionary_alias.py`: 3 stubs for MissionaryAlias model behavior
- `test_spo_services.py`: 20 stubs for reconcile_missionaries + import_spo_gifts + idempotency
- `test_spo_commands.py`: 7 stubs for management command integration
- `test_spo_views.py`: 5 stubs for SPO API views

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed list_filter with user__isnull lookup transform**
- **Found during:** Task 1 migration generation
- **Issue:** `list_filter = ['user__isnull']` raised `admin.E116` — Django admin does not support lookup expressions in list_filter, only field names
- **Fix:** Created `UnresolvedAliasFilter(admin.SimpleListFilter)` with `lookups()` returning Resolved/Unresolved options and `queryset()` filtering on `user__isnull`
- **Files modified:** `apps/imports/admin.py`
- **Commit:** d920d85

## Self-Check: PASSED

All created files verified on disk. Both task commits (d920d85, b2c2650) confirmed in git log.
