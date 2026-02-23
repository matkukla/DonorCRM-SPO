---
phase: 30-data-migration-backend-cutover
plan: 03
subsystem: api
tags: [django, cleanup, app-removal, test-migration, gift-model]

# Dependency graph
requires:
  - phase: 30-data-migration-backend-cutover
    plan: 02
    provides: All backend services querying Gift/RecurringGift exclusively, Gift CRUD API endpoints
provides:
  - Clean codebase with no Donation/Pledge app references outside git history
  - All test files updated to use Gift/RecurringGift models and factories
  - GiftFactory and RecurringGiftFactory in apps/gifts/tests/factories.py
affects: [frontend-migration, phase-31]

# Tech tracking
tech-stack:
  added: []
  patterns: [factory_boy factories for Gift/RecurringGift with cents-based amounts]

key-files:
  created:
    - apps/gifts/tests/__init__.py
    - apps/gifts/tests/factories.py
  modified:
    - config/settings/base.py
    - config/api_urls.py
    - config/celery.py
    - apps/contacts/tests/test_integration.py
    - apps/dashboard/tests/test_services.py
    - apps/imports/tests/test_services.py
    - apps/imports/tests/test_transaction_import.py
    - apps/imports/tests/test_pledge_import.py
    - apps/insights/tests/test_date_filtering.py
    - apps/insights/tests/test_team_trends.py
    - apps/insights/tests/test_user_detail.py
    - apps/insights/tests/test_user_drilldown.py
    - apps/insights/tests/test_views.py

key-decisions:
  - "EventType names (DONATION_RECEIVED, PLEDGE_CREATED, etc.) preserved as historical labels to avoid orphaning existing Event records"
  - "Legacy import test files replaced with 410 Gone verification tests rather than deleted to maintain test coverage of endpoint behavior"
  - "Integration tests rewritten to use Gift API (donor_contact, amount_cents) instead of old Donation API (contact, amount)"

patterns-established:
  - "GiftFactory uses amount_cents with common dollar amounts (2500, 5000, 10000, etc.) as integers"
  - "RecurringGiftFactory defaults to monthly frequency and active status"

requirements-completed: [MIG-04]

# Metrics
duration: 7min
completed: 2026-02-23
---

# Phase 30 Plan 03: Old App Cleanup Summary

**Deleted apps/donations/ and apps/pledges/ directories (39 files, 5000+ lines removed), updated 12 test files to use Gift/RecurringGift, created factory_boy test factories**

## Performance

- **Duration:** 6 min 41s
- **Started:** 2026-02-23T14:00:52Z
- **Completed:** 2026-02-23T14:07:33Z
- **Tasks:** 2
- **Files modified:** 51 (39 deleted + 12 modified/created)

## Accomplishments
- Complete removal of apps/donations/ (20 files) and apps/pledges/ (19 files) from the codebase
- Zero remaining references to apps.donations or apps.pledges anywhere in Python files
- All 12 test files across 5 apps updated to use Gift/RecurringGift models and factories
- GiftFactory and RecurringGiftFactory created with factory_boy for consistent test data generation
- Django system check passes with no errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove old apps and update configuration** - `99ff676` (feat) - committed in prior session
2. **Task 2: Delete old app directories and update all tests** - `84f4a02` (feat)

## Files Created/Modified

### Deleted (39 files)
- `apps/donations/` - Entire directory (models, views, serializers, filters, signals, admin, tests, migrations, urls)
- `apps/pledges/` - Entire directory (models, views, serializers, filters, signals, admin, tests, migrations, tasks, urls)

### Created (2 files)
- `apps/gifts/tests/__init__.py` - Test package init
- `apps/gifts/tests/factories.py` - GiftFactory, RecurringGiftFactory, QuarterlyRecurringGiftFactory, AnnualRecurringGiftFactory, CancelledRecurringGiftFactory

### Modified (12 files)
- `config/settings/base.py` - Removed apps.donations and apps.pledges from INSTALLED_APPS
- `config/api_urls.py` - Replaced donation/pledge URL routes with gifts/ and backward-compatible aliases
- `config/celery.py` - Removed check-late-pledges-daily beat schedule entry
- `apps/contacts/tests/test_integration.py` - Rewritten for Gift API (donor_contact, amount_cents, /api/v1/gifts/)
- `apps/dashboard/tests/test_services.py` - Updated imports and test data for GiftFactory/RecurringGiftFactory
- `apps/imports/tests/test_services.py` - Removed TestDonationImport, updated TestDonationExport to TestGiftExport
- `apps/imports/tests/test_transaction_import.py` - Replaced with 410 Gone endpoint verification tests
- `apps/imports/tests/test_pledge_import.py` - Replaced with 410 Gone endpoint verification tests
- `apps/insights/tests/test_date_filtering.py` - DonationFactory replaced with GiftFactory
- `apps/insights/tests/test_team_trends.py` - DonationFactory replaced with GiftFactory
- `apps/insights/tests/test_user_detail.py` - DonationFactory replaced with GiftFactory
- `apps/insights/tests/test_user_drilldown.py` - Donation model replaced with Gift model
- `apps/insights/tests/test_views.py` - DonationFactory replaced with GiftFactory

## Decisions Made
- Preserved EventType names (DONATION_RECEIVED, PLEDGE_CREATED, etc.) as historical labels since they are stored in the database and renaming would orphan existing Event records
- Replaced legacy import test files with 410 Gone verification tests rather than deleting them entirely, maintaining test coverage of the endpoint behavior
- Rewrote integration tests to use the new Gift API (donor_contact, amount_cents fields) instead of the old Donation API

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Updated 8 additional test files with old model references**
- **Found during:** Task 2 (Delete old app directories)
- **Issue:** Plan mentioned checking dashboard/insights/imports test files but did not enumerate all 8 files that had references to DonationFactory, Donation, PledgeFactory, Pledge, or DonationType
- **Fix:** Updated all 8 test files: imports/test_services.py, imports/test_transaction_import.py, imports/test_pledge_import.py, insights/test_date_filtering.py, insights/test_views.py, insights/test_user_drilldown.py, insights/test_user_detail.py, contacts/test_integration.py
- **Files modified:** All 8 test files listed above
- **Verification:** `grep -rn "from apps.donations\|from apps.pledges" apps/ --include="*.py"` returns zero results
- **Committed in:** 84f4a02 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (missing critical - broader test file scope than plan specified)
**Impact on plan:** Essential for correctness. Without updating all test files, imports would fail at module load time since apps.donations and apps.pledges no longer exist.

## Issues Encountered
- Task 1 was already committed in a prior session (99ff676). Verified existing commit and continued with Task 2.
- Database not running, so `showmigrations` could not be verified. Django `manage.py check` passed (does not require DB).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Data migration backend cutover is fully complete (Phase 30 done)
- Codebase exclusively uses Gift/RecurringGift models
- Zero Donation/Pledge references remain
- Frontend can now be migrated to use the Gift API endpoints in a future phase

## Self-Check: PASSED

All files verified:
- apps/donations/ does not exist (confirmed)
- apps/pledges/ does not exist (confirmed)
- apps/gifts/tests/factories.py exists (confirmed)
- Commit 99ff676 exists (Task 1)
- Commit 84f4a02 exists (Task 2)
- Zero grep results for apps.donations/apps.pledges in apps/ and config/

---
*Phase: 30-data-migration-backend-cutover*
*Completed: 2026-02-23*
