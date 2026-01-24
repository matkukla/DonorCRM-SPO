---
phase: 04-grid-ui-core
plan: 03
subsystem: grid-ui
tags: [react, typescript, grid, ui-components, sticky-layout, memoization]
requires: [04-01, 04-02]
provides: [journal-grid-components, sticky-headers, stage-cell-indicators]
affects: [04-04, 04-05]
tech-stack:
  added: []
  patterns:
    - React.memo with custom comparison
    - CSS sticky positioning with z-index hierarchy
    - Tooltip composition with asChild
    - useCallback for stable props
decisions:
  - Sticky CSS over virtualization for initial implementation
  - Z-index hierarchy: z-10 headers, z-20 columns, z-30 intersection
  - 300ms tooltip delay to prevent interference with clicks
key-files:
  created:
    - frontend/src/pages/journals/components/StageCell.tsx
    - frontend/src/pages/journals/components/ContactNameCell.tsx
    - frontend/src/pages/journals/components/JournalGrid.tsx
  modified: []
metrics:
  tasks: 3
  commits: 3
  duration: 1.82 min
  completed: 2026-01-24
---

# Phase 4 Plan 03: Grid Components with Sticky Headers Summary

**One-liner:** Journal grid with React.memo cells, CSS sticky positioning (z-10/20/30), and color-coded freshness tooltips

## What Was Built

Created the core journal grid UI components with sticky headers and contact name column:

1. **StageCell** - Memoized stage cell component with:
   - React.memo with custom comparison to prevent cascade re-renders
   - Color-coded Badge based on event freshness (getFreshnessColor)
   - Tooltip with asChild composition for hover + click
   - formatDistanceToNow for "3 days ago" style timestamps
   - Event type formatting (call_logged → "Call Logged")
   - Empty state button for cells with no events
   - Accessible aria-label with event count

2. **ContactNameCell** - Sticky first column component with:
   - React.memo for performance
   - min-w-[180px] for consistent sticky width
   - Name and email display with truncation
   - Simple design (main complexity in parent grid)

3. **JournalGrid** - Main grid container with:
   - Sticky header row (sticky top-0 z-10)
   - Sticky contact name column (sticky left-0 z-20)
   - Intersection cell (sticky top-0 left-0 z-30)
   - bg-background on all sticky elements to cover scrolling content
   - overflow-x-auto on container for horizontal scroll
   - useCallback for memoized click handler
   - Empty and loading states
   - Helper function to extract stage event summaries

## Technical Approach

**Performance optimizations per RESEARCH.md:**
- All cell components wrapped in React.memo
- Custom comparison in StageCell (only re-render if eventSummary changes)
- Click handler wrapped in useCallback with stable dependencies
- Prevents N+1 render cascade when individual cells change

**Sticky layout implementation:**
- Z-index hierarchy: z-10 (headers), z-20 (sticky column), z-30 (intersection)
- bg-background on all sticky elements prevents transparent overlap
- Intersection cell has both top-0 and left-0 with highest z-index
- Parent container has overflow-x-auto for horizontal scrolling

**Tooltip + click composition:**
- TooltipTrigger uses asChild to compose with button onClick
- 300ms delayDuration prevents tooltip interfering with quick clicks
- Shows event summary: type, relative time, notes, total count
- formatDistanceToNow for user-friendly "3 days ago" format

## Decisions Made

**1. Sticky CSS over virtualization**
- Decision: Use CSS position: sticky for initial implementation
- Rationale: Dataset size (dozens of contacts) doesn't require virtualization complexity
- Trade-off: May need TanStack Virtual in Phase 5 if performance degrades
- Context: RESEARCH.md recommended starting simple, add virtualization only if needed

**2. Z-index hierarchy (z-10, z-20, z-30)**
- Decision: Three-tier z-index system for sticky elements
- Rationale: Prevents overlap during bi-directional scroll
- Implementation: z-10 headers, z-20 columns, z-30 intersection
- Context: Standard pattern from TanStack Table sticky examples

**3. 300ms tooltip delay**
- Decision: delayDuration={300} on Tooltip component
- Rationale: Prevents tooltip from interfering with quick clicks
- Alternative: Could use shorter delay, but 300ms is tested standard
- Context: RESEARCH.md flagged tooltip/click interaction as potential pitfall

## Dependencies & Integration

**Upstream dependencies (from prior plans):**
- 04-01: Tooltip component, Badge variants (including orange), types (getFreshnessColor)
- 04-02: useJournalMembers hook providing JournalMember data

**Provides for downstream:**
- 04-04: JournalGrid component ready for integration into page
- 04-05: Stage cell click handler interface for timeline drawer

**Key imports:**
- `@/components/ui/tooltip` (Radix UI primitive from 04-01)
- `@/components/ui/badge` (with orange variant from 04-01)
- `@/types/journals` (JournalMember, StageEventSummary, getFreshnessColor)
- `date-fns` (formatDistanceToNow for relative time)
- `lucide-react` (Check icon for stage indicators)

## Deviations from Plan

None - plan executed exactly as written.

All components follow RESEARCH.md patterns:
- React.memo with custom comparison
- useCallback for stable props
- Tooltip asChild composition
- Z-index hierarchy for sticky elements
- bg-background on sticky cells

## Testing & Verification

**Verification completed:**
1. ✅ TypeScript compiles: `npx tsc --noEmit` - no errors
2. ✅ StageCell uses React.memo: grep confirmed
3. ✅ Grid has sticky positioning: grep confirmed
4. ✅ Z-index hierarchy correct: z-10, z-20, z-30 verified
5. ✅ Tooltip integration: asChild composition verified

**Success criteria met:**
- ✅ StageCell wrapped in React.memo with custom comparison
- ✅ StageCell uses Tooltip with asChild for hover + click
- ✅ StageCell displays color-coded Badge based on getFreshnessColor
- ✅ JournalGrid has sticky header row (sticky top-0 z-10)
- ✅ JournalGrid has sticky contact name column (sticky left-0 z-20)
- ✅ JournalGrid has intersection cell (sticky top-0 left-0 z-30)
- ✅ All sticky elements have bg-background
- ✅ Grid container has overflow-x-auto
- ✅ All TypeScript compiles without errors

## Code Quality

**Accessibility:**
- aria-label on stage cell buttons with event count
- sr-only text for empty state cells
- Semantic button elements for clickable cells
- Radix Tooltip follows WAI-ARIA standards

**Performance:**
- React.memo prevents unnecessary re-renders
- Custom comparison in StageCell (only checks eventSummary)
- useCallback ensures stable click handler reference
- No inline function creation in render

**Maintainability:**
- Clear component separation (StageCell, ContactNameCell, JournalGrid)
- Helper function for stage event summary extraction
- Comprehensive JSDoc comments explaining performance patterns
- Explicit z-index values with comments

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 4927f93 | feat | Create memoized StageCell component |
| e8049e2 | feat | Create ContactNameCell for sticky column |
| 7d1c34e | feat | Create JournalGrid with sticky layout |

## Next Phase Readiness

**Immediate next step (04-04):**
- Integrate JournalGrid into journal detail page
- Wire up onStageCellClick handler to open timeline drawer
- Test sticky layout with real data from API

**Phase completion blockers:**
None. All grid components ready for integration.

**Recommended follow-up:**
- Test scroll behavior with 50+ contacts
- Verify tooltip positioning at scroll container edges
- Test on mobile (may need responsive width adjustments)
- Consider adding keyboard navigation for accessibility

**Research flags resolved:**
- ✅ React grid cell re-render cascade - Solved with React.memo + useCallback
- ✅ Fine-tune grid virtualization - Started with CSS sticky, virtualization deferred

**Open questions for next plans:**
- Should tooltip have collision padding for cells near edges?
- Should mobile use different sticky column width?
- Need keyboard navigation (arrow keys) for grid accessibility?
