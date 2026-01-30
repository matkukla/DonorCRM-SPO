---
phase: 07-foundation
plan: 02
subsystem: database
tags: [django, postgresql, migrations, external_id, fund, imports]

# Dependency graph
requires:
  - phase: 07-01
    provides: Fund, ImportRun, ImportRowError models in imports app
provides:
  - Contact.external_id field for idempotent contact imports
  - Donation.fund FK linking donations to Fund model
  - Pledge.external_id field for idempotent pledge imports
  - Pledge.fund FK linking pledges to Fund model
  - Applied database migrations for all v1.1 model changes
affects: [08-entity-import, 09-transaction-import, 10-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Conditional UniqueConstraint for optional external IDs (blank allowed, unique when present)
    - Owner-scoped uniqueness for Contact.external_id (same ID allowed for different owners)
    - Global uniqueness for Pledge.external_id (SPO pledge_ids are globally unique)

key-files:
  created:
    - apps/imports/migrations/0001_create_import_models.py
    - apps/contacts/migrations/0005_add_external_id.py
    - apps/donations/migrations/0004_add_fund_fk.py
    - apps/pledges/migrations/0003_add_external_id_and_fund.py
  modified:
    - apps/contacts/models.py
    - apps/donations/models.py
    - apps/pledges/models.py

key-decisions:
  - "Contact.external_id owner-scoped: same external ID allowed for different owners"
  - "Pledge.external_id globally unique: SPO pledge_ids are globally unique"
  - "Conditional uniqueness using ~Q(external_id='') allows multiple blank values"

patterns-established:
  - "External ID pattern: CharField(max_length=100, blank=True, db_index=True) with conditional UniqueConstraint"
  - "Fund FK pattern: ForeignKey(imports.Fund, SET_NULL, null=True, blank=True) for optional fund tracking"

# Metrics
duration: 2m 41s
completed: 2026-01-30
---

# Phase 7 Plan 02: Entity Fields for Import Summary

**External_id fields added to Contact/Pledge models for idempotent imports, fund FKs added to Donation/Pledge models for fund tracking, all migrations applied**

## Performance

- **Duration:** 2m 41s
- **Started:** 2026-01-30T17:43:48Z
- **Completed:** 2026-01-30T17:46:29Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Contact model now has external_id field with owner-scoped conditional uniqueness
- Donation model now has fund FK to imports.Fund for fund tracking
- Pledge model now has external_id field with global conditional uniqueness and fund FK
- All 4 migrations generated and applied cleanly (imports, contacts, donations, pledges)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add external_id to Contact model** - `7f2030e` (feat)
2. **Task 2: Add fund FK to Donation and external_id + fund FK to Pledge** - `198dd8d` (feat)
3. **Task 3: Generate and apply all migrations** - `79b3a19` (chore)

## Files Created/Modified
- `apps/contacts/models.py` - Added external_id CharField and UniqueConstraint
- `apps/donations/models.py` - Added fund FK to imports.Fund
- `apps/pledges/models.py` - Added external_id CharField, fund FK, and UniqueConstraint
- `apps/imports/migrations/0001_create_import_models.py` - Creates Fund, ImportRun, ImportRowError tables
- `apps/contacts/migrations/0005_add_external_id.py` - Adds external_id column and constraint
- `apps/donations/migrations/0004_add_fund_fk.py` - Adds fund_id column
- `apps/pledges/migrations/0003_add_external_id_and_fund.py` - Adds external_id, fund_id columns and constraint

## Decisions Made
- **07-02-D1:** Contact.external_id uses owner-scoped uniqueness - same external ID allowed for different owners since SPO entity_ids may overlap between organizations
- **07-02-D2:** Pledge.external_id uses global uniqueness - SPO pledge_ids are globally unique across all organizations
- **07-02-D3:** Conditional uniqueness via ~Q(external_id='') allows existing records to have blank external_id without violating constraint

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all model changes and migrations applied cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All entity models now ready for CSV import processing
- Contact, Donation, Pledge models have external_id fields for upsert matching
- Donation, Pledge models have fund FK for fund attribution
- Phase 08 (Entity Import) can now implement import service for entities
- Phase 09 (Transaction Import) can now implement import service for donations/pledges with fund linking

---
*Phase: 07-foundation*
*Completed: 2026-01-30*
