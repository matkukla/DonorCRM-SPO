# Roadmap: DonorCRM

## Milestones

- **v1.0 Journal Feature** - Phases 1-6 (shipped 2026-01-29)
- **v1.1 CSV Import** - Phases 7-12 (in progress)

## Phases

<details>
<summary>v1.0 Journal Feature (Phases 1-6) - SHIPPED 2026-01-29</summary>

See milestones/v1.0-ROADMAP.md for complete phase details.

**Key Features:**
- Journal CRUD with owner-scoped visibility
- Contact membership management (many-to-many)
- 6-stage pipeline: Contact -> Meet -> Close -> Decision -> Thank -> Next Steps
- Decision tracking with history (dual-table pattern)
- Interactive grid UI with stage cell indicators
- Event timeline drawer with infinite scroll
- Analytics charts (decision trends, stage activity, pipeline breakdown)
- Contact detail integration (Journals tab)
- Task system integration (journal-linked tasks)
- Admin analytics endpoints

**Scope:** 19 requirements, 6 phases, 24 plans, 35 UAT tests passed

</details>

### v1.1 CSV Import (In Progress)

**Milestone Goal:** Enable admins to import SPO-exported CSV files (Funds, Entities, Transactions, Pledges) into DonorCRM with validation, preview, and idempotent upserts.

**Target features:**
- Import Center UI for 4 CSV types
- Fund model for account/campaign tracking
- External ID support for idempotent imports
- Row-level validation and error reporting
- Import audit trail (ImportRun, ImportRowError)

#### Phase 7: Foundation
**Goal:** Establish core data models and migration infrastructure for idempotent CSV import with audit trail support.

**Depends on:** Phase 6 (v1.0 Journal Feature complete)

**Requirements:** IMP-01, IMP-02, IMP-03, IMP-04, IMP-13

**Success Criteria** (what must be TRUE):
  1. Fund model exists with external_id unique constraint and indexed for fast lookups
  2. Contact, Donation, and Pledge models have external_id fields for upsert operations
  3. ImportRun model tracks import history with type, status, counts, and uploader
  4. ImportRowError model stores row-level validation failures with row numbers and error messages
  5. Database migrations apply cleanly without breaking existing data

**Plans:** 2 plans

Plans:
- [x] 07-01-PLAN.md - Create Fund, ImportRun, ImportRowError models
- [x] 07-02-PLAN.md - Add external_id fields and fund FKs, apply migrations

---

#### Phase 8: Funds CSV Import
**Goal:** Deliver complete Funds CSV import workflow with validation patterns reusable across subsequent import types.

**Depends on:** Phase 7

**Requirements:** IMP-05, IMP-09, IMP-11, IMP-12, IMP-14

**Success Criteria** (what must be TRUE):
  1. Admin can upload Funds CSV file via API endpoint and receive validation results
  2. System validates required columns (fund_id, name, status) are present and rejects malformed CSVs
  3. System validates data types (fund_id is string, status is valid enum value) and reports parse errors with row numbers
  4. System creates new Funds or updates existing Funds based on fund_id match (idempotent upsert)
  5. Import summary displays total rows, created count, updated count, error count
  6. CSV injection attacks are blocked (formula prefixes sanitized on import)

**Plans:** 2 plans

Plans:
- [x] 08-01-PLAN.md - TDD for parse_funds_csv and import_funds service functions
- [x] 08-02-PLAN.md - FundImportView API endpoint with URL wiring and tests

---

#### Phase 9: Entities CSV Import
**Goal:** Enable Contact upserts from Entities CSV with owner assignment and duplicate detection.

**Depends on:** Phase 8

**Requirements:** IMP-06

**Success Criteria** (what must be TRUE):
  1. Admin can upload Entities CSV file (entity_id, name, email, phone, address, entity_type columns)
  2. System validates entity_id uniqueness within uploaded file and reports in-file duplicates
  3. System detects existing Contacts with matching external_id and separates into create vs update batches
  4. New Contacts are created with external_id from entity_id and assigned to uploading user as owner
  5. Existing Contacts are updated with new data from CSV while preserving owner relationship
  6. Import summary distinguishes between created and updated contact counts

**Plans:** 2 plans

Plans:
- [x] 09-01-PLAN.md - TDD for parse_entities_csv and import_entities service functions
- [x] 09-02-PLAN.md - EntityImportView API endpoint with URL wiring and tests

---

#### Phase 10: Transactions CSV Import
**Goal:** Enable Donation imports with foreign key validation and denormalized stat updates.

**Depends on:** Phase 9 (Entities must exist), Phase 8 (Funds must exist)

**Requirements:** IMP-07

**Success Criteria** (what must be TRUE):
  1. Admin can upload Transactions CSV file (transaction_id, entity_id, fund_id, amount, posted_date columns)
  2. System validates all entity_id values reference existing Contact.external_id before import
  3. System validates all fund_id values reference existing Fund.external_id before import
  4. System rejects entire import if any orphan references exist and provides missing ID report with row numbers
  5. Donations are created or updated using transaction_id as external_id with correct Contact and Fund foreign keys
  6. Contact denormalized stats (total_given, gift_count, last_gift_date) update correctly after bulk import completes

**Plans:** 2 plans

Plans:
- [x] 10-01-PLAN.md - TDD for parse_transactions_csv, import_transactions, update_contact_stats_for_import
- [x] 10-02-PLAN.md - TransactionImportView API endpoint with URL wiring and tests

---

#### Phase 11: Pledges CSV Import
**Goal:** Complete CSV import pipeline with Pledges using validated patterns from Transactions.

**Depends on:** Phase 10

**Requirements:** IMP-08

**Success Criteria** (what must be TRUE):
  1. Admin can upload Pledges CSV file (pledge_id, entity_id, fund_id, amount, cadence, status, start_date columns)
  2. System validates entity_id and fund_id references exist using same validation as Transactions
  3. System validates cadence and status are valid enum values and rejects invalid choices
  4. Pledges are created or updated using pledge_id as external_id with correct Contact and Fund foreign keys
  5. Import summary displays created/updated/error counts matching actual database state

**Plans:** 2 plans

Plans:
- [x] 11-01-PLAN.md - TDD for parse_pledges_csv and import_pledges service functions
- [x] 11-02-PLAN.md - PledgeImportView API endpoint with URL wiring and tests

---

#### Phase 12: Import Center UI
**Goal:** Deliver admin-only Import Center with upload workflow, preview, and error reporting for all 4 CSV types.

**Depends on:** Phase 11

**Requirements:** IMP-10, IMP-15, IMP-16, IMP-17, IMP-18, IMP-19

**Success Criteria** (what must be TRUE):
  1. Import Center page is accessible only to admin users at /admin/imports route
  2. Import Center displays 4 tiles (Funds, Entities, Transactions, Pledges) with last import date and status
  3. Each tile supports Upload -> Preview -> Validate -> Import -> Summary workflow with cancel at any step
  4. Admin can preview first 25 rows of uploaded CSV client-side before submitting to server
  5. Import button is disabled until validation passes and enabled only for valid CSVs
  6. Admin can download errors CSV with original row data plus error_message column for failed imports
  7. UI warns when attempting Transaction/Pledge import with empty Funds or Entities (dependency guidance)
  8. UI shows recommended import order: Funds -> Entities -> Transactions -> Pledges

**Plans:** 5 plans

Plans:
- [x] 12-01-PLAN.md - Backend API for import status (LatestImportRunsView) and dependency counts
- [x] 12-02-PLAN.md - Frontend dependencies (react-papaparse), ImportCenter page shell, routing
- [x] 12-03-PLAN.md - SPOImportTile components with status display and dependency warnings
- [x] 12-04-PLAN.md - Import workflow dialog with state machine (Upload -> Preview -> Validate -> Import -> Summary)
- [x] 12-05-PLAN.md - Error CSV download functionality

---

## Progress

**Execution Order:**
Phases execute in numeric order: 7 -> 8 -> 9 -> 10 -> 11 -> 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6. v1.0 Journal | v1.0 | 24/24 | Complete | 2026-01-29 |
| 7. Foundation | v1.1 | 2/2 | Complete | 2026-01-30 |
| 8. Funds CSV Import | v1.1 | 2/2 | Complete | 2026-01-30 |
| 9. Entities CSV Import | v1.1 | 2/2 | Complete | 2026-02-01 |
| 10. Transactions CSV Import | v1.1 | 2/2 | Complete | 2026-02-02 |
| 11. Pledges CSV Import | v1.1 | 2/2 | Complete | 2026-02-03 |
| 12. Import Center UI | v1.1 | 5/5 | Complete | 2026-02-04 |

---

*Last updated: 2026-02-04 (Phase 12 complete - v1.1 milestone complete)*
