# Phase 39: Dashboard Modifications - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the missionary dashboard visually tighter and more flexible: remove stale text and tiles, tighten spacing, add a chart type toggle, and enable fully free cross-section tile dragging. The dashboard already has per-section drag-and-drop (via @dnd-kit), a Recharts bar chart, and the tiles/cards targeted for modification.

</domain>

<decisions>
## Implementation Decisions

### Chart Toggle UX
- Toggle control style is Claude's discretion (icon buttons, segmented control, etc.)
- Position: card header, right-aligned — inline with the Monthly Gifts card title
- Persist chart type preference to localStorage so it survives page reloads
- Smooth crossfade animation when switching between bar and line chart views

### Cross-Section Dragging
- Remove all section boundaries — one fully flat grid where any tile can go to any position
- Each tile keeps its natural/fixed size (stat cards = small/quarter width, charts/content = half width). Grid reflows around mixed sizes.
- No section headers — clean flat grid with no visual grouping labels
- Save tile layout to backend (user profile) so arrangement persists across devices/browsers
- Include a small "reset to default" button somewhere on the dashboard to restore default tile order

### Tile Spacing & Density
- Moderate gaps between tiles: 12-16px range
- Tighten both inter-tile gaps AND internal card padding for an overall denser feel
- No specific aesthetic reference — just reduce current spacing to be tighter than today
- No section headers or dividers in the flat grid

### Removal Behavior
- Recent Journal Activity tile: permanent removal — delete frontend component, API call, backend view, and service function
- Remaining tiles reflow automatically to fill gaps left by removed tile
- Text removals ("2026 calendar year" from Giving summary, "Updated today" from Monthly Gifts): Claude's discretion on whether space collapses or is preserved, based on visual balance of each card

### Claude's Discretion
- Chart toggle control style (icon buttons vs segmented control vs other)
- Text removal space handling (collapse vs preserve) based on card visual balance
- Journal activity backend cleanup scope (Claude to verify nothing else uses the endpoint before removing)
- Exact reset button placement and styling
- Drag handle visibility and interaction design
- Grid reflow algorithm for mixed tile sizes

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants the dashboard to just feel tighter and more flexible without a specific reference aesthetic.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 39-dashboard-modifications*
*Context gathered: 2026-02-27*
