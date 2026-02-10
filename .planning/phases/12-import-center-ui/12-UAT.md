---
status: testing
phase: 12-import-center-ui
source: 12-01-SUMMARY.md, 12-02-SUMMARY.md, 12-03-SUMMARY.md, 12-04-SUMMARY.md, 12-05-SUMMARY.md
started: 2026-02-05T12:00:00Z
updated: 2026-02-05T12:00:00Z
---

## Current Test

number: 9
name: Validation Step
expected: |
  After preview, click "Validate". It should call the API with validate_only=true and show validation results — either a success message or an error count.
awaiting: user response

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
result: [pending]

### 10. Import Button Disabled on Errors
expected: If validation shows errors (error_count > 0), the Import button is disabled and cannot be clicked
result: [pending]

### 11. Import Button Enabled on Success
expected: If validation passes (error_count = 0), the Import button is enabled and can be clicked
result: [pending]

### 12. Import Summary - Counts
expected: After successful import, summary step shows created count, updated count, and error count
result: [pending]

### 13. Download Errors CSV Button
expected: If import has errors (error_count > 0), a "Download Errors CSV" button appears in the summary step
result: [pending]

### 14. Download Errors CSV - File Contents
expected: Clicking "Download Errors CSV" downloads a CSV file containing original row data plus an error_message column
result: [pending]

### 15. Status Badge Updates After Import
expected: After completing a successful import, the tile's status badge updates to show "Completed" (green) with timestamp
result: [pending]

### 16. Cancel During Import - Confirmation
expected: If you try to close the dialog during import (while loading spinner shows), a confirmation prompt appears
result: [pending]

## Summary

total: 16
passed: 0
issues: 0
pending: 16
skipped: 0

## Gaps

[none yet]
