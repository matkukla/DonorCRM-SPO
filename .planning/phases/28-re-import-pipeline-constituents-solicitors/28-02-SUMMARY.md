---
phase: 28-re-import-pipeline-constituents-solicitors
plan: 02
subsystem: api
tags: [csv-import, raisers-edge, constituent, contact-matching, merge-only, django-management-command]

# Dependency graph
requires:
  - phase: 28-re-import-pipeline-constituents-solicitors
    plan: 01
    provides: "Shared RE import utilities: decode_csv_bytes, check_duplicate_import, _build_header_mapping"
  - phase: 27-foundation-models
    provides: "Contact.external_constituent_id field, ImportBatch model with SHA256 dedup"
provides:
  - "import_re_constituents() service orchestrator with three-tier contact matching"
  - "merge_contact_fields() merge-only update helper (never overwrites non-blank)"
  - "_match_contact() three-tier hierarchy: constituent_id > email > phone"
  - "Management command: import_re_constituents with --owner flag"
  - "API endpoint: POST /api/v1/imports/re/constituents/"
  - "CONSTITUENT_HEADER_ALIASES for flexible RE CSV column name matching"
affects: [phase-29, phase-32]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Three-tier contact matching hierarchy (constituent_id > email > phone)"
    - "Merge-only updates: fill blank fields, never overwrite existing non-blank values"
    - "ID match conflict warnings logged when email/phone differs from existing Contact"

key-files:
  created:
    - apps/imports/management/commands/import_re_constituents.py
  modified:
    - apps/imports/re_services.py
    - apps/imports/views.py
    - apps/imports/urls.py

key-decisions:
  - "Constituent header aliases support 5+ RE column name variants per field (e.g., cnbio_id, consid, constituent_id, cons_id, id)"
  - "Minimum data validation requires (first_name + last_name) or organization_name per row"
  - "external_constituent_id match is global (not owner-scoped) per UniqueConstraint; email/phone matches are owner-scoped"
  - "ID match conflicts logged as warnings but do not prevent merge-only update"

patterns-established:
  - "Three-tier contact matching: constituent_id (global) > email (owner-scoped) > phone (owner-scoped)"
  - "merge_contact_fields() reusable for any future merge-only import scenarios"

requirements-completed: [IMP-01, IMP-05, IMP-06, IMP-07]

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 28 Plan 02: RE Constituent Import Summary

**Three-tier contact matching (constituent_id > email > phone) with merge-only updates, minimum data validation, and row-level error collection for RE Constituent CSV import**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T02:00:29Z
- **Completed:** 2026-02-21T02:03:20Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Built import_re_constituents() orchestrator with SHA256 dedup, cascading encoding detection, header alias mapping, and row-level error collection
- Implemented three-tier contact matching hierarchy: external_constituent_id first (global), then email (owner-scoped), then phone (owner-scoped)
- Created merge_contact_fields() that only fills blank fields, never overwrites existing non-blank values
- Added management command (import_re_constituents --owner) and API endpoint (POST /api/v1/imports/re/constituents/) both sharing the same service layer

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement RE Constituent import service with match hierarchy and merge-only updates** - `945e236` (feat)
2. **Task 2: Create Constituent management command and API endpoint** - `b57f5eb` (feat)

## Files Created/Modified
- `apps/imports/re_services.py` - Added CONSTITUENT_HEADER_ALIASES, merge_contact_fields(), _match_contact(), import_re_constituents()
- `apps/imports/management/commands/import_re_constituents.py` - CLI command for constituent CSV import with --owner flag
- `apps/imports/views.py` - Added REConstituentImportView API endpoint
- `apps/imports/urls.py` - Added re/constituents/ URL pattern

## Decisions Made
- Constituent header aliases support 5+ RE column name variants per canonical field, matching the pattern established in Plan 01 for solicitors
- Minimum data validation requires at least (first_name AND last_name) or organization_name; rows lacking both are rejected with descriptive error
- external_constituent_id match is global (not owner-scoped) because the field has a global UniqueConstraint; email and phone matches are owner-scoped per existing Contact constraints
- When constituent_id matches but email/phone differs from existing Contact, warnings are logged and included in ImportBatch summary but do not block the merge-only update
- Reused existing flat alias_map format ({alias: canonical}) from Plan 01 rather than refactoring to {canonical: [aliases]} -- consistent with solicitor imports

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RE Constituent and Solicitor import pipelines both complete, ready for Phase 29 (Gift/RecurringGift imports)
- merge_contact_fields() and _match_contact() helpers available for reuse in any future contact-touching import
- Header alias mapping pattern established for all RE CSV import types

## Self-Check: PASSED

All 4 files verified present. Both task commits (945e236, b57f5eb) verified in git log.

---
*Phase: 28-re-import-pipeline-constituents-solicitors*
*Completed: 2026-02-20*
