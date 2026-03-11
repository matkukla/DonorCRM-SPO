---
phase: quick-15
plan: 15
subsystem: dashboard
tags: [bug-fix, scoping, support-progress, recurring-gifts]
dependency_graph:
  requires: []
  provides: [correct-monthly-support-goal-calculation]
  affects: [dashboard-support-progress-tile, admin-finance-read_only-dashboards]
tech_stack:
  added: []
  patterns: [always-scope-personal-tiles-by-owner]
key_files:
  created: []
  modified:
    - apps/dashboard/services.py
    - apps/dashboard/tests/test_services.py
decisions:
  - "Scope get_support_progress() by donor_contact__owner=user for all roles — the Monthly Support Goal tile is always personal, not role-scoped"
  - "Do not use get_visible_user_ids() sentinel (None = all-access) for personal progress tiles — the all-access pattern is correct for list views only"
  - "BIMONTHLY multiplier confirmed correct at 0.5 (every 2 months) — not the cause of the bug"
metrics:
  duration: "~4 minutes"
  completed: "2026-03-11"
  tasks_completed: 2
  files_modified: 2
---

# Quick Task 15: Monthly Support Goal Calculation Error — Summary

**One-liner:** Fixed admin/finance/read_only roles seeing ALL missionaries' recurring gifts in their personal Monthly Support Goal tile by scoping `get_support_progress()` to `donor_contact__owner=user` for all roles.

## Root Cause

`get_support_progress()` used `get_visible_user_ids(user)` to scope recurring gifts. For admin, finance, and read_only roles, `get_visible_user_ids` returns `None` (all-access sentinel), which caused:

```python
if visible is None:
    recurring_gifts = RecurringGift.objects.all()  # BUG: all missionaries' gifts!
```

This summed ALL active recurring gifts from ALL missionaries' contacts against the admin's personal `monthly_goal`. For example: an admin user with a $5,000/month goal would see $50,000+ as their "current monthly support" if the organization had many missionaries.

The `None` sentinel is correct for list views (where admins should see all data), but incorrect for the personal "Monthly Support Goal" dashboard tile.

## Investigation Findings

1. **Cross-missionary isolation (missionary role):** Working correctly. `get_visible_user_ids` returns `{user.id}` for missionaries, so `donor_contact__owner_id__in={user.id}` correctly scopes to only their own contacts. Verified by new test.

2. **BIMONTHLY multiplier:** Confirmed correct at `Decimal('1') / Decimal('2')` = 0.5. RE uses "bimonthly" to mean "every 2 months" (6 payments/year, $100 bimonthly = $50/month). Not the cause of the bug. Verified by new test.

3. **Admin scoping bug:** Confirmed failing. Admin with no personal contacts sees all missionaries' recurring gifts summed as their support. Fixed.

## Fix Applied

**`apps/dashboard/services.py` — `get_support_progress()`:**

Replaced the `get_visible_user_ids()` branching with a direct owner-scoped filter:

```python
# Before (buggy):
visible = get_visible_user_ids(user)
if visible is None:
    recurring_gifts = RecurringGift.objects.all()
else:
    recurring_gifts = RecurringGift.objects.filter(donor_contact__owner_id__in=visible)

# After (fixed):
recurring_gifts = RecurringGift.objects.filter(donor_contact__owner=user)
```

Added a detailed comment explaining why the all-access sentinel should not be used for personal progress tiles.

## Tests

3 new regression tests added to `apps/dashboard/tests/test_services.py`:

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_missionary_only_sees_own_contacts_gifts` | Missionary A has $100/mo, Missionary B has $200/mo | A sees only $100/mo | PASS (was already correct) |
| `test_admin_support_progress_only_shows_own_contacts` | Admin has no contacts, missionary has $500/mo gifts | Admin sees $0/mo | FAIL before fix, PASS after |
| `test_bimonthly_gift_monthly_equivalent` | $200 bimonthly gift | $100/month equivalent | PASS (multiplier was correct) |

**All 21 dashboard tests pass** (14 service + 7 view tests).

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly. Both investigation directions (BIMONTHLY multiplier and scoping) were checked as planned. BIMONTHLY was confirmed correct; the scoping bug for admin/finance/read_only was identified and fixed as anticipated.

## Self-Check

Commits: bebc0a0 (tests), 0c4ab71 (fix)
