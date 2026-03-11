# Phase 38: UI Polish & List Page Cleanup - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean up UI inconsistencies across list pages, dialogs, and analytics. Center all modal dialogs, rename "Prospect" to "Potential Donor", modify gift/pledge list columns, and remove Review Queue + heat map from analytics dashboard. All frontend changes + minor backend display string update. No new features or capabilities.

</domain>

<decisions>
## Implementation Decisions

### Gift Type Column
- Add a NEW `payment_type` field to the Gift model with exactly 3 choices: Credit Card, Direct Deposit, Check
- Field is optional (blank allowed) — imported gifts without a type show "---" in the column
- Remove Fund and Description columns from the gifts list page
- Add Type as both a visible column AND a FilterBar filter option
- Empty cells display "---" consistent with existing patterns

### Analytics Cleanup
- Full removal: delete backend views (ReviewQueueView, ActivityHeatmapView), frontend components, and @uiw/react-heat-map package if unused elsewhere
- Remove Review Queue sidebar navigation link
- Remove Review Queue route but redirect it to the main analytics dashboard (not 404)
- Delete component files entirely, not just hide them

### Dialog Centering
- Convert ALL Sheet (side-sliding) components to centered Dialog components — no side-sliders remain
- Max height ~80vh with internal scrolling for large content (contact detail, event timeline)
- Dark semi-transparent backdrop overlay on all dialogs
- Backdrop click dismisses the dialog (standard pattern)
- Close via backdrop click, close button, or Escape key

### Label Rename
- Rename "Prospect" to "Potential Donor" in BOTH frontend and backend
- Update Django TextChoices display string: `PROSPECT = 'prospect', 'Potential Donor'` (stored value stays 'prospect')
- Update ALL occurrences: status labels, badges, filter dropdowns, form selects
- Badge keeps the same gray (secondary) variant — only label text changes
- Requires a Django migration for the TextChoices display string change

### Claude's Discretion
- Column ordering in gifts/pledges tables
- Exact dialog width/max-width values per component
- Which analytics backend endpoints to keep vs remove (check for other consumers)

</decisions>

<specifics>
## Specific Ideas

- Gift type empty state should show "---" (triple dash) matching existing app patterns
- Review Queue route should redirect to analytics dashboard, not 404
- All side-sliding Sheets become centered Dialogs — no exceptions

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 38-ui-polish-list-page-cleanup*
*Context gathered: 2026-02-27*
