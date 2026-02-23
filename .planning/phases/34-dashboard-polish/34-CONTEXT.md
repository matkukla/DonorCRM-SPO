# Phase 34: Dashboard Polish - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Make dashboard tiles draggable so users can rearrange their layout. Tile order persists for the browser session but resets on page refresh. Dashboard already queries Gift/RecurringGift models (Phase 31). This phase adds drag-and-drop interaction only — no new tiles, no new data, no persistent storage.

</domain>

<decisions>
## Implementation Decisions

### Drag interaction design
- Grip icon handle (6-dot pattern) in top-left of each card header, before the title text
- Drag starts only from the handle — links, buttons, and charts inside tiles remain fully clickable
- While dragging: tile follows cursor at ~60% opacity (semi-transparent ghost)
- Drop zone shown as dashed-border placeholder in the gap where the tile will land
- Desktop only — no mobile/touch drag support (avoids scroll gesture conflicts)

### Claude's Discretion
- Tile grouping and constraints — whether tiles can move between sections (stat row vs left/right columns) or only reorder within their section
- Layout reset behavior — whether to show a reset button, discoverability hints for dragging
- Visual feedback details — exact animation timing, hover states, drop zone styling
- Which drag-and-drop library to use
- Session persistence mechanism (React state vs sessionStorage)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for the undiscussed areas.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 34-dashboard-polish*
*Context gathered: 2026-02-23*
