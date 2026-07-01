# 10. The follow-up latch resets when its Task is deleted

Date: 2026-07-01

## Status

Accepted

## Context

A [[Pledge]] that is not [[Fulfilled]] by its check date gets one auto-generated
[[Follow-up]] Task. To keep the sweep idempotent, creating that Task sets a latch on
the Decision — `follow_up_created_at` — and the sweep skips any Decision whose latch
is already set.

The latch was **create-only**: nothing ever cleared it. Two facts made that a live,
user-reachable bug:

- `TaskDetailView` is a `RetrieveUpdateDestroyAPIView` — a missionary can hard-delete
  their own follow-up Task through the normal UI.
- When they do, the latch stays set forever. The pledge becomes permanently invisible
  to the sweep: no Task, no reminder, no error. An unfulfilled pledge silently rots —
  exactly the money the follow-up feature exists to recover.

Issue #176 (in-UI reopen) surfaced the latch but is **not** the bug: a reopened Task
is an open Task, and the latch correctly suppresses a duplicate. The bug is the
missing reset path, made reachable by Task **deletion**.

## Decision

The latch resets **only** when the follow-up Task is deleted (immediate re-arm). We
model the latch as one fact in two halves on the Decision:

- `follow_up_created_at` — idempotency timestamp (unchanged)
- `follow_up_task` — new FK to `tasks.Task`, `on_delete=SET_NULL`, set when the Task
  is created.

**Invariant:** `follow_up_created_at` is set **iff** `follow_up_task` points at a live
Task.

`apps/journals/pledge_followup.py` owns the whole lifecycle behind three verbs:

- `run_pledge_followup_sweep()` — arms follow-ups (sets both halves)
- `release_followup(task)` — clears both halves; no-op for non-follow-up Tasks
- `is_pledge_fulfilled(decision)` — the fulfillment predicate (kept public: it is the
  clean test surface for the CONTEXT.md "Fulfilled" rule)

The reset is **triggered** by a Task `pre_delete` signal (wired via
`TasksConfig.ready()`) that calls `release_followup`. `pre_delete`, not `post_delete`,
because `SET_NULL` nulls `follow_up_task` before `post_delete` fires — the same
constraint the RecurringGift handler in `apps/gifts/signals.py` already documents. The
signal guarantees every delete path (API, admin, cascade) is covered; the logic lives
once, in the module.

A defensive data migration backfills `follow_up_task` for Decisions whose follow-up
Task still exists, then clears the latch for true orphans (Task already deleted).
Backfill-before-heal avoids re-arming a pledge that still has a live Task (which would
produce a duplicate on the next sweep). The migration is a no-op if the data is clean.

## Consequences

- Deleting a follow-up Task re-arms the sweep; a fresh follow-up appears on a later run
  if the pledge is still unfulfilled. Deleting-instead-of-completing is nudged back.
- Immediate re-arm means a deleted follow-up can reappear as soon as the next daily
  sweep. Accepted for the pilot; a `follow_up_suppressed_until` delay was considered
  and **deferred** as speculative UX, not a bug fix.
- Out of scope (deliberately, matching the [[Fulfilled]] reversal clause): clearing the
  latch when a fulfilling [[Gift]] is deleted/refunded, or when a Decision is
  re-activated. These are separate behaviors, not this bug.
- The follow-up Task is now distinguishable from a manual Task via the FK, removing the
  prior "indistinguishable / heuristic-match" friction.
