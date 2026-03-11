---
phase: 42-mission-supervisor-role
plan: 02
subsystem: api
tags: [django, rbac, queryset-scoping, supervisor, permissions]

# Dependency graph
requires:
  - "42-01: get_visible_user_ids() helper and IsSupervisorWriteRestricted permission class"
provides:
  - "All list/detail views scoped via get_visible_user_ids() for supervisor role"
  - "IsSupervisorWriteRestricted on all detail views with write operations"
  - "Owner filter expanded to admin + mission_supervisor on contacts/gifts exports"
  - "Dashboard and insights services scoped via centralized helper"
affects: [42-03, 42-04, 42-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "visible = get_visible_user_ids(user); if visible is None: all else filter(owner_id__in=visible)"
    - "Owner filter expansion: user.role in ['admin', 'mission_supervisor'] with visible set validation"
    - "Write restrictions preserved on delete operations (JournalStageEventDeleteByStageView uses owner=user for non-admin)"

key-files:
  created: []
  modified:
    - "apps/contacts/views.py"
    - "apps/contacts/export_views.py"
    - "apps/gifts/views.py"
    - "apps/gifts/export_views.py"
    - "apps/tasks/views.py"
    - "apps/tasks/export_views.py"
    - "apps/events/views.py"
    - "apps/groups/views.py"
    - "apps/prayers/views.py"
    - "apps/journals/views.py"
    - "apps/journals/export_views.py"
    - "apps/dashboard/services.py"
    - "apps/insights/services.py"

key-decisions:
  - "JournalStageEventDeleteByStageView keeps admin-only write check (supervisor cannot delete missionaries' stage events)"
  - "JournalContactDestroyView keeps owner=user write restriction (supervisor cannot remove contacts from missionaries' journals)"
  - "Events views only show user's own events (not supervised users' events) since events are personal notifications"
  - "Owner filter validation uses int() cast for owner_id comparison against visible set (UUIDs stored as int in set)"

patterns-established:
  - "Consistent visible = get_visible_user_ids(user) pattern across all 13 view/service files"
  - "IsSupervisorWriteRestricted added to detail views: ContactDetailView, GiftDetailView, RecurringGiftDetailView, TaskDetailView, GroupDetailView, JournalDetailView, DecisionDetailView, NextStepDetailView"

requirements-completed: [SUPV-03]

# Metrics
duration: 9min
completed: 2026-03-02
---

# Phase 42 Plan 02: View-Level Queryset Scoping Summary

**Replaced all inline role checks across 13 view/service files with centralized get_visible_user_ids() helper for supervisor data visibility**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-02T17:36:35Z
- **Completed:** 2026-03-02T17:46:19Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Replaced 40+ inline role checks across contacts, gifts, tasks, events, groups, prayers, journals, dashboard, and insights with centralized get_visible_user_ids() helper
- Added IsSupervisorWriteRestricted permission to 8 detail views that support write operations
- Expanded owner filter from admin-only to admin + mission_supervisor with visible set validation on contacts and gifts list/export views
- Updated 6 dashboard service functions and 3 insights scope helpers for supervisor-aware data scoping

## Task Commits

Each task was committed atomically:

1. **Task 1: Update contacts, gifts, tasks, events, groups, and prayers view scoping** - `587117f` (feat)
2. **Task 2: Update journal views, dashboard services, and insights services scoping** - `c224891` (feat)

## Files Created/Modified
- `apps/contacts/views.py` - 11 role checks replaced with get_visible_user_ids(), IsSupervisorWriteRestricted added to ContactDetailView
- `apps/contacts/export_views.py` - Role check and owner filter updated for supervisor support
- `apps/gifts/views.py` - 4 role checks replaced, IsSupervisorWriteRestricted on GiftDetailView and RecurringGiftDetailView
- `apps/gifts/export_views.py` - 3 role checks and owner filters updated
- `apps/tasks/views.py` - 5 role checks replaced, IsSupervisorWriteRestricted on TaskDetailView
- `apps/tasks/export_views.py` - 1 role check replaced
- `apps/events/views.py` - 2 role checks replaced (events remain personal to user)
- `apps/groups/views.py` - 4 role checks replaced, IsSupervisorWriteRestricted on GroupDetailView
- `apps/prayers/views.py` - _owner_scoped_queryset helper updated
- `apps/journals/views.py` - 14+ role checks replaced across all journal views and analytics, IsSupervisorWriteRestricted on JournalDetailView, DecisionDetailView, NextStepDetailView
- `apps/journals/export_views.py` - 1 role check replaced
- `apps/dashboard/services.py` - 6 service functions updated (needs_attention, thank_you_queue, support_progress, recent_gifts, giving_summary, monthly_gifts)
- `apps/insights/services.py` - 3 scope helpers updated (_scope_gifts, _scope_recurring_gifts, _scope_tasks)

## Decisions Made
- JournalStageEventDeleteByStageView keeps admin-only write check -- supervisor cannot delete missionaries' stage events (write restriction by design)
- JournalContactDestroyView keeps owner=user write restriction -- supervisor cannot remove contacts from missionaries' journals
- Events views only show user's own events -- events are personal notifications, not shared data
- Owner filter validation uses int() cast for owner_id comparison -- ensures type compatibility with visible set

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All view-layer scoping complete, ready for frontend role-aware components (Plan 03)
- Supervisor can see aggregated data across assigned missionaries in all list views
- Write operations properly restricted to own data via IsSupervisorWriteRestricted
- Dashboard and insights services will correctly scope data when supervisor views their dashboard

## Self-Check: PASSED

All 13 modified files verified present. Both commit hashes (587117f, c224891) found in git log.

---
*Phase: 42-mission-supervisor-role*
*Completed: 2026-03-02*
