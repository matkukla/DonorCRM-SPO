# Phase 28: RE Import Pipeline (Constituents & Solicitors) - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend import services that parse Raiser's Edge (RE) Constituent and Solicitor CSV files, create/update Contact and Solicitor records, with SHA256 dedup, cascading encoding detection, and row-level error reporting. Includes management commands and API endpoints. No frontend UI (that's Phase 32).

</domain>

<decisions>
## Implementation Decisions

### Contact Matching
- Match hierarchy: external_constituent_id first, then email, then phone. If none match, create new Contact.
- When external_constituent_id matches but email/phone differs from existing Contact: trust the ID match but log a warning flagging the conflict for admin review
- Merge-only: only fill blank fields on the Contact. Never overwrite existing non-blank values, even if RE has different data.
- Minimum data for new Contact creation: Claude's discretion based on RE data patterns and duplicate risk

### Solicitor Linking
- Name normalization handles "Last, First" vs "First Last" format differences (case-insensitive, trimmed, reversed format detection), but no fuzzy matching beyond that
- When a solicitor doesn't match any User account: create Solicitor unlinked, and include it in the import summary as "unlinked solicitors" for admin review
- Solicitor dedup strategy within a file: Claude's discretion based on RE data structure
- Multiple Solicitor records can link to the same User account (many-to-one is allowed). Admin cleans up later if needed.

### Error Handling
- Row-scoped errors: always process every row, collect all errors, report at end. Never abort mid-file for row errors.
- File-scoped errors (can't interpret safely — wrong format, missing required headers, unreadable encoding): abort entire file immediately
- Error detail per row: row number + error message. No raw row data stored.
- SHA256 dedup: re-uploading same file returns the cached ImportBatch result. No force-reprocess option.
- Header validation: flexible by default (required headers must be present, extras ignored), strict when it protects correctness

### Admin Trigger
- Management command: `python manage.py import_re_constituents <file>` and `python manage.py import_re_solicitors <file>`
- Also build API endpoints now (for Phase 32's UI to call later). Management command and API share the same service layer.
- Permissions: admin/superuser only (is_staff or is_superuser)
- CLI output: show progress indicator while processing, then print summary counts (created, updated, skipped, errors)

### Claude's Discretion
- Minimum data threshold for creating new Contacts from name-only rows
- Solicitor dedup key strategy (external_solicitor_id vs normalized name)
- Exact progress indicator format in management commands
- Service layer architecture (how to structure shared logic between command and API)
- Encoding cascade implementation details (UTF-8-sig, UTF-8, Windows-1252)

</decisions>

<specifics>
## Specific Ideas

- The service layer should be the single source of import logic — both management command and API endpoint call the same service functions
- Import summary should clearly separate "created", "updated", "skipped", and "errored" counts
- Unlinked solicitors should be surfaced prominently in the import result so admins know to review them

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 28-re-import-pipeline-constituents-solicitors*
*Context gathered: 2026-02-20*
