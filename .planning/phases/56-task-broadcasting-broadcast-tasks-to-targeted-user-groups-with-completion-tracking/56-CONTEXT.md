# Phase 56: Task Broadcasting - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Full-stack implementation of a broadcast task system: admins and supervisors create tasks distributed to targeted groups of users. Each recipient gets their own Task copy in their regular Tasks tab. The sender can track completion across all recipients via dedicated tracking views (admin: /admin/broadcasts page; supervisor: section on Team page).

</domain>

<decisions>
## Implementation Decisions

### Broadcast Task UI & Placement
- Separate "Broadcast Task" button next to existing "New Task" button on Tasks page — visible only to admin and supervisor roles
- Broadcast tasks visually distinguished in task list with Megaphone icon badge + "Assigned by [Name]" subtitle text
- Broadcast creation form uses a dialog (same pattern as TaskForm) — consistent with existing task creation flow
- Confirmation dialog before sending: "This will create a task for X users. Proceed?"

### Tracking View Architecture
- Admin broadcast tracking: new "/admin/broadcasts" page linked from Admin sidebar section
- Supervisor broadcast tracking: new section on Team page ("Broadcast Tasks" below existing team content)
- Completion progress displayed as fraction + mini progress bar ("28/40" with colored bar) — compact, scannable
- Broadcast detail uses DataTable with sort/filter for per-user status — consistent with all other list views

### Target Selection & Scope
- Supervisor target options: "My Team" radio (all supervised) + "Specific Members" with multi-select — mirrors admin's pattern
- Admin can target "All Missionaries", "All Supervisors", or "Specific Users"
- Recipient list locked at send time — edit only changes task content (title, description, due_date, priority), not recipients
- Completed broadcast task copies remain visible to missionary after broadcast is cancelled (historical record)

### Claude's Discretion
- Exact BroadcastTask model field specs (follow existing Task model conventions)
- Service function organization (new services.py or extend existing)
- Broadcast API serializer structure
- View As integration details (broadcast copies are regular tasks — should work automatically)
- Event creation for new broadcast tasks (follow existing event patterns if straightforward)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Task model (apps/tasks/models.py): TimeStampedModel base, UUID PK, owner FK, status/priority choices, mark_complete(user) method
- TaskSerializer / TaskCreateSerializer (apps/tasks/serializers.py): full field set, owner auto-assignment
- TaskFilterSet (apps/tasks/filters.py): status, type, priority, date range, contact, owner filters
- useTasks hooks (frontend/src/hooks/useTasks.ts): CRUD hooks with React Query invalidation of ["tasks"], ["dashboard"]
- tasks.ts API (frontend/src/api/tasks.ts): typed API functions, label maps
- TaskList.tsx: DataTable with filters, pagination, role-based owner column
- TaskForm.tsx: dialog-based create/edit with contact selector
- TeamPage.tsx: supervisor team view — will host broadcast tracking section

### Established Patterns
- Data scoping: get_visible_user_ids(user, request=request) returns set of IDs or None
- View As: X-View-As-User-Id header, request.view_as_user attribute in middleware
- Ownership: owner FK on Task, scoped by visible user IDs in list views
- Permission classes: IsAuthenticated, IsOwnerOrAdmin, IsSupervisorWriteRestricted
- M2M relationships: user.supervised_users (reverse of supervisors M2M), user.coached_users
- Role checks: user.role in ['admin', 'supervisor', 'missionary', 'coach', 'finance', 'read_only']
- Dashboard needs-attention: queries Task with status in [PENDING, IN_PROGRESS] and due_date filters — broadcast copies will appear automatically since they're regular Tasks with owner set

### Integration Points
- apps/tasks/urls.py: add broadcast URL patterns
- config/api_urls.py: tasks/ already included
- frontend/src/App.tsx: add /admin/broadcasts route
- frontend/src/components/layout/Sidebar.tsx: add Broadcasts link under Admin section
- frontend/src/pages/team/TeamPage.tsx: add broadcast tracking section
- frontend/src/pages/tasks/TaskList.tsx: add broadcast badge and "Broadcast Task" button

</code_context>

<specifics>
## Specific Ideas

From GitHub Issue #32:
- SPO sends monthly MPD tasks (newsletter, text partners, Christmas cards, etc.) — this replaces manual Smartsheet tracking
- Acceptance criteria explicitly require: admin broadcast, needs-attention integration, supervisor team tracking, admin completion tracking, visual distinction in Tasks tab
- Priority: P1 — needed before pilot launch
- Broadcast edit cascades to incomplete copies only; completed copies are untouched
- Cancel removes incomplete copies, keeps completed ones
- Supervisor can only target their supervised missionaries (enforced server-side)
- Missionary can only mark complete (no edit/delete on broadcast tasks)

</specifics>

<deferred>
## Deferred Ideas

- Recurring broadcasts (monthly auto-send) — would need a scheduler
- Broadcast templates (save and reuse common task patterns)
- Email/push notifications when broadcast is sent
- Broadcast analytics over time (completion rate trends)

</deferred>
