# 3. Scrub raw PII from importer error messages, keep the structured error-row data

Date: 2026-06-19

## Status

Accepted

## Context

The pilot-readiness audit (#113) flagged donor PII leaking into CSV-importer
error output. The admin SPO/RE importers were scrubbed first (PR #115); the
self-service generic and contact/entity importers remained (#117).

Two distinct channels carry importer errors, and they have different exposure:

1. **Error message strings** — short human-readable text stored in
   `ImportBatch.summary["errors"][*]["error"]` (generic importers) or returned
   in the import response. These persisted/aggregated strings embedded raw donor
   values: the donor name/email/external_id in "No contact found matching ..."
   (`generic_services.py`), the raw email in "Invalid email format / Duplicate
   email / already exists" (`services.py`), and raw exception text via `str(e)` /
   `f"...{e}"`, which can carry field values from a `DataError`/`IntegrityError`.

2. **Structured error-row data** — `{"data": dict(row)}` on each error
   (`services.py` `parse_*_csv`) and the persisted `ImportRowError.row_data`.
   This is the *entire uploaded row*. It powers the "download my error rows,
   fix, re-upload" workflow: the export at `ImportRunErrorsCSVView`
   (`views.py`) writes each failed row back out with an `error_message` column.

These importers are own-scope (`IsStaffOrAbove`) or admin (`IsAdmin`); the
exposure is the uploader's own donors, not cross-role — lower risk than the
admin SPO/RE importers, hence MEDIUM.

## Decision

**Scrub messages; keep the structured row.**

- **Messages carry no raw values.** Drop donor name/email/external_id from
  "No contact found ..." (keep "matching the provided <field>"). Drop the raw
  email from the `services.py` validation messages (keep the reason). Replace
  every `str(e)` / `f"...{e}"` exception interpolation with
  `type(e).__name__`. This matches the pattern already applied to RE/SPO in
  PR #115.

- **`data: dict(row)` / `ImportRowError.row_data` is kept, unredacted.** It is
  the caller's *own* uploaded data round-tripping back to them; the export is
  `IsAdmin`-gated and already re-sanitized against CSV/formula injection
  (`sanitize_csv_value`). Redacting it would break the fix-and-reupload workflow
  (you cannot fix a value you cannot see) for no real confidentiality gain.

The invariant: **a value a user must act on round-trips only through the
structured `data` row, never duplicated into a persisted/aggregated message
string.**

## Consequences

- `ImportBatch.summary` and import responses no longer contain donor PII or raw
  exception text — safe to log, persist, and surface in aggregate error views.
- Inline error messages are slightly less specific (no offending value inline),
  but the structured row in the same payload still shows it.
- The `dict(row)` sites in `services.py` carry a comment pointing here so the
  next reviewer does not "fix" them into redaction.
- Covered by tests asserting the scrubbed messages contain the prefix but not
  the donor name/email, and that exceptions surface only the class name.

## Alternatives considered

- **Redact `row_data` too.** Rejected: breaks the legitimate fix-and-reupload
  workflow and adds no real protection — it is the uploader's own data behind an
  admin-gated, injection-sanitized export.
- **Leave messages as-is (own-scope, low risk).** Rejected: persisted summaries
  and logs outlive the request and are read in aggregate; raw PII there is the
  exact class of leak the audit exists to close, and the fix is cheap.
