---
phase: 24-smartsheet-import-backend
plan: 01
subsystem: database
tags: [django, models, openpyxl, mpd, smartsheet, import]

# Dependency graph
requires:
  - phase: 06-import-infrastructure
    provides: "imports app with Fund, ImportRun, ImportRowError models and TimeStampedModel base"
provides:
  - "MPDUpload model for audit trail of Smartsheet MPD report uploads"
  - "MPDSnapshot model for per-missionary monthly financial data"
  - "openpyxl dependency for Excel file parsing"
  - "Django admin registrations for MPDUpload and MPDSnapshot"
affects: [24-02-smartsheet-import-backend, 25-smartsheet-import-frontend]

# Tech tracking
tech-stack:
  added: [openpyxl>=3.1]
  patterns: [JSONField for unmatched row details, UniqueConstraint for dedup, nullable financial fields for partial data]

key-files:
  created:
    - apps/imports/migrations/0002_mpd_models.py
  modified:
    - apps/imports/models.py
    - apps/imports/admin.py
    - requirements/base.txt

key-decisions:
  - "DecimalField max_digits=12 for financial fields (accommodates values like $71,352.72 and roll forward balances)"
  - "months_remaining_rf as CharField (can be numeric or 'infinite')"
  - "pct_standard_to_max as IntegerField storing raw percentage (104 for '104%')"

patterns-established:
  - "MPDSnapshot accumulates historically (new records per upload, never overwrite)"
  - "UniqueConstraint on (user, upload) prevents duplicate snapshots per missionary per upload"

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 24 Plan 01: Data Models Summary

**MPDUpload and MPDSnapshot Django models with openpyxl dependency, migration, and admin registrations for Smartsheet MPD report import**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-19T15:31:12Z
- **Completed:** 2026-02-19T15:33:13Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- Created MPDUpload model with full audit trail (uploaded_by, filename, file_format, row counts, unmatched_rows JSON, status, error_message)
- Created MPDSnapshot model with 14 DecimalFields, 4 BooleanFields, 1 IntegerField (pct), 1 CharField (months_remaining_rf), UniqueConstraint on (user, upload), and index on (user, -created_at)
- Added openpyxl>=3.1,<4.0 to requirements/base.txt and installed in environment
- Registered both models in Django admin with list_display, list_filter, search_fields, readonly_fields

## Task Commits

Each task was committed atomically:

1. **Task 1: Add openpyxl dependency and create MPDUpload + MPDSnapshot models with migration and admin** - `cf249ab` (feat)

## Files Created/Modified
- `requirements/base.txt` - Added openpyxl>=3.1,<4.0 under Excel parsing section
- `apps/imports/models.py` - Added MPDUpload and MPDSnapshot model classes
- `apps/imports/admin.py` - Added MPDUploadAdmin and MPDSnapshotAdmin registrations
- `apps/imports/migrations/0002_mpd_models.py` - Django migration creating both tables with constraint and index

## Decisions Made
- DecimalField max_digits=12 (not 10) for financial fields to accommodate larger values like annual MPD estimates and roll forward balances
- months_remaining_rf stored as CharField since it can be numeric or "infinite"
- pct_standard_to_max stored as IntegerField (raw integer, e.g. 104 for "104%") for easy comparison
- Nullable financial fields allow partial data imports

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- MPDUpload and MPDSnapshot models are ready for Plan 02 to build the parsing service layer and API endpoint
- openpyxl is installed and available for XLSX parsing in the service layer
- Admin interface allows immediate visibility into imported data

## Self-Check: PASSED

All files verified present. Commit cf249ab verified in git log.

---
*Phase: 24-smartsheet-import-backend*
*Completed: 2026-02-19*
