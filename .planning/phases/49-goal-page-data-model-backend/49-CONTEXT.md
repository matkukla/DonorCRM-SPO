# Phase 49: Goal Page — Data Model & Backend - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend infrastructure for Goal tracking: fiscal year utility, data model additions (User field rename + goalWeeks + GoalJournalSelection model), and API endpoints that calculate support progress from selected journals. No frontend work in this phase — that's Phase 50.

</domain>

<decisions>
## Implementation Decisions

### Monthly goal field migration
- Rename `User.monthly_goal` (DecimalField, dollars) → `monthly_support_goal_cents` (PositiveBigIntegerField, cents)
- Data migration: multiply existing values × 100, rounded (e.g., 3500.00 → 350000 cents)
- Done in Phase 49 — Phase 50 gets a clean cents-based API to work with
- Add `goal_weeks` (PositiveIntegerField, default=52) to User model alongside the cents field
- Update all existing references: dashboard services (get_support_progress uses user.monthly_goal), Settings serializer, CurrentUser serializer, admin

### Serializer/Settings API
- Add `monthly_support_goal_cents` and `goal_weeks` to the Settings serializer's writable fields (SettingsUpdateSerializer or equivalent) — keeps /api/users/me/ PATCH as the mechanism for profile updates
- Settings page UI change (remove/replace Fundraising Goal card) is deferred to Phase 50 — Phase 49 only updates the API

### GoalJournalSelection model
- Lives in `apps/users/` — goal config is user-owned preferences, consistent with monthly_support_goal_cents on User
- Shape: `GoalJournalSelection(user FK→User, journal FK→Journal, unique_together=[user, journal])`
- Separate model (not M2M without through), following JournalContact pattern
- TimeStampedModel base class

### API endpoint
- New dedicated endpoint: `GET /api/goals/me/` and `PATCH /api/goals/me/`
- GET returns: current goal (cents), goal_weeks, selected journal IDs, and calculated `effective_monthly_support`
- PATCH saves: goal amount, goal_weeks, journal selections (replace-all semantics for journal list)
- URL registered in `apps/users/urls.py` or a new `apps/users/urls_goals.py`

### Journal → gift attribution logic
- Effective monthly support = active RecurringGifts whose `donor_contact` is a JournalContact.contact in any selected journal — scoped to requesting user
- One-time Gifts: sum Gifts where `gift_date` is in the current fiscal year AND `donor_contact` is in journal contacts — divide by months_remaining (minimum 1)
- Total = recurring_monthly_equivalent + (fiscal_year_gifts ÷ months_remaining)
- New `apps/users/goal_services.py` with `get_goal_progress(user)` — separate from dashboard's `get_support_progress()` which stays unchanged

### Fiscal year utility
- New `apps/core/fiscal_year.py` — shared, importable by any app
- `fiscal_year_start(today)` → returns July 1 of the current fiscal year (July of current year if month >= 7, else July of prior year)
- `months_remaining(today)` → integer months from today to June 30 end of fiscal year, minimum 1
- `fiscal_year_end(today)` → returns June 30 of the current fiscal year end

### Claude's Discretion
- Whether to use SQL aggregation (like the existing `_monthly_equivalent_aggregate`) or Python iteration for the goal calculation — SQL preferred for performance consistency
- Exact URL path for the goals endpoint (`/api/goals/me/` vs `/api/users/goal/`)
- Whether GoalJournalSelection PATCH uses replace-all or add/remove semantics at the serializer level

</decisions>

<specifics>
## Specific Ideas

- The existing `_monthly_equivalent_aggregate()` helper in `apps/dashboard/services.py` uses SQL CASE/WHEN for frequency multipliers — goal_services.py should use the same or factor it out to a shared location
- `get_support_progress()` in dashboard must be updated to reference `monthly_support_goal_cents` (converted) after the rename — it currently reads `user.monthly_goal`

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/dashboard/services.py` → `get_support_progress(user)`: Existing support progress calculation. Reads `user.monthly_goal` — must be updated to `monthly_support_goal_cents`. The SQL aggregate helper `_monthly_equivalent_aggregate()` can be reused or extracted for goal_services.py.
- `apps/core/models.py` → `TimeStampedModel`: Base class for GoalJournalSelection.
- `apps/journals/models.py` → `JournalContact`: The join table — `JournalContact.contact_id` gives the contacts in a journal. Query: `JournalContact.objects.filter(journal__in=selected_journals).values_list('contact_id', flat=True)`.

### Established Patterns
- Money: `PositiveBigIntegerField` (cents) + `amount_dollars` Decimal property — follow Gift/RecurringGift pattern for `monthly_support_goal_cents`
- Model base: `TimeStampedModel` from `apps.core.models`
- Migrations: One migration for schema changes, one data migration for the cents conversion
- Serializer writable fields: follow SettingsUpdateSerializer pattern (see `apps/users/serializers.py` ~line 81)
- Permission classes: `IsAuthenticated` for own-data endpoints; goal endpoint should scope to `request.user` always

### Integration Points
- `apps/users/models.py`: Add `monthly_support_goal_cents`, `goal_weeks`, add `GoalJournalSelection` model
- `apps/users/serializers.py`: Update all serializers referencing `monthly_goal` → `monthly_support_goal_cents`; add goal fields to Settings serializer
- `apps/dashboard/services.py` ~line 173: `float(user.monthly_goal)` → `user.monthly_support_goal_cents / 100`
- `apps/core/fiscal_year.py`: New shared utility
- `apps/users/goal_services.py`: New service with `get_goal_progress(user)`
- `apps/users/urls.py`: Register new `/api/goals/me/` endpoint
- Frontend `apps/users/serializers.py` → CurrentUserSerializer: update `monthly_goal` → `monthly_support_goal_cents` field

</code_context>

<deferred>
## Deferred Ideas

- Frontend Settings page removal of Fundraising Goal card — Phase 50
- Goal history / trend chart — Phase backlog (GOAL-EX-01)
- Per-journal goal breakdown — Phase backlog (GOAL-EX-02)

</deferred>

---

*Phase: 49-goal-page-data-model-backend*
*Context gathered: 2026-03-12*
