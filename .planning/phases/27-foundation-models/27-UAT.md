---
status: complete
phase: 27-foundation-models
source: [27-01-SUMMARY.md, 27-02-SUMMARY.md]
started: 2026-02-20T23:10:00Z
updated: 2026-02-20T23:45:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 6
name: Server Starts Without Errors
expected: |
  Run `python manage.py check` in the terminal. Output shows "System check identified no issues." with zero warnings or errors.
result: pass

## Tests

### 1. Gift Admin Page
expected: Navigate to Django admin. Under the "Gifts" section, you should see: Solicitors, Gifts, Gift credits, Recurring gifts, Recurring gift credits. Click "Gifts" — the list page loads without errors.
result: pass

### 2. Solicitor Admin Page
expected: In Django admin, click "Solicitors". The list page loads showing columns for name, normalized_name, and linked user. Click "Add Solicitor" — the form shows fields for first_name, last_name, normalized_name, external_solicitor_id, and an optional User link.
result: pass — Add form shows Normalized Name, User, and External solicitor id. First/last name are not separate admin fields (stored via normalized_name). Fields map correctly.

### 3. PrayerIntention Admin Page
expected: In Django admin, under "Prayers" section, click "Prayer intentions". The list page loads. Click "Add Prayer intention" — the form shows required Contact field, optional Gift link, title, description, status dropdown (Active/Answered/Archived), and answered_at/archived_at fields.
result: pass

### 4. ImportBatch Admin Page
expected: In Django admin, under "Imports" section, click "Import batchs" (or "Import batches"). The list page loads. Click "Add Import batch" — the form shows import_type dropdown with 7 types (including RE Constituent, RE Solicitor, RE Gift, RE Recurring Gift, Generic Contact, Generic Donation, Smartsheet MPD), status, sha256_hash, row counts, and summary fields.
result: pass

### 5. Contact Admin - New Fields
expected: In Django admin, open any existing Contact record for editing. Scroll through the form — you should see two new fields: "External constituent id" and "Organization name" (both may be blank on existing records).
result: pass — Initially missing due to explicit fieldsets in ContactAdmin. Fixed by adding "Organization" fieldset with organization_name and external_constituent_id (collapsed by default).

### 6. Server Starts Without Errors
expected: Run `python manage.py check` in the terminal. Output shows "System check identified no issues." with zero warnings or errors.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
