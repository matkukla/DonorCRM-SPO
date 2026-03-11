---
phase: 38-ui-polish-list-page-cleanup
plan: 02
subsystem: ui
tags: [dialog, sheet, radix-ui, shadcn, django-migration, label-rename]

# Dependency graph
requires:
  - phase: 38-01
    provides: "Filter bar and list page cleanup foundation"
provides:
  - "All modal overlays use centered Dialog (no side-sliding Sheets remain in converted files)"
  - "Contact status label 'Potential Donor' replacing 'Prospect' in backend and frontend"
  - "Django migration for ContactStatus display label change"
affects: [38-03, contacts, analytics, prayer, journals]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dialog-first modal pattern: all overlays use centered Dialog with max-h-[80vh] and overflow-y-auto"

key-files:
  created:
    - "apps/contacts/migrations/0007_alter_contact_status.py"
  modified:
    - "frontend/src/components/layout/Header.tsx"
    - "frontend/src/pages/admin/analytics/components/FunnelDrilldownPanel.tsx"
    - "frontend/src/pages/admin/analytics/components/UserDrilldownPanel.tsx"
    - "frontend/src/pages/prayer/PrayerIntentionPanel.tsx"
    - "frontend/src/pages/journals/components/EventTimelineDrawer.tsx"
    - "apps/contacts/models.py"
    - "frontend/src/pages/contacts/ContactList.tsx"
    - "frontend/src/pages/contacts/ContactForm.tsx"
    - "frontend/src/pages/contacts/ContactDetail.tsx"

key-decisions:
  - "Kept DonationDetail.tsx Sheet import as-is (out of scope for this plan)"
  - "EventTimelineDrawer wrapped in Fragment to keep LogEventDialog as sibling outside Dialog"

patterns-established:
  - "Dialog modal sizing: max-w-xs (nav), max-w-lg (forms), max-w-2xl (tables), max-w-3xl (wide layouts)"
  - "Large-content Dialogs always have max-h-[80vh] overflow-y-auto"

requirements-completed: [UI-01, UI-02]

# Metrics
duration: 3min
completed: 2026-02-27
---

# Phase 38 Plan 02: Sheet-to-Dialog Conversion & Prospect Rename Summary

**Converted 5 Sheet (side-sliding) components to centered Dialog overlays and renamed 'Prospect' to 'Potential Donor' across backend model + 3 frontend contact pages**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-27T16:59:51Z
- **Completed:** 2026-02-27T17:02:41Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Converted Header mobile nav, FunnelDrilldownPanel, UserDrilldownPanel, PrayerIntentionPanel, and EventTimelineDrawer from Sheet to Dialog
- Each Dialog sized appropriately: xs for nav, lg for forms, 2xl for tables, 3xl for wide layouts
- All large-content Dialogs have max-h-[80vh] with overflow-y-auto for internal scrolling
- Renamed ContactStatus.PROSPECT display label from 'Prospect' to 'Potential Donor' in Django model
- Generated and included Django migration 0007_alter_contact_status
- Updated statusLabels and filterValueLabels in ContactList, ContactForm, and ContactDetail

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert 5 remaining Sheet components to centered Dialog** - `ca55477` (feat)
2. **Task 2: Rename "Prospect" to "Potential Donor" in backend and frontend** - `31c8e8c` (feat)

**Plan metadata:** (pending final commit)

## Files Created/Modified
- `frontend/src/components/layout/Header.tsx` - Mobile nav Sheet to Dialog (max-w-xs)
- `frontend/src/pages/admin/analytics/components/FunnelDrilldownPanel.tsx` - Funnel drilldown Sheet to Dialog (max-w-2xl)
- `frontend/src/pages/admin/analytics/components/UserDrilldownPanel.tsx` - User drilldown Sheet to Dialog (max-w-3xl)
- `frontend/src/pages/prayer/PrayerIntentionPanel.tsx` - Prayer intention Sheet to Dialog (max-w-lg)
- `frontend/src/pages/journals/components/EventTimelineDrawer.tsx` - Event timeline Sheet to Dialog (max-w-2xl)
- `apps/contacts/models.py` - ContactStatus.PROSPECT display label changed to 'Potential Donor'
- `apps/contacts/migrations/0007_alter_contact_status.py` - Django migration for label change
- `frontend/src/pages/contacts/ContactList.tsx` - statusLabels + filterValueLabels updated
- `frontend/src/pages/contacts/ContactForm.tsx` - statusLabels updated
- `frontend/src/pages/contacts/ContactDetail.tsx` - statusLabels updated

## Decisions Made
- Kept DonationDetail.tsx Sheet import untouched -- it was not in the plan's scope (only 5 specific files were targeted)
- EventTimelineDrawer: moved LogEventDialog outside the Dialog as a sibling wrapped in a Fragment, since nested Dialogs can cause portal issues

## Deviations from Plan

None - plan executed exactly as written.

Note: Task 2 commit (31c8e8c) included pre-existing staged files from previous work (gifts migrations, insights cleanup, sidebar changes). These were already staged before this plan's execution and are unrelated to the Prospect rename.

## Issues Encountered
- Database not running locally, so `python manage.py migrate` could not be applied. Migration file was created successfully and `python manage.py check` passes. Migration will be applied when database is available.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 5 targeted Sheet components now use centered Dialog
- One remaining Sheet import exists in DonationDetail.tsx (out of scope, may be addressed in future plans)
- Prospect-to-Potential Donor rename complete; migration needs to be applied when DB is available
- Ready for plan 03

## Self-Check: PASSED

All 10 files verified present. Both task commits (ca55477, 31c8e8c) verified in git log.

---
*Phase: 38-ui-polish-list-page-cleanup*
*Completed: 2026-02-27*
