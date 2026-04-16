---
phase: 01-duplicate-contact-checking-merging-github-issue-37
plan: 05
subsystem: ui
tags: [react, radix-ui, merge, contacts, duplicate-detection]

# Dependency graph
requires:
  - phase: 01-duplicate-contact-checking-merging-github-issue-37
    plan: 04
    provides: DuplicateList page, placeholder DuplicateMergeView, routes, sidebar nav
  - phase: 01-duplicate-contact-checking-merging-github-issue-37
    plan: 03
    provides: Frontend data layer (API types, hooks for merge/dismiss/contact queries)
  - phase: 01-duplicate-contact-checking-merging-github-issue-37
    plan: 02
    provides: Backend API endpoints for merge, dismiss, duplicate scan
  - phase: 01-duplicate-contact-checking-merging-github-issue-37
    plan: 01
    provides: Contact merge service, DismissedDuplicate model, MERGEABLE_FIELDS
provides:
  - Full DuplicateMergeView page at /contacts/duplicates/:pairId
  - MergeFieldRow component for per-field radio selection
  - Side-by-side contact comparison with survivor selection
  - Related records migration summary (gifts, recurring gifts, tasks, journal entries)
  - AlertDialog merge confirmation with destructive action
  - Keep Both Contacts dismissal flow
  - external_id and external_constituent_id exposed in ContactDetailSerializer
  - external_id and external_constituent_id added to MERGEABLE_FIELDS
affects: [01-06-creation-time-duplicate-check]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Accessible clickable table cells with role=radio instead of nested RadioGroup"
    - "Controlled field-override state reset on survivor selection change"
    - "Dynamic loser-side related record loading based on survivor selection"

key-files:
  created:
    - frontend/src/pages/contacts/components/MergeFieldRow.tsx
  modified:
    - frontend/src/pages/contacts/DuplicateMergeView.tsx
    - frontend/src/api/contacts.ts
    - apps/contacts/serializers.py
    - apps/contacts/services.py

key-decisions:
  - "Used clickable button cells with role=radio instead of nested RadioGroup to avoid table-semantics anti-pattern"
  - "Dynamic loser-side related record loading switches based on survivor selection"
  - "Added external_id and external_constituent_id to serializer and MERGEABLE_FIELDS for merge comparison"

patterns-established:
  - "MergeFieldRow: Accessible table cell radio pattern with visual indicator, aria-checked, min-h-[44px] touch target"

requirements-completed: [DUP-03, DUP-05, DUP-06, DUP-07, DUP-08]

# Metrics
duration: 4min
completed: 2026-03-27
---

# Phase 01 Plan 05: Merge View Summary

**Side-by-side contact merge page with survivor selection, 15-field comparison including external IDs, related records summary, and AlertDialog confirmation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T22:11:07Z
- **Completed:** 2026-03-27T22:15:00Z
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments
- Built full DuplicateMergeView page replacing Plan 04 placeholder with 383-line implementation
- Created MergeFieldRow component with accessible radio-like clickable cells (role=radio, aria-checked)
- All 15 merge-eligible fields including external_id and external_constituent_id per CONTEXT.md
- Related records migration summary with dynamic loser-side loading (gifts with total, recurring gifts, tasks, journal entries)
- AlertDialog merge confirmation with destructive CTA and Keep Both Contacts dismissal

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MergeFieldRow component and DuplicateMergeView page** - `1e3864a` (feat)

## Files Created/Modified
- `frontend/src/pages/contacts/components/MergeFieldRow.tsx` - Per-field radio selection row with identical-value collapse
- `frontend/src/pages/contacts/DuplicateMergeView.tsx` - Full merge view page (replaced placeholder)
- `frontend/src/api/contacts.ts` - Added external_id and external_constituent_id to ContactDetail type
- `apps/contacts/serializers.py` - Exposed external_id and external_constituent_id in ContactDetailSerializer
- `apps/contacts/services.py` - Added external_id and external_constituent_id to MERGEABLE_FIELDS

## Decisions Made
- Used accessible clickable button cells with role="radio" and aria-checked instead of nested RadioGroup components to avoid breaking table semantics (two RadioGroups for one value is an anti-pattern)
- Related records load dynamically based on which side is the loser, so switching survivor immediately updates the migration counts
- Added external_id and external_constituent_id to backend serializer and MERGEABLE_FIELDS (deviation Rule 2) since these fields were required for the merge comparison but not previously exposed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added external_id and external_constituent_id to backend**
- **Found during:** Task 1 (DuplicateMergeView implementation)
- **Issue:** external_id and external_constituent_id exist on the Contact model but were not exposed in ContactDetailSerializer or included in MERGEABLE_FIELDS, preventing the merge view from comparing or overriding these fields
- **Fix:** Added both fields to ContactDetailSerializer.fields and to the MERGEABLE_FIELDS frozenset in services.py; added to frontend ContactDetail TypeScript interface
- **Files modified:** apps/contacts/serializers.py, apps/contacts/services.py, frontend/src/api/contacts.ts
- **Verification:** TypeScript compilation passes; fields appear in MERGE_FIELDS constant in DuplicateMergeView
- **Committed in:** 1e3864a (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for the merge view to compare external IDs as specified in CONTEXT.md. No scope creep.

## Issues Encountered
None

## Known Stubs
None - all data sources are wired to live API hooks.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Merge view complete, ready for Plan 06 (creation-time duplicate check) which is already implemented
- All plan 01-05 requirements (DUP-03, DUP-05, DUP-06, DUP-07, DUP-08) satisfied

## Self-Check: PASSED

All files verified present. Commit 1e3864a confirmed in git log.

---
*Phase: 01-duplicate-contact-checking-merging-github-issue-37*
*Completed: 2026-03-27*
