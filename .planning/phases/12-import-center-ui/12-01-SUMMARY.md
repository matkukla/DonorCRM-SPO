---
phase: 12
plan: 01
subsystem: backend-api
completed: 2026-02-04
duration: 9m 12s

requires:
  - "07-01: Funds CSV Import API (Fund model with external_id)"
  - "09-01: Entities CSV Import API (Contact.external_id for SPO compatibility)"
  - "10-01: Transactions CSV Import API (ImportRun audit trail)"
  - "11-01: Pledges CSV Import API (ImportRun for all 4 types)"

provides:
  - "GET /api/v1/imports/runs/latest/ endpoint for fetching latest import status"
  - "Admin-only API for Import Center UI tile data"
  - "Dependency counts for transaction/pledge import warnings"

affects:
  - "12-02: Import Center UI (will consume this API for tile status display)"

tech-stack:
  added: []
  patterns:
    - "Admin-only APIView with IsAdmin permission"
    - "ImportType.values iteration for latest run lookup"
    - "UUID to string serialization for JSON response"
    - "Dependency count queries with exclude filters"

key-files:
  created:
    - "apps/imports/tests/test_views.py"
  modified:
    - "apps/imports/views.py"
    - "apps/imports/urls.py"

decisions:
  - id: "12-01-D1"
    question: "How to structure latest runs response?"
    decision: "Return flat dict with import type keys (funds, entities, transactions, pledges) mapping to run data or null"
    alternatives:
      - "Array of runs with type field"
      - "Nested structure with metadata"
    rationale: "Flat structure easier for frontend to map directly to import tiles, null values explicit for never-imported types"

  - id: "12-01-D2"
    question: "Where does Fund model live?"
    decision: "apps.imports.models.Fund (not apps.donations.models)"
    alternatives:
      - "apps.donations.models.Fund"
    rationale: "Fund is part of SPO import infrastructure, not core donation domain"

  - id: "12-01-D3"
    question: "How to count entities with external_id?"
    decision: "Contact.objects.exclude(external_id='').exclude(external_id__isnull=True).count()"
    alternatives:
      - "Check if ImportRun for entities exists"
      - "Count all Contacts"
    rationale: "Accurate check for SPO-imported entities, excludes manually created contacts without external_id"

tags:
  - django
  - rest-framework
  - api
  - imports
  - admin
---

# Phase 12 Plan 01: Backend API for import status and dependency counts Summary

**One-liner:** Admin-only REST API endpoint returning latest ImportRun for each of 4 SPO import types plus dependency counts for UI warnings

## What Was Built

Added GET /api/v1/imports/runs/latest/ endpoint to support Import Center UI:

**LatestImportRunsView:**
- Admin-only APIView (IsAuthenticated + IsAdmin permissions)
- Returns latest ImportRun for each type (funds, entities, transactions, pledges)
- Null for types never imported
- Includes dependency_counts: funds_count, entities_with_external_id_count
- Used by frontend to display last import date/status on tiles and show dependency warnings

**Response format:**
```json
{
  "funds": {
    "id": "uuid-string",
    "status": "completed",
    "created_at": "2026-02-04T13:42:00Z",
    "created_count": 10,
    "updated_count": 5,
    "error_count": 0
  },
  "entities": null,
  "transactions": null,
  "pledges": null,
  "dependency_counts": {
    "funds_count": 15,
    "entities_with_external_id_count": 100
  }
}
```

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create LatestImportRunsView API endpoint | 4073239 | apps/imports/views.py |
| 2 | Wire URL and add tests | 6c1ce35 | apps/imports/urls.py, apps/imports/tests/test_views.py, apps/imports/views.py |

## Test Coverage

Created apps/imports/tests/test_views.py with 4 test cases:

1. **test_latest_import_runs_returns_null_for_no_imports**: Verifies all types return null when no imports exist, dependency_counts present with zeros
2. **test_latest_import_runs_returns_latest_run**: Creates 2 ImportRun for same type, verifies newest returned (by created_at DESC)
3. **test_latest_import_runs_requires_admin**: Non-admin user receives 403 Forbidden
4. **test_latest_import_runs_includes_dependency_counts**: Verifies accurate counts (excludes empty/null external_id)

All 206 import tests passing (no regressions).

## Decisions Made

### 12-01-D1: Flat response structure
**Context:** Frontend needs to map import types to tiles efficiently.

**Decision:** Return flat dict with type keys mapping to run data or null.

**Rationale:** Direct key access simpler than filtering arrays, null values explicit.

### 12-01-D2: Fund model location
**Context:** Initially imported from wrong module (apps.donations.models).

**Decision:** Fund lives in apps.imports.models (part of import infrastructure).

**Rationale:** Fund is SPO-specific import artifact, not core donation domain entity.

### 12-01-D3: Entity count excludes manually created contacts
**Context:** Dependency warning should reflect SPO-imported entities only.

**Decision:** Count contacts with non-empty external_id: `.exclude(external_id='').exclude(external_id__isnull=True)`

**Rationale:** Manually created contacts won't have external_id, only SPO imports provide external_id values.

## Deviations from Plan

None - plan executed exactly as written.

## Key Learnings

1. **ImportType.values iteration**: Clean pattern for querying latest run per type without hardcoding type strings
2. **UUID serialization**: str(run.id) required for JSON serialization of UUIDs
3. **Conditional uniqueness on external_id**: Contact.external_id allows blank ('') but not null, must exclude both for accurate count
4. **Admin-only patterns**: IsAdmin already imported and established pattern across import views

## Next Phase Readiness

**Phase 12-02 (Import Center UI) can proceed:**
- API endpoint available at /api/v1/imports/runs/latest/
- Response format matches 12-RESEARCH.md specification
- Admin-only enforcement in place
- Dependency counts ready for warning display

**No blockers identified.**

## Verification Evidence

```bash
# All LatestImportRunsView tests passing
python -m pytest apps/imports/tests/test_views.py::TestLatestImportRunsView -v --no-cov
# Result: 4 passed, 2 warnings in 3.77s

# All import tests passing (no regressions)
python -m pytest apps/imports -v --no-cov
# Result: 206 passed, 14 warnings in 8.43s
```

## Performance Notes

- **Duration:** 9 minutes 12 seconds
- **Velocity:** On track (v1.1 average: 4.4 min, this plan includes comprehensive test coverage)
- **Test execution:** 8.43s for full import test suite (206 tests)

## Links

- **Phase Research:** .planning/phases/12-import-center-ui/12-RESEARCH.md
- **Plan:** .planning/phases/12-import-center-ui/12-01-PLAN.md
- **Next Plan:** .planning/phases/12-import-center-ui/12-02-PLAN.md (Import Center UI)
