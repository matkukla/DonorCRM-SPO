---
phase: 53-view-as-frontend
plan: "03"
subsystem: frontend
tags: [view-as, read-only, sidebar, mutation-blocking, react]
dependency_graph:
  requires:
    - 53-01  # ViewAsProvider context + useViewAs hook
    - 53-02  # Banner + dashboard selector
  provides:
    - Full frontend read-only enforcement while isViewingAs is true
  affects:
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/pages/contacts/ContactList.tsx
    - frontend/src/pages/contacts/ContactDetail.tsx
    - frontend/src/pages/donations/DonationList.tsx
    - frontend/src/pages/donations/DonationDetail.tsx
    - frontend/src/pages/pledges/PledgeList.tsx
    - frontend/src/pages/tasks/TaskList.tsx
    - frontend/src/pages/journals/JournalList.tsx
    - frontend/src/pages/journals/JournalDetail.tsx
    - frontend/src/pages/journals/components/StageCell.tsx
    - frontend/src/pages/journals/components/EventTimelineDrawer.tsx
    - frontend/src/pages/groups/GroupList.tsx
    - frontend/src/pages/prayer/PrayerList.tsx
    - frontend/src/pages/goal/GoalPage.tsx
tech_stack:
  added: []
  patterns:
    - "useViewAs() second-pass filter: sidebar items filtered by isViewingAs after canAccess"
    - "isReadOnly extension: isViewingAs || existingCondition merges View As into existing guards"
    - "{!isViewingAs && <Button>} pattern for standalone create buttons"
    - "useViewAs() called directly in sub-components (StageCell, EventTimelineDrawer) to avoid prop drilling"
key_files:
  created: []
  modified:
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/pages/contacts/ContactList.tsx
    - frontend/src/pages/contacts/ContactDetail.tsx
    - frontend/src/pages/donations/DonationList.tsx
    - frontend/src/pages/donations/DonationDetail.tsx
    - frontend/src/pages/pledges/PledgeList.tsx
    - frontend/src/pages/tasks/TaskList.tsx
    - frontend/src/pages/journals/JournalList.tsx
    - frontend/src/pages/journals/JournalDetail.tsx
    - frontend/src/pages/journals/components/StageCell.tsx
    - frontend/src/pages/journals/components/EventTimelineDrawer.tsx
    - frontend/src/pages/groups/GroupList.tsx
    - frontend/src/pages/prayer/PrayerList.tsx
    - frontend/src/pages/goal/GoalPage.tsx
decisions:
  - "[53-03]: StageCell and EventTimelineDrawer use useViewAs() directly inside the component rather than via props — avoids prop drilling through JournalGrid intermediary"
  - "[53-03]: PrayerList inline status Select replaced with read-only StatusBadge when isViewingAs — prevents the onValueChange mutation from firing"
  - "[53-03]: GroupList Dialog open prop set to false when isViewingAs, DialogTrigger hidden — prevents dialog from opening even if open state somehow gets set"
  - "[53-03]: ContactDetail/DonationDetail isReadOnly extended as isViewingAs || existingCondition — existing !isReadOnly guards cover all mutations automatically"
metrics:
  duration: ~10min
  completed_date: "2026-03-17"
  tasks: 2
  files_changed: 14
requirements_satisfied:
  - VIEWAS-06
  - VIEWAS-09
---

# Phase 53 Plan 03: View As Read-Only Enforcement Summary

View As mode is now fully read-only from the frontend perspective: sidebar hides admin items, all 10 content pages hide create/edit/delete triggers, and GoalPage isReadOnly is driven by View As context.

## Tasks Completed

### Task 1: Sidebar nav hiding (commit 8302273)

Added `useViewAs` import and destructured `isViewingAs` in `Sidebar.tsx`. Added `VIEW_AS_HIDDEN_HREFS` set containing `/import-export` and `/admin`. Applied two second-pass filters on top of the existing `canAccess` function:

- `bottomNavItems.filter(canAccess).filter((item) => !isViewingAs || !VIEW_AS_HIDDEN_HREFS.has(item.href))` — hides Import/Export and Admin from bottom nav
- `filteredInsightsItems` extended: `.filter((item) => !isViewingAs || item.href !== "/insights/transactions")` — hides Transactions from Insights dropdown

The `canAccess` function was not modified. The `My Team` nav item remains visible in View As mode per the locked decision.

### Task 2: Mutation blocking across 11 pages (commit 2ed175a)

Applied `useViewAs` to all 11 page/component files:

**Pattern A — Extend isReadOnly (ContactDetail, DonationDetail):**
`const isReadOnly = isViewingAs || (existingCondition)` — all existing `!isReadOnly` guards automatically hide mutations.

**Pattern B — Direct `{!isViewingAs && <Button>}` wrapping (ContactList, DonationList, PledgeList, TaskList, JournalList, JournalDetail, GroupList, PrayerList):**
Each create button conditionally rendered.

**Pattern C — Row action guards:**
- ContactList: `canEdit && !isViewingAs` for Log Entry and Mark Thanked
- TaskList: `canEdit && !isViewingAs` for Edit and Mark Complete
- GroupList: Edit and Delete items each wrapped with `{!isViewingAs && ...}`

**Pattern D — Sub-component useViewAs() (StageCell, EventTimelineDrawer):**
Hook called directly inside each component to avoid prop drilling through JournalGrid.
- StageCell: `handleClick` returns early when `isViewingAs` (no stage event create/delete)
- EventTimelineDrawer: Log Event button hidden when `isViewingAs`

**GoalPage fix:**
Replaced `const isReadOnly = false // TODO(phase-52)` with:
```typescript
const { isViewingAs } = useViewAs()
const isReadOnly = isViewingAs
```

**PrayerList:**
Inline status `Select` replaced with read-only `StatusBadge` when `isViewingAs`. Row click guarded with `!isViewingAs && openEdit(intention)`.

## Verification

- `npm run build` passes (only 6 pre-existing errors unrelated to this plan)
- `grep -r "TODO(phase-52)" frontend/src` returns no results
- All 14 files modified, all compile without new errors

## Deviations from Plan

### Auto-applied

**[Rule 2 - Missing mutation guard] PrayerList inline status Select**
- **Found during:** Task 2
- **Issue:** The plan mentioned "Add Prayer intention actions" but the inline `Select` in each prayer row also triggers `handleInlineStatusChange` — a write mutation not explicitly listed in the audit table.
- **Fix:** Replaced the `Select` with a read-only `StatusBadge` when `isViewingAs`. Also guarded row click to prevent opening the edit panel.
- **Files modified:** `frontend/src/pages/prayer/PrayerList.tsx`
- **Commit:** 2ed175a

**[Rule 2 - Missing mutation guard] StageCell create/delete stage events**
- **Found during:** Task 2
- **Issue:** The plan listed "JournalDetail.tsx: journal edit/stage actions" but `StageCell` is a separate component inside `JournalGrid` that directly calls `createEvent`/`deleteEvents`. Not guarding it would leave a significant mutation pathway open.
- **Fix:** Added `useViewAs()` directly in `StageCell`, guarded `handleClick` to return early when `isViewingAs`.
- **Files modified:** `frontend/src/pages/journals/components/StageCell.tsx`
- **Commit:** 2ed175a

**[Rule 2 - Missing mutation guard] EventTimelineDrawer Log Event button**
- **Found during:** Task 2
- **Issue:** Plan listed "JournalDetail.tsx" mutations but `EventTimelineDrawer` (a sub-component) contains its own "Log Event" button which opens `LogEventDialog`.
- **Fix:** Added `useViewAs()` directly in `EventTimelineDrawer`, hidden Log Event button when `isViewingAs`.
- **Files modified:** `frontend/src/pages/journals/components/EventTimelineDrawer.tsx`
- **Commit:** 2ed175a

## Self-Check: PASSED

- SUMMARY.md: FOUND at .planning/phases/53-view-as-frontend/53-03-SUMMARY.md
- Commit 8302273: FOUND (Task 1 - Sidebar nav hiding)
- Commit 2ed175a: FOUND (Task 2 - Mutation blocking across all pages)
- All 14 key files modified and committed
- `TODO(phase-52)` reference: REMOVED from GoalPage.tsx
