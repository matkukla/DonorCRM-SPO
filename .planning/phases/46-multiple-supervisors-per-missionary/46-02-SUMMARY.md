---
phase: 46-multiple-supervisors-per-missionary
plan: 02
subsystem: database
tags: [django, m2m, migrations, users, supervisor, coach]

# Dependency graph
requires:
  - phase: 46-01
    provides: RED tests (TestM2MModelBehaviors, TestAssignmentsViewM2M) establishing behavioral contract for M2M fields

provides:
  - User model with supervisors/coaches as ManyToManyField (symmetrical=False)
  - Migration 0006_m2m_supervisors.py: AddField x2, RunPython copy_fk_to_m2m, RemoveField x2
  - Updated AssignmentsView GET (supervisor_ids/coach_ids as lists) and PATCH (additive flag, M2M operations)
  - Updated serializers removing stale FK field references

affects: [46-03, 46-04, 46-05, apps/users/views_assignments.py, apps/users/serializers.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "M2M self-referencing with symmetrical=False preserves reverse related_name — all existing queryset code unchanged"
    - "RunPython BEFORE RemoveField: copy FK data while FK columns still exist, then drop them"
    - "prefetch_related replaces select_related for M2M traversal in querysets"
    - "M2M .set() replaces bulk .update(fk_field=) for assignment operations"

key-files:
  created:
    - apps/users/migrations/0006_m2m_supervisors.py
  modified:
    - apps/users/models.py
    - apps/users/serializers.py
    - apps/users/views_assignments.py

key-decisions:
  - "supervisors/coaches M2M field names are plural; related_names supervised_users/coached_users kept identical — all existing code in permissions.py unchanged"
  - "Migration uses RunPython copy_fk_to_m2m BEFORE RemoveField to preserve historical FK assignments"
  - "AssignmentsView PATCH updated to accept supervisor_ids list + additive flag (not scalar supervisor_id) as part of auto-fix"
  - "UserSerializer fields list: removed supervisor and coach_id (stale FK) since M2M assignment is done via AssignmentsView"

patterns-established:
  - "M2M auto-fix pattern: replace select_related(FK) with prefetch_related(M2M) in querysets"
  - "M2M auto-fix pattern: replace .update(fk=instance) with .set(queryset) for assignment operations"

requirements-completed: [SUPV-01, SUPV-02]

# Metrics
duration: 9min
completed: 2026-03-08
---

# Phase 46 Plan 02: Multiple Supervisors — M2M Schema Migration Summary

**User model supervisor/coach converted from ForeignKey to ManyToManyField with data-preserving migration and stale FK reference auto-fixes in serializers and views**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-03-08T04:49:31Z
- **Completed:** 2026-03-08T04:58:07Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Replaced `supervisor` FK and `coach` FK with `supervisors` M2M and `coaches` M2M (symmetrical=False, same related_names) — all existing permissions.py queryset code unchanged
- Created migration 0006_m2m_supervisors.py with exact operation order: AddField x2, RunPython copy_fk_to_m2m, RemoveField x2 — applied cleanly
- Auto-fixed 5 stale FK references across views_assignments.py and serializers.py that would have caused runtime crashes

## Task Commits

Each task was committed atomically:

1. **Task 1: Update User model — replace FK fields with ManyToManyFields** - `b389759` (feat)
2. **Task 2: Create migration + auto-fix stale FK references** - `fd47495` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `apps/users/models.py` - supervisor/coach ForeignKey replaced with supervisors/coaches ManyToManyField
- `apps/users/migrations/0006_m2m_supervisors.py` - data-preserving migration (AddField x2, RunPython, RemoveField x2)
- `apps/users/views_assignments.py` - select_related removed; GET uses supervisor_ids/coach_ids lists; PATCH uses M2M .add()/.set() with additive flag
- `apps/users/serializers.py` - UserSerializer: removed stale supervisor/coach_id fields; UserAdminUpdateSerializer.update() uses M2M .set()

## Decisions Made

- `supervisors`/`coaches` field names are plural (M2M convention); `related_name='supervised_users'`/`'coached_users'` kept identical so `permissions.py` and all view queryset code work unchanged
- Migration uses `RunPython copy_fk_to_m2m` BEFORE `RemoveField` — critical ordering to preserve existing FK data
- `AssignmentsView` PATCH extended to accept `supervisor_ids` (list) and `additive` flag as part of auto-fix (full API migration is Plan 03 scope, but the crash-preventing fix was needed here)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] select_related('supervisor', 'coach') in AssignmentsView caused FieldError**
- **Found during:** Task 2 (running pytest apps/users/tests/)
- **Issue:** `views_assignments.py` had `select_related('supervisor', 'coach')` — after FK removal, Django raised `FieldError: Invalid field name(s) given in select_related`
- **Fix:** Replaced with `prefetch_related('supervisors', 'coaches')`; updated GET response to use `supervisor_ids`/`coach_ids` list fields from M2M; updated PATCH to use M2M `.add()`/`.set()` with additive flag
- **Files modified:** `apps/users/views_assignments.py`
- **Verification:** `pytest apps/users/tests/test_m2m_assignments.py::TestAssignmentsViewM2M` — 3/3 view tests now pass
- **Committed in:** fd47495 (Task 2 commit)

**2. [Rule 1 - Bug] UserSerializer referenced removed supervisor and coach_id FK fields**
- **Found during:** Task 2 (running pytest apps/users/tests/)
- **Issue:** `ImproperlyConfigured: Field name 'supervisor' is not valid for model User in UserSerializer`
- **Fix:** Removed `'supervisor'` and `'coach_id'` from UserSerializer fields list
- **Files modified:** `apps/users/serializers.py`
- **Verification:** `pytest apps/users/tests/test_views.py::TestUserListView::test_admin_can_list_users` passes
- **Committed in:** fd47495 (Task 2 commit)

**3. [Rule 1 - Bug] UserAdminUpdateSerializer.update() used .update(supervisor=None) on M2M reverse manager**
- **Found during:** Task 2 (code review while fixing serializer)
- **Issue:** `instance.supervised_users.update(supervisor=None)` — M2M reverse managers don't support .update() with FK field names
- **Fix:** Replaced with `instance.supervised_users.set(supervised_users)` using M2M .set() semantics
- **Files modified:** `apps/users/serializers.py`
- **Verification:** Django system check passes; no runtime errors
- **Committed in:** fd47495 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — existing code referencing removed FK fields)
**Impact on plan:** All auto-fixes were direct consequences of removing the FK fields. No scope creep — view/serializer changes are minimal crash-prevention updates.

## Issues Encountered

Two pre-existing test failures were confirmed as out-of-scope:
- `test_role_properties` — tests `is_staff_role` property that doesn't exist in the model (pre-existing)
- `test_admin_can_create_user` — sends `role: 'staff'` which is not a valid role (old role name, pre-existing)

Both failed before Plan 02 changes and remain in deferred-items scope.

## Next Phase Readiness

- M2M schema foundation is complete — Plan 03 can now build the full AssignmentsView API (supervisor_ids list read/write, auto-unassign on role change signal)
- `TestM2MModelBehaviors`: 2/2 GREEN
- `TestAssignmentsViewM2M`: 3/3 GREEN (view shape now matches expected M2M API)
- `TestAutoUnassignOnRoleChange`: 1/1 RED (Plan 03 responsibility)
- `manage.py check` passes with no errors
- Migration 0006_m2m_supervisors [X] applied

---
*Phase: 46-multiple-supervisors-per-missionary*
*Completed: 2026-03-08*
