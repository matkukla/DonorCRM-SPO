---
phase: 36-full-stack-audit
plan: 01
subsystem: api, ui, database
tags: [django-filters, react-query, cache-invalidation, import-pipeline]

# Dependency graph
requires:
  - phase: 27-gift-model
    provides: Gift/RecurringGift models and ImportBatch model
  - phase: 28-re-import
    provides: RE import pipeline with SHA256 dedup
  - phase: 31-gift-recurring-gift-ui
    provides: NeedsAttention component and useImports hooks
provides:
  - ImportBatch duplicate status persisted to DB for accurate import history
  - Gift amount filters correctly convert dollars to cents
  - NeedsAttention renders conditionally based on actual data
  - useREImport invalidates correct cache keys for all affected resources
  - MODEL-01 through MODEL-08 requirements marked complete
affects: [36-full-stack-audit, dashboard, imports]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Method filters for dollar-to-cents conversion in django-filters"
    - "Cache key consistency between query definitions and invalidation calls"

key-files:
  created: []
  modified:
    - apps/imports/re_services.py
    - apps/gifts/filters.py
    - frontend/src/components/dashboard/NeedsAttention.tsx
    - frontend/src/hooks/useImports.ts
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Keep latePledges/latePledgeCount in NeedsAttention interface for backward compatibility with Dashboard.tsx caller"
  - "RecurringGiftFilterSet has no amount filters so no fix needed there"

patterns-established: []

requirements-completed: [AUDIT-01]

# Metrics
duration: 5min
completed: 2026-02-24
---

# Phase 36 Plan 01: Known Tech Debt Fixes Summary

**Fixed 6 tech debt items: ImportBatch duplicate status persistence, gift amount dollar-to-cents filter conversion, NeedsAttention conditional rendering, and React Query cache key corrections**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-24T15:28:36Z
- **Completed:** 2026-02-24T15:33:13Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- All 4 ImportBatch duplicate status assignments in re_services.py now persist to DB via save(update_fields=['status'])
- Gift amount filters convert dollar input to cents (value * 100) before querying amount_cents field
- NeedsAttention component renders based on actual hasItems condition instead of always-true workaround
- useREImport cache invalidation corrected from 'recurringGifts' to 'recurring-gifts' and added missing 'prayers' and 'dashboard' keys
- MODEL-01 through MODEL-08 checkboxes and traceability rows marked as Complete in REQUIREMENTS.md

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix backend tech debt (ImportBatch duplicate status + Gift amount filter)** - `d7fdffd` (fix)
2. **Task 2: Fix frontend tech debt (NeedsAttention, cache keys, REQUIREMENTS.md)** - `1bf7835` (fix)

## Files Created/Modified
- `apps/imports/re_services.py` - Added existing.save(update_fields=['status']) after all 4 DUPLICATE status assignments
- `apps/gifts/filters.py` - Replaced direct NumberFilter with method filters that multiply dollar input by 100
- `frontend/src/components/dashboard/NeedsAttention.tsx` - Removed || true workaround, late pledges placeholder, and unused Clock import
- `frontend/src/hooks/useImports.ts` - Fixed 'recurringGifts' to 'recurring-gifts', added 'prayers' and 'dashboard' invalidations
- `.planning/REQUIREMENTS.md` - Checked MODEL-01 through MODEL-08 and updated traceability table

## Decisions Made
- Kept latePledges/latePledgeCount in NeedsAttentionProps interface (but removed from destructuring) to avoid breaking Dashboard.tsx caller
- RecurringGiftFilterSet confirmed to have no amount filters, so no fix needed there

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused Clock import**
- **Found during:** Task 2 (NeedsAttention cleanup)
- **Issue:** After removing the late pledges placeholder, the Clock icon import from lucide-react was unused
- **Fix:** Removed Clock from the import statement
- **Files modified:** frontend/src/components/dashboard/NeedsAttention.tsx
- **Verification:** TypeScript compilation passes (npx tsc --noEmit)
- **Committed in:** 1bf7835 (Task 2 commit)

**2. [Rule 2 - Missing Critical] Updated REQUIREMENTS.md traceability table**
- **Found during:** Task 2 (REQUIREMENTS.md update)
- **Issue:** Traceability table still showed MODEL-01 through MODEL-08 as "Pending" even though checkboxes were being updated
- **Fix:** Updated all 8 MODEL rows in traceability table from "Pending" to "Complete"
- **Files modified:** .planning/REQUIREMENTS.md
- **Verification:** Confirmed both checkboxes and table rows match
- **Committed in:** 1bf7835 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both auto-fixes necessary for correctness and consistency. No scope creep.

## Issues Encountered
- Pre-existing test failure in TestGiftExport::test_export_gifts_csv (expects "100.00" but gets "100") -- unrelated to our changes, not in scope

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Clean baseline established for the rest of the full-stack audit (plans 02-06)
- All known v2.0 milestone tech debt items resolved
- Pre-existing test failure in gift export noted for future audit plans

---
*Phase: 36-full-stack-audit*
*Completed: 2026-02-24*
