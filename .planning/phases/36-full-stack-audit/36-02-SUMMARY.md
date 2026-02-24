---
phase: 36-full-stack-audit
plan: 02
subsystem: api, ui, security
tags: [input-validation, rbac, csv-import, query-params, route-guards]

# Dependency graph
requires:
  - phase: 36-01
    provides: "Research findings identifying 11+ bare int() casts and missing write-route guards"
provides:
  - "Shared get_safe_int_param and get_safe_year_param in apps/core/utils.py"
  - "Write-route guards for read_only users on all create/edit routes"
  - "Import parser hardening: null byte strip, field truncation, sanitization"
affects: [security, api-endpoints, frontend-routing, import-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Shared query param validation utility in apps/core/utils.py", "requiredRole='staff' pattern for write-route protection"]

key-files:
  created:
    - apps/core/utils.py
  modified:
    - apps/dashboard/views.py
    - apps/insights/views.py
    - apps/insights/export_views.py
    - apps/tasks/views.py
    - apps/imports/re_services.py
    - frontend/src/App.tsx

key-decisions:
  - "get_safe_int_param placed in apps/core/utils.py as shared utility (avoids cross-app imports from insights)"
  - "get_safe_year_param added as dedicated year parser with 2000-2100 bounds"
  - "requiredRole='staff' used for write-route guards (excludes read_only=1 but allows staff=2, finance=3, admin=4 via existing hierarchy)"
  - "Import-export route also guarded since imports are write operations"
  - "Null byte stripping done at decode_csv_bytes level (single entry point for all importers)"
  - "Field truncation at 10000 chars via _sanitize_field helper applied to all row data extraction"

patterns-established:
  - "All query parameter int parsing must use get_safe_int_param from apps/core/utils"
  - "Write routes (new/edit) must have requiredRole='staff' guard in App.tsx"
  - "CSV import field values must go through _sanitize_field before DB storage"

requirements-completed: [AUDIT-01]

# Metrics
duration: 8min
completed: 2026-02-24
---

# Phase 36 Plan 02: Security Input Validation & Route Guards Summary

**Replaced 12 bare int() casts with safe param parsing, guarded 10 write routes for read_only users, and hardened CSV import parsers with null byte stripping and field truncation**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-24T15:28:39Z
- **Completed:** 2026-02-24T15:37:07Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created shared `get_safe_int_param` and `get_safe_year_param` utilities in `apps/core/utils.py` -- eliminates all bare int() casts on query parameters across dashboard, insights, tasks, and export views
- Guarded 10 write routes (contacts, donations, pledges, tasks, groups new/edit + import-export) with `requiredRole="staff"` to prevent read_only users from navigating to create/edit forms
- Hardened all 4 RE import parsers with null byte stripping at the decode level and field value truncation at 10,000 chars via `_sanitize_field` helper

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix all unvalidated int() casts across backend views** - `e139125` (fix)
2. **Task 2: Add write-route guards and review import parser input validation** - `fccc724` (fix)

**Plan metadata:** (pending)

## Files Created/Modified
- `apps/core/utils.py` - Shared get_safe_int_param and get_safe_year_param utilities
- `apps/dashboard/views.py` - 4 bare int() casts replaced (limit, days, months, year)
- `apps/insights/views.py` - 5 bare int() casts replaced + local get_safe_int_param removed
- `apps/insights/export_views.py` - 1 bare int() cast replaced (limit)
- `apps/tasks/views.py` - 1 bare int() cast replaced (days)
- `apps/imports/re_services.py` - Null byte stripping, _sanitize_field helper, applied to all row extraction
- `frontend/src/App.tsx` - 10 write routes guarded with requiredRole="staff"

## Decisions Made
- Placed shared utility in `apps/core/utils.py` rather than leaving it in insights/views.py to avoid cross-app imports
- Created dedicated `get_safe_year_param` for year parameters (returns None by default, bounds 2000-2100) since year has different semantics than general int params
- Used `requiredRole="staff"` for write-route guards -- leveraging existing role hierarchy (admin=4 > finance=3 > staff=2 > read_only=1) so read_only users are blocked while all other roles retain access
- Guarded `/import-export` route since imports are write operations that modify database state
- Applied null byte stripping at the `decode_csv_bytes` level since it is the single entry point for all 4 import orchestrators
- Set MAX_FIELD_LENGTH=10000 for field truncation as a reasonable upper bound for any CSV field value

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed bare int(year) in DonationsByMonthView**
- **Found during:** Task 1
- **Issue:** insights/views.py DonationsByMonthView had `year = int(year) if year else None` without try/except, same pattern as the dashboard GivingSummaryView
- **Fix:** Replaced with `get_safe_year_param(request, 'year')`
- **Files modified:** apps/insights/views.py
- **Committed in:** e139125

**2. [Rule 2 - Missing Critical] Fixed bare int() in export_views.py**
- **Found during:** Task 1 (full codebase search)
- **Issue:** TeamActivityCSVView in export_views.py had `limit = int(request.query_params.get('limit', 10000))` not identified in research
- **Fix:** Replaced with `get_safe_int_param(request, 'limit', default=10000, min_val=1, max_val=100000)`
- **Files modified:** apps/insights/export_views.py
- **Committed in:** e139125

---

**Total deviations:** 2 auto-fixed (2 missing critical)
**Impact on plan:** Both were additional bare int() casts found during comprehensive search. No scope creep -- directly within task scope.

## Issues Encountered
- App.tsx was concurrently modified by parallel plan execution (36-03 lazy loading), requiring a re-read before editing. Changes applied cleanly on the updated file.
- Pre-existing test failure in `test_team_trends.py::test_counts_donations_by_week` confirmed unrelated to our changes (fails on clean HEAD too).
- Pre-existing test failure in `test_services.py::TestGiftExport::test_export_gifts_csv` confirmed unrelated (fails on clean HEAD too).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All query parameter parsing is now safe across the entire backend
- Write routes are properly guarded for read_only users
- Import parsers handle malformed input gracefully
- Ready for remaining audit plans (API consistency, query optimization, etc.)

---
*Phase: 36-full-stack-audit*
*Completed: 2026-02-24*
