# 2. Quarantine unresolved-solicitor gift imports instead of admin-owned fallback

Date: 2026-06-19

## Status

Accepted

## Context

Gift and recurring-gift import (e.g. `import_re_gifts` in
`apps/imports/re_services.py`) reassigns a contact's [[Owner]] to the resolved
[[Solicitor]]'s user when the rows carry a solicitor name. The reassignment loop
(around `re_services.py:1540`) only acts when the solicitor name resolves to a linked
user; if the contact is still owned by the **admin uploader** and the solicitor name
resolves to **no** user, the loop finds nothing, the contact stays owned by the admin,
and the gift is **still created**.

The result is a silent misroute: real money lands under the wrong owner (the admin),
with no signal that the intended missionary never received it. Because owner is the
data-scoping key, the donor then sits in the admin's scope, invisible to the missionary
who actually solicited the gift. This is the class of defect the pilot-readiness audit
treats as CRITICAL — donors silently assigned to the wrong owner on import.

## Decision

When **all** of the following hold, the gift group is **quarantined** — not created:

1. the matched contact is still owned by the **admin uploader** (the owner has no
   [[Solicitor]] record), **and**
2. the rows carry solicitor names (attribution intent is present), **and**
3. **none** of those names resolve to a linked solicitor's user.

Quarantined groups are reported in a prominent `quarantined` / `quarantined_count`
field on the import summary (served via the import-status API) so an admin can assign a
solicitor and re-import. Groups that do not meet all three conditions are unaffected:

- rows with **no solicitor column / no solicitor name** import normally (admin-owned is
  legitimate — there was no attribution intent to honor);
- a contact already owned by a linked missionary is left alone;
- a **resolvable** solicitor still creates the gift and reassigns ownership as today.

The actual code change lands during the audit's fix phase (phase 8), not before — this
ADR records the decision; it does not authorize an out-of-gate edit.

## Consequences

- Import is no longer "every valid row always lands." A row can be intentionally
  withheld, which the summary must surface prominently or the data silently goes
  missing instead of silently misrouting — trading one failure mode for a louder one.
- The summary gains `quarantined` / `quarantined_count`; downstream consumers of the
  summary (the import-status UI) must render it.
- Re-import after solicitor assignment must be idempotent so a quarantined-then-fixed
  group is not double-counted. (Tracked with the existing import-idempotency work.)
- Covered by a service-level test asserting `quarantined_count` and that the gift was
  **not** created, plus that a resolvable solicitor still creates+reassigns.

## Alternatives considered

- **Keep the admin-owned fallback (current behavior).** Rejected: it misattributes real
  donations and hides the donor from the soliciting missionary — the exact CRITICAL the
  audit exists to close.
- **Create the gift but flag it for review.** Rejected: a created-but-flagged gift still
  pollutes the admin's scope and denormalized totals; withholding is cleaner to reason
  about and to re-drive once the solicitor is assigned.
