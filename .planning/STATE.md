# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems.
**Current focus:** Phase 12 - Import Center UI (v1.1 CSV Import milestone)

## Current Position

Phase: 12 of 12 (Import Center UI)
Plan: 05 of 05 completed
Status: Phase complete
Last activity: 2026-02-10 - Completed quick task 004: Fix ImportDialog empty file bug

Progress: [█████████░░░░░░░░░░░] 54% (v1.0 complete + Phases 7-11 + 12-01, 12-02, 12-03, 12-04, 12-05)

## Performance Metrics

**Velocity:**
- Total plans completed: 39 (24 v1.0 + 15 v1.1)
- Average duration: 3.5 minutes
- Total execution time: 2.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| v1.0 (Phases 1-6) | 24 | 1.4 hours | 2.8 min |
| v1.1 (Phases 7-12) | 15/15 | 76m 43s | 5.1 min |

**Recent Trend:**
- v1.0 milestone shipped successfully
- v1.1 milestone: 07-01 (1m 53s), 07-02 (2m 41s), 08-01 (4m), 08-02 (3m 38s), 09-01 (7m), 09-02 (4m 14s), 10-01 (5m 48s), 10-02 (4m 45s), 11-01 (6m 26s), 11-02 (3m 55s), 12-01 (9m 12s), 12-02 (7m 28s), 12-03 (10m 1s), 12-04 (2m 28s), 12-05 (2m 54s)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Django/DRF backend pattern continues from existing codebase
- External ID fields for idempotent upserts (SPO compatibility)
- Strict mode validation (reject entire import if any orphan references)
- Synchronous import processing for MVP (no Celery infrastructure)
- **07-01-D1:** Fund.external_id globally unique (not owner-scoped)
- **07-01-D2:** Fund.owner nullable for org-wide funds
- **07-02-D1:** Contact.external_id owner-scoped (same ID allowed for different owners)
- **07-02-D2:** Pledge.external_id globally unique (SPO pledge_ids are globally unique)
- **07-02-D3:** Conditional uniqueness via ~Q(external_id='') allows blank values
- **08-01-D1:** Status validation is case-insensitive (ACTIVE → active)
- **08-01-D2:** Status defaults to 'active' when missing from CSV
- **08-01-D3:** Formula character detection prevents CSV injection attacks
- **08-01-D4:** Funds imported with null owner (org-wide by default)
- **09-01-D1:** update_or_create for Contact upserts (bulk_create incompatible with conditional unique constraints)
- **09-01-D2:** Name splitting: last word = last_name, rest = first_name
- **09-01-D3:** entity_type column ignored (Contact has no such field)
- **10-01-D1:** update_or_create for Donation upserts (same conditional unique constraint issue as Contact)
- **10-01-D2:** Contact lookup is owner-scoped, Fund lookup is global (critical for data isolation)
- **10-01-D3:** Strict mode rejects entire import if ANY orphan FK found (ensures data consistency)
- **11-01-D1:** fund_id optional for pledges (validate only if non-empty, different from transactions)
- **11-01-D2:** CSV 'cadence' column maps to Pledge.frequency model field (SPO vs DonorCRM terminology)
- **11-01-D3:** No Contact stats update after pledge import (pledges use computed properties, not denormalized fields)
- **11-01-D4:** start_date can be in future for pledges (unlike donation posted_date which must be historical)
- **11-02-D1:** PledgeImportView has no update_contact_stats_for_import call (traced to 11-01-D3)
- **11-02-D2:** Integration tests verify computed properties work and stats unchanged
- **11-02-D3:** UTF-8 BOM test uses byte format matching Excel export format
- **12-01-D1:** Flat response structure (dict with type keys) for efficient frontend mapping
- **12-01-D2:** Fund model in apps.imports.models (SPO import artifact, not core domain)
- **12-01-D3:** Entity count excludes manually created contacts (only SPO-imported with external_id)
- **12-02-D1:** react-papaparse for client-side CSV preview (types bundled, no @types package)
- **12-02-D2:** SPOImportResult type distinct from legacy ImportResult (different response structure)
- **12-02-D3:** Import Center as /admin/imports (separate from /import-export legacy page)
- **12-03-D1:** 30-second stale time for import status queries (imports don't change frequently)
- **12-03-D2:** Status badges use semantic colors (green/red/yellow/gray for completed/failed/in-progress/never)
- **12-03-D3:** Dependency warnings shown inline on tiles (yellow background with AlertTriangle icon)
- **12-03-D4:** Import order displayed as numbered badges (1-4) for visual guidance
- **12-04-D1:** useReducer state machine for workflow (enforces valid state transitions)
- **12-04-D2:** Preview first 25 rows client-side (balance between preview and performance)
- **12-04-D3:** Import button disabled when validation has errors (prevents failed imports)
- **12-04-D4:** Validation dry-run with validate_only=true (API call before real import)
- **12-04-D5:** Cancel with confirmation during import (prevents accidental data loss)
- **12-05-D1:** CSV error_message column joins multiple errors with semicolon separator (Excel-safe, human-readable)
- **12-05-D2:** Filename format {type}_errors_{run_id}.csv for easy identification
- **12-05-D3:** 404 when no errors exist (better UX than empty CSV)
- **12-05-D4:** Download button only shows when error_count > 0 AND import_run_id exists

### Pending Todos

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 004 | Fix ImportDialog empty file bug + generate test CSV data | 2026-02-10 | pending | [004-fix-import-dialog-empty-file-bug](./quick/004-fix-import-dialog-empty-file-bug/) |

### Blockers/Concerns

**Phase 7 Readiness:**
- ~~Need to verify existing Import app structure before adding new models~~ (Verified: imports app exists, models.py created)
- ~~Need to confirm external_id field naming convention~~ (Using snake_case: external_id)
- ~~Entity model fields for import~~ (Completed: Contact, Donation, Pledge models updated)
- Research recommended validation-first pattern (validate ALL rows before atomic import)

**Phase 10 Readiness:**
- ~~Contact.update_giving_stats() performance with bulk imports needs verification~~ (Verified: acceptable for MVP, 126 tests passing)
- ~~Denormalized field update strategy must handle 1000+ row imports efficiently~~ (Implemented: batch fetch affected contacts, call update_giving_stats())
- ~~import_entities uses update_or_create (one query per record) - may need bulk optimization for 100+ rows~~ (Same pattern for transactions, acceptable for MVP)

**Phase 12 Readiness:**
- ~~Backend API for latest import runs and dependency counts~~ (Completed: 12-01)
- ~~react-papaparse dependency needs to be added to frontend package.json~~ (Completed: 12-02)
- ~~Import Center route (/admin/imports) needs to fit existing admin navigation structure~~ (Completed: 12-02)

## Session Continuity

Last session: 2026-02-04
Stopped at: Completed 12-05-PLAN.md (Error CSV download functionality) - Phase 12 complete
Resume file: None

---

*Last updated: 2026-02-04 (Phase 12 complete - all 5 plans executed)*
