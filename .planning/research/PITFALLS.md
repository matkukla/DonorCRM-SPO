# Domain Pitfalls: v2.2 -- Mission Supervisor Role, Journal Report Rebuild, Begin Prayer, UI Polish

**Domain:** Adding supervisor role with scoped visibility to existing owner-scoped CRM, rebuilding chart-heavy report, expanding prayer session, and UI column/layout changes
**Researched:** 2026-02-26
**Confidence:** HIGH (verified against actual DonorCRM codebase -- all 40+ `get_queryset` methods, 6 permission classes, 4 role-check patterns, 3 DndContext sections, and the Radix Dialog component analyzed)

## Critical Pitfalls

Mistakes that cause data leaks, security bypasses, or full rewrites.

### Pitfall 1: Supervisor Role Leaks Data Through Inconsistent Queryset Scoping

**What goes wrong:** The codebase has **four distinct role-check patterns** across 40+ `get_queryset` methods, and adding a `supervisor` role to `UserRole` TextChoices without updating every single one will either (a) leak all users' data to supervisors or (b) lock supervisors out of data entirely.

The patterns found in the actual codebase:

| Pattern | Files Using It | Current Behavior |
|---------|---------------|-----------------|
| `if user.role == 'admin'` | journals/views.py (8 places), tasks/views.py (4), groups/views.py (3), events/views.py (1) | Only admin sees all; supervisor would see nothing |
| `if user.role in ['admin', 'finance', 'read_only']` | contacts/views.py (5), gifts/views.py (4), prayers/views.py (1) | Finance and read_only see ALL data; supervisor would see nothing |
| `if user.role != 'admin'` | journals/views.py (5 places) | Inverted check; supervisor filtered to own data only |
| `_scope_gifts(user)` / `_scope_tasks(user)` | insights/services.py (helper functions) | Separate helper with its own role list |

If `supervisor` is simply added to `UserRole.choices` and only some views are updated, a supervisor would:
- See **zero** journals, tasks, or groups (the `== 'admin'` pattern excludes them)
- See **all** contacts, gifts, and prayers if added to the `in ['admin', ...]` list (because those lists show ALL data, not scoped data)
- See **zero** insights data (the `_scope_*` helpers have hardcoded role strings)

**Why it happens:** The "owner or admin" pattern was designed for a simple two-tier model. Supervisor is a third tier -- "sees some other users' data but not all" -- which none of the existing patterns support.

**Consequences:** Data leaked to supervisors who should only see their assigned missionaries, or supervisors locked out and filing bug reports. Both are security issues in a system handling donor PII.

**Prevention:**
1. Create a single `get_visible_users(user)` helper that returns the set of User IDs a given user can see:
   - Admin: all active users
   - Supervisor: `user.supervised_users.all()` (their assigned missionaries)
   - Everyone else: just `[user.id]`
2. Create a `scope_by_owner(queryset, user, owner_field='owner')` helper that uses `get_visible_users`:
   ```python
   def scope_by_owner(queryset, user, owner_field='owner'):
       if user.role == 'admin':
           return queryset
       visible = get_visible_users(user)
       return queryset.filter(**{f'{owner_field}__in': visible})
   ```
3. Replace ALL 40+ `get_queryset` role checks with calls to this helper
4. Add a regression test that creates a supervisor, assigns 2 of 5 missionaries, and asserts they see exactly those 2 missionaries' data across every endpoint

**Detection:** Before shipping, run a script that greps for `user.role` across all `views.py` and `services.py` files. Any remaining hardcoded role check that does not go through the centralized helper is a leak.

### Pitfall 2: Self-Referential User FK Creates Circular Dependency and Deletion Cascade

**What goes wrong:** Adding a `supervisor` ForeignKey on User pointing to User (self-referential) introduces:
1. **PROTECT cascade trap:** If using `on_delete=models.PROTECT` (matching the Contact.owner pattern), you cannot deactivate or delete a supervisor without first reassigning all their missionaries
2. **SET_NULL data integrity issue:** If using `on_delete=models.SET_NULL`, deactivating a supervisor silently orphans all their missionaries, who then lose visibility from any supervisor
3. **Admin assignment loop:** Nothing prevents assigning User A as supervisor of User B while User B supervises User A, or a user supervising themselves

**Why it happens:** Self-referential ForeignKeys on User models are a known Django pitfall. The existing `User.destroy` method (line 49-54 of `apps/users/views.py`) simply sets `is_active = False` -- it does not check for downstream relationships.

**Consequences:** Admin deactivates a supervisor and either hits a 500 error (PROTECT), or missionaries silently lose their supervisor scope and all supervisor-visible endpoints return empty.

**Prevention:**
- Use a **ManyToMany through table** instead of FK, so the relationship is independent of User lifecycle:
  ```python
  # On User model
  supervised_users = models.ManyToManyField(
      'self', symmetrical=False, blank=True,
      related_name='supervisors'
  )
  ```
- M2M is better than FK because: (a) no cascade issues on user deactivation, (b) supports future "multiple supervisors per missionary" without schema change, (c) assignment/unassignment is just `.add()/.remove()` with no migration needed
- Add validation in the admin assignment endpoint: supervisor cannot supervise themselves, and cycles are prevented (a user cannot be both supervisor and supervised by the same person)
- Add a Django admin inline for the M2M so administrators can manage assignments in the Django admin as fallback

### Pitfall 3: Permission Classes Do Not Support "Same Access as Admin but Scoped"

**What goes wrong:** The existing permission classes in `apps/core/permissions.py` are designed for binary access -- you are admin or you are not. The `IsAdmin` class (line 18-26) checks `role == 'admin'`. The `IsOwnerOrAdmin` class checks ownership OR admin. There is no "is supervisor and owns through relationship" permission.

If the supervisor role is given `IsAdmin`-level permissions, they get unscoped full access. If not, they get staff-level "own data only" access. Neither is correct.

**Why it happens:** The spec says "same access as admin but scoped." This is a fundamentally different authorization model -- it requires both permission-level access (can do CRUD on others' data) AND queryset-level scoping (but only for assigned missionaries). The existing permission classes only handle the first dimension.

**Consequences:** Either supervisors can create/edit/delete contacts belonging to missionaries they do NOT supervise (security hole), or they are stuck with read-only access on their missionaries' data (broken feature).

**Prevention:**
- Keep the permission classes focused on **what operations are allowed** (CRUD vs read-only)
- Handle **whose data is visible** entirely through queryset scoping (the `scope_by_owner` pattern from Pitfall 1)
- Create `IsSupervisorOrAdmin` permission class for admin-level endpoints that supervisors also need:
  ```python
  class IsSupervisorOrAdmin(permissions.BasePermission):
      def has_permission(self, request, view):
          return request.user.role in ['admin', 'supervisor']
  ```
- Object-level permissions (like `IsOwnerOrAdmin.has_object_permission`) need updating to also check if the object's owner is in `get_visible_users(request.user)`
- The `IsStaffOrAbove` class needs supervisor added to its allowed roles for write operations

### Pitfall 4: Frontend `ProtectedRoute` Role Hierarchy Breaks with Supervisor

**What goes wrong:** The `ProtectedRoute` component (line 23 of `ProtectedRoute.tsx`) uses a numeric role hierarchy:
```typescript
const roleHierarchy = { admin: 4, finance: 3, staff: 2, read_only: 1 }
```

The supervisor role does not fit this linear hierarchy. A supervisor has admin-level page access but not admin-level data visibility. If supervisor is ranked at 4 (same as admin), they can access admin-only pages like User Management. If ranked at 3, they cannot access pages that require `admin` role.

Additionally, the `User` type in `frontend/src/api/auth.ts` (line 18) hardcodes role as a union type:
```typescript
role: "admin" | "staff" | "finance" | "read_only"
```

Adding `"supervisor"` requires updating this type AND the identical type in `frontend/src/api/users.ts` (line 6) AND the `userRoleLabels` record (line 45).

**Why it happens:** Linear role hierarchies cannot express "same permissions as X but different data scope."

**Consequences:** Supervisor either gets admin-only pages they should not have (user management, system settings) or gets blocked from pages they need (analytics dashboard, missionary dashboard viewer).

**Prevention:**
- Replace the numeric hierarchy with a **capability-based check** in `ProtectedRoute`:
  ```typescript
  const pageAccess: Record<string, string[]> = {
    admin: ['admin', 'supervisor', 'finance', 'staff', 'read_only'],
    finance: ['admin', 'supervisor', 'finance'],
    // etc.
  }
  // Or better: check if user.role is in the allowed list for the route
  ```
- Update the `User` type in **both** `auth.ts` and `users.ts` -- they are separate interfaces and both need `"supervisor"` added
- Update `userRoleLabels` in `users.ts` to include `supervisor: "Mission Supervisor"`
- Do NOT simply add supervisor to the numeric hierarchy -- replace the hierarchy with explicit access lists

## Moderate Pitfalls

### Pitfall 5: Missionary Dashboard Selector Creates "Acting As" Security Surface

**What goes wrong:** The spec requires supervisors and admins to "select a missionary and view their dashboard." This means the dashboard must accept a `?user_id=` parameter and fetch that user's data instead of the current user's data. Every dashboard API endpoint must then:
1. Accept and validate the `user_id` parameter
2. Verify the requesting user has permission to view that user's data
3. Return data scoped to the target user, not the requesting user

If the frontend passes `user_id` but the backend dashboard endpoint ignores it and returns `request.user`'s data, the feature silently fails. If the backend accepts `user_id` without validating supervisor access, any authenticated user can view anyone's dashboard.

**What goes wrong specifically in this codebase:** The `CurrentUserView` (line 57-88 of `apps/users/views.py`) annotates `request.user.pk` directly. The `useDashboardSummary` hook likely hardcodes the current user. The entire dashboard API stack would need a "viewing as" concept threaded through.

**Prevention:**
- Add a `?viewing_as=<user_id>` query parameter to dashboard endpoints
- Create a `get_target_user(request)` utility that:
  - If `viewing_as` is absent, returns `request.user`
  - If `viewing_as` is present, validates that `request.user` is admin or supervisor of that user
  - Returns 403 if unauthorized
- Pass the target user (not `request.user`) to all data-fetching functions
- Frontend: add a user selector dropdown that only appears for admin/supervisor roles, and pass the selected user ID as a query parameter to all dashboard API calls
- React Query key must include the selected user ID to avoid cache collisions between "my dashboard" and "viewing John's dashboard"

### Pitfall 6: Cross-Section Drag in Dashboard Requires Single DndContext but Current Code Uses Three SortableContexts

**What goes wrong:** The spec says "make tiles draggable anywhere." Currently the Dashboard has three separate `SortableContext` blocks (lines 154, 165, 196 of `Dashboard.tsx`) within one `DndContext`. The `handleDragEnd` function (line 76) only reorders within the same section (`tryReorder` checks if both `active.id` and `over.id` exist in the same array). Cross-section drag (e.g., moving a stat card into the content grid) would:
1. Find `oldIndex` in one array but `newIndex === -1` in the same array
2. Silently do nothing

Making tiles "draggable anywhere" means merging all three `SortableContext` arrays into a single flat list, which breaks the grid layout (stat cards are in a 4-column grid, content tiles in a 2-column grid, giving widgets in a 2-column grid).

**Prevention:**
- Clarify the spec: "draggable anywhere" likely means "within each section" (reorder stat cards among themselves, reorder content tiles among themselves), NOT cross-section moves
- If cross-section is truly desired, use a single flat array and a `renderTileById` function that maps tile IDs to grid positioning dynamically -- this is significantly more complex
- The simpler interpretation: merge `givingOrder`, `statsOrder`, and `contentOrder` into one array but use CSS grid `grid-template-areas` to maintain the layout structure while allowing any-to-any reordering

### Pitfall 7: Removing Columns from List Pages While API Still Returns Data Creates Inconsistency

**What goes wrong:** The gifts page todo says "remove Funds column" and "remove Description column" but keep the data in the API. Meanwhile, a new "Type" column requires a model field addition. This creates three inconsistency risks:
1. **Filter orphaning:** The Funds dropdown filter (lines 217-238 of `DonationList.tsx`) references the `fund` filter parameter. Removing the column but keeping the filter is confusing; removing the filter but keeping the API field means existing bookmarked URLs with `?fund=X` silently filter but show no fund column
2. **Export inconsistency:** The CSV export endpoint still includes Fund and Description columns even though the UI does not show them. Users see data in exports that is not visible on the page.
3. **Detail panel mismatch:** The `DonationDetailPanel` slide-in likely still shows Fund and Description. Removing from the list but not the detail creates a jarring inconsistency.

**Prevention:**
- Remove columns from the list page `columns` array only (not from the API serializer)
- Also remove the Fund dropdown filter from the FilterBar children
- Keep the data in the detail panel and CSV export (they are different contexts)
- Add the new `payment_type` field as a model CharField with choices, migration, and serializer update BEFORE adding the frontend column
- Handle the bookmarked URL case: `useFilterParams` will simply ignore unknown filter keys, so old `?fund=X` URLs will work but the filter will not display

### Pitfall 8: Journal Report Rebuild Requires New Backend Endpoint That Does Not Exist

**What goes wrong:** The journal report spec (in `prompts/journal_report.md`) references `journalsApi.getReport(journalId)` returning a `JournalReport` type with `summary.stageDistribution`, `summary.decisions`, `summary.goalProgressPercent`, etc. But the current backend has no `/journals/<id>/report/` endpoint. The existing `JournalAnalyticsViewSet` (in `apps/journals/views.py`) provides separate endpoints for `decision-trends`, `stage-activity`, `pipeline-breakdown`, and `next-steps-queue` -- but these are global analytics, not per-journal report data.

If the frontend is built against the spec's expected API shape without first building the backend endpoint, the entire report component will show empty/error state.

**Prevention:**
- Build the backend `JournalReportView` endpoint first (or simultaneously), returning:
  ```python
  # GET /api/journals/<journal_id>/report/
  {
    "journal": { "id", "name", "goal_amount", "deadline", "status" },
    "summary": {
      "total_contacts": int,
      "stalled_contacts": int,
      "stage_distribution": { "contact": N, "meet": N, ... },
      "decisions": { "pending": N, "confirmed": N, "declined": N, ... },
      "goal_progress_percent": float,
      "open_next_steps": int,
      "overdue_next_steps": int
    }
  }
  ```
- The stage distribution query already exists in `pipeline_breakdown` -- just scope it to a single journal
- Use `select_related`/`prefetch_related` to avoid N+1 (this is journal-report-specific, querying all contacts in one journal)

### Pitfall 9: Checkbox "Direct Check" Behavior Conflicts with Event-Sourced Stage Tracking

**What goes wrong:** The journal report spec says "whenever a checkbox is clicked, the box should be checked instead of having to log an event." But the journal grid's stage tracking is **event-sourced** -- a contact's current stage is determined by the most recent `JournalStageEvent` record (see `get_current_stage` in `ContactJournalMembershipSerializer`, lines 173-181 of `contacts/serializers.py`). There is no boolean "checked" field on `JournalContact`.

"Clicking a checkbox" to check a stage means creating a `JournalStageEvent` behind the scenes. If the checkbox creates the event silently, the user loses the ability to add notes to the stage transition. If the checkbox sets a separate boolean field, the stage state diverges from the event log.

**Prevention:**
- Implement checkboxes as "instant stage event creation" -- clicking the checkbox POSTs a new `JournalStageEvent` with the stage value and empty notes
- Do NOT add boolean stage fields to `JournalContact` -- this would create two sources of truth
- Optimistically update the UI (mark checkbox checked immediately) and let the mutation create the event in the background
- If the mutation fails, revert the checkbox state with a toast error
- The existing `JournalStageEventListCreateView` endpoint already handles POST -- just call it from the checkbox click handler

## Minor Pitfalls

### Pitfall 10: Dialog Centering Is Already Correct in Component but Overridden by Consumer Usage

**What goes wrong:** The `DialogContent` component (line 38-52 of `dialog.tsx`) already uses `fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%]` for centering. If dialogs appear off-center, the issue is NOT in the base component -- it is that some edit flows use the `Sheet` component (which slides from the side by design) instead of `Dialog`.

"Fixing" the Dialog component when Sheets are the actual problem would break existing centered dialogs. Changing Sheets to Dialogs requires different layout considerations (Sheets have scrollable content areas; Dialogs have max-height constraints).

**Prevention:**
- Audit every edit flow to determine which use Dialog vs Sheet
- For flows that should be centered: switch from Sheet to Dialog
- For the Sheet-to-Dialog conversion, ensure the content has `max-h-[85vh] overflow-y-auto` to handle long forms
- Do NOT modify the base `dialog.tsx` component unless testing confirms it is actually mispositioned

### Pitfall 11: Begin Prayer Feature Must Not Break Existing Focus Mode Keyboard Handlers

**What goes wrong:** The existing `PrayerFocusMode` (lines 56-86 of `PrayerFocusMode.tsx`) registers global keyboard event listeners for Arrow keys, Space, Enter, P, and Escape. If a new "Begin Prayer" feature adds its own component with different keyboard shortcuts, the handlers can conflict (both listening on the same `window` keydown event).

Additionally, the Focus Mode uses `fixed inset-0 z-50` (fullscreen overlay). If the new prayer session view also uses a fullscreen overlay, they can stack incorrectly.

**Prevention:**
- Build "Begin Prayer" as an extension of the existing Focus Mode, not a separate overlay
- Reuse the existing keyboard handler infrastructure
- If the prayer session has different stages (e.g., reading a scripture, then praying), use component state within the same fullscreen overlay rather than stacking overlays

### Pitfall 12: Removing Pipeline Breakdown from Journal Report Leaves Orphaned Backend Endpoint and Frontend Hook

**What goes wrong:** The `pipeline_breakdown` endpoint in `JournalAnalyticsViewSet` (line 499-518 of `journals/views.py`) and its corresponding frontend hook `usePipelineBreakdown` (referenced in `ReportCharts.tsx`) will become dead code after removal. The `PipelineBreakdownChart` component is exported but if only referenced in the report, removing the import leaves the component file as dead code.

**Prevention:**
- Remove the frontend component and hook import
- Do NOT remove the backend endpoint in this milestone -- it may be used by other consumers or can be removed in a cleanup phase
- Search for all imports of `PipelineBreakdownChart` and `usePipelineBreakdown` to confirm no other pages use them before removal

### Pitfall 13: Adding `payment_type` Field to Gift Model Requires Default Value for Existing Records

**What goes wrong:** Adding a new `payment_type` CharField to the Gift model with choices `('credit_card', 'direct_deposit', 'check')` requires a default value for the migration. If the default is empty string, the column displays as blank for all historical gifts. If the default is a specific type, it misrepresents historical data.

**Prevention:**
- Add the field as `blank=True, default=''` so historical records show no type
- Frontend displays empty type as a dash or "Unknown"
- Do NOT set a default of `credit_card` -- existing imported data has no payment type information
- Consider whether the field should be required on new gifts only (validate in serializer, not model)

### Pitfall 14: Removing Review Queue and Heat Map Must Clean Up Sidebar, Routes, and API Hooks

**What goes wrong:** The Review Queue and Activity Heat Map are referenced across multiple layers:
- Sidebar navigation link
- React Router route in App.tsx
- API function in insights API client
- React Query hook (e.g., `useReviewQueue`, `useActivityHeatmap`)
- Backend view, URL, and service function

Removing the frontend component but leaving the route creates a blank page. Leaving the sidebar link creates a dead nav item. Leaving the hook creates unused imports that may cause build warnings.

**Prevention:**
- Work backwards from UI to API: Sidebar link -> Route -> Page component -> Hook -> API function
- For backend: leave the endpoint in place (no harm, avoids migration) or mark as deprecated
- Run `tsc --noEmit` after removal to catch any remaining TypeScript references
- Test that navigating to the old URL does not crash (it should 404 or redirect)

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Supervisor role (backend) | Pitfall 1 (queryset scoping), Pitfall 2 (self-referential FK), Pitfall 3 (permission classes) | Build centralized `scope_by_owner` helper FIRST, then update all 40+ views; use M2M not FK |
| Supervisor role (frontend) | Pitfall 4 (role hierarchy), Pitfall 5 (dashboard selector) | Replace numeric hierarchy with capability map; thread `viewing_as` through all dashboard API calls |
| Journal report rebuild | Pitfall 8 (missing backend), Pitfall 9 (checkbox vs events), Pitfall 12 (orphaned code) | Build backend endpoint first; checkboxes create events silently; clean up dead imports |
| Dashboard modifications | Pitfall 6 (cross-section drag) | Clarify "draggable anywhere" scope; likely means within-section only |
| UI polish (dialogs) | Pitfall 10 (Sheet vs Dialog confusion) | Audit which flows use Sheet vs Dialog before modifying base component |
| UI polish (columns) | Pitfall 7 (filter/export inconsistency) | Remove column + filter together; keep data in API and exports |
| Begin Prayer | Pitfall 11 (keyboard handler conflicts) | Extend existing Focus Mode; do not create parallel overlay |
| Gift columns | Pitfall 13 (migration default) | Use `blank=True, default=''`; display empty as dash |
| Analytics cleanup | Pitfall 14 (orphaned references) | Work backwards: sidebar -> route -> component -> hook -> API |

## Sources

- Direct codebase analysis of `/home/matkukla/projects/DonorCRM/apps/core/permissions.py` (6 permission classes)
- Direct codebase analysis of all `get_queryset` methods across `contacts/views.py`, `journals/views.py`, `gifts/views.py`, `tasks/views.py`, `groups/views.py`, `events/views.py`, `prayers/views.py`, `imports/views.py`, `insights/services.py`
- Direct codebase analysis of `apps/users/models.py` (UserRole TextChoices, User model)
- Direct codebase analysis of `frontend/src/components/auth/ProtectedRoute.tsx` (role hierarchy)
- Direct codebase analysis of `frontend/src/api/auth.ts` and `frontend/src/api/users.ts` (User type definitions)
- Direct codebase analysis of `frontend/src/pages/Dashboard.tsx` (3 SortableContexts, DndContext)
- Direct codebase analysis of `frontend/src/pages/donations/DonationList.tsx` (column definitions, filter bar)
- Direct codebase analysis of `frontend/src/components/ui/dialog.tsx` (Radix Dialog positioning)
- Direct codebase analysis of `frontend/src/pages/prayer/PrayerFocusMode.tsx` (keyboard handlers, overlay)
- Direct codebase analysis of `frontend/src/pages/journals/components/ReportCharts.tsx` (chart components)
- Direct codebase analysis of `apps/journals/views.py` (JournalAnalyticsViewSet endpoints)
- Direct codebase analysis of `apps/contacts/serializers.py` (event-sourced stage tracking)
- Spec files: `prompts/mission_supervisor.md`, `prompts/journal_report.md`, `prompts/dashboard_modification.md`
- Todo files: all 9 pending todos in `.planning/todos/pending/`
