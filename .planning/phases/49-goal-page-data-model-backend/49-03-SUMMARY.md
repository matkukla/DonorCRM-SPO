---
phase: 49-goal-page-data-model-backend
plan: 03
subsystem: database
tags: [django, migrations, postgresql, user-model, goal-tracking]

# Dependency graph
requires:
  - phase: 49-01
    provides: UserFactory with monthly_support_goal_cents, TDD stubs for goal_services and goals/me/ endpoint
  - phase: 49-02
    provides: fiscal year utility, FREQUENCY_MULTIPLIERS in core.gift_utils

provides:
  - Django migrations 0007 (schema) and 0008 (data) applied cleanly to users app
  - User.monthly_support_goal_cents (PositiveBigIntegerField, default=0)
  - User.goal_weeks (PositiveIntegerField, default=52)
  - User.monthly_support_goal_dollars property (cents / 100 as Decimal)
  - GoalJournalSelection model (user FK + journal FK + unique_together)
  - All serializers updated: monthly_support_goal_cents in 5 serializers, goal_weeks in 2
  - apps/dashboard/services.py reads monthly_support_goal_cents / 100 in 3 functions

affects: [49-04, goal-api, goal-frontend-50]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-migration strategy: schema-only (RenameField + AddField + CreateModel) then data-conversion + AlterField avoids PostgreSQL type-cast error"
    - "GoalJournalSelection follows JournalContact pattern: TimeStampedModel + user FK + journal FK + unique_together in Meta"
    - "monthly_support_goal_dollars property on User for convenient dollar access without service layer"

key-files:
  created:
    - apps/users/migrations/0007_goal_fields_schema.py
    - apps/users/migrations/0008_goal_fields_data.py
  modified:
    - apps/users/models.py
    - apps/users/serializers.py
    - apps/users/admin.py
    - apps/dashboard/services.py
    - apps/dashboard/tests/test_services.py
    - apps/users/management/commands/set_missionary_goals.py
    - apps/core/management/commands/create_test_accounts.py
    - apps/core/management/commands/generate_sample_data.py

key-decisions:
  - "Two-migration pattern used: 0007 renames and adds fields (keeping Decimal type), 0008 converts data then AlterField to PositiveBigIntegerField — avoids PostgreSQL type-cast error on direct decimal-to-integer ALTER"
  - "GoalJournalSelection unique_together set in CreateModel options dict (not separate AlterUniqueTogether) for cleaner migration"
  - "TDD stub test files (test_goal_services.py and test_views_goals.py) excluded from this plan's verification — they are intentional RED stubs awaiting Plan 04 implementation"
  - "API response dict keys kept as 'monthly_goal' in dashboard/services.py for backwards API compat — only model field access updated to monthly_support_goal_cents"

patterns-established:
  - "Two-migration split pattern: schema migration (rename/add/create) + data migration (RunPython convert + AlterField)"

requirements-completed: [GOAL-02, GOAL-03, GOAL-11]

# Metrics
duration: 25min
completed: 2026-03-12
---

# Phase 49 Plan 03: Goal Fields Schema Migration Summary

**Django two-migration schema change: DecimalField monthly_goal renamed to PositiveBigIntegerField monthly_support_goal_cents, goal_weeks added, GoalJournalSelection model created with user/journal FK unique_together**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-12T04:10:00Z
- **Completed:** 2026-03-12T04:35:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Migrations 0007 and 0008 applied cleanly: schema first (RenameField, AddField, CreateModel), data conversion second (RunPython + AlterField)
- GoalJournalSelection model created with correct FK references, unique_together, and Meta
- All 5 serializer classes updated to monthly_support_goal_cents; UserUpdateSerializer and CurrentUserSerializer also include goal_weeks
- Three dashboard service functions updated from float(user.monthly_goal) to monthly_support_goal_cents / 100
- All 66 users/dashboard/core tests pass GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Write migrations 0007 (schema) and 0008 (data + type change)** - `5b7b594` (feat)
2. **Task 2: Update User model, serializers, admin, and dashboard service** - `b2ef212` (feat)

## Files Created/Modified
- `apps/users/migrations/0007_goal_fields_schema.py` - RenameField + AddField goal_weeks + CreateModel GoalJournalSelection
- `apps/users/migrations/0008_goal_fields_data.py` - RunPython convert Decimal to cents + AlterField to PositiveBigIntegerField
- `apps/users/models.py` - Updated User fields, monthly_support_goal_dollars property, GoalJournalSelection class
- `apps/users/serializers.py` - monthly_goal renamed in 5 serializers; goal_weeks added to 2
- `apps/users/admin.py` - Role & Permissions fieldset updated
- `apps/dashboard/services.py` - 3 monthly_goal → monthly_support_goal_cents / 100 conversions
- `apps/dashboard/tests/test_services.py` - Factory kwargs updated from monthly_goal to monthly_support_goal_cents
- `apps/users/management/commands/set_missionary_goals.py` - Updated field references and dollar-to-cents conversion
- `apps/core/management/commands/create_test_accounts.py` - Updated defaults dict, removed Decimal import
- `apps/core/management/commands/generate_sample_data.py` - Updated monthly_goal to monthly_support_goal_cents

## Decisions Made
- Two-migration strategy confirmed: 0007 does schema work only (RenameField keeps Decimal type intact), 0008 does data conversion (RunPython) then AlterField. This avoids PostgreSQL's inability to cast Decimal → Integer in a single ALTER.
- GoalJournalSelection unique_together placed directly in CreateModel options dict instead of separate AlterUniqueTogether operation — Django 4+ style, avoids lowercased model name pitfall.
- TDD stub tests excluded from verification scope: test_goal_services.py and test_views_goals.py are intentional RED stubs from Plan 01, awaiting Plan 04 implementation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_services.py factory calls using old monthly_goal kwarg**
- **Found during:** Task 2 (verification run)
- **Issue:** 5 test calls used `monthly_goal=Decimal('...')` which would crash at runtime since field no longer exists on User model
- **Fix:** Updated all 5 calls to `monthly_support_goal_cents=<int_cents>`, removed now-unused Decimal import
- **Files modified:** apps/dashboard/tests/test_services.py
- **Verification:** All dashboard tests pass GREEN
- **Committed in:** b2ef212 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed set_missionary_goals.py management command**
- **Found during:** Task 2 (grep for monthly_goal references)
- **Issue:** Management command used `monthly_goal` in ORM filter and `user.monthly_goal = goal` assignment
- **Fix:** Updated to `monthly_support_goal_cents`, converted dollar goal to cents (goal_dollars * 100)
- **Files modified:** apps/users/management/commands/set_missionary_goals.py
- **Verification:** Code review confirms correct field reference
- **Committed in:** b2ef212 (Task 2 commit)

**3. [Rule 1 - Bug] Fixed create_test_accounts.py management command**
- **Found during:** Task 2 (grep for monthly_goal references)
- **Issue:** get_or_create defaults dict used `'monthly_goal': goal` with Decimal values
- **Fix:** Changed to `'monthly_support_goal_cents': goal_cents` with pre-converted integer cents, removed Decimal import
- **Files modified:** apps/core/management/commands/create_test_accounts.py
- **Verification:** Code review confirms correct field reference
- **Committed in:** b2ef212 (Task 2 commit)

**4. [Rule 1 - Bug] Fixed generate_sample_data.py management command**
- **Found during:** Task 2 (grep for monthly_goal references)
- **Issue:** get_or_create defaults dict used `'monthly_goal': Decimal('5000.00')`
- **Fix:** Changed to `'monthly_support_goal_cents': 500000`, removed now-unused Decimal import
- **Files modified:** apps/core/management/commands/generate_sample_data.py
- **Verification:** Code review confirms correct field reference
- **Committed in:** b2ef212 (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (all Rule 1 - Bug)
**Impact on plan:** All auto-fixes necessary for correctness — stale field references would crash at runtime. No scope creep.

## Issues Encountered
- TDD stub test files (test_goal_services.py, test_views_goals.py) fail as expected — they import/call modules/endpoints that don't exist yet (Plan 04's work). These were excluded from the verification scope per Plan 01's design intent.

## Next Phase Readiness
- Plan 04 (goal service + API) is unblocked: User.monthly_support_goal_cents, goal_weeks, and GoalJournalSelection model all exist
- GoalJournalSelection API (list/set journal selections) can be built immediately
- TDD stubs (test_goal_services.py, test_views_goals.py) are ready to go GREEN in Plan 04

---
*Phase: 49-goal-page-data-model-backend*
*Completed: 2026-03-12*
