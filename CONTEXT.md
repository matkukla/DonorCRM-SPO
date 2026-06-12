# Context

A glossary of the domain language used in DonorCRM. Terms here are the canonical
vocabulary — code, docs, and conversation should use these words to mean these things.

## Glossary

### Pledge
A donor's recorded commitment to give. In this codebase a pledge **is** a
[[Decision]] in the `active` state — there is no separate "Pledged" status or table.
A pledge carries an `amount` (dollars) and a `cadence` (one-time / monthly /
quarterly / annual). The moment the Decision is created is the pledge's start; the
pledge has no separately editable date.

### Decision
The single, mutable record (one per Journal Contact) capturing the current state of a
donor's giving decision: `amount`, `cadence`, and `status`
(pending / active / paused / declined). An `active` Decision is a [[Pledge]].
Changes are audited in `DecisionHistory`.

### Fulfilled (pledge)
A [[Pledge]] is **fulfilled** when, on or after the pledge's start date, the donor
has either a single [[Gift]] whose amount is at least the pledged amount, **or** an
active [[Recurring Gift]]. Partial gifts that do not individually meet the pledged
amount do **not** fulfill the pledge. Fulfillment is evaluated only to decide whether
a [[Follow-up]] is needed; once a pledge is treated as fulfilled, a later reversal
(refund / gift deletion) does not reopen it.

### Gift
A single donation from a donor (`Gift` model: `donor_contact`, `amount_cents`,
`gift_date`). The unit used to test [[Fulfilled]].

### Recurring Gift
A standing commitment that generates Gifts on a frequency (`RecurringGift`,
`status=active` meaning live). An active Recurring Gift fulfills a [[Pledge]].

### Follow-up
The single auto-generated Task created when a [[Pledge]] is **not** [[Fulfilled]] by
its check date — titled "Donation still not received — follow up", assigned to the
donor's owning missionary and linked to the donor. Exactly one follow-up is ever
created per pledge.
