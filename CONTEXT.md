# Context

A glossary of the domain language used in DonorCRM. Terms here are the canonical
vocabulary — code, docs, and conversation should use these words to mean these things.

## Glossary

### Last Contacted
The most recent point at which the missionary actually had a logged conversation
with a donor — the canonical "when did I last touch this relationship?" signal.
Defined as the **maximum** of two timestamps for the contact:
- a completed [[Task]] of type **Call** or **Meeting** (`completed_at`), and
- a [[Journal]] stage event of type `call_logged` or `meeting_completed`
  (`created_at`).
Deliberately **excludes** money signals (`last_gift_date` is not contact) and noise
like newsletter/other task types. Works whether or not the donor is in a journal.
**Computed on the fly** (a query annotation), not stored on the contact — unlike the
denormalized gift stats (`last_gift_date`, `total_given`). May be null (never
contacted via a logged call/meeting). Powers the "not contacted recently" surface
([[F6]]) and the contact Overview "last touch" line ([[F7]]).
See `docs/adr/0005-last-contacted-signal.md`.

### Not Contacted Recently
A donor whose [[Last Contacted]] is older than a fixed **60-day** threshold, **or**
who has never been contacted via a logged call/meeting at all (the latter sort to the
top as most-neglected). The threshold is a hardcoded default for the pilot (tunable
in code; not user-configurable and not per-donor cadence). Surfaced two ways, both
reading the same `last_contacted` annotation: a Contacts **preset** ("Not Contacted
Recently", a `last_contacted_before` filter) and a dashboard **Reconnect card** whose
"see all" links into that preset — mirroring the Late Donations tile → Insights table
pattern. This is the surface for the missionary's "who have I lost touch with?"
question that [[F6]] found missing.

### Monthly Support (effective)
The canonical "how am I doing against goal?" number, in **actual money received**:
`recurring_monthly + (fiscal-year one-time gifts / 12)`, computed by
`compute_monthly_support` (`apps/core/support_math.py`). It is a **monthly** figure.
Distinct from the dashboard's **Given & Expecting**, which is an **annual** figure
(FY gifts + annualized recurring) — same underlying gifts, different time basis.
Scope: by default **all the requesting user's owned donor contacts**. On the Goal
page, selecting [[Journal]]s **narrows** the scope to those journals' contacts; with
no journals selected the Goal page reflects all owned donors (matching the dashboard
tile). Never includes [[Decision]] pipeline amounts — those are a separate forecast.
See `docs/adr/0004-goal-page-falls-back-to-all-donors-when-no-journals-selected.md`.

### Journal Goal
A per-[[Journal]] fundraising target (`Journal.goal_amount`, dollars). It is a
**monthly** figure — the monthly support target for that one journal — not a campaign
lifetime total. Summing the Journal Goals of the journals checked under "Track Progress
By Journals" yields a missionary's [[Support Goal]] (straight sum, no annualization,
because the parts are already monthly). Today it also feeds the Goal page's **Decisions**
forecast bar (sum of selected journals' goals as the denominator). See `docs/adr/0008-journal-goal-is-monthly.md`.

### Support Goal
The missionary's personal monthly fundraising target (`User.monthly_support_goal_cents`,
integer cents), shown on the Goal page as **"Monthly Goal ($)"**. It is the denominator
of the [[Monthly Support (effective)]] progress bar. On Save Settings, if at least one
[[Journal]] is checked, it is **overwritten** with the sum of the checked journals'
[[Journal Goal]]s; with no journals checked, the manually typed value is kept. Distinct
from the org-wide **Annual Goal** (an organization setting used by the Admin Analytics
pace tile), which this never touches.

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

### Owner
The `User` a piece of donor data belongs to. Most owner-scoped models carry a direct
`owner` FK; others derive it transitively (a [[Gift]] is owned via its
`donor_contact.owner`; a journal stage event via its journal-contact's journal owner).
The owner is the missionary whose donor relationship the record represents.

### Visible Set
The set of user IDs whose data a requester may read, computed by
`get_visible_user_ids(user, request)` in `apps/core/permissions.py`. It is the central
data-scoping choke point. Returns `{self}` for admin / supervisor / missionary, and
`{self} ∪ coached` for a [[Coach]]. When [[View-As]] is active it collapses to
`{view_as_user}` regardless of role. (The PRD also names a `visible_queryset` helper;
on this codebase no such helper exists — scoping is done per-view by filtering on
`owner__in=get_visible_user_ids(...)`.)

### Financial Role
A role permitted to see individual transaction amounts ([[Gift]] amounts, [[Pledge]]
amounts). `is_financial_role(user)` is True for admin / supervisor / missionary and
**False for [[Coach]]**. A coach may see aggregate/summary financials but never
individual gift or pledge amounts.

The boundary is **aggregate vs. individual**:
- **Allowed to a coach (summaries):** cumulative `total_given`, `gift_count`, and
  `last_gift_date` on the contact list, and aggregate dashboard tiles.
- **Gated from a coach (individual transaction values):** a [[Gift]]'s `amount`, a
  [[Pledge]]'s `amount` / `monthly_equivalent`, `last_gift_amount`, and individual
  recent-gift rows on the dashboard. `last_gift_amount` counts as individual (the exact
  value of one gift), not a summary, even though it sits beside the summary fields.

### Coach
A role that reads its coached missionaries' non-financial data to support them. A coach
is **not** a [[Financial Role]]: gift detail, pledge amounts, and `last_gift_amount`
are gated away. Coaches have no write access (read-only via `IsStaffOrAbove`).

### View-As
A mode (Phase 52+) in which an admin or supervisor scopes their session to one target
user via the `X-View-As-User-Id` header, set on the request as `request.view_as_user`.
While active the [[Visible Set]] collapses to that user and all mutating requests must
be blocked server-side — View-As is **read-only**, not merely UI-hidden.

### Solicitor
The missionary credited for a [[Gift]] on import. Import rows may carry a solicitor
name; the importer resolves it to a linked solicitor's `User` to set [[Owner]]. An
unresolved solicitor name triggers [[Quarantine]] rather than defaulting ownership to
the admin uploader.

### Quarantine (import)
The held-back state for an RE gift / recurring-gift import group that carries solicitor
attribution intent but whose solicitor name resolves to no linked user, while the matched
contact is still owned by an **admin** (the uploader). Quarantined groups are **not
created**; they are reported in a `quarantined` / `quarantined_count` field on the import
summary for manual solicitor assignment and re-import. Chosen over silently creating the
gift under admin [[Owner]]ship. Implemented in `apps/imports/re_services.py` for both
`import_re_gifts` and `import_re_recurring_gifts`; the trigger is an **admin-role owner**
(a missionary-owned contact whose solicitors merely lack a user link still imports). See
`docs/adr/0002-import-quarantine-over-admin-owned-fallback.md`.
