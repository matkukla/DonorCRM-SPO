# 4. The Goal page reflects all donors when no journals are selected

Date: 2026-06-25

## Status

Accepted

## Context

Three surfaces answer the missionary's question "how am I doing against my
support goal?" and they disagreed, which the dogfood report (F10, F11) flagged as
the most trust-destroying issue for a fundraising-anxious user:

- **Dashboard "Given & Expecting"** (`get_giving_summary`) showed **$2,025** — an
  *annual* figure (FY gifts + annualized recurring) over all the user's contacts.
- **Dashboard "Monthly Support" tile** (`get_support_progress` →
  `compute_monthly_support(Q(donor_contact__owner=user))`) showed **$552 / 25%** —
  a *monthly* figure over all the user's contacts.
- **Goal page** (`get_goal_progress`) showed **$0** — the *same* monthly formula as
  the dashboard tile, but scoped to contacts inside journals the user had selected
  on the Goal page. With no journals selected, `get_goal_progress` short-circuited
  to `0.0`, and the page told the user to "select journals above" with no journal
  selector and no journals to select.

The $2,025-vs-$552 gap is *annual vs. monthly* — a labeling problem, not a data
conflict. The genuinely broken number was the Goal page's **$0**: it answered a
narrower question (monthly support from *journal-cultivated* donors only) than the
user was asking (monthly support from *all* my donors), and it failed closed to
zero when the narrowing set was empty.

Journal selection exists as a deliberate feature: a missionary running a
cultivation campaign can track their goal against *that* campaign rather than their
whole portfolio. But the default user — no journals — got a dead end.

## Decision

The Goal page's Monthly Support number uses **all owned donors as the default
scope**, and journal selection acts as an **optional narrowing filter**:

- **No journals selected** → Monthly Support reflects **all the user's owned
  contacts** (`compute_monthly_support(Q(donor_contact__owner=user))`), the same
  scope and formula as the dashboard Monthly Support tile. The two now agree by
  default.
- **Journals selected** → scope narrows to contacts in the selected journals
  (unchanged behavior for campaign users).

When no journals are selected, the Goal page shows **only the Monthly Support
row**. The Calls, Meetings, and Decisions rows are inherently journal-based (counted
from `JournalStageEvent`s and `Journal.goal_amount` within selected journals; there
is no all-donor equivalent), so they appear **only once journals are selected**.
This removes the three dormant "select journals above" rows the user saw.

"Raised / effective monthly support" is defined as **actual money** —
`recurring_monthly + (FY one-time gifts / 12)` per `compute_monthly_support` — never
journal-pipeline decision amounts. Decisions remain a separate forecast row.

## Consequences

- The Goal page and the dashboard Monthly Support tile now show the **same number**
  for a user with no journals, removing the worst F11 contradiction.
- F10's dead `$0` + un-followable "select journals above" instruction is gone for
  the support number; the activity rows no longer render until they can be acted on.
- The `if not selected_journal_ids:` early-return-zero block in
  `apps/users/goal_services.py` must fall through to the all-donor computation
  instead. A test must assert that a user with gifts but no journals sees their real
  monthly support on the Goal page (not $0), and that it equals the dashboard tile —
  this is the regression guard for F10/F11.
- The annual ($2,025) vs. monthly ($552) figures still coexist on the dashboard;
  they are not reconciled here because they answer different questions (year-to-date
  coverage vs. monthly pace). Relabeling or consolidating the two dashboard tiles was
  considered and **deliberately declined** — the tiles stay as-is. The only F11 fix
  is the Goal-page fallback above.

## Alternatives considered

- **Rip journal-scoping out of the goal number entirely** (goal always = all
  donors; journal tracking lives only in the Decisions row). Rejected: throws away
  the intentional campaign-tracking feature for users who rely on it.
- **Treat the empty-journal state as an onboarding problem** (push Sarah to create
  journals). Rejected: the default "how am I doing?" question must answer from real
  gifts without first requiring the user to build a journal pipeline.
- **Make the goal track decision/pipeline amounts** instead of received gifts.
  Rejected: the user explicitly wants the goal grounded in actual money received,
  not projected commitments.
