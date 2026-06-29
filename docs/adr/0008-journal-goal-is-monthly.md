# Journal goal_amount is a monthly figure; Monthly Goal auto-sums from selected journals

Status: accepted

## Context

The Goal page's "Monthly Goal ($)" (`User.monthly_support_goal_cents`) was always set
by hand and was unrelated to any [[Journal]]'s `goal_amount`. Meanwhile `Journal.goal_amount`
had no explicit time basis — UI treated it as a campaign lifetime total (e.g. the Journal
Detail header reads "Goal: $X" with a cumulative-pledges-÷-goal progress bar). Issue #166
asked to express journal and goal amounts consistently in **monthly** terms and to derive
the Monthly Goal from the journals a missionary tracks.

## Decision

`Journal.goal_amount` is now defined as a **monthly** support target per journal (a
relabel only — existing values are test data and are NOT divided by 12). On Goal Settings
**Save** (button or Enter), if at least one journal is checked under "Track Progress By
Journals", the Monthly Goal is **overwritten** with the straight sum of the checked
journals' goals (each converted dollars→integer cents first, then summed as integers, so
the total is exact). With **no** journals checked, the manually typed Monthly Goal is kept
(preserving the all-donor mode of ADR 0004). The sum is computed client-side and sent as
`monthly_support_goal_cents` through the existing `PATCH /goals/me/`; no new backend
endpoint is added.

## Considered alternatives

- **Server-side sum** (new endpoint/field computing the Decimal sum). Rejected as
  unnecessary API surface for a small, exact client-side integer sum.
- **Full semantic fix** of the Journal Detail header progress bar (cumulative pledges vs a
  monthly target is apples-to-oranges). Deliberately left out of scope — labels are made
  honest ("Monthly Goal") but the header progress math is unchanged. Tracked as a separate
  follow-up.

## Consequences

- The Decisions forecast bar denominator (`decisions_goal = Σ selected journals' goals`) is
  now a monthly figure, consistent with the rest of the Goal page. Its cadence
  normalization (one-time/annual ÷ 12) is unchanged and out of scope.
- The Journal Detail header still divides cumulative pledges by a now-monthly goal — a known
  inconsistency to be addressed separately.
