---
phase: 46-multiple-supervisors-per-missionary
verified: 2026-03-07T12:00:00Z
status: passed
score: 16/16 must-haves verified
re_verification:
  previous_status: passed (initial — pre-UAT)
  previous_score: 12/12
  gaps_closed:
    - "AssignmentsView GET returns only supervisor_ids for users with role=supervisor and is_active=True"
    - "AssignmentsView GET returns only coach_ids for users with role=coach and is_active=True"
    - "Ghost M2M rows (role-changed users in junction table) are removable via management command"
    - "Running the cleanup command removes all junction rows where the referenced user no longer holds the expected role"
  gaps_remaining: []
  regressions: []
gaps: []
human_verification:
  - test: "Navigate to /admin/assignments and confirm multi-select chip UI renders"
    expected: "Each missionary row shows Popover+Command cells for Supervisor and Coach with chip badges; View mode toggle shows 'By Missionary' and 'By Supervisor' buttons"
    why_human: "Visual/interactive React component — cannot verify rendering from static file analysis"
  - test: "Assign 2+ supervisors to one missionary and save, then reload the page"
    expected: "Both supervisors persist and appear as chips; GET response shows both IDs in supervisor_ids array"
    why_human: "End-to-end data persistence through the full stack (DB, API, UI) cannot be verified programmatically without running the app"
  - test: "Assign 5+ supervisors to a single missionary"
    expected: "A warning toast appears in the UI; backend PATCH response includes a 'warnings' entry"
    why_human: "Toast display requires running browser"
---

# Phase 46: Multiple Supervisors per Missionary — Verification Report

**Phase Goal:** Convert supervisor and coach relationships from ForeignKey to ManyToMany so each missionary can have multiple supervisors and coaches; update assignment UI with multi-select chips and a supervisor view toggle

**Verified:** 2026-03-07

**Status:** PASSED

**Re-verification:** Yes — after UAT gap closure (Plan 06). Previous verification was initial (pre-UAT) with score 12/12. UAT test #9 found a ghost-supervisor bug; Plan 06 closed that gap. This re-verification covers Plan 06 artifacts plus regression checks on all previously verified items.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User model has `supervisors` and `coaches` as ManyToManyFields (not ForeignKey) | VERIFIED | `apps/users/models.py`: `ManyToManyField('self', symmetrical=False, blank=True)` x2 |
| 2 | Migration `0006_m2m_supervisors` exists, data-preserving, applied to DB | VERIFIED | File exists; `showmigrations` shows `[X] 0006_m2m_supervisors` |
| 3 | `related_name` preserved (`supervised_users`, `coached_users`) — permission code works | VERIFIED | `apps/core/permissions.py` `get_visible_user_ids()` uses `user.supervised_users.filter(...)` unchanged |
| 4 | Auto-clear M2M on role change — switching away from supervisor clears `supervised_users` | VERIFIED | `User.save()` override queries old role, calls `.supervised_users.clear()` on role change |
| 5 | All 10 active tests in `test_m2m_assignments.py` pass GREEN | VERIFIED | `pytest apps/users/tests/test_m2m_assignments.py` — 10 passed, 1 skipped |
| 6 | `AssignmentsView` GET returns only `supervisor_ids` for role=supervisor AND is_active=True | VERIFIED | `views_assignments.py` line 37: `m.supervisors.filter(role='supervisor', is_active=True)` |
| 7 | `AssignmentsView` GET returns only `coach_ids` for role=coach AND is_active=True | VERIFIED | `views_assignments.py` line 38: `m.coaches.filter(role='coach', is_active=True)` |
| 8 | Ghost M2M rows (stale role-changed users) do NOT appear in GET supervisor/coach lists | VERIFIED | `TestAssignmentsViewRoleFilter::test_ghost_supervisor_excluded_from_get` PASSES; `test_ghost_coach_excluded_from_get` PASSES |
| 9 | `AssignmentsView` PATCH accepts `supervisor_ids[]` list and `additive` flag; uses `.set()` or `.add()` | VERIFIED | `views_assignments.py` lines 68-95: reads `supervisor_ids` list, `additive` flag, calls `.add(*...)` or `.set(...)` |
| 10 | `UserSerializer` exposes `supervisor_ids` and `coach_ids` as string arrays | VERIFIED | `serializers.py` lines 17-24: `SerializerMethodField` returning `[str(s.id) for s in obj.supervisors.all()]` |
| 11 | `frontend/src/api/users.ts` interfaces updated to M2M arrays | VERIFIED | `MissionaryAssignment` has `supervisor_ids: string[]`, `coach_ids: string[]`; `User` has same |
| 12 | `AdminAssignments.tsx` uses Popover+Command multi-select chips, view toggle, additive bulk apply | VERIFIED | 714-line component with `viewMode` state, Popover/Command/Badge/Check/X imports, `bulkDirty` Set |
| 13 | `AdminUsers.tsx` reads from `supervisor_ids`/`coach_ids` arrays — no scalar FK assumptions | VERIFIED | Lines 138, 143: `u.supervisor_ids?.includes(user.id)` |
| 14 | Ghost M2M junction rows are removable via management command | VERIFIED | `purge_ghost_assignments.py` exists; dry-run runs cleanly; reports `Would remove 0 ghost supervisor row(s)` on live DB |
| 15 | Management command supports `--dry-run` flag | VERIFIED | `add_arguments` registers `--dry-run` store_true; `handle` branches on `dry_run` option |
| 16 | TypeScript compilation clean — no errors in frontend | VERIFIED | `npx tsc --noEmit` produced zero errors in initial verification; no TS files changed in Plan 06 |

**Score:** 16/16 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/users/models.py` | M2M supervisor/coach fields + `User.save()` auto-clear | VERIFIED | ManyToManyField x2; save override clears M2M on role change |
| `apps/users/migrations/0006_m2m_supervisors.py` | AddField x2, RunPython data migration, RemoveField x2 | VERIFIED | Applied `[X]` in DB |
| `apps/users/views_assignments.py` | M2M GET with role+active filter + PATCH additive flag + warnings | VERIFIED | Line 37: `.filter(role='supervisor', is_active=True)`; line 38: `.filter(role='coach', is_active=True)`; lines 68-104: PATCH with warnings |
| `apps/users/management/__init__.py` | Package init | VERIFIED | File exists |
| `apps/users/management/commands/__init__.py` | Package init | VERIFIED | File exists |
| `apps/users/management/commands/purge_ghost_assignments.py` | Management command: `--dry-run`, removes ghost rows, success output | VERIFIED | 69 lines; `Command` class; `add_arguments` + `handle`; `supervisors.remove()` + `coaches.remove()` present |
| `apps/users/tests/test_m2m_assignments.py` | 4 test classes, 10 active tests + 1 skipped migration test | VERIFIED | `TestM2MModelBehaviors` + `TestAssignmentsViewM2M` + `TestAutoUnassignOnRoleChange` + `TestAssignmentsViewRoleFilter`; 10 passed, 1 skipped |
| `apps/users/tests/factories.py` | `SupervisorUserFactory` and `CoachUserFactory` | VERIFIED | Lines 44-53; role override factories |
| `apps/users/serializers.py` | `supervisor_ids`/`coach_ids` SerializerMethodFields; no scalar FK fields | VERIFIED | Lines 17-24; Meta.fields clean |
| `frontend/src/api/users.ts` | M2M array interfaces for all 3 types | VERIFIED | Lines 21-22, 62-63, 74-76 |
| `frontend/src/pages/admin/AdminAssignments.tsx` | Multi-select chips, view toggle, additive bulk apply | VERIFIED | 714 lines; all patterns present |
| `frontend/src/pages/admin/AdminUsers.tsx` | Array-includes patterns; "Currently Assigned Missionaries" section | VERIFIED | Lines 138, 143, 382, 387, 493, 583 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `0006_m2m_supervisors.py` | `models.py` | Django migration AddField | VERIFIED | Applied to DB; M2M managers created |
| `permissions.py` | `models.py` | `supervised_users` reverse M2M manager | VERIFIED | `user.supervised_users.filter(is_active=True)` — works identically on M2M reverse |
| `views_assignments.py` | `User M2M junction table` | `m.supervisors.filter(role='supervisor', is_active=True)` | VERIFIED | Line 37 confirmed; role+active guard applied |
| `views_assignments.py` | `User M2M junction table` | `m.coaches.filter(role='coach', is_active=True)` | VERIFIED | Line 38 confirmed |
| `views_assignments.py` | `models.py` | `prefetch_related('supervisors', 'coaches')` + `.set()`/`.add()` | VERIFIED | Line 17: prefetch; lines 78-80: add/set |
| `purge_ghost_assignments.py` | `User M2M junction table` | `missionary.supervisors.remove()` for ghost users | VERIFIED | Lines 39, 54: `.remove(*ghost_sups)` and `.remove(*ghost_coaches)` |
| `serializers.py` | `models.py` | `obj.supervisors.all()` / `obj.coaches.all()` | VERIFIED | Lines 21, 24 |
| `AdminAssignments.tsx` | `api/users.ts` | `AssignmentUpdate` type import | VERIFIED | Line 24 of component |
| `AdminAssignments.tsx` | `hooks/useUsers.ts` | `useAssignments`, `useUpdateAssignments` | VERIFIED | Line 5 of component |
| `AdminUsers.tsx` | `api/users.ts` | `User.supervisor_ids` / `User.coach_ids` arrays | VERIFIED | Lines 138, 143 |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SUPV-01 | 46-01, 46-02 | Mission Supervisor role exists in the system (UserRole choice + migration) | SATISFIED | `UserRole.SUPERVISOR` in `models.py`; `SupervisorUserFactory` in factories; M2M migration completed |
| SUPV-02 | 46-01, 46-02, 46-03, 46-04, 46-05, 46-06 | Admin can assign missionaries to a supervisor via management UI | SATISFIED | `AssignmentsView` PATCH with M2M arrays; `AdminAssignments.tsx` multi-select chips; role-filtered GET prevents ghost supervisors from appearing in the UI |
| SUPV-03 | 46-01, 46-03 | Supervisor sees only their assigned missionaries' data across all pages | SATISFIED | `get_visible_user_ids()` in `permissions.py` uses M2M reverse manager `supervised_users`; `test_get_visible_user_ids_returns_missionary_for_both_supervisors` PASSES |

No orphaned requirements. SUPV-01/02/03 were originally completed in Phase 42 (scalar FK); Phase 46 upgrades the implementation to M2M. All three are satisfied at a higher capability level.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | None |

Scanned files (Plan 06): `apps/users/views_assignments.py`, `apps/users/management/commands/purge_ghost_assignments.py`, `apps/users/tests/test_m2m_assignments.py`. No placeholders, TODOs, empty returns, or stub handlers.

---

### Human Verification Required

#### 1. Multi-Select Chip UI Renders Correctly

**Test:** Navigate to `/admin/assignments` in a running instance
**Expected:** Each missionary row shows Popover+Command multi-select cells for Supervisor and Coach columns; selected supervisors/coaches appear as Badge chips with X remove buttons; "By Missionary" and "By Supervisor" toggle buttons appear above the table
**Why human:** React component rendering and interactive Popover state cannot be verified from static file analysis

#### 2. Multi-Supervisor Persistence End-to-End

**Test:** Assign two different supervisors to one missionary via the chip UI, click Save, then reload the page
**Expected:** Both supervisors persist and both chips appear after page reload; the API GET response shows both IDs in `supervisor_ids[]`
**Why human:** Requires running application with database; full-stack persistence test

#### 3. Soft Warning Toast at 5+ Supervisors

**Test:** Assign 5 or more supervisors to a single missionary
**Expected:** A warning toast fires in the UI; the PATCH response body includes a `warnings` array entry for that missionary
**Why human:** Toast rendering requires live browser; backend warning logic verified by code inspection

---

### Re-Verification: Gap Closure Summary

**UAT gap #9 was the only failing item.** Root cause: `views_assignments.py` called `m.supervisors.all()` with no role filter, so any user ID in the M2M junction table appeared in `supervisor_ids` regardless of current role. Ghost rows were created by migration 0006 copying FK data without validating that the referenced user still held the supervisor role.

**Plan 06 closed all 4 gaps defined in the plan frontmatter:**

1. `views_assignments.py` line 37 changed from `.supervisors.all()` to `.supervisors.filter(role='supervisor', is_active=True)` — ghost IDs no longer returned.
2. `views_assignments.py` line 38 changed from `.coaches.all()` to `.coaches.filter(role='coach', is_active=True)` — same for coaches.
3. `TestAssignmentsViewRoleFilter` added with 4 regression tests (ghost supervisor excluded, ghost coach excluded, active supervisor included, inactive supervisor excluded) — all 4 PASS.
4. `purge_ghost_assignments` management command created — supports `--dry-run`; runs on live DB reporting 0 ghost rows.

**No regressions.** All 10 previously passing tests continue to pass (test count grew from 6 at initial verification to 10 post-Plan 06).

**Commits verified (Plan 06):** `1279fae` (RED tests), `6df1b81` (GREEN fix), `a068204` (management command), `3adcbd7` (summary/state) — all 4 present in git history.

---

_Verified: 2026-03-07_
_Verifier: Claude (gsd-verifier)_
_Re-verification after UAT gap closure (Plan 06)_
