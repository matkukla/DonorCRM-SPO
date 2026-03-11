---
phase: quick-15
plan: 15
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/dashboard/services.py
  - apps/gifts/models.py
  - apps/dashboard/tests/test_services.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Monthly Support Goal tile shows correct dollar amount matching active pledge monthly equivalents"
    - "Percentage bar reflects actual ratio of current_monthly_support to monthly_goal"
  artifacts:
    - path: "apps/dashboard/services.py"
      provides: "get_support_progress() with correct calculation"
    - path: "apps/gifts/models.py"
      provides: "monthly_equivalent property consistent with services.py multipliers"
  key_links:
    - from: "apps/dashboard/services.py"
      to: "apps/gifts/models.py"
      via: "FREQUENCY_MULTIPLIERS must match monthly_equivalent property exactly"
      pattern: "FREQUENCY_MULTIPLIERS"
---

<objective>
Investigate and fix the calculation error in the Monthly Support Goal dashboard tile.

Purpose: The tile shows incorrect values — the bug is somewhere in the recurring gift monthly equivalent aggregation in get_support_progress(). Fix the calculation so the tile accurately reflects the missionary's active pledge commitments vs their goal.
Output: Corrected calculation in services.py and/or models.py with updated/new tests proving the fix.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Key files:
- apps/dashboard/services.py — get_support_progress() and _monthly_equivalent_aggregate()
- apps/gifts/models.py — RecurringGift.monthly_equivalent property and RecurringGiftFrequency enum
- apps/dashboard/tests/test_services.py — existing tests for get_support_progress
</context>

<tasks>

<task type="auto">
  <name>Task 1: Investigate the calculation error via shell and test inspection</name>
  <files>apps/dashboard/tests/test_services.py</files>
  <action>
Run the Django shell to diagnose what's wrong. Use `python manage.py shell` to:

1. Check real data: query RecurringGift.objects.filter(status='active') and inspect .frequency distribution and .monthly_equivalent values for a sample user.

2. Compare Python property vs SQL aggregate for the same queryset:
   ```python
   from apps.dashboard.services import _monthly_equivalent_aggregate, get_support_progress
   from apps.gifts.models import RecurringGift, RecurringGiftStatus
   from apps.users.models import User

   # Pick a real missionary user
   user = User.objects.filter(role='missionary').first()
   rg = RecurringGift.objects.filter(donor_contact__owner=user, status='active')

   # Python property sum
   python_total = sum(r.monthly_equivalent for r in rg)

   # SQL aggregate
   sql_total = _monthly_equivalent_aggregate(rg)

   print(f"Python total: {python_total}, SQL total: {sql_total}")
   print(f"User monthly_goal: {user.monthly_goal}")
   print(f"Frequencies: {list(rg.values_list('frequency', flat=True))}")
   ```

3. Check for the BIMONTHLY interpretation issue: In Raiser's Edge, "bimonthly" typically means "every two months" (multiplier 0.5), but look at actual RE data to confirm. The RE import FREQUENCY_MAP maps 'bimonthly' -> BIMONTHLY without clarifying the direction.

4. Check if the scoping bug exists: `get_support_progress` scopes by `donor_contact__owner_id__in=visible`. If `get_visible_user_ids(user)` for a missionary role returns `None` (all-access), that would include ALL recurring gifts from ALL users — causing inflated numbers. Check apps/core/permissions.py for the missionary case.

Document the root cause found before writing the fix.

After identifying the root cause, add a focused regression test to test_services.py that:
- Sets up the specific scenario that was wrong (e.g., bimonthly gift, or wrong scoping)
- Asserts the CORRECT expected value
- Run: `python -m pytest apps/dashboard/tests/test_services.py -x -q` — it should FAIL before the fix
  </action>
  <verify>
    <automated>python -m pytest apps/dashboard/tests/test_services.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>Root cause identified and documented in code comment; new regression test added that fails with current code</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Fix the calculation and verify all tests pass</name>
  <files>apps/dashboard/services.py, apps/gifts/models.py</files>
  <behavior>
    - If BIMONTHLY means "every 2 months" (multiplier 0.5): multiplier in both FREQUENCY_MULTIPLIERS and monthly_equivalent property are correct — not the bug
    - If BIMONTHLY means "twice a month" (multiplier 2.0): both FREQUENCY_MULTIPLIERS and monthly_equivalent property need to change from Decimal('1')/Decimal('2') to Decimal('2')
    - If the scoping bug is the issue (visible=None includes all users): get_support_progress must handle the missionary role explicitly — missionaries should only see their own contacts' gifts (not all contacts)
    - If get_visible_user_ids returns None for missionaries, fix the scoping to filter by donor_contact__owner=user for non-admin roles
    - Both FREQUENCY_MULTIPLIERS in services.py and the multipliers dict in RecurringGift.monthly_equivalent must be kept in sync
  </behavior>
  <action>
Apply the fix identified in Task 1. Typical fixes:

**Fix A — BIMONTHLY multiplier wrong direction:**
In apps/gifts/models.py RecurringGift.monthly_equivalent property AND in apps/dashboard/services.py FREQUENCY_MULTIPLIERS, change:
  `RecurringGiftFrequency.BIMONTHLY: Decimal('1') / Decimal('2')`
to:
  `RecurringGiftFrequency.BIMONTHLY: Decimal('2')`
if "bimonthly" in context means "twice a month".

**Fix B — Scoping includes all users for missionary role:**
In apps/dashboard/services.py get_support_progress(), change the visible=None (all-access) branch to still scope by the user if the user is a missionary role (not admin/supervisor). Check apps/core/permissions.py for get_visible_user_ids behavior per role.

Apply whichever fix (or combination) the Task 1 investigation reveals. Add a clear comment explaining the intent.

After fixing, verify the new regression test from Task 1 now PASSES, and all existing tests still pass.
  </action>
  <verify>
    <automated>python -m pytest apps/dashboard/tests/test_services.py -v -q 2>&1 | tail -15</automated>
  </verify>
  <done>All dashboard service tests pass including the new regression test; get_support_progress returns the correct monthly_equivalent total for the test scenario</done>
</task>

</tasks>

<verification>
python -m pytest apps/dashboard/tests/ -v -q
The calculation fix should make the new regression test pass while all pre-existing tests remain green.
</verification>

<success_criteria>
- Root cause of calculation error identified and documented
- Fix applied to services.py and/or models.py
- New regression test added covering the exact failure scenario
- All dashboard service tests pass (11+ tests)
- FREQUENCY_MULTIPLIERS in services.py and monthly_equivalent property in models.py remain in sync
</success_criteria>

<output>
After completion, create `.planning/quick/15-investigate-and-fix-calculation-error-in/15-SUMMARY.md`
</output>
