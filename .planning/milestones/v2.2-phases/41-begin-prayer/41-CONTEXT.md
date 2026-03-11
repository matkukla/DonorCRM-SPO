# Phase 41: Begin Prayer - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a dedicated, prominent "Begin Prayer" button on the Prayer Request page that launches expanded Focus Mode with selected prayer intentions. Replaces the existing small "Enter Focus Mode" button with a more prominent entry point that includes an intention selection step.

</domain>

<decisions>
## Implementation Decisions

### Button placement & prominence
- Button lives inside the Today's Focus section, replacing the existing "Enter Focus Mode" button
- Medium accent button — primary amber styling, larger than current button but not full-width
- Label: "Begin Prayer" (exact text)
- Icon: Sparkles (same as current "Enter Focus Mode" for continuity)

### Button behavior & empty state
- Button is always visible and clickable, even with no active intentions
- When clicked with no intentions: launches Focus Mode which already has an empty state screen ("No Intentions for Today" with Return button)
- When clicked with intentions: opens a selection dialog before entering Focus Mode

### Intention selection dialog
- Centered modal/dialog opens when "Begin Prayer" is clicked
- Shows all active prayer intentions with checkboxes (not just today's focus)
- Today's focus intentions are pre-checked by default
- User can check/uncheck individual intentions to customize their prayer session
- "Start Prayer" button at bottom launches Focus Mode with selected intentions
- Dialog should show intention title and contact name for each item

### Existing Focus Mode entry
- "Enter Focus Mode" button is completely removed/replaced by "Begin Prayer"
- Single entry point — cleaner UI

### Claude's Discretion
- Whether to include a "Select All" / "Deselect All" toggle in the selection dialog (decide based on typical intention count and UX)
- Dialog layout and styling details (fit the warm prayer aesthetic)
- Exact button sizing within the "medium accent" direction
- How to handle the case where user deselects all intentions and clicks "Start Prayer"

</decisions>

<specifics>
## Specific Ideas

- The selection dialog is the key new UX element — it adds flexibility to choose which intentions to pray through rather than always using today's focus
- Pre-checking today's focus intentions provides a sensible default while allowing customization
- The dialog should feel like a gentle preparation step, not a complex configuration screen

</specifics>

<deferred>
## Deferred Ideas

- "Add Prayer Intention isn't working" — reported as a bug, needs investigation outside this phase
- Quick-start option that skips selection (potential future enhancement if selection step feels heavy)

</deferred>

---

*Phase: 41-begin-prayer*
*Context gathered: 2026-02-27*
