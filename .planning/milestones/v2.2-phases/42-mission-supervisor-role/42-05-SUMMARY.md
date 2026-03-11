---
phase: 42-mission-supervisor-role
plan: 05
subsystem: ui
tags: [react, django, serializers, owner-column, supervisor, read-only, filters]

# Dependency graph
requires:
  - phase: 42-02
    provides: "View-level queryset scoping with get_visible_user_ids, IsSupervisorWriteRestricted permission"
  - phase: 42-03
    provides: "mission_supervisor role in frontend types, supervised_users on auth User"
provides:
  - "Owner column on all 6 list pages for admin and supervisor"
  - "Owner filter expanded from admin-only to admin + supervisor on all list pages"
  - "Supervisor owner filter uses supervised_users from auth context"
  - "Row action gating: edit/delete hidden for supervisor on items they don't own"
  - "ContactDetail and GiftDetail read-only enforcement for supervisor viewing missionary data"
  - "owner_name field on GiftSerializer, RecurringGiftSerializer, JournalListSerializer, PrayerIntentionSerializer"
  - "Owner filter on TaskFilterSet, JournalFilterSet, PrayerIntentionFilterSet"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "canSeeOwner = admin || mission_supervisor for Owner column and filter visibility"
    - "ownerOptions pattern: admin uses usersData, supervisor uses supervised_users from auth context"
    - "isReadOnly = mission_supervisor && owner !== current user for detail page button gating"
    - "Conditional column spread: ...(canSeeOwner ? [{ accessorKey: 'owner_name' }] : [])"

key-files:
  created: []
  modified:
    - "apps/gifts/serializers.py"
    - "apps/gifts/views.py"
    - "apps/journals/serializers.py"
    - "apps/journals/filters.py"
    - "apps/prayers/serializers.py"
    - "apps/prayers/views.py"
    - "apps/prayers/filters.py"
    - "apps/tasks/filters.py"
    - "frontend/src/api/gifts.ts"
    - "frontend/src/api/tasks.ts"
    - "frontend/src/api/prayers.ts"
    - "frontend/src/types/journals.ts"
    - "frontend/src/hooks/useFilterParams.ts"
    - "frontend/src/pages/contacts/ContactList.tsx"
    - "frontend/src/pages/contacts/ContactDetail.tsx"
    - "frontend/src/pages/donations/DonationList.tsx"
    - "frontend/src/pages/donations/DonationDetail.tsx"
    - "frontend/src/pages/tasks/TaskList.tsx"
    - "frontend/src/pages/journals/JournalList.tsx"
    - "frontend/src/pages/prayer/PrayerList.tsx"
    - "frontend/src/pages/pledges/PledgeList.tsx"

key-decisions:
  - "Supervisor owner filter uses supervised_users from auth context rather than admin-only useUsers() hook"
  - "TaskList Owner column conditional for canSeeOwner (was previously always visible as 'Assigned To')"
  - "GiftDetail read-only check uses owner_name string comparison since gift detail doesn't expose owner_id directly"
  - "Backend filter sets for tasks, journals, and prayers now accept owner parameter"
  - "select_related expanded to include donor_contact__owner and contact__owner for N+1 prevention"

patterns-established:
  - "ownerOptions pattern: build array from usersData (admin) or supervised_users (supervisor)"
  - "canSeeOwner guard for conditional columns and filter visibility"
  - "isReadOnly guard for detail page mutation button gating"

requirements-completed: [SUPV-03]

# Metrics
duration: 12min
completed: 2026-03-02
---

# Phase 42 Plan 05: Supervisor List Pages & Read-Only UI Summary

**Owner columns on 6 list pages, expanded owner filters for supervisors, and read-only UI gating on ContactDetail and GiftDetail**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-02T17:50:12Z
- **Completed:** 2026-03-02T18:02:33Z
- **Tasks:** 2
- **Files modified:** 21

## Accomplishments
- Owner column visible on all 6 list pages (contacts, donations, tasks, journals, prayers, pledges) for admin and supervisor roles
- Owner filter expanded from admin-only to admin + supervisor on all list pages; supervisor's filter shows only their visible missionaries
- Row action gating hides edit/delete actions for supervisor on items they don't own
- ContactDetail hides edit, delete, and all child-create buttons when supervisor views a missionary's contact
- GiftDetail hides edit and delete buttons when supervisor views a missionary's gift
- Backend serializers (gifts, journals, prayers) now include owner_name; views updated with select_related for N+1 prevention
- Backend filter sets for tasks, journals, and prayers now accept owner query parameter

## Task Commits

Each task was committed atomically:

1. **Task 1: Add owner_name serializer fields and owner filter parsers** - `d3e1de8` (feat)
2. **Task 2: Add Owner columns, expand owner filter on list pages, and add read-only gating on detail pages** - `25c6091` (feat)

## Files Created/Modified
- `apps/gifts/serializers.py` - Added owner_name SerializerMethodField to GiftSerializer and RecurringGiftSerializer
- `apps/gifts/views.py` - Expanded select_related to include donor_contact__owner
- `apps/journals/serializers.py` - Added owner_name to JournalListSerializer
- `apps/journals/filters.py` - Added owner filter to JournalFilterSet
- `apps/prayers/serializers.py` - Added owner_name SerializerMethodField to PrayerIntentionSerializer
- `apps/prayers/views.py` - Expanded select_related to include contact__owner
- `apps/prayers/filters.py` - Added owner filter to PrayerIntentionFilterSet
- `apps/tasks/filters.py` - Added owner filter to TaskFilterSet
- `frontend/src/api/gifts.ts` - Added owner_name to Gift and RecurringGift interfaces
- `frontend/src/api/tasks.ts` - Added owner field to TaskFilters and getTasks
- `frontend/src/api/prayers.ts` - Added owner_name to PrayerIntention interface
- `frontend/src/types/journals.ts` - Added owner and owner_name to JournalListItem
- `frontend/src/hooks/useFilterParams.ts` - Added owner parser to task, journal, pledge filter parsers
- `frontend/src/pages/contacts/ContactList.tsx` - Owner column, expanded owner filter, row action gating
- `frontend/src/pages/contacts/ContactDetail.tsx` - Read-only enforcement for supervisor
- `frontend/src/pages/donations/DonationList.tsx` - Owner column, expanded owner filter
- `frontend/src/pages/donations/DonationDetail.tsx` - Read-only enforcement for supervisor
- `frontend/src/pages/tasks/TaskList.tsx` - Conditional Owner column, owner filter, row action gating
- `frontend/src/pages/journals/JournalList.tsx` - Owner name on cards, owner filter
- `frontend/src/pages/prayer/PrayerList.tsx` - Owner column, owner filter
- `frontend/src/pages/pledges/PledgeList.tsx` - Owner column, owner filter

## Decisions Made
- Supervisor owner filter uses `supervised_users` from auth context rather than admin-only `useUsers()` hook, since supervisors don't have access to the users API endpoint
- TaskList "Assigned To" column renamed to conditional "Owner" column visible only for admin/supervisor (was previously always visible)
- GiftDetail read-only check uses `owner_name` string comparison since the gift detail serializer doesn't expose a direct `owner_id` field
- Added `owner` filter to TaskFilterSet, JournalFilterSet, and PrayerIntentionFilterSet backend filter sets to support frontend owner filtering
- Expanded `select_related` in gift views and prayer views to include owner through relation chains (donor_contact__owner, contact__owner) to prevent N+1 queries

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added owner filter to backend FilterSets**
- **Found during:** Task 2 (Frontend owner filter implementation)
- **Issue:** TaskFilterSet, JournalFilterSet, PrayerIntentionFilterSet did not accept an `owner` query parameter, so frontend owner filter would be silently ignored
- **Fix:** Added `owner = django_filters.NumberFilter(field_name='owner_id')` (or `contact__owner_id`) to all three filter sets
- **Files modified:** apps/tasks/filters.py, apps/journals/filters.py, apps/prayers/filters.py
- **Verification:** Django check passes, frontend filter integrates correctly
- **Committed in:** 25c6091 (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added owner to TaskFilters TS interface**
- **Found during:** Task 2 (TaskList owner filter)
- **Issue:** TaskFilters interface and getTasks API function didn't include `owner` parameter
- **Fix:** Added owner field to TaskFilters and owner param append to getTasks
- **Files modified:** frontend/src/api/tasks.ts
- **Committed in:** 25c6091 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 missing critical)
**Impact on plan:** Both auto-fixes necessary for the owner filter to actually work end-to-end. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 42 (Mission Supervisor Role) is now complete with all 5 plans executed
- SUPV-01 through SUPV-04 requirements addressed across plans 01-05
- Backend security enforced by IsSupervisorWriteRestricted on all detail endpoints
- Frontend provides UX-level read-only gating on ContactDetail and GiftDetail
- Remaining detail pages (TaskDetail, JournalDetail, PrayerDetail, PledgeDetail) secured by backend; frontend gating can be added incrementally

## Self-Check: PASSED

All 21 modified files verified on disk. Both task commits (d3e1de8, 25c6091) verified in git log.

---
*Phase: 42-mission-supervisor-role*
*Completed: 2026-03-02*
