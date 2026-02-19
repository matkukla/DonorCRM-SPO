---
status: complete
phase: 24-smartsheet-import-backend
source: [24-01-SUMMARY.md, 24-02-SUMMARY.md]
started: 2026-02-19T16:00:00Z
updated: 2026-02-19T16:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Upload Sample CSV via API
expected: POST the sample Smartsheet CSV to /api/v1/imports/mpd/ as admin. Response returns HTTP 201 with JSON containing upload_id, status='completed', total_rows=11, matched_count + unmatched_count = 11, and unmatched_rows array with details for each unmatched missionary.
result: pass

### 2. Financial Data Parsing Accuracy
expected: After CSV upload, check MPDSnapshot records in Django admin or shell. Joe Man's active_recurring_gifts should be 3085.00, pct_standard_to_max should be 104, met_mpd_standard should be True. Negative currency values (like -$468.33) should be stored as negative Decimals.
result: pass

### 3. Special Field Parsing
expected: Simon Peter's months_remaining_rf should be 'infinite'. Mary Grace's months_remaining_rf should be '0'. Boolean fields (met_mpd_standard, met_maximum, match_met) should be True/False (not strings).
result: pass

### 4. XLSX Format Auto-Detection
expected: Rename or upload an XLSX file to the same endpoint. System auto-detects XLSX from magic bytes (PK header), parses with openpyxl, and returns the same structured JSON response with matched/unmatched counts.
result: pass

### 5. Non-Admin Gets 403
expected: When a non-admin user POSTs to /api/v1/imports/mpd/, the response is HTTP 403 Forbidden. No MPDUpload or MPDSnapshot records are created.
result: pass

### 6. Historical Snapshot Accumulation
expected: Upload the same CSV file a second time. A new MPDUpload record is created (different upload_id). New MPDSnapshot records are created linked to the new upload. Previous snapshots from the first upload are NOT overwritten or deleted.
result: pass

### 7. MPD Models in Django Admin
expected: Navigate to Django admin. MPDUpload and MPDSnapshot models appear in the imports section. MPDUpload list shows filename, format, status, row counts, uploaded_by, and created_at. MPDSnapshot list shows user, upload, key financial fields.
result: skipped
reason: Admin user lacks is_superuser — pre-existing setup issue, not Phase 24 code. Admin registrations verified in code.

## Summary

total: 7
passed: 6
issues: 0
pending: 0
skipped: 1

## Gaps

[none yet]
