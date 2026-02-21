---
phase: 30-data-migration-backend-cutover
plan: 01
subsystem: database
tags: [django, migrations, runpython, signals, data-migration, gifts]

# Dependency graph
requires:
  - phase: 27-new-models-prayer-intentions
    provides: Gift, RecurringGift, Solicitor models and migrations
  - phase: 29-re-import-pipeline-gifts-recurring
    provides: Gift and RecurringGift import services (donation/pledge migrations must exist)
provides:
  - Data migration copying all Donation -> Gift and Pledge -> RecurringGift records
  - Gift post_save/post_delete signal handlers for contact stat updates and event creation
  - RecurringGift.monthly_equivalent property for dashboard calculations
  - Signal skip mechanism (disable_gift_signals/enable_gift_signals) for bulk operations
affects: [30-02, 30-03, dashboard-services, contact-stats]

# Tech tracking
tech-stack:
  added: []
  patterns: [RunPython batched bulk_create with ignore_conflicts, thread-local signal skip]

key-files:
  created:
    - apps/gifts/migrations/0003_migrate_donation_pledge_data.py
    - apps/gifts/signals.py
  modified:
    - apps/gifts/models.py
    - apps/gifts/apps.py

key-decisions:
  - "Reuse DONATION_RECEIVED event type for Gift events to avoid orphaning existing events"
  - "Signal handler unconditionally sets needs_thank_you=True on new gifts (no thanked field check like Donation)"

patterns-established:
  - "Gift signal handlers mirror Donation signal pattern with donor_contact FK name"
  - "Batched bulk_create with ignore_conflicts for data migrations"

requirements-completed: [MIG-01, MIG-02]

# Metrics
duration: 2min
completed: 2026-02-20
---

# Phase 30 Plan 01: Data Migration & Gift Signals Summary

**RunPython migration copying 62 Donations to Gifts and 11 Pledges to RecurringGifts with UUID preservation, cents conversion, and Gift signal handlers for contact stat updates**

## Performance

- **Duration:** 2 min 16s
- **Started:** 2026-02-21T03:41:33Z
- **Completed:** 2026-02-21T03:43:49Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Data migration preserves UUIDs, converts Decimal amounts to cents, and maps legacy frequency/status values
- Gift post_save signal recalculates contact stats, sets needs_thank_you, and creates DONATION_RECEIVED events
- RecurringGift.monthly_equivalent property handles all 8 frequency types with correct Decimal math
- Thread-local signal skip mechanism available for bulk operations

## Task Commits

Each task was committed atomically:

1. **Task 1: Create data migration and RecurringGift.monthly_equivalent property** - `be12551` (feat)
2. **Task 2: Create Gift signal handlers and wire in apps.py** - `1250af6` (feat)

## Files Created/Modified
- `apps/gifts/migrations/0003_migrate_donation_pledge_data.py` - RunPython data migration with batched bulk_create
- `apps/gifts/signals.py` - Gift post_save/post_delete handlers with signal skip mechanism
- `apps/gifts/models.py` - Added monthly_equivalent property to RecurringGift
- `apps/gifts/apps.py` - Wired signals via GiftsConfig.ready()

## Decisions Made
- Reuse DONATION_RECEIVED event type for Gift events (per research recommendation) to avoid orphaning existing event records
- Gift signal sets needs_thank_you unconditionally on create (Gift has no `thanked` field unlike Donation)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Data migration applied and verified (62 Gifts, 11 RecurringGifts match source counts and amounts)
- Gift model now has full signal-driven behavior equivalent to Donation model
- Ready for Plan 02 (service cutover to use Gift/RecurringGift)

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 30-data-migration-backend-cutover*
*Completed: 2026-02-20*
