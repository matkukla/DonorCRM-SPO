# Phase 44: Modify the SPO Data Import and Reconciliation Workflow - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

A targeted reconciliation pipeline to get 25 missionaries, their donations, and prayer intentions correctly loaded into DonorCRM from SPO source files (Solicitors CSV, Gifts/Donations CSV, Prayer Intentions embedded in gifts, Smartsheet MPD). Includes missionary account creation/reconciliation, donation attribution with anonymous donor handling, and a full audit trail proving nothing was missed. Does NOT redesign the data model or replace the existing RE import pipeline.

</domain>

<decisions>
## Implementation Decisions

### Missionary Account Creation

- When a solicitor from the CSV doesn't match any existing User: auto-create a User with role=missionary, name from CSV, placeholder email `firstname.lastname@spo.org`, flagged in audit as "created — needs real email"
- Name matching levels: 1) exact full name match, 2) normalized match (lowercase, trimmed, punctuation-stripped), 3) check alias table. If no match after all three: create new User or flag if alias table entry is marked unresolved
- When a solicitor CSV row matches an existing User: fill blank fields only (merge-only pattern from Phase 28) — never overwrite existing values
- Tri-source reconciliation: compare solicitors CSV names, Smartsheet MPD names, and existing User accounts in one pass. Flag missionaries that appear in one source but not another
- Trigger: both a management command (`reconcile_missionaries <file.csv>`) AND an API endpoint (same service layer, same as Phase 28 pattern). Both surface results in ImportBatch history

### Unresolved Name Review Queue

- Unresolved/ambiguous names: print to terminal AND stored in ImportBatch.summary JSON — survives terminal close, queryable via Django admin
- Donations referencing an unresolved missionary: skip and report — counted explicitly in audit as "unmatched — unresolved solicitor". Admin resolves name, reruns to pick them up
- Alias table: a lightweight `MissionaryAlias` model (source_name, user FK). Admin populates via Django admin to register known name variants. Reconciliation service checks this before attempting normalized matching

### Anonymous Donor Handling

- Detection: blank/missing donor name field = anonymous (does not require "Anonymous" keyword)
- Strategy: one per-missionary "Anonymous Donor" contact. All anonymous gifts for a given missionary link to their dedicated anonymous contact
- `Contact.owner` for anonymous contacts = the missionary User the donation was credited to (scopes correctly for supervisor/coach visibility)
- Anonymous contacts are auto-created on first anonymous gift for that missionary

### Multi-Step Pipeline Architecture

- Separate management commands for each step:
  1. `reconcile_missionaries <solicitors.csv>` — creates/verifies 25 missionary accounts
  2. `import_spo_gifts <gifts.csv>` — imports donations, attributes to missionaries
  3. `import_spo_prayers <file>` — routes prayer intentions to correct contact/missionary context
- Each step produces its own ImportBatch record
- Admin runs step 1, reviews audit output, fixes alias table if needed, then runs step 2 with confidence

### Audit Output

- Terminal output: formatted summary table printed at end of each command
- Stored in ImportBatch.summary JSON (same data, persisted for Import History UI)
- Format: aggregate totals section first, then per-missionary breakdown table
  - Aggregate: total missionaries expected, created, matched, unresolved, total donations processed, imported, skipped, anonymous count, prayer intentions imported
  - Per-missionary: name, match type (exact/normalized/alias/created), gifts imported, total amount, anonymous gifts count
- Missionaries with zero donations explicitly flagged

### Idempotency / Reruns

- SHA256 dedup reused from existing ImportBatch infrastructure — same file = skip
- Alias table changes allow reruns to pick up previously unresolved names after admin registers the alias (admin must submit a slightly modified file or use a management command `--force` flag to bypass dedup)

### Claude's Discretion

- MissionaryAlias model exact fields and admin registration UX
- Exact terminal output formatting (table vs. structured text)
- Service layer module organization (one file per step vs. shared spo_services.py)
- Smartsheet tri-source comparison implementation details
- Prayer intention detection from gifts CSV (reuse Phase 29 patterns where applicable)

</decisions>

<specifics>
## Specific Ideas

- import_prompt.md is the canonical spec — all 5 phases in that doc map to this implementation
- Placeholder email format: `firstname.lastname@spo.org` (not `@placeholder.internal`)
- Accuracy over cleverness: uncertain matches go to review queue, never silently auto-merged
- Workflow must be safe to rerun — idempotency guaranteed by SHA256 dedup + upsert logic
- "do not auto-assign uncertain donations to the wrong missionary" — core non-goal from import_prompt.md

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- `ImportBatch` model: universal tracking with SHA256 dedup, status, row counts, summary JSON — use for all 3 pipeline steps
- `re_services.decode_csv_bytes()`: cascading encoding detection (UTF-8-sig, UTF-8, Windows-1252) — reuse for SPO files
- `re_services.skip_re_type_label_row()`: strips RE type-label rows — adapt if SPO files have similar leading rows
- `import_re_solicitors()` service: Solicitor name normalization, User account auto-linking — reuse normalization logic
- `import_re_gifts()` service: prayer intention auto-creation from gift description column (Phase 29) — reuse for SPO gifts
- `MissionaryAlias` — new model needed (doesn't exist yet)

### Established Patterns

- Merge-only contact/user updates: fill blank fields, never overwrite (Phase 28 pattern)
- SHA256 dedup: `(import_type, sha256_hash)` unique constraint on ImportBatch
- Row-scoped errors: always process every row, collect all errors, report at end
- Management command + API sharing same service layer (Phase 28)
- `ImportBatch.summary` JSON for type-specific metadata and unresolved items

### Integration Points

- `apps/imports/re_services.py`: add SPO services alongside or in a new `spo_services.py`
- `apps/imports/management/commands/`: add `reconcile_missionaries.py`, `import_spo_gifts.py`, `import_spo_prayers.py`
- `apps/imports/views.py`: add API views for each SPO step (same shape as `REConstituentImportView`)
- `apps/imports/models.py`: add `MissionaryAlias` model; add `SPO_*` types to `ImportBatchType`
- `frontend/src/components/imports/REImportSection.tsx`: SPO import section can be added alongside RE section

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 44-modify-the-spo-data-import-and-reconciliation-workflow*
*Context gathered: 2026-03-07*
