# Phase 46: Multiple Supervisors per Missionary - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Change the supervisor and coach relationships from one-to-one (ForeignKey) to many-to-many, so a missionary can be assigned to multiple supervisors and multiple coaches simultaneously. Includes data migration, updated assignment UI, and updated data scoping logic. No new pages — all changes are within existing Admin > Assignments, Admin > Users, and list/detail page scoping.

</domain>

<decisions>
## Implementation Decisions

### Scope — which relationships change
- Both supervisor and coach relationships become many-to-many (not just supervisors)
- A single user can hold both supervisor and coach roles for the same missionary (allowed)
- No hard limit on supervisors/coaches per missionary — soft UI guidance only (warn if count seems high, e.g. 5+), no enforcement
- When a user's role is changed away from supervisor or coach, their missionary assignments are automatically cleared (auto-unassign on role change)

### Assignment UI — Assignments page
- Replace the single-select dropdowns with multi-select dropdowns (chip/tag style) for both supervisor and coach columns
- Uses the same searchable multi-select pattern already present in the user edit form
- Selected supervisors/coaches appear as removable chips in the table cell
- Bulk assignment is additive: bulk action adds selected supervisor(s)/coach(es) to missionaries' existing assignments without replacing them
- Assignments page gains a toggle to switch between two views:
  - **Missionary view** (current default): rows are missionaries, columns are their supervisors/coaches
  - **Supervisor view**: rows are supervisors, showing all missionaries assigned to each

### Assignment UI — User detail page
- Supervisor and coach user detail pages show a read-only list of missionaries currently assigned to them
- Visible in Admin > Users > [supervisor/coach user]

### Data scoping behavior
- All assigned supervisors independently see a missionary's data — additive, no primary/secondary distinction
- Each supervisor's list page and dashboard selector shows their own assigned set (Sup1 sees [A, B], Sup2 sees [A, C] — no cross-supervisor info displayed)
- Supervisors cannot see who else supervises a shared missionary (no cross-supervisor visibility)
- Owner column on list pages is unchanged — still shows the missionary's name, no indicator of multiple supervisors

### Migration
- Auto-migrate: existing ForeignKey assignments are copied into the new M2M join tables during the migration
- No admin action required — existing assignments are silently preserved
- After data is copied to M2M, the old ForeignKey columns (supervisor_id, coach_id) are dropped — clean break, no backward-compatibility shim
- Join table design (through model vs auto-generated M2M) is Claude's discretion

### Claude's Discretion
- M2M join table structure (explicit through model with timestamps vs Django auto-generated)
- Backend queryset update for scoping (how to query M2M supervisors instead of ForeignKey)
- Soft limit UX implementation detail (warning threshold and display)
- API serializer structure for M2M supervisor/coach fields

</decisions>

<specifics>
## Specific Ideas

- The multi-select chip pattern for the Assignments table should match the existing supervisee picker in the user edit form (Phase 42 established this pattern)
- The supervisor-view toggle on Assignments page is useful for org-level planning (seeing which supervisor has how many missionaries)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AdminAssignments.tsx`: Current assignments page with single-select dropdowns — needs multi-select upgrade for both supervisor and coach columns
- `UserAdminUpdateSerializer`: Already handles `supervised_user_ids` and `coached_user_ids` as list fields — the serializer pattern exists, needs updating for M2M reads too
- `views_assignments.py`: `AssignmentsView` GET/PATCH — needs to return arrays instead of single IDs, and accept arrays for updates
- `CurrentUserSerializer.get_supervised_users`: Returns list of supervised users — pattern can be reused for M2M queries

### Established Patterns
- Multi-select with search already used in user edit form (Phase 42) — reuse for Assignments table
- Chip/tag display pattern already exists in the UI — use for selected supervisors/coaches in table cells
- Queryset scoping via `supervised_users` related manager already in `can_view_contact()` — same pattern for list view filtering, just changes from ForeignKey to M2M traversal

### Integration Points
- `apps/users/models.py` — User model: replace `supervisor = ForeignKey(self)` and `coach = ForeignKey(self)` with ManyToManyFields; remove `supervisor_id`/`coach_id` columns
- `apps/users/serializers.py` — `UserSerializer`, `UserAdminUpdateSerializer`, `CurrentUserSerializer` all reference supervisor/coach fields
- `apps/users/views_assignments.py` — `AssignmentsView` GET returns `supervisor_id`/`coach_id` (scalars); PATCH accepts them — both need to become arrays
- All queryset filters across contacts, gifts, pledges, tasks, journals, prayers that use `supervisor__supervised_users` or equivalent ForeignKey traversal — need M2M update
- `frontend/src/hooks/useUsers.ts` + `frontend/src/api/users.ts` — API types for assignments need to change from single ID to array

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 46-multiple-supervisors-per-missionary*
*Context gathered: 2026-03-07*
