# 6. Imported gifts enqueue a thank-you only when the gift is recent

Date: 2026-06-25

## Status

Accepted

## Context

The dogfood report (F4) found the dashboard Thank You Queue read 0 despite fresh
$1,000 gifts, and guessed the cause was that "a new gift does not enqueue a
thank-you." Investigation showed the opposite for **UI-entered** gifts: the
`post_save` signal on `Gift` (`apps/gifts/signals.py`) already sets
`donor_contact.needs_thank_you = True` for a newly-created non-recurring gift.

But the report's instinct pointed at a **larger, real bug** in the import path. All
three gift importers — `re_services.py`, `generic_services.py`, `spo_services.py` —
**disable gift signals** during bulk insert (for performance: one
`recompute_giving_stats` per contact instead of N signal fires) and then call
`update_giving_stats`, which writes `total_given`, `gift_count`,
`first_gift_date`, `last_gift_date`, `last_gift_amount`, `status` — but **never
`needs_thank_you`**.

Consequence: **every gift that arrives by CSV import is silently excluded from the
Thank You Queue.** Since import (e.g. from Raiser's Edge) is the primary way real
donation data enters this app, the Thank You Queue would stay near-empty despite
hundreds of real gifts — exactly the "supporter quietly drifts off the list" silent
failure the product exists to prevent. The original F4 finding understated this as a
seed-data artifact; it is a genuine bug.

## Decision

After the bulk recompute, each importer sets `needs_thank_you = True` for a contact
when its newly-imported gift is **both**:

- **non-recurring** (`recurring_gift_id IS NULL` — recurring auto-payments are not
  re-thanked, matching the UI signal), and
- **recent**: `gift_date` within the last **60 days** of the import run.

Historical backfill gifts (older than 60 days) do **not** enqueue a thank-you. The
60-day window encodes the actual intent — "thank people who *just* gave" — not "thank
everyone in a multi-year history dump."

## Consequences

- A weekly donation export imported into the app now correctly populates the Thank
  You Queue; a one-time historical migration does not flood it with thousands of
  stale thank-yous.
- The recency rule lives in the importer bulk path (signals are off there), so it is
  a third place that must agree with the UI signal's intent. The shared invariant —
  "a fresh non-recurring gift enqueues a thank-you" — is now enforced in two code
  paths (signal + importer); a test must cover the importer path specifically.
- The 60-day window is a hardcoded default (consistent with the
  [Not Contacted Recently](../../CONTEXT.md) 60-day threshold). Tunable in code; not
  a per-import option.
- Seed data (`generate_sample_data`) should likewise mark a few recent-gift contacts
  so the dashboard demonstrates the real behavior during dogfooding (the artifact
  that originally masked this).

## Alternatives considered

- **Flag every contact with any newly-imported gift.** Rejected: importing a year of
  back-history would mark essentially everyone as needing thanks — an unusable flood
  that would train users to ignore the queue.
- **Per-import checkbox ("mark new gifts as needing thank-you").** Rejected for the
  pilot: adds UI and uploader decision-load; the recency rule captures the intent
  automatically without a new control. Can be revisited if an org needs to override.
- **Leave it to the UI signal only (treat F4 as seed data).** Rejected: that leaves
  the primary data-entry path (import) silently broken — the real finding.
