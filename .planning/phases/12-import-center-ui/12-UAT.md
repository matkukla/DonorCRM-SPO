---
status: complete
phase: 12-import-center-ui
source: 12-01-SUMMARY.md, 12-02-SUMMARY.md, 12-03-SUMMARY.md, 12-04-SUMMARY.md, 12-05-SUMMARY.md
started: 2026-02-05T12:00:00Z
updated: 2026-02-10T12:00:00Z
---

## Tests

### 1. Admin Access to Import Center
expected: Import Center page at /admin/imports is accessible to admin users, shows header and import order guidance
result: pass

### 2. Import Tiles Display
expected: 4 tiles displayed for Funds, Entities, Transactions, and Pledges with numbered badges (1-4) showing import order
result: pass

### 3. Status Badge - Never Imported
expected: For an import type that has never been imported, tile shows gray "Never imported" status badge with clock icon
result: pass

### 4. Dependency Warning - Transactions
expected: Transactions tile shows yellow warning when no Funds or Entities exist (warning about missing dependencies)
result: pass

### 5. Dependency Warning - Pledges
expected: Pledges tile shows yellow warning when no Entities exist (warning about missing dependencies)
result: pass

### 6. Import Button Opens Dialog
expected: Clicking "Import" button on any tile opens a dialog for uploading CSV file
result: pass

### 7. CSV File Upload
expected: In the import dialog, you can upload a CSV file using the file picker or drag-and-drop
result: pass

### 8. CSV Preview - First 25 Rows
expected: After uploading CSV, dialog shows preview table with first 25 rows, column headers, and row numbers
result: pass

### 9. Validation Step
expected: After preview, clicking "Validate" calls API with validate_only=true and shows validation results (pass or error count)
result: pass

### 10. Import Button Disabled on Errors
expected: If validation shows errors (error_count > 0), the Import button is disabled and cannot be clicked
result: pass

### 11. Import Button Enabled on Success
expected: If validation passes (error_count = 0), the Import button is enabled and can be clicked
result: pass

### 12. Import Summary - Counts
expected: After successful import, summary step shows created count, updated count, and error count
result: pass

### 13. Download Errors CSV Button
expected: If import has errors (error_count > 0), a "Download Errors CSV" button appears in the summary step
result: pass

### 14. Download Errors CSV - File Contents
expected: Clicking "Download Errors CSV" downloads a CSV file containing original row data plus an error_message column
result: pass

### 15. Status Badge Updates After Import
expected: After completing a successful import, the tile's status badge updates to show "Completed" (green) with timestamp
result: pass

### 16. Cancel During Import - Confirmation
expected: If you try to close the dialog during import (while loading spinner shows), a confirmation prompt appears
result: pass

## Summary

total: 16
passed: 16
issues: 0
pending: 0
skipped: 0

## Issues Found During UAT

### Issue 1: Empty file sent to backend (FIXED)
- **Symptom:** Validation returned "CSV file is empty or has no headers"
- **Root cause:** ImportDialog used a separate fileInputRef that was never populated by react-papaparse's CSVReader
- **Fix:** Replaced with acceptedFileRef capturing the File object from CSVReader render props
- **Commit:** 05ed533

### Issue 2: No navigation to Import Center (FIXED)
- **Symptom:** No way to access /admin/imports without pasting URL
- **Fix:** Added Users/Imports sub-navigation tabs to Admin section (both AdminUsers and ImportCenter pages)

## Gaps

[none]
