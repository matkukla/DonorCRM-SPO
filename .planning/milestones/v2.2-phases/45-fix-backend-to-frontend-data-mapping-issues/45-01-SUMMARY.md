---
phase: 45-fix-backend-to-frontend-data-mapping-issues
plan: 01
subsystem: testing
tags: [pytest, factory-boy, tdd, contacts, organization-name]

requires:
  - phase: 44-spo-data-import
    provides: Contact model with organization_name field

provides:
  - OrgContactFactory in apps/contacts/tests/factories.py
  - 7 failing RED tests specifying all org-contact mapping behaviors in test_org_contact_mapping.py

affects: [45-02, 45-03, 45-04, 45-05]

tech-stack:
  added: []
  patterns: [Nyquist TDD scaffold - RED tests written before any Wave 1 implementation]

key-files:
  created:
    - apps/contacts/tests/test_org_contact_mapping.py
  modified:
    - apps/contacts/tests/factories.py

key-decisions:
  - "OrgContactFactory uses empty string literals (not factory.Faker) for first_name and last_name to reliably produce blank names"
  - "All 7 org-contact behaviors specified as failing tests before any implementation — Nyquist compliance for Wave 1"

patterns-established:
  - "Test scaffold pattern: write all failing RED tests first, Wave N+1 tasks turn them green one-by-one"

requirements-completed: [ORG-01, ORG-02, ORG-03, ORG-04, ORG-05]

duration: 2min
completed: 2026-03-08
---

# Phase 45 Plan 01: Org-Contact TDD Test Scaffold Summary

**7 failing RED tests and OrgContactFactory establish the Nyquist compliance baseline for all org-contact mapping fixes across Wave 1 plans**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-08T00:07:33Z
- **Completed:** 2026-03-08T00:08:52Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `OrgContactFactory` to `apps/contacts/tests/factories.py` — subclasses `ContactFactory` with blank first/last names and fake company organization_name
- Created `apps/contacts/tests/test_org_contact_mapping.py` with 7 test functions covering all org-contact behaviors that Wave 1 must fix
- Verified all 7 tests FAIL against current unmodified codebase (confirmed RED state)

## Task Commits

1. **Task 1: Add OrgContactFactory to factories.py** - `776f3d3` (feat)
2. **Task 2: Create test_org_contact_mapping.py with 7 failing tests** - `cd87bab` (test)

## Files Created/Modified

- `apps/contacts/tests/factories.py` - Added `OrgContactFactory` subclass with blank names and fake company org name
- `apps/contacts/tests/test_org_contact_mapping.py` - 7 failing tests covering full_name, serializers, API endpoints, search, and CSV export

## Decisions Made

- `OrgContactFactory` uses empty string literals (`first_name = ''`, `last_name = ''`) rather than `factory.Faker` overrides — direct assignment is simpler and guarantees blank values
- All 7 behaviors specified as FAILING tests before any implementation code is written — strict Nyquist compliance ensures no Wave 1 task proceeds without a red test to turn green

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The pytest HTML coverage report showed a permission error on `htmlcov/` directory, but this is a pre-existing infrastructure issue unrelated to the tests themselves — tests ran and reported `7 failed` as expected.

## Next Phase Readiness

- Test scaffold complete — Wave 1 plans (45-02 through 45-05) can now proceed
- Each Wave 1 plan takes a subset of these 7 failing tests and turns them green by fixing the corresponding backend/frontend code
- Run `pytest apps/contacts/tests/test_org_contact_mapping.py -q --no-cov` to see current RED state at any time

---
*Phase: 45-fix-backend-to-frontend-data-mapping-issues*
*Completed: 2026-03-08*
