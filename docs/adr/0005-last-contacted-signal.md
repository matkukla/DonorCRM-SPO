# 5. "Last Contacted" is a computed signal over completed call/meeting tasks and journal events

Date: 2026-06-25

## Status

Accepted

## Context

The dogfood report (F6, F7) found the product had no answer to the missionary's most
important relational question: "who have I not talked to in a while, and when did I
last touch this person?" The report notes explicitly that **"Last Gift ≠ last
contacted"** — money arriving is not a conversation. A lapsed donor opened from the
contact page showed no reason to call, and there was no list anywhere surfacing
neglected relationships.

Several touch-like signals already exist, but none is unified:

- **Completed Tasks** of type Call / Meeting linked to a contact (`Task.contact`,
  `status=completed`, `completed_at` timestamp). This is how a missionary records a
  conversation with a donor who is **not** in a journal (e.g. lapsed Stephanie).
- **JournalStageEvents** of type `call_logged` / `meeting_completed` (`created_at`).
  This is how conversations are recorded for donors inside a cultivation journal.
- `Contact.last_gift_date` — money, not contact.
- Notes / prayer requests — context, but no reliable interaction timestamp.

We need one canonical "last contacted" value that both the "not contacted recently"
surface (F6) and the contact Overview "last touch" line (F7) can read.

## Decision

**Last Contacted** is defined as the **maximum** of:

- the `completed_at` of any completed `Task` of type **Call** or **Meeting** linked
  to the contact, and
- the `created_at` of any `JournalStageEvent` of type `call_logged` or
  `meeting_completed` for the contact.

It **excludes** gift dates and all other task types (newsletter sends, generic
"other" tasks, thank-yous) — only a logged call or meeting counts as "I talked to
them." It may be **null** (a contact never reached via a logged call/meeting).

It is **computed on the fly** as a query annotation, not denormalized onto the
Contact. This differs from the gift stats (`last_gift_date`, `total_given`,
`gift_count`), which are denormalized and kept fresh by signals
(`apps/gifts/signals.py`).

## Consequences

- **No migration, no signals, no backfill, no drift.** The value is always correct
  because it is derived at read time from the source timestamps.
- F6's "not contacted recently" surface is a **sort/filter on this annotation** —
  a contact-list queryset annotated with `last_contacted` and ordered/filtered by
  it. This is the queryable form F6 needs regardless, so the annotation pays for
  itself.
- F7(b)'s contact Overview reads the same annotation to render "Last touch: Call,
  N days ago" (or a clear "no logged contact yet" when null).
- The trigger surface spans **two** models (Task and JournalStageEvent), which is
  why denormalization was not chosen up front — it would require two signal handlers
  plus a backfill, versus gift stats' single source.
- If contact-list pages later show this subquery is a performance problem at scale,
  denormalizing `Contact.last_contacted_at` with signals (mirroring the gift-stats
  pattern) is a clean, isolated follow-up. Not done now: not worth the
  migration/signal/drift cost for a pilot.
- A test must assert `last_contacted` reflects the latest of the two sources and
  ignores gifts and non-call/meeting task types.

## Alternatives considered

- **Tasks only** (ignore journal events). Rejected: would under-count for journal
  users, who log conversations as stage events, not tasks.
- **Any logged interaction** (all completed tasks + notes + prayer + journal events).
  Rejected: dilutes the signal — marking a "send newsletter" task done is not "I
  talked to them," which is exactly the noise that would make the F6 list untrustworthy.
- **Denormalized `last_contacted_at` field + signals**, mirroring gift stats.
  Rejected for now: two trigger models, a migration, and a backfill, plus a new
  drift risk, for no read-path benefit a query annotation can't provide at pilot scale.
- **Reuse `last_gift_date`.** Rejected outright: the report's central insight is that
  money received is not the same as a relationship touch.
