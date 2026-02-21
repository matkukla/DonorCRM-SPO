---
status: complete
phase: 28-re-import-pipeline-constituents-solicitors
source: [28-01-SUMMARY.md, 28-02-SUMMARY.md]
started: 2026-02-21T02:15:00Z
updated: 2026-02-21T02:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Solicitor Import via Management Command
expected: Running `python manage.py import_re_solicitors <csv_file> --owner <user_id>` with a valid RE solicitor CSV processes all rows, creates Solicitor records, and prints a summary showing created/updated/skipped/error counts.
result: pass
notes: Verified with synthetic CSV — 4 created, 0 skipped, 1 error (row with missing name). Auto-linked "Kukla, Matthew" to user. Summary output clean.

### 2. Solicitor Import via API Endpoint
expected: POST to `/api/v1/imports/re/solicitors/` with a CSV file upload creates an ImportBatch, processes solicitors, and returns a JSON response with batch ID and summary stats.
result: pass
notes: Verified via Django test client — returns 200 with batch_id, status, counts, and summary JSON.

### 3. Solicitor Duplicate File Detection
expected: Re-importing the same CSV file (identical content) is detected via SHA256 hash. The ImportBatch is marked DUPLICATE and no rows are re-processed.
result: pass
notes: Second import of same file output "File already imported (batch <id>). Skipping."

### 4. Solicitor User Auto-Linking
expected: When a Solicitor name matches exactly one User's full name (normalized), the Solicitor.user FK is automatically set. When the name matches two or more Users, auto-linking is skipped (ambiguous).
result: pass
notes: "Kukla, Matthew" auto-linked to mkukla1105@gmail.com. Ambiguous match ("user, admin") correctly excluded with warning.

### 5. Solicitor Row-Level Error Handling
expected: Rows with missing required name field are skipped with an error logged per-row. The import continues processing remaining rows and the error count appears in the summary.
result: pass
notes: Row 5 (empty name) reported "Missing solicitor name", other 4 rows processed successfully.

### 6. Constituent Import via Management Command
expected: Running `python manage.py import_re_constituents <csv_file> --owner <user_id>` with a valid RE constituent CSV processes all rows, creates or updates Contact records, and prints a summary with created/updated/skipped/error counts.
result: pass
notes: 4 created, 1 error (row with no name/org). Summary includes error details.

### 7. Constituent Import via API Endpoint
expected: POST to `/api/v1/imports/re/constituents/` with a CSV file upload creates an ImportBatch, processes constituents, and returns a JSON response with batch ID and summary stats.
result: pass
notes: Verified via Django test client — returns 200 with full batch summary.

### 8. Constituent Three-Tier Matching
expected: Contact matching follows the hierarchy: external_constituent_id first (global), then email (owner-scoped), then phone (owner-scoped). A CSV row with a constituent_id that matches an existing Contact updates that Contact rather than creating a duplicate.
result: pass
notes: Re-import with same constituent_ids matched existing contacts. Phone mismatches flagged as warnings, no duplicates created.

### 9. Constituent Merge-Only Updates
expected: When matching an existing Contact, only blank/empty fields are filled from the CSV. Fields that already have values in the database are never overwritten.
result: pass
notes: Created contact without phone, then re-imported with phone — "Updated: 1". Existing email preserved, blank phone filled.

### 10. Constituent Duplicate File Detection
expected: Re-importing the same constituent CSV (identical content) is detected via SHA256 hash and marked DUPLICATE, same as solicitor imports.
result: pass
notes: Second import output "File already imported (batch <id>). Skipping."

### 11. CSV Encoding Cascade
expected: CSV files in UTF-8-BOM, UTF-8, or Windows-1252 encoding are all handled automatically without user intervention or encoding errors.
result: pass
notes: Windows-1252 CSV with "Müller, Hans" parsed correctly — umlaut preserved in normalized name.

### 12. Flexible Header Aliases
expected: RE CSV files with various column name formats (e.g., "solicitor_name", "name", "full_name", "cnsol_1_01_name" for solicitor name) are all recognized correctly via header alias mapping.
result: pass
notes: CSV with "cnsol_1_01_name" and "cnsol_1_01_solicit_id" headers mapped correctly — 2 solicitors created.

## Summary

total: 12
passed: 12
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
