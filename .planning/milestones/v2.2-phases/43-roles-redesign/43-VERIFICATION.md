---
phase: 43-roles-redesign
verified: 2026-03-04T00:00:00Z
status: passed
score: 5/5 success criteria verified (gaps fixed post-verification)
gaps:
  - truth: "DB and UI use `missionary` (not `staff`) and `supervisor` (not `mission_supervisor`) everywhere"
    status: partial
    reason: "Production model/permissions/views fully updated. But apps/users/managers.py line 55 still has role='staff' in staff_users(), and generate_sample_data.py line 97 references UserRole.STAFF which no longer exists (AttributeError at runtime). Test files also reference UserRole.STAFF causing test failures."
    artifacts:
      - path: "apps/users/managers.py"
        issue: "Line 55: role='staff' in staff_users() method — stale string, method appears unused but is semantically incorrect"
      - path: "apps/core/management/commands/generate_sample_data.py"
        issue: "Line 97: UserRole.STAFF no longer exists — AttributeError when running generate_sample_data command"
      - path: "apps/users/tests/test_models.py"
        issue: "References UserRole.STAFF — test suite will fail with AttributeError"
      - path: "apps/imports/tests/test_generic_imports.py"
        issue: "References UserRole.STAFF — test suite will fail with AttributeError"
    missing:
      - "Update managers.py staff_users() to use role='missionary' (or rename the method)"
      - "Update generate_sample_data.py: UserRole.STAFF → UserRole.MISSIONARY and update email/description"
      - "Update all test files: UserRole.STAFF → UserRole.MISSIONARY"
  - truth: "Admin can assign both a supervisor and a coach to each missionary via /admin/assignments"
    status: partial
    reason: "The primary /admin/assignments page uses AssignmentsView (GET/PATCH) which correctly handles both supervisor and coach assignments. However, UserAdminUpdateSerializer does NOT handle coached_user_ids — the AdminUsers page sends coached_user_ids via updateUser() but the backend silently ignores it, so coach assignment via AdminUsers page does not persist. The critical path (Assignments page) works correctly."
    artifacts:
      - path: "apps/users/serializers.py"
        issue: "UserAdminUpdateSerializer only handles supervised_user_ids — coached_user_ids field is absent from fields list and update() method, so PATCH /users/{id}/ ignores coached_user_ids"
    missing:
      - "Add coached_user_ids to UserAdminUpdateSerializer fields and implement update logic mirroring supervised_user_ids handling"
human_verification:
  - test: "Log in as supervisor, navigate to /team"
    expected: "My Team page shows assigned missionaries, subtitle says 'Missionaries under your supervision'"
    why_human: "supervised_users data comes from auth context — cannot verify rendering without browser"
  - test: "Log in as coach, navigate to /team"
    expected: "My Team page shows assigned coachees, subtitle says 'Your coachees'"
    why_human: "Coach-specific subtitle requires actual coach user in system"
  - test: "Log in as coach, open a missionary profile at /team/:userId"
    expected: "Profile shows Contacts/Journals/Tasks tabs but NOT Donations tab"
    why_human: "Tab visibility conditioned on role — requires live session to verify"
  - test: "Log in as admin, navigate to /admin/assignments, change a supervisor dropdown"
    expected: "Row shows dirty indicator (amber dot), Save button shows count, saving sends only dirty rows"
    why_human: "UI state interactions require browser"
---

# Phase 43: Roles Redesign Verification Report

**Phase Goal:** Rename roles to clearer names, add Coach role with limited visibility, and provide admin tools for managing assignments alongside supervisor/coach team views
**Verified:** 2026-03-04
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Success Criteria (from ROADMAP.md)

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | DB and UI use `missionary` (not `staff`) and `supervisor` (not `mission_supervisor`) everywhere | PARTIAL | Model, permissions, all prod views updated. But managers.py line 55 still has `'staff'`, generate_sample_data.py has `UserRole.STAFF` (AttributeError), and multiple test files reference `UserRole.STAFF` |
| 2 | Admin can assign both a supervisor and a coach to each missionary via `/admin/assignments` | PARTIAL | `AssignmentsView` GET/PATCH works correctly. `AdminAssignments.tsx` is fully built. But `UserAdminUpdateSerializer` lacks `coached_user_ids`, so the AdminUsers page coach assignment path silently fails |
| 3 | Coach role sees contacts + journals for assigned missionaries, but NOT gifts/pledges/donations | VERIFIED | `gifts/views.py` returns `Gift.objects.none()` for coach (lines 39, 69, 103, 134). `gifts/export_views.py` returns 403 for coach (lines 31, 93). `insights/views.py` uses `is_financial_role()` guard (lines 59, 79, 93, 112). `get_visible_user_ids()` has coach branch |
| 4 | Supervisors and coaches see a `/team` page listing their assigned missionaries | VERIFIED | `TeamPage.tsx` exists at `frontend/src/pages/team/TeamPage.tsx` with full search, table, and "View Profile" link. Sidebar has `My Team` with `visibleRoles: ["supervisor", "coach"]`. Route `/team` registered in `App.tsx` |
| 5 | Clicking a missionary on the team page opens a read-only profile with tabbed content | VERIFIED | `MissionaryProfilePage.tsx` exists with Contacts/Journals/Tasks/Donations tabs. Coach branch hides Donations tab. Authorization guard shows 403 state when userId not in supervised_users |

**Score:** 3/5 truths fully verified, 2/5 partially verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/users/migrations/0005_roles_redesign.py` | DB migration: rename roles, add coach FK | VERIFIED | RunPython data migration → AlterField (new choices) → AddField coach FK — correct order |
| `apps/users/models.py` | Updated UserRole enum, coach FK, is_coach property | VERIFIED | `MISSIONARY`, `SUPERVISOR`, `COACH` choices; coach FK with `coached_users` related_name; `is_coach` property; `can_view_contact()` has coach branch |
| `apps/core/permissions.py` | get_visible_user_ids coach branch, is_financial_role helper | VERIFIED | Coach branch (lines 38-45) returns own + coached user IDs. `is_financial_role()` defined, excludes coach |
| `apps/gifts/views.py` | Coach returns empty queryset | VERIFIED | All 4 gift views return `none()` for coach role |
| `apps/gifts/export_views.py` | Coach blocked from exports | VERIFIED | Returns 403 for coach at lines 31, 93 |
| `apps/insights/views.py` | Financial views gated by is_financial_role | VERIFIED | `is_financial_role` check at lines 59, 79, 93, 112 |
| `apps/users/views_assignments.py` | Assignments GET/PATCH API | VERIFIED | Full implementation with GET (missionaries/supervisors/coaches) and PATCH (batch update with validation) |
| `apps/users/urls.py` | `/admin/assignments/` URL registered | VERIFIED | Line 20: `path('admin/assignments/', AssignmentsView.as_view(), ...)` |
| `apps/users/serializers.py` | CurrentUserSerializer handles coach via coached_users | VERIFIED | `get_supervised_users()` branches on supervisor vs coach (lines 186-197) |
| `apps/users/serializers.py` | UserAdminUpdateSerializer handles coached_user_ids | STUB | Field absent from `fields` list — backend silently drops `coached_user_ids` when PATCH /users/{id}/ is called |
| `apps/users/managers.py` | Updated role strings | STUB | Line 55: `staff_users()` still uses `role='staff'` — stale string |
| `apps/core/management/commands/generate_sample_data.py` | Updated to use UserRole.MISSIONARY | MISSING | Line 97: `UserRole.STAFF` → AttributeError at runtime |
| `frontend/src/api/users.ts` | Updated types, assignment API functions | VERIFIED | `UserRole` union has missionary/supervisor/coach; `MissionaryAssignment`, `AssignmentsData`, `AssignmentUpdate` interfaces; `getAssignments()`, `updateAssignments()` functions |
| `frontend/src/api/auth.ts` | Updated role union | VERIFIED | Role union includes "missionary", "supervisor", "coach" (line 18) |
| `frontend/src/hooks/useUsers.ts` | useAssignments, useUpdateAssignments hooks | VERIFIED | Both hooks present (lines 62-77), wired to API functions |
| `frontend/src/components/auth/ProtectedRoute.tsx` | Updated roleHierarchy | NOT VERIFIED | Not directly read — inferred from App.tsx using correct role strings |
| `frontend/src/components/layout/Sidebar.tsx` | My Team nav, visibleRoles, updated roleHierarchy | VERIFIED | "My Team" item (line 44) with `visibleRoles: ["supervisor", "coach"]`; roleHierarchy has coach at 3 |
| `frontend/src/App.tsx` | Routes for /admin/assignments, /team, /team/:userId | VERIFIED | Lines 137, 142, 143 register all three routes with correct guards |
| `frontend/src/pages/admin/AdminAssignments.tsx` | Inline table, dirty tracking, bulk ops, search | VERIFIED | Full implementation: Map-based local state, dirty Set, bulk supervisor/coach apply, search filter, save with diff |
| `frontend/src/pages/team/TeamPage.tsx` | Team list with search and profile links | VERIFIED | Full implementation using `user.supervised_users`, search filter, role-conditional subtitle |
| `frontend/src/pages/team/MissionaryProfilePage.tsx` | Tabbed read-only profile, coach-aware | VERIFIED | Contacts/Journals/Tasks/Donations tabs; coach hides Donations; 403 guard for non-assigned users |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `AdminAssignments.tsx` | `AssignmentsView` (GET/PATCH) | `useAssignments` + `useUpdateAssignments` hooks → `getAssignments()` + `updateAssignments()` → `/users/admin/assignments/` | WIRED | Hook calls API function, API function calls correct endpoint, endpoint URL registered in urls.py |
| `TeamPage.tsx` | auth context | `user.supervised_users` | WIRED | TeamPage reads `user.supervised_users` from `useAuth()`; backend `CurrentUserSerializer.get_supervised_users()` populates for both supervisor and coach |
| `MissionaryProfilePage.tsx` | Contact/Journal/Task/Gift APIs | `useContacts`, `useJournals`, `useTasks`, `useGifts` with `owner` param | WIRED | All hooks called with `ownerParam` (userId), coach path excludes gifts |
| `App.tsx` → `/admin/assignments` | `AdminAssignments.tsx` | `React.lazy()` + `requiredRole="admin"` | WIRED | Lazy import on line 42, route on line 137 |
| `App.tsx` → `/team` | `TeamPage.tsx` | `React.lazy()` + `requiredRole="missionary"` | WIRED | Lazy import on line 43, route on line 142 |
| `Sidebar.tsx` | `/team` route | `visibleRoles: ["supervisor", "coach"]` filter | WIRED | `canAccess()` checks `visibleRoles.includes(user.role)` — My Team only appears for supervisor/coach |
| `get_visible_user_ids()` | all view querysets | imported in gifts/contacts/tasks/journals/dashboard views | WIRED | Used in GiftListCreateView, ContactListView, and other views |
| `is_financial_role()` | insights views | imported and checked at top of each financial view | WIRED | 4 financial view guards confirmed in insights/views.py |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| ROLE-01 | 43-01, 43-03 | DB and UI rename: staff→missionary, mission_supervisor→supervisor | PARTIAL | DB migration and prod code updated; UserRole.STAFF stale in managers.py, generate_sample_data.py, test files |
| ROLE-02 | 43-01, 43-02, 43-03 | Coach role with limited visibility (no financial data) | VERIFIED | Coach FK on User model; get_visible_user_ids coach branch; gifts views return none(); is_financial_role guard |
| ROLE-03 | 43-02, 43-03 | Coach can see contacts + journals but not gifts/pledges | VERIFIED | Gift views block coach; contacts owner filter includes coach; frontend hides financial tabs for coach |
| ROLE-04 | 43-04 | Admin Assignments page at /admin/assignments | PARTIAL | AdminAssignments.tsx fully built and routed. UserAdminUpdateSerializer silently drops coached_user_ids (affects AdminUsers page coach assignment, not Assignments page) |
| ROLE-05 | 43-05 | /team page and /team/:userId missionary profile | VERIFIED | TeamPage.tsx and MissionaryProfilePage.tsx fully implemented and routed |

**Orphaned Requirements:** ROLE-01 through ROLE-05 are referenced in ROADMAP.md and plan frontmatter but are NOT documented in `.planning/REQUIREMENTS.md`. They have no entries in the requirements file, no traceability table rows, and the coverage count is not updated. This is a documentation gap — the implementation exists but the requirements are untracked.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `apps/users/managers.py` | 55 | `role='staff'` — stale role string after rename | Warning | method appears unused in production; no runtime impact unless called |
| `apps/core/management/commands/generate_sample_data.py` | 97 | `UserRole.STAFF` — deleted enum member | Blocker | `AttributeError: STAFF` when running `manage.py generate_sample_data` |
| `apps/users/tests/test_models.py` | 20, 44 | `UserRole.STAFF` — deleted enum member | Blocker | Test suite crashes with AttributeError |
| `apps/imports/tests/test_generic_imports.py` | 33, 202, 281 | `UserRole.STAFF` — deleted enum member | Blocker | Test suite crashes with AttributeError |
| `apps/users/serializers.py` | 77-104 | `UserAdminUpdateSerializer` missing `coached_user_ids` | Warning | Coach assignment via AdminUsers page silently dropped; Assignments page unaffected |

---

## Human Verification Required

### 1. Team Page for Supervisor

**Test:** Log in as a supervisor user, navigate to `/team`
**Expected:** Page shows "My Team" heading, subtitle "Missionaries under your supervision", table of assigned missionaries with Name/Email columns and "View Profile" buttons
**Why human:** Requires live supervisor session with assigned missionaries in database

### 2. Team Page for Coach

**Test:** Log in as a coach user, navigate to `/team`
**Expected:** Same page layout but subtitle reads "Your coachees"
**Why human:** Requires live coach session; subtitle is role-conditional

### 3. Missionary Profile — Coach sees no Donations tab

**Test:** Log in as coach, click "View Profile" on a team member
**Expected:** Tabs show Contacts, Journals, Tasks — Donations tab is absent
**Why human:** Tab visibility conditioned on runtime role value

### 4. Missionary Profile — Supervisor sees Donations tab

**Test:** Log in as supervisor, click "View Profile" on a team member
**Expected:** Tabs show Contacts, Journals, Tasks, Donations
**Why human:** Financial tab conditional on role

### 5. Admin Assignments page behavior

**Test:** Log in as admin, navigate to `/admin/assignments`, change one supervisor dropdown
**Expected:** Amber dot appears on that row, Save button shows "Save Changes (1)"; click Save — assignments persist on reload
**Why human:** React state interactions and persistence require browser

---

## Gaps Summary

Two gaps were found that are functionally significant:

**Gap 1 — Stale `staff` references (ROLE-01 partial):** The `UserRole.STAFF` enum member was removed in the model but three files still reference it by attribute (`UserRole.STAFF`). The `generate_sample_data` management command will crash with `AttributeError`. Test files in `users/` and `imports/` will also fail. The production application is unaffected (these are management commands and tests), but the test suite is broken. The `managers.py` `staff_users()` method uses the string `'staff'` directly rather than `UserRole.STAFF`, so it won't AttributeError — but it would silently return no results since no users have that role anymore.

**Gap 2 — coached_user_ids not handled in UserAdminUpdateSerializer (ROLE-04 partial):** The AdminUsers page (`AdminUsers.tsx`) sends `coached_user_ids` when updating a coach user's assignments. The backend `UserAdminUpdateSerializer` only declares and processes `supervised_user_ids` — `coached_user_ids` is absent from the `fields` list entirely, so Django REST Framework discards it silently. This means coach-to-missionary assignment via the AdminUsers user edit modal does not persist. The primary Assignments page (`/admin/assignments`) uses `AssignmentsView.patch()` which directly sets `missionary.coach` — that path works correctly. So ROLE-04's core deliverable (the Assignments page) works, but the AdminUsers page coach assignment path is broken.

**Orphaned requirements:** ROLE-01 through ROLE-05 have no entries in `.planning/REQUIREMENTS.md`. The requirements document was last updated after Phase 42 and was not extended for Phase 43. This is a tracking/documentation gap.

---

_Verified: 2026-03-04_
_Verifier: Claude (gsd-verifier)_
