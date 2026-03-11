---
phase: 47-fix-coach-role-gaps
verified: 2026-03-10T15:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 47: Fix Coach Role Gaps — Verification Report

**Phase Goal:** Close critical v2.2 audit gaps — coach users can access contacts they are assigned to, test suite passes with correct role names, and coach assignments via AdminUsers page are persisted.
**Verified:** 2026-03-10T15:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                         | Status     | Evidence                                                                                 |
|----|-----------------------------------------------------------------------------------------------|------------|------------------------------------------------------------------------------------------|
| 1  | All four test files use role='missionary' (not role='staff') for non-coach test users         | VERIFIED   | grep confirms zero role='staff' in target files; all 24 Plan 01 tests pass               |
| 2  | Full test suite passes with zero role='staff' failures in the four target files               | VERIFIED   | `24 passed` for conftest.py, test_spo_views.py, test_spo_csv_fixture_mapping.py, test_user_drilldown.py |
| 3  | Insight user-drilldown role assertion checks 'missionary', not 'staff'                        | VERIFIED   | apps/insights/tests/test_user_drilldown.py line 171: `assertEqual(response.data['user']['role'], 'missionary')` |
| 4  | Coach GET /api/v1/contacts/ returns 200 (not 403)                                             | VERIFIED   | TestCoachContactAccess::test_coach_can_list_contacts passes (3/3 coach tests green)       |
| 5  | Coach GET /api/v1/contacts/?owner=<missionary_id> returns 200 with scoped results             | VERIFIED   | TestCoachContactAccess::test_coach_contact_list_scoped_to_missionaries passes             |
| 6  | Admin PATCH with coached_user_ids=[id1] persists the M2M relationship                        | VERIFIED   | TestCoachAssignment::test_admin_can_set_coached_user_ids passes; M2M checked via refresh_from_db |
| 7  | Coach cannot POST/PATCH/DELETE contacts (write operations still return 403)                   | VERIFIED   | TestCoachContactAccess::test_coach_cannot_create_contact passes                           |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact                                                  | Expected                                    | Status   | Details                                                                              |
|-----------------------------------------------------------|---------------------------------------------|----------|--------------------------------------------------------------------------------------|
| `conftest.py`                                             | authenticated_client with role='missionary' | VERIFIED | Line 25: `user_factory(role='missionary')`; also adds admin_user, missionary_user, coach_user fixtures |
| `apps/imports/tests/test_spo_views.py`                    | _make_staff() with role='missionary'        | VERIFIED | Line 74: `role='missionary'`                                                         |
| `apps/imports/tests/test_spo_csv_fixture_mapping.py`      | _make_staff_owner() with role='missionary'  | VERIFIED | Line 40: `role='missionary'`                                                         |
| `apps/insights/tests/test_user_drilldown.py`              | assertEqual uses 'missionary'               | VERIFIED | Line 171: `assertEqual(response.data['user']['role'], 'missionary')`                 |
| `apps/core/permissions.py`                                | IsStaffOrAbove with coach safe-method gate  | VERIFIED | Line 86: `if request.user.role in ['read_only', 'coach']:` — coach NOT in write-allowed list |
| `apps/contacts/tests/test_integration.py`                 | TestCoachContactAccess class (ROLE-03/05)   | VERIFIED | Class exists at line 276 with 3 test methods; all pass                               |
| `apps/users/tests/test_views.py`                          | TestCoachAssignment with coached_user_ids   | VERIFIED | TestCoachAssignment class at line 165; test_admin_can_set_coached_user_ids passes     |

---

### Key Link Verification

| From                                           | To                              | Via                                      | Status   | Details                                                                         |
|------------------------------------------------|---------------------------------|------------------------------------------|----------|---------------------------------------------------------------------------------|
| `conftest.py`                                  | UserFactory                     | role='missionary'                        | WIRED    | Line 25 uses UserFactory with role='missionary'                                  |
| `apps/insights/tests/test_user_drilldown.py`   | user role assertion              | assertEqual                              | WIRED    | Line 171: `assertEqual(response.data['user']['role'], 'missionary')`            |
| `apps/core/permissions.py`                     | IsStaffOrAbove.has_permission   | coach in SAFE_METHODS guard              | WIRED    | Line 86: `in ['read_only', 'coach']`; coach absent from write-allowed line 89    |
| `apps/contacts/tests/test_integration.py`      | ContactListCreateView            | GET /api/v1/contacts/                    | WIRED    | test_coach_can_list_contacts hits live endpoint; passes with 200                 |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                               | Status    | Evidence                                                                               |
|-------------|-------------|-------------------------------------------------------------------------------------------|-----------|----------------------------------------------------------------------------------------|
| ROLE-01     | 47-01       | DB and UI use `missionary` (not `staff`) everywhere; test suite passes with correct names | SATISFIED | Four files corrected; 24 tests pass; zero role='staff' in target files                 |
| ROLE-03     | 47-02       | Coach users can access contacts for their assigned missionaries (no 403)                  | SATISFIED | TestCoachContactAccess::test_coach_can_list_contacts passes (200)                      |
| ROLE-04     | 47-02       | Admin can assign coaches to missionaries via AdminUsers page (coached_user_ids persisted) | SATISFIED | TestCoachAssignment::test_admin_can_set_coached_user_ids passes; M2M verified          |
| ROLE-05     | 47-02       | /team/:userId Contacts tab works for coach users                                          | SATISFIED | TestCoachContactAccess::test_coach_contact_list_scoped_to_missionaries passes (200)    |

**Orphaned requirements check:** REQUIREMENTS.md maps ROLE-01 through ROLE-05 to Phase 47. ROLE-02 (Coach role exists in UserRole + migration) was completed in Phase 43 and is not claimed by Phase 47 plans — correctly orphaned to its origin phase. No unaccounted requirements for Phase 47.

---

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments or empty implementations detected in any phase-modified file.

---

### Human Verification Required

**1. AdminUsers Page — Coach Assignment UI**

- **Test:** Log in as admin, navigate to /admin/users, select a coach user, assign missionaries via the coached_user_ids UI control, save, then reload and confirm the assignments persist.
- **Expected:** Missionaries appear in the coach's assignment list after page reload.
- **Why human:** The backend PATCH and M2M persistence are test-verified, but the frontend AdminUsers page UI rendering and form submission wiring require manual confirmation.

**2. /team/:userId Contacts Tab for Coach**

- **Test:** Log in as a coach user, navigate to /team/<missionary_id>/contacts where that missionary is in the coach's coached_users set. Confirm the tab loads contacts without a 403 or blank state.
- **Expected:** Contacts owned by the coached missionary are visible; contacts outside the scope are not shown.
- **Why human:** Scoping correctness at data level is test-verified, but the frontend route and tab rendering are not covered by backend tests.

---

### Commits Verified

| Commit  | Description                                               | Verified |
|---------|-----------------------------------------------------------|----------|
| b8b95cf | fix(47-01): replace stale role='staff' in test fixtures   | Yes — exists in git log |
| 484c7b1 | test(47-02): add failing tests for ROLE-03/04/05 (RED)    | Yes — exists in git log |
| a2b16d1 | fix(47-02): allow coach safe-method access in IsStaffOrAbove | Yes — exists in git log |

---

### Gaps Summary

No gaps. All seven must-have truths verified against actual code. All four requirement IDs satisfied with passing tests. Permission fix is surgically correct — 'coach' appears only in the SAFE_METHODS guard (line 86), not in the write-allowed role list (line 89). The broader contacts + users test suite runs 53 passed, 1 skipped with zero failures.

---

_Verified: 2026-03-10T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
