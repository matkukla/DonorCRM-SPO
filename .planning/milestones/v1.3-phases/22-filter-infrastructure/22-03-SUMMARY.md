---
phase: 22-filter-infrastructure
plan: 03
subsystem: ui
tags: [nuqs, react, url-state, filter-bar, filter-wiring, csv-export, presets, FLT-08]

# Dependency graph
requires:
  - phase: 22-filter-infrastructure
    plan: 01
    provides: "Backend FilterSet classes with date range filtering and CSV export endpoints"
  - phase: 22-filter-infrastructure
    plan: 02
    provides: "useFilterParams hook, FilterBar/Badge/Presets/ExportCSV components, nuqs integration"
provides:
  - "ContactList reference implementation with FilterBar, useFilterParams, presets, badges, export"
  - "Transactions page FLT-08 fix (filters in URL params, not useState)"
  - "Reference pattern for wiring filter infrastructure to any list page"
affects: [23-per-page-filters]

# Tech tracking
tech-stack:
  added: []
  patterns: [FilterBar + useFilterParams wiring pattern for list pages, FilterPreset application with page reset]

key-files:
  created: []
  modified:
    - frontend/src/pages/contacts/ContactList.tsx
    - frontend/src/pages/insights/Transactions.tsx
    - frontend/src/api/contacts.ts
    - frontend/src/hooks/useFilterParams.ts

key-decisions:
  - "Used Record<string, any> for FilterParsers type constraint to avoid SingleParserBuilder incompatibility with ReturnType<>"
  - "Kept local searchInput state with useEffect sync for controlled search input (URL state drives truth, local state for typing)"
  - "Removed Transactions separate Filters Card wrapper in favor of FilterBar-managed layout"

patterns-established:
  - "Page wiring pattern: import useFilterParams + parsers, destructure filters/setFilters/clearAll/activeFilters/toQueryParams, pass to FilterBar and data hook"
  - "Filter reset pattern: setFilters({ [key]: null, page: 1 }) for page-based, setFilters({ [key]: null, offset: 0 }) for offset-based"
  - "Preset application pattern: setFilters({ ...preset.getParams(), page: 1 }) to apply preset and reset pagination"

# Metrics
duration: 5min
completed: 2026-02-17
---

# Phase 22 Plan 03: Filter Wiring to Pages Summary

**ContactList reference implementation with FilterBar/presets/badges/export and Transactions FLT-08 fix migrating useState to URL params**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-17T21:57:01Z
- **Completed:** 2026-02-17T22:02:38Z
- **Tasks:** 2 of 2 auto tasks completed (Task 3 is human-verify checkpoint)
- **Files modified:** 4

## Accomplishments
- ContactList page fully integrated with FilterBar, useFilterParams, contactPresets, ExportCSVButton, and active filter badges
- Transactions page FLT-08 bug fixed: dateFrom, dateTo, and offset now persisted in URL params instead of useState
- Added last_gift_after and last_gift_before to ContactFilters interface and getContacts API function
- Fixed FilterParsers type constraint in useFilterParams.ts that caused tsc -b build failure with nuqs SingleParserBuilder

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire FilterBar and useFilterParams to ContactList** - `2a1605a` (feat)
2. **Task 2: Fix Transactions page FLT-08 bug** - `d8249ee` (fix)

**Task 3:** Human verification checkpoint (handled by orchestrator)

## Files Created/Modified
- `frontend/src/pages/contacts/ContactList.tsx` - Full FilterBar integration replacing manual useSearchParams; status dropdown, thank-you toggle, search, presets, badges, export CSV
- `frontend/src/pages/insights/Transactions.tsx` - useState replaced with useFilterParams(transactionFilterParsers); FilterBar with date range inputs; handleFilterChange removed
- `frontend/src/api/contacts.ts` - Added last_gift_after and last_gift_before to ContactFilters interface and getContacts params
- `frontend/src/hooks/useFilterParams.ts` - Fixed FilterParsers type from ReturnType<> (incompatible with SingleParserBuilder) to Record<string, any>

## Decisions Made
- **Used Record<string, any> for FilterParsers type** -- nuqs SingleParserBuilder objects are not callable, so ReturnType<typeof parseAsString> fails under tsc -b strict mode. Using any for the index type preserves runtime safety (parsers are typed at definition site) while fixing the build.
- **Kept local searchInput state with useEffect sync** -- search needs a controlled input for typing without URL updates on every keystroke. useEffect syncs from URL -> local on external changes (back/forward navigation).
- **Removed Transactions Filters Card wrapper** -- FilterBar provides its own layout container, making the Card/CardHeader/CardTitle wrapper redundant.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed FilterParsers type constraint causing build failure**
- **Found during:** Task 1 (ContactList wiring)
- **Issue:** `tsc -b` (used by `npm run build`) failed with "SingleParserBuilder does not satisfy '(...args: any) => any'" because ReturnType<> expects a callable type but nuqs parsers are objects
- **Fix:** Changed FilterParsers from `Record<string, ReturnType<typeof parseAsString> | ...>` to `Record<string, any>` with eslint-disable comment
- **Files modified:** frontend/src/hooks/useFilterParams.ts
- **Verification:** `npm run build` passes
- **Committed in:** 2a1605a (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Pre-existing type issue in useFilterParams.ts from Plan 22-02 that only manifested with `tsc -b`. Minimal fix, no scope creep.

## Issues Encountered
- The `tsc --noEmit` check passes for the FilterParsers type but `tsc -b` (incremental build mode used by `npm run build`) is stricter and catches the type incompatibility. Future verification should use `npm run build` as the primary check.

## Pending Verification

**Task 3 (checkpoint:human-verify)** requires manual end-to-end testing:
- ContactList URL persistence, Clear All, presets, filter badges, Export CSV
- Transactions date filter URL persistence across refresh
- Dark mode rendering of all filter components

This checkpoint will be presented to the user by the orchestrator.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ContactList serves as the reference implementation for Phase 23 (per-page filter wiring)
- Transactions FLT-08 fix validates the useFilterParams pattern for offset-based pages
- All filter infrastructure (backend FilterSets + frontend hooks/components + page wiring) is complete
- Phase 23 can replicate the ContactList pattern to DonationList, PledgeList, TaskList

## Self-Check: PASSED

- All 4 modified files verified present on disk
- SUMMARY.md created at .planning/phases/22-filter-infrastructure/22-03-SUMMARY.md
- Commit 2a1605a (Task 1) found in git log
- Commit d8249ee (Task 2) found in git log
- npm run build passes (tsc -b + vite build)

---
*Phase: 22-filter-infrastructure*
*Completed: 2026-02-17*
