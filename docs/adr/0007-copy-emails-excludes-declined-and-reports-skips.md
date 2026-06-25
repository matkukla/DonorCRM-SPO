# 7. Copy Emails excludes declined contacts unconditionally and reports what it skipped

Date: 2026-06-25

## Status

Accepted

## Context

The dogfood report flagged two faults in the Contacts "Copy Emails" action, both of
which make the clipboard silently disagree with what the missionary thinks they are
copying:

- **F8:** With Status=Donor (9 donors), Copy Emails copied **8** addresses — Patricia
  Taylor has no email and was dropped silently. A success toast does exist
  (`Copied N emails`), but it reports only the count *copied*, never that anyone was
  *skipped*, so the omission is invisible.
- **F9:** With **no** filter applied, Copy Emails copies every contact-with-email,
  including **Declined** supporters. A missionary who clicks Copy Emails for a
  newsletter without first filtering would email people who explicitly said no.

Both are the same defect: the action gives no trustworthy account of who is and isn't
on the clipboard, and the cost of the silent errors is high (omitting a real donor
from a newsletter; emailing a declined supporter).

## Decision

Copy Emails becomes self-reporting and safe by default:

- **Declined contacts are excluded unconditionally**, regardless of the active
  filter. A declined supporter must never land in a copied email list.
- The backend email endpoint returns, alongside the emails, a **skipped-no-email
  count** and a **declined-excluded count**.
- The success toast reports all three, e.g.
  **"Copied 8 · 1 skipped (no email) · 2 excluded (declined)."** When nothing is
  skipped or excluded, the extra clauses are omitted.

## Consequences

- The newsletter path is safe even when the user forgets to filter: declined
  supporters can no longer be copied.
- The missionary always knows the clipboard's true contents — no silent drops.
- "Exclude declined" is a **hard rule in the email action**, not a filter the user
  can turn off; a future change that "respects the filter literally" would reopen
  F9 and must not. This ADR is the reason the rule exists.
- Showing *which* contacts were skipped/excluded (names, not just counts) is a
  possible later enhancement; counts in the toast are sufficient for the pilot.
- A test must assert that an unfiltered Copy Emails omits declined contacts and that
  the skipped/excluded counts are reported.

## Alternatives considered

- **Only fix the skipped-count; leave Declined to the user's filter discipline.**
  Rejected: relies on the user remembering to filter every time, and the failure
  (emailing someone who declined) is exactly the silent, high-cost error the product
  should prevent.
- **Warn when the copy includes Declined, but still include them.** Rejected: a
  warning on a clipboard action is easily missed after the paste has happened;
  exclusion is the safe default.
