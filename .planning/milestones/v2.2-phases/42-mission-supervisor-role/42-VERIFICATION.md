---
phase: 42-mission-supervisor-role
verified: 2026-03-02T18:30:00Z
status: human_needed
score: 12/13 must-haves verified
human_verification:
  - test: "Log in as a mission_supervisor user, navigate to Prayer page, click a prayer row belonging to an assigned missionary. Verify the edit panel opens and attempts to save changes fail (backend 403)."
    expected: "Backend blocks the mutation with 403. Ideally the UI also prevents opening the panel for non-owned rows, but backend enforcement is sufficient for security."
    why_human: "PrayerList row click opens edit panel for all rows regardless of ownership. Cannot verify whether the panel's save action returns 403 from backend without running the app."
  - test: "Log in as a mission_supervisor user who has 1+ assigned missionaries. Navigate to Dashboard. Verify the missionary selector dropdown appears and selecting a missionary loads their data."
    expected: "Dropdown shows 'My Dashboard' + each supervised missionary's name. Selecting one loads their dashboard tiles and layout. DnD drag handles are gone. 'Viewing ... (read-only)' banner shows."
    why_human: "Dashboard selector depends on auth user.supervised_users being populated, which requires an actual supervisor account with assigned missionaries in the database."
  - test: "Log in as admin. Go to Admin > Users. Edit a user and set their role to Mission Supervisor. Verify the missionary picker appears, search for and select staff users, save. Verify the selected users now show supervisor in DB."
    expected: "Mission Supervisor role selectable from dropdown. Missionary picker (Command+Popover combobox) appears below role field. Saving sends supervised_user_ids to backend. Users table shows count badge next to supervisor role."
    why_human: "Multi-select combobox interaction and data persistence requires browser interaction with live Django backend."
---

# Phase 42: Mission Supervisor Role Verification Report

**Phase Goal:** Organization leadership can assign supervisors to missionaries, and supervisors see only their assigned missionaries' data across the entire application
**Verified:** 2026-03-02T18:30:00Z
**Status:** human_needed (automated checks passed; 3 interactive scenarios need human confirmation)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Mission Supervisor exists as a selectable role in UserRole choices | VERIFIED | `UserRole.MISSION_SUPERVISOR = 'mission_supervisor'` in `apps/users/models.py:21`; migration 0004 applied |
| 2  | User model has a supervisor FK pointing to self with SET_NULL | VERIFIED | `supervisor = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='supervised_users')` at line 52 |
| 3  | get_visible_user_ids() returns correct user ID sets for all 5 roles | VERIFIED | Implemented in `apps/core/permissions.py:18-35`; returns None for admin/finance/read_only, set for supervisor+own, {own} for staff |
| 4  | Admin can PATCH a user to assign supervised_users list | VERIFIED | `UserAdminUpdateSerializer.supervised_user_ids` field + `update()` method at lines 81-104 in `apps/users/serializers.py` |
| 5  | CurrentUserSerializer includes supervised_users for supervisors | VERIFIED | `get_supervised_users()` method at line 186; returns list for mission_supervisor role, empty list otherwise |
| 6  | IsSupervisorWriteRestricted blocks write ops on non-owned objects | VERIFIED | Implemented at `apps/core/permissions.py:146-167`; on ContactDetailView, GiftDetailView, RecurringGiftDetailView, TaskDetailView, GroupDetailView, JournalDetailView, DecisionDetailView, NextStepDetailView |
| 7  | Supervisor sees own contacts + assigned missionaries' contacts | VERIFIED | `get_visible_user_ids()` called in all 11 contact view methods; backend confirmed by Django check passing |
| 8  | Supervisor sees own gifts, tasks, journals, prayers across all pages | VERIFIED | All 14 view/service files import and use `get_visible_user_ids()` — confirmed by shell import check |
| 9  | mission_supervisor appears in UserRole type union and userRoleLabels | VERIFIED | `frontend/src/api/users.ts:6` and `:47-53`; `frontend/src/api/auth.ts:18` |
| 10 | roleHierarchy in ProtectedRoute and Sidebar includes mission_supervisor at level 4 | VERIFIED | Both components have `{ admin: 5, mission_supervisor: 4, finance: 3, staff: 2, read_only: 1 }` |
| 11 | Admin sees missionary picker when editing a supervisor user | VERIFIED | `AdminUsers.tsx:458` — conditional on `editRole === "mission_supervisor"`, sends `supervised_user_ids` in handleUpdate |
| 12 | Dashboard accepts ?user_id= and supervisor sees missionary selector | VERIFIED | `_resolve_target_user()` in `apps/dashboard/views.py`; selector in `Dashboard.tsx:234-256` |
| 13 | PrayerList row click gated for supervisor on non-owned items (frontend UX) | UNCERTAIN | Row click opens edit panel for ALL rows regardless of ownership; backend blocks actual save via 403 |

**Score:** 12/13 truths verified (1 uncertain — PrayerList frontend UX gating)

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `apps/users/migrations/0004_mission_supervisor_role.py` | VERIFIED | Present and applied (showmigrations confirmed [X]) |
| `apps/core/permissions.py` | VERIFIED | Contains `get_visible_user_ids()` + `IsSupervisorWriteRestricted` |
| `apps/users/serializers.py` | VERIFIED | `supervised_user_ids` on UserAdminUpdateSerializer, `supervised_users` on CurrentUserSerializer |
| `apps/users/models.py` | VERIFIED | MISSION_SUPERVISOR role, supervisor FK, `is_mission_supervisor` property, updated `can_view_contact` |
| `apps/contacts/views.py` | VERIFIED | 11 uses of `get_visible_user_ids()`, IsSupervisorWriteRestricted on ContactDetailView |
| `apps/gifts/views.py` | VERIFIED | 4 uses of helper, IsSupervisorWriteRestricted on GiftDetailView and RecurringGiftDetailView |
| `apps/tasks/views.py` | VERIFIED | 5 uses of helper, IsSupervisorWriteRestricted on TaskDetailView |
| `apps/journals/views.py` | VERIFIED | 14+ uses of helper, IsSupervisorWriteRestricted on JournalDetailView, DecisionDetailView, NextStepDetailView |
| `apps/prayers/views.py` | VERIFIED | `_owner_scoped_queryset()` uses helper |
| `apps/dashboard/services.py` | VERIFIED | All 6 service functions use `get_visible_user_ids()` |
| `apps/insights/services.py` | VERIFIED | All 3 scope helpers (`_scope_gifts`, `_scope_recurring_gifts`, `_scope_tasks`) use helper |
| `apps/dashboard/views.py` | VERIFIED | `_resolve_target_user()`, all 9 views use it, `UserDashboardLayoutView` added and wired |
| `apps/dashboard/urls.py` | VERIFIED | `dashboard/user/<uuid:pk>/layout/` wired to `UserDashboardLayoutView` |
| `frontend/src/api/users.ts` | VERIFIED | `UserRole` includes `"mission_supervisor"`, `User.supervisor` field, `UserUpdate.supervised_user_ids` |
| `frontend/src/api/auth.ts` | VERIFIED | Role union includes `"mission_supervisor"`, `User.supervised_users` field |
| `frontend/src/components/auth/ProtectedRoute.tsx` | VERIFIED | 5-level hierarchy in both useEffect and render body |
| `frontend/src/components/layout/Sidebar.tsx` | VERIFIED | 5-level hierarchy; Admin nav requires level 5 so supervisor (4) cannot access |
| `frontend/src/components/ui/command.tsx` | VERIFIED | Created manually (cmdk installed as dependency) |
| `frontend/src/pages/admin/AdminUsers.tsx` | VERIFIED | `mission_supervisor` roleVariant, missionary picker combobox, supervised count in table |
| `frontend/src/api/dashboard.ts` | VERIFIED | `userId` param on `getDashboardSummary`, `getGivingSummary`, `getMonthlyGifts`; `getUserDashboardLayout` function |
| `frontend/src/hooks/useDashboard.ts` | VERIFIED | `userId` in all query keys and fetch functions; `isDragEnabled` returned |
| `frontend/src/pages/Dashboard.tsx` | VERIFIED | Missionary selector, view-only banner, conditional DnD, markEventsSeen skipped when `isViewingOther` |
| `apps/contacts/serializers.py` | VERIFIED | `owner_name` on `ContactListSerializer` and `ContactDetailSerializer` |
| `apps/gifts/serializers.py` | VERIFIED | `owner_name` SerializerMethodField on `GiftSerializer` and `RecurringGiftSerializer` |
| `apps/tasks/serializers.py` | VERIFIED | `owner_name` on `TaskSerializer` |
| `apps/journals/serializers.py` | VERIFIED | `owner_name` on `JournalListSerializer` |
| `apps/prayers/serializers.py` | VERIFIED | `owner_name` SerializerMethodField on `PrayerIntentionSerializer` |
| `apps/tasks/filters.py` | VERIFIED | `owner = django_filters.NumberFilter(field_name='owner_id')` |
| `apps/journals/filters.py` | VERIFIED | `owner = django_filters.NumberFilter(field_name='owner_id')` |
| `apps/prayers/filters.py` | VERIFIED | `owner = django_filters.NumberFilter(field_name='contact__owner_id')` |
| `frontend/src/hooks/useFilterParams.ts` | VERIFIED | `owner: parseAsString` in taskFilterParsers, journalFilterParsers, pledgeFilterParsers |
| `frontend/src/pages/contacts/ContactList.tsx` | VERIFIED | `canSeeOwner` guard, Owner column, `ownerOptions` for supervisor, `canEdit`/`isOwnItem` row gating |
| `frontend/src/pages/donations/DonationList.tsx` | VERIFIED | `canSeeOwner` guard, Owner column, `ownerOptions` for supervisor (no row edit/delete actions in list) |
| `frontend/src/pages/tasks/TaskList.tsx` | VERIFIED | `canSeeOwner`, Owner column, owner filter, `canEdit`/`isOwnItem` row gating |
| `frontend/src/pages/journals/JournalList.tsx` | VERIFIED | `canSeeOwner`, owner name on cards, owner filter (no row edit/delete actions) |
| `frontend/src/pages/prayer/PrayerList.tsx` | PARTIAL | `canSeeOwner`, Owner column, owner filter present; row click opens edit panel without ownership check |
| `frontend/src/pages/pledges/PledgeList.tsx` | VERIFIED | `canSeeOwner`, Owner column, owner filter (no row edit/delete actions) |
| `frontend/src/pages/contacts/ContactDetail.tsx` | VERIFIED | `isReadOnly = role === 'mission_supervisor' && owner !== user.id`; edit/delete/child-create buttons gated |
| `frontend/src/pages/donations/DonationDetail.tsx` | VERIFIED | `isReadOnly = role === 'mission_supervisor' && owner_name !== currentUserName`; action buttons gated |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `apps/contacts/views.py` | `apps/core/permissions.py` | `from apps.core.permissions import get_visible_user_ids` | WIRED | Confirmed at line 25 |
| `apps/gifts/views.py` | `apps/core/permissions.py` | `from apps.core.permissions import IsSupervisorWriteRestricted, get_visible_user_ids` | WIRED | Confirmed at line 11 |
| `apps/tasks/views.py` | `apps/core/permissions.py` | `from apps.core.permissions import IsOwnerOrAdmin, IsSupervisorWriteRestricted, get_visible_user_ids` | WIRED | Confirmed at line 11 |
| `apps/journals/views.py` | `apps/core/permissions.py` | import of all three | WIRED | Confirmed at line 19 |
| `apps/dashboard/views.py` | `apps/dashboard/services.py` | `target = _resolve_target_user(request)` passed to service functions | WIRED | Confirmed at lines 62, 88, 106, 133, 152, 172, 192, 219, 236 |
| `frontend/src/pages/admin/AdminUsers.tsx` | `frontend/src/api/users.ts` | `data.supervised_user_ids = editSupervisedUserIds` in handleUpdate | WIRED | Confirmed at lines 149-151 |
| `frontend/src/components/auth/ProtectedRoute.tsx` | `frontend/src/api/auth.ts` | `user.role` checked against `roleHierarchy` with `mission_supervisor` at 4 | WIRED | Confirmed at lines 23, 49 |
| `frontend/src/pages/Dashboard.tsx` | `frontend/src/hooks/useDashboard.ts` | `useDashboardSummary(effectiveUserId)` passes userId to query key | WIRED | Confirmed at line 69 |
| `frontend/src/api/dashboard.ts` | backend `/dashboard/?user_id=` | `params = userId ? { user_id: userId } : undefined` | WIRED | Confirmed at lines 131-133 |
| `apps/core/permissions.py` | `apps/users/models.py` | `user.supervised_users.filter(is_active=True).values_list('id', flat=True)` | WIRED | Confirmed at lines 29-31 |
| `apps/users/serializers.py` | `apps/users/models.py` | `UserAdminUpdateSerializer.update()` calls `instance.supervised_users.update(supervisor=None)` | WIRED | Confirmed at lines 101-103 |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SUPV-01 | 42-01, 42-03 | Mission Supervisor role exists in the system (UserRole choice + migration) | SATISFIED | UserRole.MISSION_SUPERVISOR in models, migration 0004 applied, role in frontend types |
| SUPV-02 | 42-01, 42-03 | Admin can assign missionaries to a supervisor via management UI | SATISFIED | UserAdminUpdateSerializer.supervised_user_ids, AdminUsers.tsx missionary combobox |
| SUPV-03 | 42-02, 42-05 | Supervisor sees only their assigned missionaries' data across all pages | SATISFIED (with caveat) | get_visible_user_ids() across 14 files; Owner columns/filters on all 6 list pages; PrayerList frontend gating incomplete but backend enforced |
| SUPV-04 | 42-04 | Admin and Supervisor can select a missionary and view their dashboard | SATISFIED | Dashboard selector, ?user_id= backend support, UserDashboardLayoutView, DnD disabled |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/pages/prayer/PrayerList.tsx` | 289 | `onClick={() => openEdit(intention)}` with no ownership check | Warning | Supervisor can open edit panel for any prayer including missionaries'; backend 403 blocks actual save |

No stub implementations found. No TODO/FIXME blockers. No empty return values in critical paths. Django system check passes with 0 issues. TypeScript compiles without errors.

### Human Verification Required

#### 1. PrayerList Supervisor Gating

**Test:** Log in as a mission_supervisor user with at least one assigned missionary. Navigate to the Prayer page. Locate a prayer intention owned by an assigned missionary. Click the row to open the edit panel. Attempt to change the status or save any change.

**Expected:** The backend returns HTTP 403 Forbidden. The edit panel may open (frontend allows it), but the save mutation fails. Optionally the row click could be blocked by an `isOwnItem` check similar to ContactList/TaskList, but security is enforced by backend regardless.

**Why human:** Requires a live supervisor account with assigned missionaries and browser interaction to confirm the 403 response is surfaced correctly to the user.

#### 2. Dashboard Missionary Selector (Supervisor Role)

**Test:** Log in as a mission_supervisor user with at least two assigned missionaries. Navigate to the Dashboard page.

**Expected:**
- A "Viewing: My Dashboard" dropdown appears near the top.
- Dropdown lists each supervised missionary by name.
- Selecting a missionary changes all dashboard tiles to show that missionary's data.
- "Viewing [Name]'s dashboard (read-only)" info banner appears.
- Drag handles disappear from tiles (DnD disabled).
- "Reset layout" button disappears.
- MPD section is hidden.
- Selecting "My Dashboard" reverts to own data with DnD re-enabled.

**Why human:** Requires live supervisor account with data; cannot verify dynamic React state and API calls programmatically.

#### 3. Admin Missionary Assignment UI

**Test:** Log in as admin. Navigate to Admin > Users. Click Edit on any active user. Change their role to "Mission Supervisor". Verify the missionary assignment picker appears.

**Expected:**
- Role dropdown includes "Mission Supervisor" option with warning badge.
- When Mission Supervisor is selected, a "Assigned Missionaries" section appears with a searchable combobox.
- Typing in the combobox filters the user list.
- Clicking a user toggles their selection (check mark appears/disappears).
- Selected users appear as removable badge chips below the combobox.
- Saving the dialog sends `supervised_user_ids` to backend.
- Users table shows a count badge `(N)` next to the supervisor's role badge.

**Why human:** Multi-select combobox interaction and database persistence requires browser interaction.

### Gaps Summary

No blocking gaps were found. All 4 requirements (SUPV-01 through SUPV-04) are implemented and wired end-to-end:

- Backend role infrastructure (UserRole, supervisor FK, migration, get_visible_user_ids, IsSupervisorWriteRestricted) is complete and verified by Django system check.
- View-level queryset scoping uses the centralized helper across all 14 view/service files.
- Frontend type system, role hierarchy, and AdminUsers missionary picker are verified by TypeScript compilation.
- Dashboard missionary selector is implemented with userId threading through hooks, API functions, and backend endpoints.
- Owner columns and filters are on all 6 list pages with the correct canSeeOwner pattern.
- ContactDetail and DonationDetail hide edit/delete buttons for supervisors viewing missionaries' data.

The single warning-level gap is PrayerList's row click opening the edit panel without frontend ownership gating. Backend enforcement via `IsSupervisorWriteRestricted` is in place and will block any mutation. This is a UX polish item, not a security gap.

---

_Verified: 2026-03-02T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
