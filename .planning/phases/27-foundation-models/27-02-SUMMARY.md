---
phase: 27-foundation-models
plan: 02
subsystem: database
tags: [django, orm, postgresql, prayer-intentions, import-dedup, sha256, re-constituent]

# Dependency graph
requires:
  - phase: 27-01
    provides: Gift model, Solicitor, GiftCredit, RecurringGift, RecurringGiftCredit models
  - phase: core
    provides: TimeStampedModel base class (UUID PK, timestamps)
  - phase: contacts
    provides: Contact model for prayer intention FK
  - phase: imports
    provides: ImportRun, ImportRowError, Fund models (coexist with new ImportBatch)
provides:
  - PrayerIntention model with required contact FK and optional gift FK
  - ImportBatch model with SHA256 dedup per import type
  - Contact model updated with external_constituent_id and organization_name fields
  - All Phase 27 migrations applied (gifts 0001, prayers 0001, imports 0003, contacts 0006)
  - Django admin registrations for PrayerIntention and ImportBatch
  - apps.prayers registered in INSTALLED_APPS
affects: [28-re-import, 30-data-migration, 33-prayer-intentions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SHA256 UniqueConstraint per import_type for file dedup (ImportBatch)"
    - "Conditional UniqueConstraint on external_constituent_id (non-empty only)"
    - "Status timestamps (answered_at, archived_at) alongside TextChoices status field"

key-files:
  created:
    - apps/prayers/__init__.py
    - apps/prayers/apps.py
    - apps/prayers/models.py
    - apps/prayers/admin.py
    - apps/prayers/migrations/__init__.py
    - apps/prayers/migrations/0001_initial.py
    - apps/gifts/migrations/__init__.py
    - apps/gifts/migrations/0001_initial.py
    - apps/imports/migrations/0003_importbatch_and_more.py
    - apps/contacts/migrations/0006_contact_external_constituent_id_and_more.py
  modified:
    - apps/imports/models.py
    - apps/imports/admin.py
    - apps/contacts/models.py
    - config/settings/base.py

key-decisions:
  - "ImportBatch coexists with ImportRun rather than replacing it"
  - "PrayerIntention.contact is required (not nullable) per user decision"
  - "external_constituent_id uses conditional UniqueConstraint (non-empty values only)"

patterns-established:
  - "SHA256 dedup: UniqueConstraint on (import_type, sha256_hash) for per-type file deduplication"
  - "Status timestamps: answered_at/archived_at alongside TextChoices status for audit tracking"

requirements-completed: [MODEL-06, MODEL-07, MODEL-08]

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 27 Plan 02: ImportBatch, PrayerIntention & Contact Updates Summary

**PrayerIntention model with required contact FK, ImportBatch with SHA256 dedup per import type, and Contact with external_constituent_id/organization_name -- all migrations applied**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-20T22:55:31Z
- **Completed:** 2026-02-20T22:58:48Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Created `apps/prayers/` Django app with PrayerIntention model (required contact FK, optional gift FK, 3-state status with timestamps)
- Added ImportBatch model to imports app with SHA256 hash UniqueConstraint per import type for file dedup, 7 import types, and 5 status values
- Added external_constituent_id and organization_name fields to Contact model with conditional unique constraint
- Created and applied all Phase 27 migrations: gifts 0001_initial (5 models), prayers 0001_initial, imports 0003_importbatch, contacts 0006_external_constituent_id
- Registered PrayerIntention and ImportBatch in Django admin with full list_display, filters, search
- Django system check passes with zero issues

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PrayerIntention model, ImportBatch model, and Contact field updates** - `43e14c8` (feat)
2. **Task 2: Register admin, update INSTALLED_APPS, and run all migrations** - `6f73cfa` (feat)

## Files Created/Modified
- `apps/prayers/__init__.py` - Empty app init
- `apps/prayers/apps.py` - PrayersConfig Django app configuration
- `apps/prayers/models.py` - PrayerIntention model with PrayerIntentionStatus TextChoices
- `apps/prayers/admin.py` - PrayerIntention admin registration with list_display, filters, search
- `apps/prayers/migrations/0001_initial.py` - Initial migration for PrayerIntention
- `apps/imports/models.py` - Added ImportBatch, ImportBatchType, ImportBatchStatus models
- `apps/imports/admin.py` - Added ImportBatch admin registration
- `apps/imports/migrations/0003_importbatch_and_more.py` - ImportBatch migration with unique constraint
- `apps/contacts/models.py` - Added external_constituent_id and organization_name fields
- `apps/contacts/migrations/0006_contact_external_constituent_id_and_more.py` - Contact field additions
- `apps/gifts/migrations/0001_initial.py` - Initial migration for all 5 gift models (from Plan 01)
- `config/settings/base.py` - Added apps.prayers to LOCAL_APPS

## Decisions Made
- **ImportBatch coexists with ImportRun** - ImportRun handles existing SPO imports; ImportBatch is the new universal import tracker for RE and future import types. No migration or replacement needed now.
- **PrayerIntention.contact is required** - Per user decision, every prayer intention must be tied to a donor contact (not nullable).
- **external_constituent_id conditional unique** - Uses conditional UniqueConstraint excluding empty strings, matching existing pattern for external_id and email constraints on Contact.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 8 MODEL requirements (MODEL-01 through MODEL-08) are now satisfied across Plans 01 and 02
- Phase 27 foundation models complete -- all migrations applied, admin registered, Django check passes
- Ready for Phase 28 (RE Import) which will build import logic on top of these models
- ImportBatch provides SHA256 dedup infrastructure for all import types
- PrayerIntention ready for Phase 33 (Prayer Intentions UI)
- Contact external_constituent_id ready for RE constituent matching in Phase 28

---
*Phase: 27-foundation-models*
*Completed: 2026-02-20*

## Self-Check: PASSED
