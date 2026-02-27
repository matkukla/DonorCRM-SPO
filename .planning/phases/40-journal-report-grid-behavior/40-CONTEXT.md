# Phase 40: Journal Report & Grid Behavior - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Rebuild the journal report component with new activity-focused metrics and charts, and make grid stage checkboxes directly clickable (currently read-only, requiring the detail panel to change stages). Report lives in the existing Reports section on the individual journal page. No new pages or routes.

</domain>

<decisions>
## Implementation Decisions

### Journal Report Content
- Primary purpose is **activity summary** — what the missionary has been doing
- Key metrics: stage movements, decisions & gifts, activity volume (journal entries created, tasks completed, notes added)
- **No** contact-level detail — aggregates only (totals and counts)
- Contact counts by stage are excluded from headline metrics

### Report Layout & Presentation
- **Full rebuild** of the current report — tear down and rebuild from scratch
- Stays in the existing Reports section on the individual journal page
- Screen-only — no print or PDF export needed
- Single journal scope — report always shows data for the journal being viewed
- Admin navigates to a user's journal page to see their report (existing journal page access pattern)

### Grid Checkbox Behavior
- Currently checkboxes are read-only; changing stages requires opening the contact detail panel
- New behavior: **instant toggle** — click saves immediately, no confirmation dialog, no undo toast
- Each stage column has its own checkbox — clicking it marks that stage as reached for the contact
- **Independent toggles** — stages can be checked in any order, checking stage 4 does NOT auto-check stages 1-3

### Report Filtering & Scope
- Custom date range picker with presets (Last 7 days, Last 30 days, This month, etc.)
- Regular users see their own journal report; admins can see any user's journal report
- Admin accesses other users' reports from the journal page itself (not a separate admin view)

### Claude's Discretion
- Whether to include charts/visualizations or keep it tables-only — pick what adds clarity for the data
- Whether to include stage filtering (e.g., show only specific stage movements) — decide based on what makes sense for the chosen metrics
- Visual design, spacing, and component choices for the rebuilt report
- Loading states and empty states for the report

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 40-journal-report-grid-behavior*
*Context gathered: 2026-02-27*
