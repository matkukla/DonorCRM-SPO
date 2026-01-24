---
phase: 03-decision-tracking
plan: 01
subsystem: database
tags: [django, postgres, models, migration, decimal]

# Dependency graph
requires:
  - phase: 02-contact-membership-search
    provides: JournalContact model for linking decisions
provides:
  - Decision model with amount, cadence, and status tracking
  - DecisionHistory model for append-only change logging
  - DecisionCadence enum (one_time, monthly, quarterly, annual)
  - DecisionStatus enum (pending, active, paused, declined)
  - monthly_equivalent property for normalized calculations
  - UniqueConstraint enforcing one decision per journal_contact
affects: [03-02-serializers, 03-03-api, analytics, reporting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Dual-table pattern (mutable Decision + append-only DecisionHistory)
    - monthly_equivalent property for cadence normalization

key-files:
  created:
    - apps/journals/migrations/0002_decision_decisionhistory.py
  modified:
    - apps/journals/models.py

key-decisions:
  - "DecimalField for amount storage (follows existing pledges/donations pattern)"
  - "Quarterly uses Decimal('1')/Decimal('3') multiplier (33.33 cents per month)"
  - "Annual uses Decimal('1')/Decimal('12') multiplier (8.33 cents per month)"
  - "One-time decisions return 0 for monthly_equivalent (excluded from recurring calculations)"

patterns-established:
  - "Decision state pattern: mutable current state + immutable history log"
  - "UniqueConstraint on journal_contact ensures single decision per membership"
  - "JSONField for changed_fields enables flexible history tracking"

# Metrics
duration: 2min
completed: 2026-01-24
---

# Phase 3 Plan 1: Decision Tracking Models Summary

**Decision and DecisionHistory models with cadence enums (one_time, monthly, quarterly, annual) and monthly_equivalent property for normalized calculations**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-24T23:01:24Z
- **Completed:** 2026-01-24T23:03:08Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Decision model with amount, cadence, status tracking and unique constraint per journal_contact
- DecisionHistory model for append-only change logging with JSONField for flexible field tracking
- DecisionCadence enum with 4 frequency options (one_time, monthly, quarterly, annual)
- DecisionStatus enum with 4 states (pending, active, paused, declined)
- monthly_equivalent property with correct multipliers for all cadences

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Decision and DecisionHistory models with enums** - `a6d39e6` (feat)
2. **Task 2: Create and apply migration** - `2de8143` (feat)

## Files Created/Modified
- `apps/journals/models.py` - Added Decision and DecisionHistory models, DecisionCadence and DecisionStatus enums
- `apps/journals/migrations/0002_decision_decisionhistory.py` - Created journal_decisions and journal_decision_history tables

## Decisions Made
None - followed plan as specified

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - no external service configuration required

## Next Phase Readiness
- Decision and DecisionHistory models ready for serializer layer (plan 03-02)
- monthly_equivalent property tested and verified for all cadences
- Database tables created with proper constraints and indexes
- Ready for API endpoint implementation

---
*Phase: 03-decision-tracking*
*Completed: 2026-01-24*
