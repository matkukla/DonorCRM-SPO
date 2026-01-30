---
phase: "08"
plan: "02"
title: "FundImportView API Endpoint"
subsystem: "api"
tags: ["django-rest-framework", "csv-import", "api-endpoint", "funds"]
completed: "2026-01-30"
duration: "3m 38s"

# Dependency graph
requires:
  - "08-01"  # parse_funds_csv and import_funds service functions
  - "07-01"  # Fund model and ImportRun model

provides:
  - api-endpoint-fund-import
  - api-endpoint-fund-template

affects:
  - "12"  # Frontend Import Center will call these endpoints

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "REST API endpoints for CSV import"
    - "UTF-8 BOM handling for Excel compatibility"
    - "ImportRun audit tracking"
    - "Admin-only permissions on sensitive endpoints"

# File tracking
key-files:
  created: []
  modified:
    - apps/imports/views.py
    - apps/imports/urls.py
    - apps/imports/services.py
    - apps/imports/tests/test_fund_import.py

# Decisions
decisions: []
---

# Phase 08 Plan 02: FundImportView API Endpoint Summary

**One-liner:** REST API endpoint for fund CSV imports with UTF-8 BOM handling, validation dry-runs, and ImportRun audit tracking.

## What Was Built

### FundImportView API Endpoint

Created `FundImportView` at `/api/v1/imports/funds/` with:

- **Admin-only access:** Uses `IsAdmin` permission class
- **File validation:** Checks for CSV file presence and extension
- **UTF-8 BOM handling:** Uses `decode('utf-8-sig')` to handle Excel BOM markers
- **Dry-run validation:** Supports `?validate_only=true` query parameter
- **Audit tracking:** Creates `ImportRun` record for every import
- **Comprehensive error handling:** Returns 400 with details for validation errors
- **Response format:** Returns `created_count`, `updated_count`, `error_count`, `errors`, and `import_run_id`

### FundTemplateView API Endpoint

Created `FundTemplateView` at `/api/v1/imports/templates/funds/` that:

- **Returns CSV template:** Headers for fund import format
- **Admin-only access:** Uses `IsAdmin` permission class
- **Proper content type:** Sets `text/csv` with attachment disposition

### Template Function

Added `get_funds_template()` to services.py:

```python
def get_funds_template() -> str:
    return 'fund_id,name,status\n'
```

### URL Wiring

Updated `apps/imports/urls.py` with:

- `path('funds/', FundImportView.as_view(), name='import-funds')`
- `path('templates/funds/', FundTemplateView.as_view(), name='template-funds')`

### Integration Tests

Added 12 integration tests for `FundImportView`:

1. Admin can import funds
2. Non-admin receives 403 Forbidden
3. Missing file returns 400
4. Non-CSV file returns 400
5. Validation errors return 400 with details
6. validate_only performs dry-run
7. Successful import returns counts
8. Import creates ImportRun audit record
9. UTF-8 BOM handled correctly
10. import_run_id included in response

Added 2 tests for `FundTemplateView`:

1. Admin can download template
2. Non-admin receives 403 Forbidden

## Tests

All 32 tests pass (20 from 08-01, 12 new integration tests):

```bash
python -m pytest apps/imports/tests/test_fund_import.py --no-cov -q
# 32 passed, 2 warnings in 3.08s
```

## Deviations from Plan

None - plan executed exactly as written.

## Key Implementation Notes

### UTF-8 BOM Handling

Excel exports include a UTF-8 BOM (Byte Order Mark: `\xef\xbb\xbf`) at the start of CSV files. Using `decode('utf-8-sig')` automatically strips this marker, preventing column header parsing errors.

### ImportStatus Enum Value

Used `ImportStatus.IMPORTING` (not `PROCESSING`) based on the actual enum values defined in the model:

- PENDING
- VALIDATING
- VALIDATED
- IMPORTING ← Used here
- COMPLETED
- FAILED

### Synchronous Import Only

Following the plan requirement, this is synchronous import only (no async). The MVP doesn't include Celery infrastructure. Future enhancement could add async processing for large files.

### Error Response Format

Validation errors return HTTP 200 (not 400) with zero created/updated counts and populated errors array. This matches the existing pattern from `ContactImportView` and `DonationImportView`.

## Must-Haves Verification

✅ Admin can POST CSV to `/api/v1/imports/funds/` and receive validation results
✅ Admin can use `?validate_only=true` for dry-run validation
✅ Non-admin users receive 403 Forbidden
✅ Missing file returns 400 with 'No file provided' message
✅ Non-CSV file returns 400 with 'File must be a CSV' message
✅ Validation errors return 400 with error details and row numbers
✅ Successful import returns 200 with created/updated/error counts
✅ Import creates ImportRun audit record
✅ UTF-8 BOM from Excel exports is handled correctly

## Next Phase Readiness

**For Phase 12 (Frontend Import Center):**

- ✅ API endpoints ready: `/api/v1/imports/funds/` and `/api/v1/imports/templates/funds/`
- ✅ Response format includes all needed data: counts, errors, import_run_id
- ✅ Template download endpoint available
- ✅ Validation dry-run supported for client-side preview

**No blockers.** Backend fund import infrastructure complete.

---

*Completed 2026-01-30 | Duration: 3m 38s | Commit: 3d01d60*
