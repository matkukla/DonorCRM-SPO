# Phase 42: Mission Supervisor Role - Research

**Researched:** 2026-03-02
**Domain:** Role-based access control, queryset scoping, frontend role rendering
**Confidence:** HIGH

## Summary

This phase adds a Mission Supervisor role to DonorCRM's existing four-role system (Admin, Staff, Finance, Read-Only). The supervisor sees their own data with full write access plus assigned missionaries' data as read-only across all pages. The implementation touches every layer of the stack: a new UserRole choice + supervisor FK on User, queryset scoping changes in 40+ view methods, permission class updates, frontend role type expansion, and two new UI features (missionary assignment on user edit form, dashboard missionary selector).

The codebase already has consistent patterns for role-based queryset scoping (checking `user.role` in `get_queryset()`) and an admin-only owner filter on list pages. The supervisor role extends these patterns rather than inventing new ones. The primary complexity is the sheer surface area: every `get_queryset()` method that checks roles must be updated, and the dashboard must support viewing another user's data.

**Primary recommendation:** Implement as a ForeignKey `supervisor` on User pointing to self, add a helper method like `get_visible_user_ids(user)` that returns the set of user IDs whose data a user can see, and use that consistently in all queryset scoping methods.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Assignment lives on the user edit form in admin user management (not a separate page)
- One supervisor per missionary (not many-to-many)
- Admin-only: missionaries cannot see who their supervisor is in the UI
- Multi-select dropdown with search for the missionary picker when editing a supervisor
- Only users with mission_supervisor role see the assignment picker on their edit form
- Dropdown at the top of the dashboard page for missionary selector
- Defaults to "My Dashboard" (supervisor's own data)
- Admin sees all missionaries; supervisor sees only assigned missionaries
- Shows the selected missionary's saved tile layout (their personal arrangement)
- View-only when viewing another user's dashboard (no drag/rearrange)
- Combined view on all list pages: supervisor sees their own items + all assigned missionaries' items merged
- An "Owner" column shows which missionary each item belongs to
- Missionary filter added to the filter bar on list pages for supervisors/admins to narrow by missionary
- Full detail pages are visible (contacts, gifts, pledges, tasks, journals, prayers) but read-only for missionaries' data
- All edit/create buttons hidden when viewing a missionary's data
- Admin: sees all data, full write access (unchanged)
- Mission Supervisor: sees own data (full write) + assigned missionaries' data (read-only)
- Staff: sees only own data (full write, unchanged)
- Finance / Read-Only: unchanged behavior
- Immediate loss of access when a missionary is reassigned to a different supervisor
- Supervisor with no assigned missionaries behaves like staff (sees own data only)
- Supervisors can be supervised (a supervisor can be assigned to another supervisor)
- No transitive visibility: if Supervisor A oversees Supervisor B who oversees Missionaries C and D, Supervisor A sees only B's own data, NOT C and D's data

### Claude's Discretion
- Database model design (ForeignKey vs separate join table for supervisor assignment)
- Backend queryset filtering implementation approach
- Permission class structure for read-only enforcement
- Filter bar component integration details
- Owner column display format and positioning

### Deferred Ideas (OUT OF SCOPE)
- SUPV-05: Supervisor can view admin analytics dashboard scoped to their missionaries -- future phase
- SUPV-06: Supervisor assignment via bulk import (CSV/Smartsheet) -- future phase
- Transitive supervisor visibility (hierarchy cascade) -- future consideration
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SUPV-01 | Mission Supervisor role exists in the system (UserRole choice + migration) | Add `MISSION_SUPERVISOR = 'mission_supervisor', 'Mission Supervisor'` to `UserRole` TextChoices in `apps/users/models.py:13-20`, create migration, add `is_supervisor` property, add `supervisor` FK on User |
| SUPV-02 | Admin can assign missionaries to a supervisor via management UI | Extend `UserAdminUpdateSerializer` to accept `supervised_users` list, add multi-select search dropdown in AdminUsers.tsx edit form, show only when editing a mission_supervisor role user |
| SUPV-03 | Supervisor sees only their assigned missionaries' data across all pages | Update `get_queryset()` in all 8 app view files + dashboard/insights services to include supervisor scoping via `get_visible_user_ids()` helper; add `IsSupervisorReadOnly` permission class for write-gating |
| SUPV-04 | Admin and Supervisor can select a missionary and view their dashboard | Add `?user_id=` query param to dashboard API endpoints, add missionary selector dropdown on Dashboard.tsx, fetch target user's `dashboard_layout`, disable drag when viewing another user |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 5.1 | Backend framework | Already in use |
| Django REST Framework | 3.15 | API layer | Already in use |
| React | 18 | Frontend framework | Already in use |
| @tanstack/react-query | 5 | Data fetching | Already in use |
| nuqs | 2.x | URL state management | Already in use for filter params |
| shadcn/ui | latest | UI components | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-filter | 24.3 | Queryset filtering | Already in use for FilterSets |
| @dnd-kit | 6.x | Dashboard drag-and-drop | Already in use for dashboard tiles |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ForeignKey `supervisor` on User | Separate `SupervisorAssignment` join table | FK is simpler for one-supervisor-per-missionary; join table only needed for M2M which is explicitly excluded |
| Per-view role checks | Custom DRF mixin class | Mixin is cleaner but adds abstraction; per-view is consistent with existing codebase patterns |
| Centralized `get_visible_user_ids()` helper | Inline Q filters per view | Helper prevents duplication across 40+ methods; single point of change |

## Architecture Patterns

### Pattern 1: Supervisor FK on User Model
**What:** Add `supervisor = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='supervised_users')` to User model.
**When to use:** One supervisor per missionary, no M2M needed.
**Rationale:** The user decision locks this to one-supervisor-per-missionary. A self-referencing FK is the simplest model. `SET_NULL` ensures reassignment doesn't cascade-delete users. The `related_name='supervised_users'` lets us query `user.supervised_users.all()` to get a supervisor's assigned missionaries.

```python
# On User model:
supervisor = models.ForeignKey(
    'self', null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name='supervised_users',
    help_text='The supervisor assigned to this user (if any)'
)
```

### Pattern 2: Centralized Visibility Helper
**What:** A utility function that returns the set of user IDs whose data the requesting user can see.
**When to use:** Every `get_queryset()` method that performs role-based scoping.
**Rationale:** 40+ view methods need supervisor scoping. Duplicating the logic is error-prone. A single helper keeps it DRY and testable.

```python
# apps/core/permissions.py or apps/users/utils.py

def get_visible_user_ids(user):
    """Return set of user IDs whose data this user can see.

    - Admin/Finance/ReadOnly: returns None (meaning "all users")
    - Supervisor: returns {own_id} + {supervised user IDs}
    - Staff: returns {own_id}
    """
    if user.role in ['admin', 'finance', 'read_only']:
        return None  # sentinel for "all"

    if user.role == 'mission_supervisor':
        ids = {user.id}
        ids.update(
            user.supervised_users.filter(is_active=True)
            .values_list('id', flat=True)
        )
        return ids

    # Staff
    return {user.id}
```

### Pattern 3: Queryset Scoping Update
**What:** Replace existing role checks with visibility helper.
**When to use:** Every `get_queryset()` method.
**Current pattern (contacts):**
```python
def get_queryset(self):
    user = self.request.user
    if user.role in ['admin', 'finance', 'read_only']:
        queryset = Contact.objects.all()
    else:
        queryset = Contact.objects.filter(owner=user)
    return queryset
```
**New pattern (contacts):**
```python
def get_queryset(self):
    user = self.request.user
    visible_ids = get_visible_user_ids(user)
    if visible_ids is None:
        queryset = Contact.objects.all()
    else:
        queryset = Contact.objects.filter(owner_id__in=visible_ids)
    return queryset
```

### Pattern 4: Read-Only Enforcement for Supervised Data
**What:** Supervisor can write to own data but not to missionaries' data. Need object-level permission that blocks write operations on objects owned by supervised users.
**When to use:** Detail views with update/delete operations.
**Approach:** A custom permission class that allows writes only if the object's owner is the request user (or the user is admin).

```python
class IsSupervisorWriteRestricted(permissions.BasePermission):
    """
    Supervisor can read all visible data but only write to own data.
    Admin bypasses this check entirely.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.role == 'admin':
            return True
        # For write ops, the object must belong to the requesting user
        owner = getattr(obj, 'owner', None)
        if owner is None and hasattr(obj, 'contact'):
            owner = obj.contact.owner if hasattr(obj, 'contact') else None
        if owner is None and hasattr(obj, 'donor_contact'):
            owner = obj.donor_contact.owner
        if owner is None and hasattr(obj, 'journal'):
            owner = obj.journal.owner if hasattr(obj, 'journal') else None
        return owner == request.user
```

### Pattern 5: Dashboard Missionary Selector
**What:** A dropdown at the top of the Dashboard page that lets admin/supervisor select a missionary to view.
**When to use:** Dashboard page only.
**Approach:**
- Backend: Dashboard endpoints accept optional `?user_id=` param. If provided and the requesting user has visibility, return that user's dashboard data.
- Frontend: Dropdown shows "My Dashboard" + list of missionaries. When a missionary is selected, all dashboard API calls include `user_id`. Tile layout reads from the selected user's `dashboard_layout`. Drag-and-drop is disabled.

### Pattern 6: Owner Column on List Pages
**What:** Add an "Owner" column to list page tables that shows which missionary each item belongs to.
**When to use:** All list pages when user is supervisor or admin.
**Approach:**
- Backend: Ensure `owner` (or the owner relation) is included in serializer response. Most list serializers already include owner info via `select_related('owner')`.
- Frontend: Conditionally show an "Owner" column when `user.role === 'admin' || user.role === 'mission_supervisor'`.

### Anti-Patterns to Avoid
- **Checking `user.role == 'mission_supervisor'` individually in each view:** Use the centralized helper instead.
- **Allowing supervisors to write missionaries' data:** The user decision explicitly states read-only for supervised data. Write operations on another user's data must be blocked.
- **Adding supervisor to the `['admin', 'finance', 'read_only']` "see all" lists:** Supervisor does NOT see all data. It sees a scoped subset. Never add it to the "all data" role arrays.
- **Transitive visibility:** Even if supervisor B is supervised by supervisor A, A only sees B's own data, not B's supervised users' data. The `get_visible_user_ids` helper must NOT recurse.

## Inventory of Files Requiring Changes

### Backend - Views with `get_queryset()` Role Checks
All files below have methods that check `user.role` to scope querysets:

| File | Methods to Update | Scoping Pattern |
|------|-------------------|-----------------|
| `apps/contacts/views.py` | `ContactListCreateView.get_queryset`, `ContactDetailView.get_queryset`, `ContactThankView.post`, `ContactGiftsView.get_queryset`, `ContactRecurringGiftsView.get_queryset`, `ContactTasksView.get_queryset`, `ContactEmailsView.get`, `ContactSearchView.get_queryset`, `ContactJournalsView.get_queryset`, `ContactPrayerIntentionsView.get_queryset`, `ContactJournalEventsView.get_queryset` | `owner=user` -> `owner_id__in=visible_ids` |
| `apps/gifts/views.py` | `GiftListCreateView.get_queryset`, `GiftDetailView.get_queryset`, `RecurringGiftListCreateView.get_queryset`, `RecurringGiftDetailView.get_queryset` | `donor_contact__owner=user` -> `donor_contact__owner_id__in=visible_ids` |
| `apps/tasks/views.py` | `TaskListCreateView.get_queryset`, `TaskDetailView.get_queryset`, `TaskCompleteView.post`, `OverdueTasksView.get_queryset`, `UpcomingTasksView.get_queryset` | `owner=user` -> `owner_id__in=visible_ids` |
| `apps/journals/views.py` | `JournalListCreateView.get_queryset`, `JournalDetailView.get_queryset`, `JournalStageEventListCreateView.get_queryset`, `JournalStageEventDeleteByStageView.delete`, `JournalContactListCreateView.get_queryset`, `JournalContactDestroyView.get_queryset`, `DecisionListCreateView.get_queryset`, `DecisionDetailView.get_queryset`, `DecisionHistoryListView.get_queryset`, `NextStepListCreateView.get_queryset`, `NextStepDetailView.get_queryset`, `JournalAnalyticsViewSet` (6 actions) | `journal__owner=user` -> `journal__owner_id__in=visible_ids` |
| `apps/prayers/views.py` | `_owner_scoped_queryset`, `TodaysFocusView.get_queryset` | `contact__owner=user` -> `contact__owner_id__in=visible_ids` |
| `apps/events/views.py` | `EventListView.get_queryset`, `EventDetailView.get_queryset` | `user=user` -> scoped by visible users |
| `apps/groups/views.py` | `GroupListCreateView.get_queryset`, `GroupDetailView.get_queryset`, `GroupContactsView.get_group` | `owner=user` -> `owner_id__in=visible_ids` |
| `apps/dashboard/services.py` | `get_needs_attention`, `get_thank_you_queue`, `get_support_progress`, `get_recent_gifts`, `get_giving_summary`, `get_monthly_gifts`, `get_dashboard_summary` | All accept `user` param; need to accept optional `target_user` for missionary selector |
| `apps/insights/services.py` | `_scope_gifts`, `_scope_recurring_gifts`, `_scope_tasks` | Add supervisor scoping to these helpers |

### Backend - Models & Serializers
| File | Changes |
|------|---------|
| `apps/users/models.py` | Add `MISSION_SUPERVISOR` to `UserRole`, add `supervisor` FK, add `is_supervisor` property, add `is_mission_supervisor` property |
| `apps/users/serializers.py` | Add `supervised_users` to `UserAdminUpdateSerializer`, add `supervisor` to `UserSerializer`, update `CurrentUserSerializer` to include `supervised_users` list for supervisors |
| `apps/core/permissions.py` | Add `get_visible_user_ids()` helper, add/update permission classes for supervisor write restriction |

### Backend - Migrations
| File | Changes |
|------|---------|
| `apps/users/migrations/0004_*.py` | Add `mission_supervisor` to UserRole choices, add `supervisor` FK |

### Frontend - Types & API
| File | Changes |
|------|---------|
| `frontend/src/api/users.ts` | Add `'mission_supervisor'` to `UserRole` type, add `supervised_users` field to `User` interface, add `supervisor` field |
| `frontend/src/api/auth.ts` | Add `'mission_supervisor'` to `User.role` union type |
| `frontend/src/api/dashboard.ts` | Add optional `userId` param to dashboard API functions |

### Frontend - Pages & Components
| File | Changes |
|------|---------|
| `frontend/src/pages/admin/AdminUsers.tsx` | Add missionary assignment multi-select when editing supervisor role user, add `mission_supervisor` to role variants/labels |
| `frontend/src/pages/Dashboard.tsx` | Add missionary selector dropdown, support `?user_id=` URL param, disable drag when viewing another user |
| `frontend/src/components/auth/ProtectedRoute.tsx` | Add `mission_supervisor` to `roleHierarchy` (level 3, between staff and admin) |
| `frontend/src/components/layout/Sidebar.tsx` | Add `mission_supervisor` to `roleHierarchy`, potentially show Admin link for supervisors (limited) |
| `frontend/src/pages/contacts/ContactList.tsx` | Show owner filter for supervisors (not just admin), add Owner column |
| `frontend/src/pages/donations/DonationList.tsx` | Show owner filter for supervisors, add Owner column |
| `frontend/src/pages/pledges/PledgeList.tsx` | Add Owner column for supervisors |
| `frontend/src/pages/tasks/TaskList.tsx` | Add Owner column for supervisors |
| `frontend/src/pages/journals/JournalList.tsx` | Add Owner column for supervisors |
| `frontend/src/pages/prayer/PrayerList.tsx` | Add Owner column for supervisors |
| `frontend/src/hooks/useFilterParams.ts` | Already has `owner` parser in most filter sets -- good |
| All detail pages | Hide edit/create/delete buttons when viewing another user's data |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Role-based queryset scoping | Per-view if/else chains for supervisor | Centralized `get_visible_user_ids()` helper | 40+ methods need the same logic; DRY prevents bugs |
| Multi-select dropdown with search | Custom dropdown component | Existing shadcn/ui `Combobox` or `Command` + `Popover` pattern | shadcn already supports searchable multi-select |
| Object-level write gating | Manual checks in each update view | DRF `BasePermission` subclass | Consistent enforcement, hard to forget |

**Key insight:** The codebase already has all the UI primitives needed (DropdownMenu, Dialog, FilterBar, useFilterParams). The work is wiring them together with the new role logic, not building new components.

## Common Pitfalls

### Pitfall 1: Forgetting a View Method
**What goes wrong:** One `get_queryset()` method is missed and supervisors can see all data or no data on that page.
**Why it happens:** 40+ methods across 8+ files need updating.
**How to avoid:** Use the inventory table above as a checklist. Grep for all `user.role` checks and `get_queryset` overrides. The centralized helper makes it possible to test coverage.
**Warning signs:** A page shows no data for supervisor, or shows all org data.

### Pitfall 2: Supervisor Writes to Missionary Data
**What goes wrong:** Supervisor can edit/delete a missionary's contact, journal, or task.
**Why it happens:** Queryset scoping allows visibility but doesn't block writes. Detail views with update/destroy need object-level permission.
**How to avoid:** Add `IsSupervisorWriteRestricted` permission to all detail views. Frontend hides edit/delete buttons for supervised data, but backend must enforce it too.
**Warning signs:** PATCH/PUT/DELETE succeeds on another user's object.

### Pitfall 3: roleHierarchy Ordering in Frontend
**What goes wrong:** `ProtectedRoute` blocks supervisor from pages they should access, or allows access where they shouldn't.
**Why it happens:** The existing `roleHierarchy` is `{ admin: 4, finance: 3, staff: 2, read_only: 1 }`. Supervisor needs to be inserted correctly.
**How to avoid:** Supervisor should be at level 3 (same as finance) or between staff and admin. Since supervisor can access all pages that staff can, plus see missionaries' data, it should be `>= staff`. But supervisor should NOT have finance access. This hierarchy is only for page-level access, not data scoping.
**Recommendation:** `{ admin: 5, mission_supervisor: 4, finance: 3, staff: 2, read_only: 1 }` -- supervisor above finance since supervisor needs broader UI access.

### Pitfall 4: Dashboard User Selector Caching
**What goes wrong:** Switching between missionary dashboards shows stale data from the previously selected user.
**Why it happens:** React Query caches by query key. If `user_id` is not in the key, stale cache is returned.
**How to avoid:** Include `userId` in all dashboard query keys: `["dashboard", "summary", userId]`. The existing `staleTime: 2min` on dashboard queries will handle re-fetching.
**Warning signs:** Dashboard shows wrong user's data after switching.

### Pitfall 5: N+1 Query on supervised_users
**What goes wrong:** Every API call triggers a DB query to fetch supervised user IDs.
**Why it happens:** `get_visible_user_ids()` queries `user.supervised_users.values_list('id')` each time.
**How to avoid:** Cache the result on the request object or use `select_related`/`prefetch_related` in auth middleware. Alternatively, since the set is small (typically <20 missionaries), the single query is fast and acceptable without caching.
**Recommendation:** Accept the single query per request for now. If profiling shows it's a problem, add caching to the request object.

### Pitfall 6: The "owner" Filter Query Param Collision
**What goes wrong:** The existing `owner` filter on contacts/gifts list pages is admin-only (hardcoded `if user.role == 'admin'`). Supervisor needs access too.
**Why it happens:** Current code explicitly checks `user.role == 'admin'` before applying the owner filter.
**How to avoid:** Expand the check to `user.role in ['admin', 'mission_supervisor']`. For supervisor, validate that the filtered owner_id is in their `get_visible_user_ids()` set.

### Pitfall 7: Dashboard Layout Save When Viewing Another User
**What goes wrong:** Supervisor drags tiles while viewing missionary's dashboard, overwriting the missionary's saved layout.
**Why it happens:** `saveDashboardLayout()` PATCHes `/users/me/` -- always saves to the requesting user.
**How to avoid:** Disable drag entirely when viewing another user's dashboard (user decision: "View-only when viewing another user's dashboard"). Frontend must check `selectedUserId !== currentUser.id` and disable DnD.

## Code Examples

### UserRole Update
```python
# apps/users/models.py
class UserRole(models.TextChoices):
    STAFF = 'staff', 'Staff'
    ADMIN = 'admin', 'Admin'
    FINANCE = 'finance', 'Finance'
    READ_ONLY = 'read_only', 'Read Only'
    MISSION_SUPERVISOR = 'mission_supervisor', 'Mission Supervisor'
```

### Supervisor FK
```python
# apps/users/models.py - User model
supervisor = models.ForeignKey(
    'self',
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name='supervised_users',
    help_text='The supervisor assigned to this user'
)

@property
def is_mission_supervisor(self):
    return self.role == UserRole.MISSION_SUPERVISOR
```

### Visibility Helper
```python
# apps/core/permissions.py
def get_visible_user_ids(user):
    """Return user IDs whose data this user can see, or None for 'all'."""
    if user.role in ['admin', 'finance', 'read_only']:
        return None
    if user.role == 'mission_supervisor':
        ids = set(
            user.supervised_users
            .filter(is_active=True)
            .values_list('id', flat=True)
        )
        ids.add(user.id)
        return ids
    return {user.id}
```

### Updated Contact View
```python
# apps/contacts/views.py
from apps.core.permissions import get_visible_user_ids

class ContactListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        user = self.request.user
        visible = get_visible_user_ids(user)
        if visible is None:
            queryset = Contact.objects.all()
        else:
            queryset = Contact.objects.filter(owner_id__in=visible)

        # Owner filter for admin/supervisor
        owner_id = self.request.query_params.get('owner')
        if owner_id and user.role in ['admin', 'mission_supervisor']:
            if visible is None or int(owner_id) in visible:
                queryset = queryset.filter(owner_id=owner_id)

        return queryset.select_related('owner')
```

### Dashboard Endpoint with User Selector
```python
# apps/dashboard/views.py
class DashboardView(APIView):
    def get(self, request):
        user = request.user
        target_user_id = request.query_params.get('user_id')

        if target_user_id and str(target_user_id) != str(user.id):
            visible = get_visible_user_ids(user)
            if visible is not None and uuid.UUID(target_user_id) not in visible:
                return Response({'detail': 'Forbidden'}, status=403)
            target_user = User.objects.get(id=target_user_id)
        else:
            target_user = user

        data = get_dashboard_summary(target_user)
        return Response(data)
```

### Frontend Type Update
```typescript
// frontend/src/api/users.ts
export type UserRole = "admin" | "staff" | "finance" | "read_only" | "mission_supervisor"

export interface User {
  // ... existing fields
  supervisor?: string | null      // supervisor user ID
  supervised_users?: string[]     // IDs of supervised missionaries (if supervisor)
}

export const userRoleLabels: Record<UserRole, string> = {
  admin: "Administrator",
  staff: "Staff",
  finance: "Finance",
  read_only: "Read Only",
  mission_supervisor: "Mission Supervisor",
}
```

### Frontend Role Hierarchy Update
```typescript
// frontend/src/components/auth/ProtectedRoute.tsx
const roleHierarchy: Record<string, number> = {
  admin: 5,
  mission_supervisor: 4,
  finance: 3,
  staff: 2,
  read_only: 1,
}
```

### Dashboard Missionary Selector
```typescript
// frontend/src/pages/Dashboard.tsx (conceptual)
const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
const isSupervisorOrAdmin = user?.role === 'admin' || user?.role === 'mission_supervisor'
const isViewingOther = selectedUserId && selectedUserId !== user?.id
const effectiveUserId = selectedUserId || user?.id

// Pass to query hooks
const { data } = useDashboardSummary(effectiveUserId)

// Disable drag when viewing another user
const isDragEnabled = !isViewingOther
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline role checks per view | Centralized visibility helper | This phase | Consistent scoping across 40+ views |
| 4-role system (Admin/Staff/Finance/ReadOnly) | 5-role system with supervisor | This phase | New access tier between staff and admin |
| Dashboard always shows own data | Dashboard supports viewing any visible user's data | This phase | Supervisor/admin can inspect missionary dashboards |

## Open Questions

1. **Supervisor in role hierarchy for ProtectedRoute**
   - What we know: Supervisor needs UI access to all pages staff can access, plus the missionary selector on dashboard. Supervisor should NOT access admin-only pages (user management, admin analytics).
   - What's unclear: Should supervisor see the Admin nav link? The user decision says supervisor assignment is admin-only, so supervisors don't manage users. The admin analytics (SUPV-05) is deferred.
   - Recommendation: Do NOT show Admin nav link to supervisors. Supervisor accesses all non-admin pages. Set hierarchy level to 4 (above finance) but admin-requiring routes remain `requiredRole="admin"`.

2. **How to expose supervised_users in the API**
   - What we know: Admin needs to assign missionaries when editing a supervisor. The frontend needs the list of supervised users to populate the selector.
   - What's unclear: Should `supervised_users` be on the UserSerializer (list endpoint), CurrentUserSerializer (me endpoint), or both?
   - Recommendation: Include `supervised_users` (as list of user IDs) on `CurrentUserSerializer` so the dashboard can build the missionary selector dropdown. Include it on `UserAdminUpdateSerializer` for the assignment form. On the list endpoint, include a `supervised_user_count` annotation to keep the payload small.

3. **owner_id column type (UUID vs int)**
   - What we know: User model uses UUID primary keys (AbstractBaseUser with UUID pk based on `uuid:pk` in URLs).
   - What's unclear: Whether `get_visible_user_ids` returns UUIDs or ints.
   - Recommendation: It returns UUIDs since User PK is UUID. Use `owner_id__in=visible_ids` which works natively with Django's UUID field.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of all view files, models, serializers, permissions, and frontend components
- `apps/users/models.py` - existing UserRole, User model structure
- `apps/core/permissions.py` - existing permission classes and role-checking patterns
- All `apps/*/views.py` files - queryset scoping patterns catalogued
- `frontend/src/` - role rendering, routing, filter infrastructure

### Secondary (MEDIUM confidence)
- Django docs on self-referencing ForeignKey with `on_delete=SET_NULL` and `related_name`
- DRF docs on object-level permissions via `has_object_permission`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries needed, all existing infrastructure sufficient
- Architecture: HIGH - patterns directly extend existing codebase conventions with minimal invention
- Pitfalls: HIGH - comprehensive analysis of 40+ view methods with concrete inventory of all changes needed

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable domain, no external dependencies)
