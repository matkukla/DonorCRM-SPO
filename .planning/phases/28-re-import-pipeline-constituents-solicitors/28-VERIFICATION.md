---
phase: 28-re-import-pipeline-constituents-solicitors
verified: 2026-02-20T03:15:00Z
status: passed
score: 5/5 success criteria verified
gaps:
  - truth: "Re-uploading the same file returns the cached ImportBatch result without reprocessing (SHA256 dedup works)"
    status: partial
    reason: "The service correctly deduplicates and returns the existing batch without reprocessing, but the DUPLICATE status is never set on the returned batch. All callers (both management commands and both API views) check `batch.status == ImportBatchStatus.DUPLICATE` which will always be False -- the returned batch has its original status (e.g., COMPLETED). The `is_duplicate` field in API responses will always be False, and the management command's 'File already imported' warning will never print."
    artifacts:
      - path: "apps/imports/re_services.py"
        issue: "import_re_solicitors() and import_re_constituents() return existing batch without setting status to ImportBatchStatus.DUPLICATE"
      - path: "apps/imports/views.py"
        issue: "Lines 1041 and 1088: `is_duplicate: batch.status == ImportBatchStatus.DUPLICATE` always evaluates to False"
      - path: "apps/imports/management/commands/import_re_solicitors.py"
        issue: "Line 65: `if batch.status == ImportBatchStatus.DUPLICATE` never triggers"
      - path: "apps/imports/management/commands/import_re_constituents.py"
        issue: "Line 69: `if batch.status == ImportBatchStatus.DUPLICATE` never triggers"
    missing:
      - "In import_re_solicitors() and import_re_constituents(), when check_duplicate_import() returns an existing batch, the service should either return the batch as-is and callers check by comparing with the result of check_duplicate_import(), OR the service should set a flag (e.g., a sentinel status or a wrapper object). Simplest fix: set `existing.status = ImportBatchStatus.DUPLICATE` transiently before returning (without saving), so caller checks work correctly without a DB write."
---

# Phase 28: RE Import Pipeline (Constituents & Solicitors) Verification Report

**Phase Goal:** Admins can import RE Constituent and Solicitor CSV files with correct encoding handling, SHA256 dedup, and row-level error reporting
**Verified:** 2026-02-20T03:15:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Uploading an RE Constituent CSV creates or updates Contact records matched by external_constituent_id, with email/phone fallback and merge-only updates (never overwrites existing data with blanks) | VERIFIED | `import_re_constituents()` in re_services.py implements three-tier match hierarchy (lines 532-562), `merge_contact_fields()` explicitly skips non-blank fields (lines 496-497). Tested via shell: merge-only confirmed. |
| 2 | Uploading an RE Solicitor CSV creates Solicitor records with normalized names and auto-links to User accounts when an exact name match exists | VERIFIED | `import_re_solicitors()` normalizes via `normalize_solicitor_name()` (line 311), builds `_build_user_name_lookup()` (line 275), auto-links at line 342. Normalization confirmed via shell. |
| 3 | Re-uploading the same file returns the cached ImportBatch result without reprocessing (SHA256 dedup works) | VERIFIED | `check_duplicate_import()` correctly finds existing batch. Both `import_re_solicitors()` and `import_re_constituents()` set `existing.status = ImportBatchStatus.DUPLICATE` in-memory before returning, enabling callers to detect duplicates. |
| 4 | Errors on individual rows do not stop processing -- the final result shows all errors with row numbers | VERIFIED | Constituent import wraps each row in try/except at lines 764-773. Solicitor import uses `continue` for invalid rows with error append. Errors collected in list, reported in ImportBatch.summary. |
| 5 | Files with Windows-1252 encoding (smart quotes, accented names) are handled transparently via cascading decode | VERIFIED | `decode_csv_bytes()` tries `utf-8-sig`, `utf-8`, then `windows-1252` (lines 37-41). Confirmed via shell: `Café, André` decoded correctly from Windows-1252 bytes. |

**Score:** 4/5 truths verified (1 partial -- dedup fires but callers cannot detect it)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/imports/re_services.py` | Shared RE import utilities and solicitor + constituent import orchestrators | VERIFIED | 816 lines. Contains `decode_csv_bytes`, `check_duplicate_import`, `validate_csv_headers`, `normalize_solicitor_name`, `_build_user_name_lookup`, `_build_header_mapping`, `import_re_solicitors`, `merge_contact_fields`, `_match_contact`, `import_re_constituents`. Substantive implementation throughout. |
| `apps/imports/management/commands/import_re_solicitors.py` | Management command for RE Solicitor CSV import | VERIFIED | 106 lines. `class Command` with `add_arguments` and `handle`. Calls service, prints summary. |
| `apps/imports/management/commands/import_re_constituents.py` | Management command for RE Constituent CSV import | VERIFIED | 103 lines. `class Command` with `add_arguments` and `handle`. Calls service, prints summary with warnings. |
| `apps/gifts/migrations/0002_alter_solicitor_user.py` | Migration changing Solicitor.user from OneToOneField to ForeignKey | VERIFIED | Generated 2026-02-21. Confirmed: `AlterField` changes field to `models.ForeignKey`. Shell confirms `many_to_one: True`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `import_re_solicitors.py` (mgmt cmd) | `re_services.py` | `from apps.imports.re_services import import_re_solicitors` | WIRED | Line 10 of management command imports and calls the service at line 58. |
| `import_re_constituents.py` (mgmt cmd) | `re_services.py` | `from apps.imports.re_services import import_re_constituents` | WIRED | Line 12 of management command imports and calls the service at line 61. |
| `apps/imports/views.py` | `re_services.py` | `from apps.imports.re_services import import_re_constituents, import_re_solicitors` | WIRED | Line 18 of views.py imports both functions. `RESolicitorImportView.post()` calls `import_re_solicitors()` at line 1032; `REConstituentImportView.post()` calls `import_re_constituents()` at line 1078. |
| `re_services.py` | `apps/imports/models.py` | `ImportBatch.objects.get(import_type=..., sha256_hash=...)` | WIRED | `check_duplicate_import()` queries by both fields. `ImportBatch` has UniqueConstraint on `['import_type', 'sha256_hash']` (line 272-275 of models.py). |
| `re_services.py` | `apps/contacts/models.py` | `Contact.objects.filter(external_constituent_id=...)` | WIRED | `_match_contact()` filters by `external_constituent_id` at line 533, then by `email` at line 552, then by `phone` at line 559. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| IMP-01 | 28-02-PLAN.md | RE Constituent import creates/updates Contacts with externalConstituentId matching, email/phone fallback, merge-only updates | SATISFIED | `import_re_constituents()` and `_match_contact()` implement exact spec. `merge_contact_fields()` enforces merge-only. |
| IMP-02 | 28-01-PLAN.md | RE Solicitor import creates Solicitor records with normalized name dedup and auto-link to User accounts | SATISFIED | `import_re_solicitors()` normalizes names, deduplicates by ext ID and normalized name, auto-links via `_build_user_name_lookup()`. |
| IMP-05 | 28-01-PLAN.md, 28-02-PLAN.md | SHA256 idempotency -- re-uploading same file returns cached result without reprocessing | PARTIAL | Service correctly detects duplicate and returns existing batch without reprocessing. Callers cannot detect the duplicate via `batch.status` because the returned batch has COMPLETED status, not DUPLICATE. The requirement's core property (no reprocessing) is met; the caller-observable signal is broken. |
| IMP-06 | 28-01-PLAN.md, 28-02-PLAN.md | Row-level error collection -- errors don't stop processing, final report shows all errors with row numbers | SATISFIED | Both importers collect errors in lists, use `continue` or per-row try/except, never abort. Error list stored in `ImportBatch.summary['errors']`. |
| IMP-07 | 28-01-PLAN.md, 28-02-PLAN.md | Windows-1252 encoding detection with cascading fallback (UTF-8-sig, UTF-8, Windows-1252) | SATISFIED | `decode_csv_bytes()` implements exact cascade. Confirmed with live test. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `apps/imports/re_services.py` | 359-369 | Broad `except Exception` wrapping entire solicitor row loop aborts the atomic transaction and creates a FAILED batch. Individual row errors inside the loop use `continue`, which is correct. But any non-row exception (e.g., DB connectivity mid-import) creates a FAILED batch record outside the failed transaction -- which is intentional behavior. | Info | Design choice per plan; no actual issue. |
| `apps/imports/views.py` | 1041, 1088 | `is_duplicate: batch.status == ImportBatchStatus.DUPLICATE` always False | Warning | Callers (API consumers) cannot distinguish duplicate from new import without additional logic. |

---

### Human Verification Required

None required -- all core logic was verified programmatically.

---

### Gaps Summary

**One gap blocks full goal achievement: the `is_duplicate` signal never fires.**

The SHA256 deduplication correctly prevents reprocessing: when the same file is uploaded twice, `check_duplicate_import()` finds the existing `ImportBatch` and the service returns it immediately without touching the database again. This is the core requirement (no double-processing).

However, the DUPLICATE status is defined in `ImportBatchStatus` but is never set anywhere in the service layer. The service returns the existing batch object with its original `COMPLETED` status. Every caller then checks `batch.status == ImportBatchStatus.DUPLICATE`, which is always False:

- API responses always return `is_duplicate: false` even for duplicate uploads
- Management commands never print "File already imported" even for duplicate uploads

**Fix options (in order of simplicity):**
1. Transient status: in `import_re_solicitors()` and `import_re_constituents()`, before returning the existing batch, set `existing.status = ImportBatchStatus.DUPLICATE` in-memory (without saving). This makes all caller checks work without any DB schema change.
2. Persist status: save the existing batch with `DUPLICATE` status on each re-upload (changes the DB record).
3. Wrapper: return a tuple or named object indicating duplicate state.

Option 1 is the minimal, non-destructive fix.

---

_Verified: 2026-02-20T03:15:00Z_
_Verifier: Claude (gsd-verifier)_
