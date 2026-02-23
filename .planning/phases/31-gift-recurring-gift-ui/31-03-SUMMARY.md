---
phase: 31-gift-recurring-gift-ui
plan: 03
subsystem: ui
tags: [react, recurring-gift, pledges, contact-detail, dashboard]

# Dependency graph
requires:
  - phase: 31-01
    provides: Gift/RecurringGift API layer, hooks, types, filter parsers, presets
provides:
  - Pledges list/detail/form pages rewired to RecurringGift model
  - Contact detail Donations/Pledges tabs rendering Gift/RecurringGift data
  - Dashboard late pledges placeholder
affects: [32-prayer-intentions-ui, 33-import-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: [re-export compatibility layer for renamed models]

key-files:
  modified:
    - frontend/src/pages/pledges/PledgeList.tsx
    - frontend/src/pages/pledges/PledgeDetail.tsx
    - frontend/src/pages/pledges/PledgeForm.tsx
    - frontend/src/api/pledges.ts
    - frontend/src/hooks/usePledges.ts
    - frontend/src/pages/contacts/ContactDetail.tsx
    - frontend/src/components/dashboard/NeedsAttention.tsx

key-decisions:
  - "Keep api/pledges.ts and hooks/usePledges.ts as re-export compatibility layers rather than removing them"
  - "NeedsAttention always shows late pledges placeholder (not conditional on count)"

patterns-established:
  - "Re-export pattern: old module re-exports from new module for backward compatibility"

requirements-completed: [UI-GIFT-02, UI-GIFT-04, UI-GIFT-06, DASH-02]

# Metrics
duration: 4min
completed: 2026-02-23
---

# Phase 31 Plan 03: Pledges/Contact/Dashboard UI Rewrite Summary

**Pledges pages rewired to RecurringGift with expanded status/frequency enums, Contact detail tabs updated for Gift/RecurringGift data, Dashboard late pledges replaced with placeholder**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-23T16:12:50Z
- **Completed:** 2026-02-23T16:17:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Pledges list shows RecurringGift data with 5 statuses (active/held/completed/cancelled/terminated) and 8 frequency options
- PledgeForm creates/updates RecurringGift with amount_cents conversion and full status/frequency dropdowns
- Contact detail Donations tab renders Gift fields (amount_dollars, gift_date, description, fund_name)
- Contact detail Pledges tab renders RecurringGift fields (amount_dollars, frequency, status) without is_late
- Dashboard NeedsAttention shows "Late detection coming soon" placeholder
- All visible text unchanged: "Pledges", "Donations", page titles, button labels

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite Pledges pages for RecurringGift model** - `368258e` (feat)
2. **Task 2: Update Contact detail tabs and Dashboard late pledges placeholder** - `881a6bf` (feat)

## Files Created/Modified
- `frontend/src/api/pledges.ts` - Re-exports RecurringGift types/functions as Pledge names
- `frontend/src/hooks/usePledges.ts` - Re-exports RecurringGift hooks as Pledge names
- `frontend/src/pages/pledges/PledgeList.tsx` - Pledges list using RecurringGift data with expanded filters
- `frontend/src/pages/pledges/PledgeDetail.tsx` - Pledge detail showing RecurringGift fields
- `frontend/src/pages/pledges/PledgeForm.tsx` - Pledge form with amount_cents conversion, all status/frequency options
- `frontend/src/pages/contacts/ContactDetail.tsx` - Donations/Pledges tabs rendering Gift/RecurringGift data shapes
- `frontend/src/components/dashboard/NeedsAttention.tsx` - Late pledges section replaced with placeholder

## Decisions Made
- Kept api/pledges.ts and hooks/usePledges.ts as thin re-export layers rather than removing them, preserving backward compatibility for any other imports
- NeedsAttention placeholder always renders (not conditional on latePledgeCount > 0) to ensure users see the "coming soon" message
- Removed pause/resume/cancel actions from PledgeList and PledgeDetail since RecurringGift API doesn't support these endpoints

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing build errors in DonationForm.tsx (references old Donation model fields like `contact`, `amount`, `date`, `donation_type`) -- NOT caused by this plan's changes. Out of scope for this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All Pledges pages fully rewired to RecurringGift model
- Contact detail tabs render correct data shapes
- Dashboard gracefully handles absent late pledge data
- DonationForm.tsx still needs updating in a separate plan (pre-existing issue)

## Self-Check: PASSED

All 7 modified files verified present. Both task commits (368258e, 881a6bf) verified in git log. Key content markers confirmed: amount_dollars in ContactDetail.tsx, "Late detection coming soon" in NeedsAttention.tsx, pledges/recurring/export/csv in PledgeList.tsx.

---
*Phase: 31-gift-recurring-gift-ui*
*Completed: 2026-02-23*
