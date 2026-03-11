# Phase 42: Mission Supervisor Role - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Organization leadership can assign supervisors to missionaries, and supervisors see only their assigned missionaries' data across the entire application. Three access tiers: Admin (all data), Mission Supervisor (own data + assigned missionaries' data read-only), Staff/Missionary (own data only). The dashboard gains a missionary selector for admin and supervisors. This phase does NOT include transitive supervision, analytics scoping (SUPV-05), or bulk import (SUPV-06).

</domain>

<decisions>
## Implementation Decisions

### Supervisor-Missionary Assignment UI
- Assignment lives on the user edit form in admin user management (not a separate page)
- One supervisor per missionary (not many-to-many)
- Admin-only: missionaries cannot see who their supervisor is in the UI
- Multi-select dropdown with search for the missionary picker when editing a supervisor
- Only users with mission_supervisor role see the assignment picker on their edit form

### Dashboard Missionary Selector
- Dropdown at the top of the dashboard page
- Defaults to "My Dashboard" (supervisor's own data)
- Admin sees all missionaries; supervisor sees only assigned missionaries
- Shows the selected missionary's saved tile layout (their personal arrangement)
- View-only when viewing another user's dashboard (no drag/rearrange)

### Data Scoping Behavior
- Combined view on all list pages: supervisor sees their own items + all assigned missionaries' items merged
- An "Owner" column shows which missionary each item belongs to
- Missionary filter added to the filter bar on list pages for supervisors/admins to narrow by missionary
- Full detail pages are visible (contacts, gifts, pledges, tasks, journals, prayers) but read-only for missionaries' data
- All edit/create buttons hidden when viewing a missionary's data

### Access Tiers
- Admin: sees all data, full write access (unchanged)
- Mission Supervisor: sees own data (full write) + assigned missionaries' data (read-only)
- Staff: sees only own data (full write, unchanged)
- Finance / Read-Only: unchanged behavior

### Role Transitions & Edge Cases
- Immediate loss of access when a missionary is reassigned to a different supervisor
- Supervisor with no assigned missionaries behaves like staff (sees own data only, dashboard selector shows only "My Dashboard")
- Supervisors can be supervised (a supervisor can be assigned to another supervisor)
- No transitive visibility: if Supervisor A oversees Supervisor B who oversees Missionaries C and D, Supervisor A sees only B's own data, NOT C and D's data

### Claude's Discretion
- Database model design (ForeignKey vs separate join table for supervisor assignment)
- Backend queryset filtering implementation approach
- Permission class structure for read-only enforcement
- Filter bar component integration details
- Owner column display format and positioning

</decisions>

<specifics>
## Specific Ideas

- The three-tier access model should be consistent: Admin > Supervisor > Staff, applied uniformly across all pages
- The missionary filter in the filter bar should use the same searchable dropdown pattern as the assignment picker
- When supervisor has own data, it should be seamlessly mixed with missionaries' data on list pages (not a separate section)

</specifics>

<deferred>
## Deferred Ideas

- SUPV-05: Supervisor can view admin analytics dashboard scoped to their missionaries — future phase
- SUPV-06: Supervisor assignment via bulk import (CSV/Smartsheet) — future phase
- Transitive supervisor visibility (hierarchy cascade) — future consideration if organizational needs grow

</deferred>

---

*Phase: 42-mission-supervisor-role*
*Context gathered: 2026-03-02*
