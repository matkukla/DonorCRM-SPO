# Requirements: DonorCRM CSV Import

## Overview

This document catalogs all requirements for the CSV Import feature (SPO-compatible import pipeline). Requirements are versioned as v1.1 (current milestone) and v1.x (future work).

## v1.1 Requirements

### Data Model

**IMP-01: Fund Model**
- System has Fund model with external_id, name, status fields
- Fund.external_id is unique and indexed for upsert operations
- Funds link to Donations and Pledges via foreign key

**IMP-02: External ID Fields**
- Contact model has external_id field (nullable, unique when set)
- Donation model has external_id field (nullable, unique when set)
- Pledge model has external_id field (nullable, unique when set)
- External IDs enable idempotent upserts during import

**IMP-03: ImportRun Audit Model**
- System tracks each import run with type (funds/entities/transactions/pledges)
- ImportRun stores status (pending/validated/imported/failed)
- ImportRun tracks counts: total_rows, created, updated, skipped, errors
- ImportRun records uploaded_by user and timestamps

**IMP-04: ImportRowError Model**
- System tracks row-level errors for each import run
- ImportRowError stores row_number, external_id (if available), error_code, message
- ImportRowError stores raw_row_json for debugging
- Errors are queryable by import_run for reporting

### Import Pipeline

**IMP-05: Funds CSV Import**
- Admin can upload Funds CSV file
- System parses fund_id, name, status columns
- System upserts Fund records using fund_id as external_id
- Existing funds with matching fund_id are updated, new funds are created

**IMP-06: Entities CSV Import**
- Admin can upload Entities CSV file
- System parses entity_id, name, email, phone, address, entity_type columns
- System upserts Contact records using entity_id as external_id
- System assigns imported contacts to the uploading user as owner
- Existing contacts with matching entity_id are updated, new contacts are created

**IMP-07: Transactions CSV Import**
- Admin can upload Transactions CSV file
- System parses transaction_id, entity_id, fund_id, amount, posted_date columns
- System validates entity_id references exist in Contact.external_id
- System validates fund_id references exist in Fund.external_id
- System upserts Donation records using transaction_id as external_id
- System updates Contact denormalized giving stats after import

**IMP-08: Pledges CSV Import**
- Admin can upload Pledges CSV file
- System parses pledge_id, entity_id, fund_id, amount, cadence, status, start_date columns
- System validates entity_id references exist in Contact.external_id
- System validates fund_id references exist (if fund_id provided)
- System upserts Pledge records using pledge_id as external_id

### Validation & Preview

**IMP-09: Column Validation**
- System validates required columns are present in uploaded CSV
- System rejects files missing required columns with clear error message
- Each import type has defined required and optional columns

**IMP-10: Row Preview**
- Admin can preview first 25 rows of uploaded CSV before importing
- Preview shows column headers and sample data
- Preview parses on client-side (no server round-trip)

**IMP-11: Foreign Key Validation**
- System validates all entity_id references exist before Transaction/Pledge import
- System validates all fund_id references exist before Transaction/Pledge import
- System reports orphan references with row numbers and missing IDs
- System blocks import if any foreign key references are invalid (strict mode)

**IMP-12: Data Type Validation**
- System validates amounts parse as decimal numbers
- System validates dates parse in expected format
- System validates enum values (status, cadence) are valid choices
- System reports parse errors with row numbers and field names

### Error Handling & Reporting

**IMP-13: Row-Level Error Tracking**
- System tracks each validation/import error at row level
- Errors include row number, field name, error type, and message
- Errors are stored in ImportRowError for audit trail

**IMP-14: Import Summary**
- System displays import results summary after completion
- Summary shows: total rows, created count, updated count, skipped count, error count
- Summary is stored in ImportRun for historical reference

**IMP-15: Download Errors CSV**
- Admin can download CSV of failed rows with error messages
- Error CSV includes original row data plus error_message column
- Allows admin to fix data and re-import

### Import Center UI

**IMP-16: Admin-Only Access**
- Import Center is only accessible to admin users
- Route: /admin/imports or /settings/imports
- Non-admin users cannot see or access import functionality

**IMP-17: Import Center Layout**
- Import Center shows 4 tiles: Funds, Entities, Transactions, Pledges
- Each tile shows import status and last import date
- Tiles indicate dependency order (Funds/Entities before Transactions/Pledges)

**IMP-18: Upload Workflow**
- Each tile supports: Upload → Preview → Validate → Import → Summary workflow
- User can cancel at any step before import
- Import button is disabled until validation passes

**IMP-19: Dependency Guidance**
- UI shows recommended import order: Funds → Entities → Transactions → Pledges
- UI warns if attempting Transaction/Pledge import with empty Funds or Entities
- Warnings are non-blocking (admin can proceed at their discretion)

## v1.x Requirements (Future)

The following are explicitly out of scope for v1.1 but considered for future releases:

**IMP-V2-01: Async Import Processing**
- Use Celery for background processing of large files (>5000 rows)
- Real-time progress updates via WebSocket

**IMP-V2-02: Column Mapping UI**
- Allow admin to map CSV columns to model fields
- Save custom mappings for reuse

**IMP-V2-03: Rollback/Undo**
- Allow admin to undo an entire import run
- Restore database to pre-import state

**IMP-V2-04: Scheduled Imports**
- Support automated imports from S3 or SFTP
- Schedule regular syncs from SPO exports

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time streaming import | Complexity, synchronous sufficient for SPO volumes |
| In-app Excel editing | Complexity, fix data in source system |
| Auto-fix validation errors | Risk of data corruption, manual review preferred |
| Multi-format support (xlsx, json) | CSV is SPO standard export format |
| Non-strict mode (allow orphan refs) | Data integrity priority, strict mode enforces FK constraints |

## Traceability

Requirement-to-Phase mapping (updated during roadmap creation):

| Requirement | Phase | Status |
|-------------|-------|--------|
| IMP-01 | Phase 7 | Complete |
| IMP-02 | Phase 7 | Complete |
| IMP-03 | Phase 7 | Complete |
| IMP-04 | Phase 7 | Complete |
| IMP-05 | Phase 8 | Pending |
| IMP-06 | Phase 9 | Pending |
| IMP-07 | Phase 10 | Pending |
| IMP-08 | Phase 11 | Pending |
| IMP-09 | Phase 8 | Pending |
| IMP-10 | Phase 12 | Pending |
| IMP-11 | Phase 8 | Pending |
| IMP-12 | Phase 8 | Pending |
| IMP-13 | Phase 7 | Complete |
| IMP-14 | Phase 8 | Pending |
| IMP-15 | Phase 12 | Pending |
| IMP-16 | Phase 12 | Pending |
| IMP-17 | Phase 12 | Pending |
| IMP-18 | Phase 12 | Pending |
| IMP-19 | Phase 12 | Pending |

**Coverage:** 19/19 requirements mapped (100%)

---

*Requirements defined: 2026-01-30*
*Last updated: 2026-01-30*
