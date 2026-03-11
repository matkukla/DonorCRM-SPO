---
status: complete
phase: 44-modify-the-spo-data-import-and-reconciliation-workflow
source: [44-01-SUMMARY.md, 44-02-SUMMARY.md, 44-03-SUMMARY.md, 44-04-SUMMARY.md]
started: 2026-03-07T00:00:00Z
updated: 2026-03-07T00:00:00Z
---

## Current Test

<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. MissionaryAlias Admin — list and filter
expected: In the Django admin, navigate to Imports > Missionary Aliases. The list shows columns: source_name, user, notes, created_at. A sidebar filter lets you choose "Resolved" (has a linked user) or "Unresolved" (no linked user). Searching by source_name narrows the list.
result: pass

### 2. MissionaryAlias Admin — create and resolve
expected: In the Django admin, create a new MissionaryAlias with a source_name (e.g. "Smith, John") and link it to an existing user via the raw_id FK field. Save. The alias appears in the list with the linked user shown. The fields id, created_at, updated_at are read-only.
result: skipped
reason: user unfamiliar with Django admin raw_id FK workflow

### 3. reconcile_missionaries management command — basic run
expected: Run `python manage.py reconcile_missionaries <path-to-spo-csv> --owner <user-id>`. The command completes without error and prints a summary table showing each missionary name from the CSV, their match outcome (exact/normalized/alias/created), and aggregate counts. Any missionary with zero donations shows "ZERO DONATIONS" in their status column.
result: pass

### 4. reconcile_missionaries — unresolved names list
expected: After running reconcile_missionaries with a CSV that contains a name not matching any existing user or alias, the command output lists that name under an "Unresolved names" section and reminds you to add an alias then rerun with --force.
result: pass

### 5. reconcile_missionaries — --force flag bypasses dedup
expected: Run reconcile_missionaries twice with the same file. The second run (without --force) reports the file as a duplicate and skips. Running with --force on the second attempt re-processes the file successfully, overwriting the previous import batch.
result: pass

### 6. import_spo_gifts management command — basic run
expected: After running reconcile_missionaries, run `python manage.py import_spo_gifts <path-to-gifts-csv> --owner <user-id>`. The command prints a summary: gifts created per missionary, skipped rows for unresolved solicitors or missing contacts, and any contact_not_found constituent IDs.
result: issue
reported: "The import worked but the total shows $0.00 for all missionaries in the per-missionary table"
severity: major

### 7. import_spo_gifts — gift and gift credit created
expected: After running import_spo_gifts with a valid gifts CSV, verify in the Django admin (or via API) that a Gift record exists for each imported row, and a GiftCredit links that gift to the correct missionary's Solicitor record.
result: pass

### 8. import_spo_gifts — blank constituent ID uses anonymous contact
expected: A gift row with a blank constituent_id should be attributed to the missionary's pre-created "Anonymous Donor" contact (not skipped). The gift appears in the DB linked to that anonymous contact.
result: pass

### 9. import_spo_prayers management command — basic run
expected: Run `python manage.py import_spo_prayers <path-to-gifts-csv> --owner <user-id>` on a CSV that has rows with prayer_description filled in. The command prints prayers_created count and skipped count. PrayerIntention records appear in the DB.
result: pass

### 10. import_spo_prayers — skips rows without prayer text
expected: Rows where prayer_description is empty are counted as skipped in the import_spo_prayers output, and no PrayerIntention record is created for them.
result: pass

### 11. SPO API — POST /api/imports/spo/missionaries/
expected: Upload the SPO missionary CSV via POST to /api/imports/spo/missionaries/ (multipart form, field name "file") as an admin user. The response is 200 with JSON containing batch_id, status, is_duplicate, created_count, updated_count, skipped_count, error_count, total_rows, summary. An unauthenticated request returns 401; a non-admin returns 403.
result: pass

### 12. SPO API — POST /api/imports/spo/gifts/
expected: Upload the SPO gifts CSV via POST to /api/imports/spo/gifts/ as an admin user. Response is 200 with ImportBatch JSON shape. No "force" parameter is accepted via the API.
result: pass

### 13. SPO API — POST /api/imports/spo/prayers/
expected: Upload the SPO gifts CSV (which contains prayer_description) via POST to /api/imports/spo/prayers/ as an admin. Response is 200 with ImportBatch JSON. A separate ImportBatch record is created with type spo_prayer (distinct from any spo_gift batch for the same file).
result: pass

### 14. SPO import batches visible in batch list
expected: After running any SPO import (via CLI or API), the resulting ImportBatch records appear in GET /api/imports/batches/ alongside any existing RE import batches, with the correct import_type values (spo_missionary, spo_gift, or spo_prayer).
result: pass

### 15. All SPO tests pass
expected: Run `python manage.py test apps.imports.tests --verbosity=1`. All 74 tests pass with no failures or errors.
result: pass

## Summary

total: 15
passed: 13
issues: 1
pending: 0
skipped: 1

## Gaps

- truth: "Gift amount_cents is populated from the SPO gifts CSV amount columns"
  status: failed
  reason: "User reported: The import worked but the total shows $0.00 for all missionaries in the per-missionary table"
  severity: major
  test: 6
  root_cause: "SPO_GIFT_HEADER_ALIAS_MAP does not include 'Fund Split Amount' as an alias for gift_amount. The actual CSV column is 'Fund Split Amount' but the alias map only has 'Gift Amount' and 'Amount'. _get(row, 'gift_amount') returns empty string → _parse_amount_to_cents returns 0. Gifts are stored with amount_cents=0."
  artifacts:
    - path: "apps/imports/spo_services.py"
      issue: "_SPO_GIFT_HEADER_ALIASES_NESTED missing 'Fund Split Amount' alias for gift_amount key"
  missing:
    - "Add 'Fund Split Amount' to _SPO_GIFT_HEADER_ALIASES_NESTED['gift_amount'] list"
  debug_session: ""
