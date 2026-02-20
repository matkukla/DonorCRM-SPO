---
phase: 27-foundation-models
plan: 01
subsystem: database
tags: [django, orm, postgresql, gift-tracking, solicitor-credits, cents-based-money]

# Dependency graph
requires:
  - phase: core
    provides: TimeStampedModel base class (UUID PK, timestamps)
  - phase: contacts
    provides: Contact model for donor_contact FK
  - phase: imports
    provides: Fund model for gift fund FK
provides:
  - Solicitor model with normalized_name and optional User link
  - Gift model with cents-based amounts and external_gift_id
  - GiftCredit junction table for solicitor credit splitting
  - RecurringGift model with frequency/status enums
  - RecurringGiftCredit junction table for recurring gift credits
  - Django admin registrations for all 5 models
  - apps.gifts registered in INSTALLED_APPS
affects: [27-02, 28-re-import, 30-data-migration, 31-dashboard, 33-prayer-intentions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PositiveBigIntegerField for cents-based money with amount_dollars property"
    - "Junction tables (GiftCredit/RecurringGiftCredit) with per-credit amount_cents"
    - "Conditional UniqueConstraint on external IDs (existing pattern)"
    - "PROTECT on Solicitor FK to prevent deletion of credited solicitors"

key-files:
  created:
    - apps/gifts/__init__.py
    - apps/gifts/apps.py
    - apps/gifts/models.py
    - apps/gifts/admin.py
  modified:
    - config/settings/base.py

key-decisions:
  - "Solicitor delete behavior uses PROTECT to prevent accidental deletion of credited solicitors"
  - "GiftCredits are optional - gifts can exist without solicitor credit records"
  - "RecurringGift uses RE-compatible statuses (Active/Held/Completed/Cancelled/Terminated)"
  - "RecurringGift frequency includes bimonthly/biweekly/weekly/irregular beyond existing Pledge choices"
  - "Money fields use PositiveBigIntegerField (cents) with Decimal-based amount_dollars property"

patterns-established:
  - "Cents-based money: PositiveBigIntegerField + amount_dollars property returning Decimal"
  - "Credit junction tables: FK to parent + FK to Solicitor + amount_cents, with UniqueConstraint"
  - "RE-compatible enums: TextChoices matching Raiser's Edge export values"

requirements-completed: [MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05]

# Metrics
duration: 2min
completed: 2026-02-20
---

# Phase 27 Plan 01: Gifts App Models Summary

**Five gift-tracking models (Solicitor, Gift, GiftCredit, RecurringGift, RecurringGiftCredit) with cents-based amounts, solicitor credit splitting, and RE-compatible enums**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-20T22:48:33Z
- **Completed:** 2026-02-20T22:51:10Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created `apps/gifts/` Django app with 5 models inheriting TimeStampedModel
- All money fields use PositiveBigIntegerField (cents) with Decimal amount_dollars property
- Gift and RecurringGift have conditional UniqueConstraint on external IDs for idempotent imports
- GiftCredit and RecurringGiftCredit junction tables support multi-solicitor credit splitting with PROTECT delete
- Admin registrations with date_hierarchy, search, filter, and readonly fields for all 5 models
- App registered in INSTALLED_APPS (migrations deferred to Plan 02)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create gifts app with models** - `b3459c0` (feat)
2. **Task 2: Create gifts admin and register app** - `3d98a5e` (feat)

## Files Created/Modified
- `apps/gifts/__init__.py` - Empty app init
- `apps/gifts/apps.py` - GiftsConfig Django app configuration
- `apps/gifts/models.py` - Solicitor, Gift, GiftCredit, RecurringGift, RecurringGiftCredit models with TextChoices enums
- `apps/gifts/admin.py` - Admin registrations for all 5 models
- `config/settings/base.py` - Added apps.gifts to LOCAL_APPS

## Decisions Made
- **Solicitor FK delete behavior: PROTECT** - Prevents accidental deletion of solicitors with historical credit data; safest approach matching existing PROTECT patterns on owner FKs
- **GiftCredits optional on Gift** - RE data shows gifts can exist without solicitor credits (unsolicited/anonymous gifts); credit records are additive
- **RE-compatible status values** - RecurringGiftStatus uses Active/Held/Completed/Cancelled/Terminated matching RE export values; "Held" replaces "Paused" from Pledge model
- **Extended frequency choices** - Added bimonthly/biweekly/weekly/irregular beyond existing Pledge frequencies to cover full RE export range

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 gift models ready for Plan 02 (ImportBatch, PrayerIntention, Contact updates, migrations)
- Gift and RecurringGift FKs reference contacts.Contact and imports.Fund (existing models)
- Migrations intentionally deferred to Plan 02 which creates remaining models and runs all migrations together

---
*Phase: 27-foundation-models*
*Completed: 2026-02-20*

## Self-Check: PASSED
