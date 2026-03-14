# Phase 51: Data Scoping — Admin & Supervisor Default to Own Data - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Change the default data visibility for admin and supervisor roles so they see only their own data (contacts, gifts, journals, tasks, prayers, dashboard personal tiles) — identical to missionary behavior. Cross-user data access only activates when a View As session is explicitly started (Phases 52–53). No frontend changes in this phase.

</domain>

<decisions>
## Implementation Decisions

### Roles affected
- `admin` role: changes from `None` (all data) → `{user.id}` (own data only)
- `supervisor` role: changes from `{own_id} + supervised IDs` → `{user.id}` (own data only)
- `finance` and `read_only` roles: **unchanged** — they continue to return `None` (see all data). Requirements SCOPE-01/SCOPE-02 only target admin and supervisor.
- The change is a single-function update to `get_visible_user_ids()` in `apps/core/permissions.py`

### Admin Analytics carve-out
- Admin Analytics / Insights services (`apps/insights/services.py`) use separate cross-user functions with no user parameter — these are intentional aggregate views and must remain untouched
- MPD Overview tile (Phase 48) also uses all-users aggregation — leave unchanged
- Admin's personal Dashboard tiles (Support Progress, Monthly Average, event counts) DO call `get_visible_user_ids()` — after this change, admin sees only their own MPD stats on the Dashboard, same as a missionary. This is the intended behavior per SCOPE-01.

### Object-level permissions (IsOwnerOrAdmin)
- `IsOwnerOrAdmin` permission class stays unchanged — admin can still access any individual object by direct URL
- Only list view queryset scoping changes (what shows up in lists/searches/exports)
- This is acceptable: View As (Phases 52–53) will provide the proper mechanism for cross-user object access

### Owner filter param (`?owner=`)
- The `?owner=<id>` query param on list views and export views stays in place — needed for View As in Phase 53
- After Phase 51, passing `?owner=<other-user-id>` naturally returns empty results since other users are outside the visible set — no special error handling needed
- No code changes to the owner param handling; the queryset fix handles it automatically
- Export views (contacts, gifts, journals, tasks) follow the same treatment — exports scope to own data after the queryset change

### Frontend
- Phase 51 is backend-only — no frontend changes
- Owner filter dropdowns on list pages (Contacts, Journals, Gifts) remain in the UI; they will return empty results for non-self owners but are left for Phase 53 to refactor into the View As mechanism

### Claude's Discretion
- Whether to add a docstring update to `get_visible_user_ids()` noting the new behavior
- Test approach for verifying the scoping change (unit test on the function or integration test on a view)

</decisions>

<specifics>
## Specific Ideas

- The change is surgical: `get_visible_user_ids()` is the single choke point for all list view scoping across every app (contacts, gifts, journals, tasks, prayers, groups, events, dashboard, insights, imports). Changing it there cascades everywhere with no per-view changes needed.
- No migration required — this is a pure Python/permissions change.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/core/permissions.py` → `get_visible_user_ids(user)`: The single function to modify. Currently: admin/finance/read_only → `None`; supervisor → `{own_id} + supervised IDs`; coach → `{own_id} + coached IDs`; missionary → `{own_id}`. After change: admin → `{user.id}`, supervisor → `{user.id}`.

### Established Patterns
- `visible is None` sentinel: Every view that calls `get_visible_user_ids()` checks `if visible is None: queryset = Model.objects.all()`. After Phase 51, admin/supervisor will never return `None`, so those branches become dead code for those roles — but the branches themselves stay (finance/read_only still use them).
- Owner filter security: The `?owner=` param check pattern is `if visible is None or int(owner_id) in visible` — after Phase 51 this naturally restricts admin/supervisor to only their own owner ID.

### Integration Points
- `apps/core/permissions.py` lines 20–40: `get_visible_user_ids()` — the only file that needs changing
- Callers (no changes needed): `apps/contacts/views.py`, `apps/contacts/export_views.py`, `apps/journals/views.py`, `apps/journals/export_views.py`, `apps/gifts/views.py`, `apps/gifts/export_views.py`, `apps/tasks/views.py`, `apps/tasks/export_views.py`, `apps/prayers/views.py`, `apps/groups/views.py`, `apps/events/views.py`, `apps/dashboard/views.py`, `apps/dashboard/services.py`, `apps/insights/services.py` (the user-scoped functions only)
- `apps/insights/services.py` cross-user functions (lines 273+, 654+, 870+): No user parameter — NOT affected by `get_visible_user_ids()` change

</code_context>

<deferred>
## Deferred Ideas

- Owner filter dropdown UI cleanup (Contacts, Journals, Gifts pages) — Phase 53 (View As frontend will repurpose it)
- Scoping `finance` and `read_only` roles to own data — not in requirements, defer to v2.4+ if needed

</deferred>

---

*Phase: 51-data-scoping-admin-supervisor-default-to-own-data*
*Context gathered: 2026-03-13*
