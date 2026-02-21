---
phase: 28-re-import-pipeline-constituents-solicitors
plan: 01
subsystem: api
tags: [csv-import, raisers-edge, solicitor, encoding, sha256, django-management-command]

# Dependency graph
requires:
  - phase: 27-foundation-models
    provides: "Solicitor model, ImportBatch model with SHA256 dedup"
provides:
  - "Solicitor.user ForeignKey (many-to-one, not OneToOne)"
  - "Shared RE import utilities: decode_csv_bytes, check_duplicate_import, validate_csv_headers, normalize_solicitor_name"
  - "import_re_solicitors() service orchestrator with row-level error collection"
  - "Management command: import_re_solicitors with --owner flag"
  - "API endpoint: POST /api/v1/imports/re/solicitors/"
affects: [28-02, phase-29, phase-32]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cascading CSV encoding detection (UTF-8-sig > UTF-8 > Windows-1252)"
    - "SHA256 file dedup via ImportBatch before processing"
    - "Header alias mapping for RE CSV column name variations"
    - "User auto-linking via normalized name lookup with ambiguous exclusion"
    - "Row-level error collection (never abort mid-file)"

key-files:
  created:
    - apps/imports/re_services.py
    - apps/imports/management/commands/import_re_solicitors.py
    - apps/imports/management/__init__.py
    - apps/imports/management/commands/__init__.py
    - apps/gifts/migrations/0002_alter_solicitor_user.py
  modified:
    - apps/gifts/models.py
    - apps/imports/views.py
    - apps/imports/urls.py

key-decisions:
  - "Solicitor header aliases support 4+ RE column name variants per field"
  - "Only solicitor name field is required; external_solicitor_id is optional but preferred for dedup"
  - "Ambiguous user name matches (two users with same normalized name) excluded from auto-linking"
  - "File-level errors create FAILED ImportBatch with error in summary (no exception raised to caller)"

patterns-established:
  - "RE service layer pattern: shared utilities + orchestrator in re_services.py"
  - "Management command + API endpoint both call same service function"
  - "Header alias mapping dict for flexible RE CSV header matching"

requirements-completed: [IMP-02, IMP-05, IMP-06, IMP-07]

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 28 Plan 01: RE Solicitor Import Summary

**Solicitor FK fix (OneToOne to ForeignKey), shared RE import utilities (encoding cascade, SHA256 dedup, name normalization), and full solicitor import pipeline (service + CLI + API)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T01:54:19Z
- **Completed:** 2026-02-21T01:57:41Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Changed Solicitor.user from OneToOneField to ForeignKey allowing multiple solicitors per User
- Built shared RE import utility functions: cascading encoding detection, SHA256 dedup, header alias mapping, solicitor name normalization with "Last, First" and "First Last" format handling
- Implemented import_re_solicitors() orchestrator with row-level error collection, in-file dedup, database dedup, and User auto-linking
- Created management command (import_re_solicitors --owner) and API endpoint (POST /api/v1/imports/re/solicitors/) both sharing the same service layer

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Solicitor FK, build shared RE utilities, and implement Solicitor import service** - `131c895` (feat)
2. **Task 2: Create Solicitor management command and API endpoint** - `dfd8e6f` (feat)

## Files Created/Modified
- `apps/gifts/models.py` - Changed Solicitor.user from OneToOneField to ForeignKey
- `apps/gifts/migrations/0002_alter_solicitor_user.py` - Migration for FK change
- `apps/imports/re_services.py` - Shared RE import utilities and solicitor import orchestrator
- `apps/imports/management/__init__.py` - Management command package init
- `apps/imports/management/commands/__init__.py` - Commands package init
- `apps/imports/management/commands/import_re_solicitors.py` - CLI command for solicitor CSV import
- `apps/imports/views.py` - Added RESolicitorImportView API endpoint
- `apps/imports/urls.py` - Added re/solicitors/ URL pattern

## Decisions Made
- Solicitor header aliases support multiple RE column name variants (solicitor_id, solid, sol_id, cnsol_1_01_solicit_id for ID; solicitor_name, name, full_name, cnsol_1_01_name for name)
- Only the name field is strictly required for solicitor CSV import; external_solicitor_id is optional but preferred when present for more reliable dedup
- When two users have the same normalized name, both are excluded from auto-linking (ambiguous match) rather than picking one arbitrarily
- File-level errors (encoding, missing headers) create a FAILED ImportBatch record with error details in summary JSON rather than raising exceptions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Shared RE import utilities (decode_csv_bytes, check_duplicate_import, normalize_solicitor_name) ready for Plan 02's Constituent importer
- Header alias mapping pattern established for reuse with constituent CSV headers
- Service layer architecture (re_services.py) ready for import_re_constituents() function

## Self-Check: PASSED

All 9 files verified present. Both task commits (131c895, dfd8e6f) verified in git log.

---
*Phase: 28-re-import-pipeline-constituents-solicitors*
*Completed: 2026-02-20*
