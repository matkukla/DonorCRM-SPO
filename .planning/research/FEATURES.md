# Feature Research: CSV Import Pipeline for CRM

**Domain:** CSV Import Center for Donor CRM
**Researched:** 2026-01-30
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| File upload with drag-and-drop | Standard web UX pattern for file operations | LOW | Existing pattern in frontend stack, use HTML5 drag-drop API |
| Column header validation | Users need to know if CSV structure matches expected schema | LOW | Compare uploaded headers against required fields per import type |
| Preview data before commit | Users expect to see sample data before execution | LOW | Show first 5-10 rows with mapped columns, standard table view |
| Validation with error messages | Critical for preventing bad data import | MEDIUM | Row-level validation with specific error messages (row number, column, issue) |
| Progress indicator during import | Users need feedback during potentially long operations | LOW | Basic progress bar or spinner, track percentage complete |
| Success/failure summary | Users need to know outcome: records created/updated/failed | LOW | Display counts after import: X created, Y updated, Z errors |
| Download error report | Users need exportable list of failures to fix source data | LOW | Generate CSV with error rows + error message column |
| Template download | Users expect example/empty CSV to understand format | LOW | Generate CSV with correct headers + sample row |
| Rollback/undo capability | Users expect to reverse imports if mistakes detected | HIGH | Requires tracking import batches, soft deletes, or transaction isolation |
| Duplicate detection | Users expect system to identify/prevent duplicate records | MEDIUM | Match on external_id (SPO compatibility) or fallback to email/name |
| Required field enforcement | Basic data quality gate | LOW | Check for null/empty values in required columns before import |
| Date format validation | Common source of import errors | LOW | Support multiple date formats (YYYY-MM-DD, MM/DD/YYYY, etc.) with clear error messages |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-file dependent import orchestration | SPO exports 4 CSVs with dependencies (Funds → Entities → Transactions/Pledges) | HIGH | Auto-detect dependencies, guide user through correct order, or allow zip upload with auto-ordering |
| Idempotent upsert with external IDs | Allows re-running imports without duplicates, critical for SPO migration | MEDIUM | Use external_id fields (fund_id, entity_id, transaction_id, pledge_id) for insert-or-update logic |
| Inline error correction | Fix validation errors directly in preview UI without re-uploading | MEDIUM | Editable table cells in preview mode, re-validate on change |
| Column auto-mapping with fuzzy matching | Saves time when CSV headers don't exactly match schema | MEDIUM | Map "Entity Name" → "name", "Email Address" → "email" using fuzzy string matching |
| Batch processing with progress tracking | Better UX for large files (1000+ rows) | MEDIUM | Process in chunks (500 rows), update progress incrementally, prevents timeout |
| Validation rules preview | Show users what will be checked before upload | LOW | Display required fields, format rules, dependency requirements per import type |
| Import history/audit trail | Track who imported what, when, for compliance and debugging | MEDIUM | ImportRun model already planned, extend with downloadable history, revert capability |
| Orphan reference detection | Identify transactions referencing non-existent entities/funds before import | MEDIUM | Pre-validate foreign keys against existing data + other files in batch |
| Smart date parsing | Handle multiple date formats automatically | LOW | Use library like `dateutil` or `day.js` to parse common formats |
| Import dry-run mode | Full validation + simulation without database commit | LOW | validateOnly flag already exists in current import API, extend to new types |
| Visual diff for upserts | Show users what will change for existing records | MEDIUM | Display "Current → New" for each field that would be updated |
| Conditional field mapping | Map columns differently based on CSV content (e.g., "Status: Active" → status=1) | HIGH | Add transformation rules layer between CSV parsing and validation |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time import streaming | Feels modern, shows instant feedback | Complex to implement, adds little value for batch operations, risk of partial failures mid-stream | Batch processing with progress updates every 100 rows is sufficient |
| Manual Excel editing in-app | Users want spreadsheet interface | Massive complexity, reinvents Excel, poor UX on web, hard to maintain | Download → Edit in Excel → Re-upload workflow with good error reporting |
| Auto-fix validation errors | Seems helpful to fix issues automatically | Silently corrupts data, users lose trust, hard to predict edge cases | Show errors clearly, let users fix source data or edit inline |
| Flexible schema (allow any columns) | Seems user-friendly | Breaks type safety, makes validation impossible, leads to garbage data | Fixed schema per import type with clear documentation |
| Immediate commit without preview | Faster workflow | Users make mistakes, can't review before import, no recovery | Always require preview/confirmation step |
| Import from URLs or APIs | Seems powerful | Scope creep, security risks, adds complexity for minimal value | CSV file upload only, users can download from external sources themselves |
| Complex ETL transformations | Users want data reshaping | Over-engineering for MVP, hard to debug, better done in external tools | Simple column mapping only, users prepare data in Excel/scripts |
| Concurrent multi-user imports | Allows team imports simultaneously | Race conditions with upserts, complex locking, not needed for single-missionary use case | Queue imports if needed, or owner-scope isolation is sufficient |
| Support for JSON/XML/Excel formats | Seems flexible | Parser complexity, schema variations, CSV is universal standard | CSV only (can add Excel later if validated need) |

## Feature Dependencies

```
[File Upload]
    └──requires──> [Column Header Validation]
                       └──requires──> [Column Mapping]
                                         └──requires──> [Data Preview]
                                                           └──requires──> [Validation]
                                                                             └──requires──> [Import Execution]

[Multi-file Import]
    └──requires──> [Dependency Detection]
                       └──requires──> [Ordered Execution (Funds → Entities → Transactions/Pledges)]

[Idempotent Upsert]
    └──requires──> [External ID Support] (fund_id, entity_id, transaction_id, pledge_id)

[Orphan Reference Detection]
    └──requires──> [Multi-file Batch Context] (check entity_id exists in Entities.csv or DB)

[Import Audit Trail]
    └──requires──> [ImportRun Model]
                       └──enhances──> [Rollback/Undo]
                                         └──requires──> [Batch Tracking]

[Visual Diff for Upserts]
    └──requires──> [Dry-run Mode]
                       └──requires──> [Existing Record Lookup by External ID]

[Inline Error Correction] ──conflicts──> [Strict CSV-Only Workflow]
```

### Dependency Notes

- **File Upload → Column Validation → Preview → Execution:** Classic wizard pattern, each step validates before proceeding
- **Multi-file Import → Dependency Detection:** Must parse all files first to build dependency graph (Transactions reference Entities and Funds)
- **Idempotent Upsert → External ID Support:** SPO compatibility requires external_id fields on Contact, Donation, Pledge, Fund models
- **Orphan Reference Detection → Multi-file Batch Context:** When importing Transactions.csv, need to check if entity_id exists in either uploaded Entities.csv OR existing Contact table
- **Visual Diff → Dry-run Mode:** Can't show what will change without simulating the operation first
- **Inline Error Correction conflicts with Strict CSV Workflow:** If users can edit in preview, CSV is no longer source of truth; document which approach we take

## MVP Definition

### Launch With (v1.1)

Minimum viable product for SPO-compatible CSV import.

- [x] **File upload with drag-and-drop** — Table stakes, standard UX pattern
- [x] **Column header validation** — Essential to catch schema mismatches early
- [x] **Data preview (first 10 rows)** — Users must see data before committing
- [x] **Row-level validation with specific errors** — Critical for data quality
- [x] **Required field enforcement** — Basic data integrity gate
- [x] **Import execution with success/failure summary** — Users need outcome feedback
- [x] **Download error report CSV** — Users need to fix errors in source data
- [x] **Template download for each import type** — Reduces user confusion about format
- [x] **Idempotent upsert with external IDs** — Core SPO compatibility requirement
- [x] **Duplicate detection via external_id** — Prevents duplicate records on re-import
- [x] **Multi-file import UI (4 types: Funds, Entities, Transactions, Pledges)** — SPO migration workflow
- [x] **Dependency guidance** — Warn users to import Funds before Transactions, Entities before Transactions/Pledges
- [x] **Orphan reference detection** — Validate entity_id/fund_id exist before importing Transactions/Pledges
- [x] **Import audit trail (ImportRun model)** — Track who imported what, when
- [x] **Admin-only access** — Security/data quality control

### Add After Validation (v1.x)

Features to add once core is working and validated with real SPO data.

- [ ] **Column auto-mapping with fuzzy matching** — Wait to see if headers vary in practice (trigger: users report mapping confusion)
- [ ] **Batch processing with granular progress** — Only if large files cause timeouts (trigger: imports >1000 rows fail)
- [ ] **Inline error correction** — If error rate is high and re-upload is painful (trigger: >20% error rate on first import)
- [ ] **Visual diff for upserts** — If users are concerned about overwriting data (trigger: user feedback requests this)
- [ ] **Rollback/undo capability** — Complex, wait to see if needed (trigger: user reports accidental data corruption)
- [ ] **Import history dashboard** — Nice to have, not critical for launch (trigger: multiple imports per week)
- [ ] **Validation rules documentation/preview** — Add if users struggle with format (trigger: repeated validation errors)
- [ ] **Zip file multi-import** — Convenience feature, wait for demand (trigger: users request streamlined workflow)

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Smart date parsing (multiple formats)** — SPO likely uses consistent format; validate first
- [ ] **Conditional field mapping/transformations** — Over-engineering for MVP; users can prep data in Excel
- [ ] **Concurrent multi-user imports** — Single-missionary use case, not needed yet
- [ ] **Excel file support** — CSV is sufficient, Excel adds parser complexity
- [ ] **Advanced ETL transformations** — Out of scope, users handle in Excel/scripts
- [ ] **API-based import** — No validated use case yet
- [ ] **Scheduled/automated imports** — Wait for recurring import pattern to emerge

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| File upload with drag-and-drop | HIGH | LOW | P1 |
| Column validation + preview | HIGH | LOW | P1 |
| Row-level validation with errors | HIGH | MEDIUM | P1 |
| Success/failure summary | HIGH | LOW | P1 |
| Download error report | HIGH | LOW | P1 |
| Template download | HIGH | LOW | P1 |
| Idempotent upsert with external_id | HIGH | MEDIUM | P1 |
| Multi-file import UI (4 types) | HIGH | LOW | P1 |
| Dependency guidance (order warning) | HIGH | LOW | P1 |
| Orphan reference detection | HIGH | MEDIUM | P1 |
| Import audit trail | MEDIUM | LOW | P1 |
| Admin-only access | HIGH | LOW | P1 |
| Column auto-mapping | MEDIUM | MEDIUM | P2 |
| Batch processing with progress | MEDIUM | MEDIUM | P2 |
| Inline error correction | MEDIUM | MEDIUM | P2 |
| Visual diff for upserts | MEDIUM | MEDIUM | P2 |
| Rollback/undo | MEDIUM | HIGH | P2 |
| Import history dashboard | LOW | MEDIUM | P2 |
| Smart date parsing | LOW | LOW | P3 |
| Zip file multi-import | LOW | MEDIUM | P3 |
| Excel format support | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch (v1.1)
- P2: Should have, add when validated need emerges (v1.x)
- P3: Nice to have, future consideration (v2+)

## Competitor Feature Analysis

| Feature | Salesforce Data Import Wizard | HubSpot Import | Our Approach (DonorCRM) |
|---------|-------------------------------|----------------|--------------------------|
| File upload | Drag-and-drop, CSV/Excel | Drag-and-drop, CSV/Excel/XLSX | Drag-and-drop, CSV only (Excel future) |
| Column mapping | Manual + auto-match | Auto-fuzzy match (95% accuracy) | Manual with planned auto-fuzzy (v1.x) |
| Preview | Sample data preview | First 100 rows | First 10 rows (sufficient for validation) |
| Validation | Field-level + custom rules | Real-time with inline editing | Row-level with download error CSV (no inline edit in MVP) |
| Duplicate handling | Match on email/ID, skip/update options | Multiple match strategies | External_id upsert (SPO-specific) |
| Progress tracking | Batch progress bar | Percentage + row count | Basic progress indicator (granular in v1.x if needed) |
| Error reporting | Download CSV with errors | Inline corrections + download | Download error CSV (inline editing v1.x) |
| Multi-file import | Sequential, manual ordering | One file at a time | 4-file UI with dependency guidance |
| Rollback | Via import history (complex) | No rollback (re-import old data) | Planned for v1.x (complex) |
| Audit trail | Full import history with details | Basic history | ImportRun model with user/timestamp/counts |

**Our competitive advantages:**
1. **SPO-specific workflow** — Built for 4-file dependent imports (Funds, Entities, Transactions, Pledges)
2. **External ID upsert** — Idempotent imports out of the box, no duplicate logic needed
3. **Orphan reference detection** — Catch missing entity_id/fund_id before import, not after
4. **Simpler UX** — Fewer options, clearer workflow (upload → preview → validate → import)

**Where we intentionally lag:**
1. **No inline editing** — Users fix errors in Excel, not in-app (simpler, less code)
2. **No auto-fuzzy mapping** — Defer until validated need (v1.x)
3. **CSV only** — No Excel/JSON support (reduces parser complexity)
4. **No rollback in MVP** — Complex feature, wait for validated need

## Existing Codebase Integration

### Current Import Features (Already Built)

- Contact CSV import with `validateOnly` flag (`/imports/contacts/`)
- Donation CSV import with `validateOnly` flag (`/imports/donations/`)
- Template download endpoints (`/imports/templates/contacts/`, `/imports/templates/donations/`)
- Export functionality (contacts, donations with date filters)
- Basic `ImportResult` type with counts and error array

### Integration Points for v1.1

| New Feature | Existing Pattern to Extend |
|-------------|---------------------------|
| Fund CSV import | Follow `/imports/contacts/` pattern, add `/imports/funds/` endpoint |
| Entity → Contact import | Extend `/imports/contacts/` to accept entity_id column for external_id mapping |
| Transaction → Donation import | Extend `/imports/donations/` to accept transaction_id, entity_id, fund_id |
| Pledge import | New `/imports/pledges/` endpoint following existing pattern |
| Import Center UI | New route `/import-center` with 4 tiles (Funds, Entities, Transactions, Pledges) |
| Validation preview | Use existing `validateOnly=true` query param pattern |
| Error download | Follow existing export pattern, generate CSV from `ImportRowError` records |
| Templates | Extend `/imports/templates/` with funds, entities, transactions, pledges |

### Data Model Extensions Needed

- Add `external_id` field to Contact, Donation, Pledge models (nullable, indexed, unique)
- Create Fund model with `fund_id` (external_id), name, status
- Create ImportRun model (type, status, counts, uploaded_by, created_at)
- Create ImportRowError model (import_run, row_number, column, error_message)

## Sources

**CRM CSV Import Best Practices:**
- [CRM data management guide: 10 best practices for 2026](https://monday.com/blog/crm-and-sales/crm-data-management/)
- [Data Import Best Practices - Salesforce Trailhead](https://trailhead.salesforce.com/content/learn/modules/lex_implementation_data_management/lex_implementation_data_import)
- [CSV to Salesforce: A Comprehensive Guide for Data Teams](https://www.integrate.io/blog/csv-to-salesforce-a-comprehensive-guide-for-data-teams/)
- [Import New Records or Update From CSV – Insycle](https://support.insycle.com/hc/en-us/articles/6586521873175-Import-New-Records-or-Update-From-CSV)
- [Set up import files - HubSpot](https://knowledge.hubspot.com/import-and-export/set-up-your-import-file)

**CSV Import Validation & Preview UX:**
- [How To Design Bulk Import UX - Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/bulk-ux/)
- [Designing An Attractive And Usable Data Importer - Smashing Magazine](https://www.smashingmagazine.com/2020/12/designing-attractive-usable-data-importer-app/)
- [Best UI patterns for file uploads - CSVBox Blog](https://blog.csvbox.io/file-upload-patterns/)
- [5 Best Practices for Building a CSV Uploader](https://www.oneschema.co/blog/building-a-csv-uploader)
- [Build A Seamless Spreadsheet Import Experience With Flatfile - Smashing Magazine](https://www.smashingmagazine.com/2019/11/flatfile-seamless-spreadsheet-import-experience/)

**Multi-file Dependent Entity Imports:**
- [Multi-Entity data file import mapping - Microsoft Learn](https://learn.microsoft.com/en-us/archive/blogs/emeadcrmsupport/multi-entity-data-file-import-mapping)
- [Import data and control duplicate records - Dynamics 365](https://learn.microsoft.com/en-us/dynamics365/customer-insights/journeys/import-data)
- [Importing two or more entities from a Single File - Dynamics 365 Blog](https://cloudblogs.microsoft.com/dynamics365/no-audience/2010/11/04/importing-two-or-more-entities-from-a-single-file/)

**Error Handling & Rollback:**
- [6 Common CSV Import Errors and How to Fix Them - Flatfile](https://flatfile.com/blog/top-6-csv-import-errors-and-how-to-fix-them/)
- [5 Common Data Import Errors and How to Fix Them - Dromo](https://dromo.io/blog/common-data-import-errors-and-how-to-fix-them)
- [CSV Import Errors: Quick Fixes for Data Pros](https://www.integrate.io/blog/csv-import-errors-quick-fixes-for-data-pros/)

**Idempotent Upsert & Duplicate Handling:**
- [How ETL Tools Load CSV Data into Custom Salesforce Objects](https://www.integrate.io/blog/how-etl-tools-reliably-load-csv-data-into-custom-salesforce-objects/)
- [How to make data pipelines idempotent](https://www.startdataengineering.com/post/why-how-idempotent-data-pipeline/)
- [Salesforce Data Loaders: Tools, Tips & Best Practices 2026](https://blog.skyvia.com/salesforce-data-loaders/)

**Batch Processing & Progress:**
- [Batch and Import Guide for Blackbaud CRM](https://help.blackbaud.com/docs/0/assets/guides/crm/batch.pdf)
- [Real-time vs. batch-based CRM data processing](https://martech.org/real-time-vs-batch-based-crm-data-processing-key-considerations/)

---
*Feature research for: CSV Import Pipeline for DonorCRM*
*Researched: 2026-01-30*
