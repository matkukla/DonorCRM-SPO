# Journal tab goal progress is gift-based monthly support (one-time gifts ÷ 12)

Status: accepted

## Context

Issue #167 asked that a confirmed one-time gift count toward goal measurement as
its monthly-equivalent (`amount ÷ 12`), with recurring monthly gifts counting at
face value, on both the journal and goal tabs — without changing any stored gift
amount and without touching the Decisions progress bar.

Investigation found the request was already half-satisfied and mis-framed against
the data model:

- There is **no "one-time gift confirmed in a journal"** concept. Gifts have no FK
  to journals; a gift is "in" a journal only because its donor contact is a journal
  member (`JournalContact`). "Confirmed" in the pipeline means a `Decision`
  (a pledge) with `status="active"`, which is a separate concept from a `Gift`.
- The **Goal tab already** divides fiscal-year one-time gifts by 12 and adds the
  recurring monthly-equivalent, via the single canonical formula
  `apps/core/support_math.compute_monthly_support` (`one-time = recurring_gift_id
  IS NULL`). Non-monthly recurring gifts (quarterly/annual/etc.) are already
  normalized to monthly via `FREQUENCY_MULTIPLIERS`, so no new rule was needed —
  answering #167's open question.
- The **journal tab** was the actual gap. The Journal Detail header showed
  *cumulative pledged Decision amounts ÷ a monthly goal* — the apples-to-oranges
  bar that ADR 0008 explicitly deferred as a follow-up. It measured pledges at face
  value, not gifts, and never divided one-time gifts.

## Decision

The Journal Detail header progress bar now measures **gift-based monthly support
÷ the journal's monthly goal**, using the same `compute_monthly_support` formula as
the Goal tab, scoped to the journal's member contacts via a new
`apps/journals/services.get_journal_monthly_support(journal)`. The journal-report
endpoint returns this under `monthly_support` (financial-gated like the existing
pledge aggregates — withheld as `null` from coach). The header's "$X pledged / N
decisions" text stats are unchanged (informational, not goal measurement).

One-time gifts contribute `amount ÷ 12`; rounding to whole cents with half-up is
inherited from `compute_monthly_support` (single source of truth for the cents
math). Stored gift amounts are never modified. The Decisions progress bar
(`get_decisions_progress`, `Decision.monthly_equivalent`) is untouched.

## Considered alternatives

- **A new ÷12 in the journal path.** Rejected — would duplicate cents/rounding
  logic. Reusing `compute_monthly_support` keeps one source of truth.
- **Make the header fetch a dedicated lightweight endpoint.** Rejected —
  `useJournalReport` already runs for the Reports tab; React Query dedupes the
  identical query, so the header adds no extra request.

## Consequences

- Resolves the ADR 0008 known inconsistency for the Journal Detail header.
- The journal and goal tabs now measure goal progress identically (gift-based,
  monthly). Pledge totals remain visible separately as decision context.
- Drive-by fix: `pledge_followup.is_pledge_fulfilled` now quantizes
  `Decision.amount` to whole cents (half-up) before the integer-cents comparison,
  removing a latent truncation risk in adjacent money math.
