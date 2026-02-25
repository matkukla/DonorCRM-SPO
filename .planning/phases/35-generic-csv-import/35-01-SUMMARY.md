---
phase: 35-generic-csv-import
plan: 01
subsystem: api
tags: [csv-import, generic-import, contacts, donations, django, rest-api]

# Dependency graph
requires:
  - phase: 28-re-csv-import
    provides: RE import utilities (decode_csv_bytes, check_duplicate_import, _build_header_mapping, _sanitize_field, _parse_amount_to_cents, _parse_date, merge_contact_fields)
provides:
  - Generic contact CSV import with configurable matching (name, email, external_id)
  - Generic donation CSV import creating Gift records linked to existing contacts
  - Two API endpoints at generic/contacts/ and generic/donations/
  - Staff-level access (IsStaffOrAbove permission, not admin-only)
affects: [35-02-generic-csv-import, frontend-import-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: [generic-import-orchestrator-pattern, configurable-match-by-strategy]

key-files:
  created:
    - apps/imports/generic_services.py
    - apps/imports/tests/test_generic_imports.py
  modified:
    - apps/imports/views.py
    - apps/imports/urls.py

key-decisions:
  - "Gift model has no owner field -- removed owner=owner from Gift.objects.create (plan specified it but model doesn't support it)"
  - "Staff users (not just admin) can access generic import endpoints via IsStaffOrAbove permission"

patterns-established:
  - "Generic import pattern: configurable match_by parameter (name, email, external_id) with header alias dicts reusing RE utilities"

requirements-completed: [IMP-08, IMP-09]

# Metrics
duration: 6min
completed: 2026-02-25
---

# Phase 35 Plan 01: Generic CSV Import Backend Summary

**Generic contact and donation CSV import orchestrators with configurable matching strategy (name/email/external_id), SHA256 dedup, row-level error collection, and staff-accessible API endpoints returning RE-compatible response shape**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-25T15:08:33Z
- **Completed:** 2026-02-25T15:14:39Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created generic_services.py with import_generic_contacts() and import_generic_donations() orchestrators
- Two API views (GenericContactImportView, GenericDonationImportView) with IsStaffOrAbove permission at generic/contacts/ and generic/donations/
- 13 tests all passing: contact create/update/name-match/dedup/error-collection, donation gift-creation/missing-contact/stat-recalculation, API endpoints/staff-access/read-only-denied

## Task Commits

Each task was committed atomically:

1. **Task 1: Create generic_services.py with contact and donation import orchestrators** - `39225eb` (feat)
2. **Task 2: Create API views, URL routes, and tests for generic imports** - `8c95d8a` (feat)

## Files Created/Modified
- `apps/imports/generic_services.py` - Two orchestrator functions (import_generic_contacts, import_generic_donations) with header alias dicts and configurable match_by
- `apps/imports/views.py` - GenericContactImportView and GenericDonationImportView with IsStaffOrAbove permission
- `apps/imports/urls.py` - generic/contacts/ and generic/donations/ URL routes
- `apps/imports/tests/test_generic_imports.py` - 13 tests covering service functions, API endpoints, permissions

## Decisions Made
- Gift model has no owner field -- removed `owner=owner` from Gift.objects.create that the plan specified (model only has donor_contact, fund, external_gift_id, amount_cents, gift_date, description)
- Staff users (not just admin) can access generic import endpoints via IsStaffOrAbove permission (per plan and research)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed non-existent owner field from Gift creation**
- **Found during:** Task 1 (generic_services.py creation)
- **Issue:** Plan specified `owner=owner` in Gift.objects.create() but Gift model has no owner field
- **Fix:** Removed owner=owner from gift_kwargs -- Gift ownership is implicit through donor_contact.owner
- **Files modified:** apps/imports/generic_services.py
- **Verification:** All 13 tests pass, Gift records created successfully
- **Committed in:** 39225eb (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix -- passing non-existent field would cause TypeError. No scope creep.

## Issues Encountered
- API test URLs initially used /api/imports/ instead of /api/v1/imports/ -- fixed to match project URL structure

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend endpoints ready for frontend integration in Plan 02
- Response shape matches RE import views so existing ImportResultBanner works without modification
- Both GENERIC_CONTACTS and GENERIC_DONATIONS ImportBatchType values already exist in models

## Self-Check: PASSED

- All 4 files verified present on disk
- Both commits (39225eb, 8c95d8a) verified in git log

---
*Phase: 35-generic-csv-import*
*Completed: 2026-02-25*
