# Phase 39: Dashboard Modifications - Research

**Researched:** 2026-02-27
**Domain:** React dashboard layout (dnd-kit, Recharts, CSS grid), Django user preferences
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Chart Toggle UX
- Toggle control style is Claude's discretion (icon buttons, segmented control, etc.)
- Position: card header, right-aligned -- inline with the Monthly Gifts card title
- Persist chart type preference to localStorage so it survives page reloads
- Smooth crossfade animation when switching between bar and line chart views

#### Cross-Section Dragging
- Remove all section boundaries -- one fully flat grid where any tile can go to any position
- Each tile keeps its natural/fixed size (stat cards = small/quarter width, charts/content = half width). Grid reflows around mixed sizes.
- No section headers -- clean flat grid with no visual grouping labels
- Save tile layout to backend (user profile) so arrangement persists across devices/browsers
- Include a small "reset to default" button somewhere on the dashboard to restore default tile order

#### Tile Spacing & Density
- Moderate gaps between tiles: 12-16px range
- Tighten both inter-tile gaps AND internal card padding for an overall denser feel
- No specific aesthetic reference -- just reduce current spacing to be tighter than today
- No section headers or dividers in the flat grid

#### Removal Behavior
- Recent Journal Activity tile: permanent removal -- delete frontend component, API call, backend view, and service function
- Remaining tiles reflow automatically to fill gaps left by removed tile
- Text removals ("2026 calendar year" from Giving summary, "Updated today" from Monthly Gifts): Claude's discretion on whether space collapses or is preserved, based on visual balance of each card

### Claude's Discretion
- Chart toggle control style (icon buttons vs segmented control vs other)
- Text removal space handling (collapse vs preserve) based on card visual balance
- Journal activity backend cleanup scope (Claude to verify nothing else uses the endpoint before removing)
- Exact reset button placement and styling
- Drag handle visibility and interaction design
- Grid reflow algorithm for mixed tile sizes

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | User can toggle between bar chart and line graph on the Donations chart | Recharts BarChart/LineChart share identical data structure; toggle via React state + conditional render. LineChart already used in admin analytics (TrendCharts.tsx). |
| DASH-02 | Dashboard tiles are draggable to any position (cross-section) | Current dnd-kit setup uses 3 separate SortableContext sections. Flatten to single SortableContext with one unified tile order array. Use CSS grid with variable column spans for mixed tile sizes. Backend persistence via new JSONField on User model. |
| DASH-03 | Dashboard gaps between tiles are visually tightened | Current: `gap-6` (24px) on all grids plus default Card padding. Reduce to `gap-3` (12px) or `gap-4` (16px) and tighten CardHeader/CardContent padding. |
| DASH-04 | "2026 calendar year" text removed from Giving summary | Located in `GivingSummaryCard.tsx` line 135: `{data.year} calendar year` in footer paragraph. Remove or collapse. |
| DASH-05 | "Updated today" text removed from Monthly Gifts | Located in `MonthlyGiftsCard.tsx` line 104-106: `Updated today` paragraph. Remove or collapse. |
| DASH-06 | "Recent Journal Activity" tile removed from dashboard | Frontend: `RecentJournalActivity.tsx` component, import in `Dashboard.tsx`, tile ID "journal-activity" in DEFAULT_CONTENT_ORDER. Backend: `get_recent_journal_activity()` in services.py, `RecentJournalActivityView` in views.py, URL in urls.py, `journal_activity` key in `get_dashboard_summary()`. Also `JournalActivityItem` type in `api/dashboard.ts`. |
</phase_requirements>

## Summary

This phase modifies the existing missionary dashboard with six discrete changes: a chart type toggle, cross-section drag-and-drop, tighter spacing, two text removals, and one tile removal. The codebase already has the core libraries installed (@dnd-kit/core 6.3.1, @dnd-kit/sortable 10.0.0, Recharts 3.6.0) and uses them correctly. The current dashboard (`frontend/src/pages/Dashboard.tsx`) has three separate `SortableContext` regions (giving, stats, content) that need merging into a single flat sortable context.

The most architecturally significant change is the cross-section drag-and-drop with backend persistence. Currently, tiles can only be reordered within their section. The user wants a single flat grid where any tile can go anywhere, with mixed tile sizes (stat cards at quarter-width, charts/content at half-width). This requires: (1) a single flat tile order array, (2) CSS grid with variable `col-span` per tile, (3) a new `dashboard_layout` JSONField on the User model, (4) a new API endpoint to save/load layout, and (5) a reset-to-default button. The dnd-kit `rectSortingStrategy` works well for grids but has documented challenges with mixed-size items -- the recommended approach for unpredictable layouts is to reorder `onDragOver` instead of `onDragEnd` and pass an empty sorting strategy function.

The chart toggle and text/tile removals are straightforward. Recharts `BarChart` and `LineChart` accept identical data structures, so toggling is just conditional rendering with localStorage persistence. The journal activity removal is a clean full-stack deletion since no other feature depends on the `RecentJournalActivityView` endpoint (verified: only the dashboard summary service and the standalone view use `get_recent_journal_activity()`).

**Primary recommendation:** Flatten the three SortableContext regions into one with a CSS grid using per-tile `col-span` classes, add a `dashboard_layout` JSONField to the User model with a dedicated save/load endpoint, and use conditional rendering for the chart toggle.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @dnd-kit/core | 6.3.1 | Drag-and-drop primitives | Already installed; provides DndContext, sensors, collision detection |
| @dnd-kit/sortable | 10.0.0 | Sortable list/grid preset | Already installed; provides SortableContext, useSortable, arrayMove |
| @dnd-kit/utilities | 3.2.2 | CSS transform utilities | Already installed; provides CSS.Transform |
| recharts | 3.6.0 | Charts (Bar, Line, Pie) | Already installed; BarChart and LineChart used in project |
| Django JSONField | built-in | Store tile layout as JSON | No external dep; native Django field for flexible schema-less data |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | 5.90.17 | Data fetching/caching | Already used for dashboard hooks; use for layout save/load |
| lucide-react | 0.562.0 | Icons | Already used; for chart toggle icons (BarChart3, LineChart) |
| tailwindcss | 3.4.19 | Utility CSS | Already used; for gap/padding adjustments and col-span classes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Backend JSONField | localStorage only | User decision explicitly requires cross-device persistence via backend |
| CSS grid col-span | CSS container queries | Grid col-span is simpler and works perfectly here; container queries add complexity |
| onDragOver reorder | onDragEnd only | For mixed-size grids, onDragOver gives smoother visual feedback during drag |

## Architecture Patterns

### Current Dashboard Structure (before changes)
```
Dashboard.tsx
  DndContext (single, wraps everything)
    SortableContext #1 (givingOrder: 2 half-width cards)
      grid gap-6 lg:grid-cols-2
    SortableContext #2 (statsOrder: 4 quarter-width stat cards)
      grid gap-6 md:grid-cols-2 lg:grid-cols-4
    MPD Section (not draggable, conditional)
    SortableContext #3 (contentOrder: 5 half-width content cards)
      grid gap-6 lg:grid-cols-2
```

### Target Dashboard Structure (after changes)
```
Dashboard.tsx
  DndContext (single)
    SortableContext (single flat tileOrder array, all 10 tiles)
      CSS grid: grid-cols-4 gap-3
        - Stat cards:   col-span-1 (quarter-width)
        - Chart/Content: col-span-2 (half-width)
    MPD Section (not draggable, conditional, outside SortableContext)
    Reset button (outside SortableContext)
```

### Pattern 1: Flat Grid with Variable Column Spans
**What:** Single CSS grid with `grid-cols-4` where tiles declare their own width via `col-span-1` or `col-span-2`.
**When to use:** When you need a single sortable list but tiles have different natural widths.
**Example:**
```typescript
// Tile size configuration map
const TILE_SIZES: Record<string, number> = {
  // Quarter-width (stat cards)
  "thank-you": 1,
  "recent-donations-stat": 1,
  "active-pledges": 1,
  "needs-attention-stat": 1,
  // Half-width (charts and content cards)
  "giving-summary": 2,
  "monthly-gifts": 2,
  "needs-attention": 2,
  "support-progress": 2,
  "recent-donations": 2,
  "late-donations": 2,
}

// In the grid:
<div className="grid grid-cols-4 gap-3">
  {tileOrder.map((id) => (
    <SortableDashboardTile
      key={id}
      id={id}
      className={TILE_SIZES[id] === 2 ? "col-span-2" : "col-span-1"}
    >
      {renderTileById(id)}
    </SortableDashboardTile>
  ))}
</div>
```

### Pattern 2: Chart Type Toggle with localStorage
**What:** React state controls which chart renders; persisted to localStorage.
**When to use:** When a single data source has multiple valid visualizations.
**Example:**
```typescript
// Source: Recharts API + project conventions
type ChartType = "bar" | "line"

function useChartType(key: string, defaultType: ChartType = "bar") {
  const [chartType, setChartType] = useState<ChartType>(() => {
    const stored = localStorage.getItem(key)
    return (stored === "bar" || stored === "line") ? stored : defaultType
  })

  const toggle = (type: ChartType) => {
    setChartType(type)
    localStorage.setItem(key, type)
  }

  return [chartType, toggle] as const
}

// In MonthlyGiftsCard:
{chartType === "bar" ? (
  <BarChart data={data.months}>
    {/* shared axes, tooltip, reference line */}
    <Bar dataKey="total" ... />
  </BarChart>
) : (
  <LineChart data={data.months}>
    {/* shared axes, tooltip, reference line */}
    <Line dataKey="total" ... />
  </LineChart>
)}
```

### Pattern 3: Backend Layout Persistence
**What:** Store tile order as JSON in user model, expose via API endpoint.
**When to use:** When layout must persist across devices.
**Example:**
```python
# User model addition
dashboard_layout = models.JSONField(
    'dashboard layout',
    default=dict,
    blank=True,
    help_text='User dashboard tile ordering preferences'
)

# Expected JSON shape:
# {"tile_order": ["giving-summary", "monthly-gifts", "thank-you", ...]}
```

```typescript
// Frontend API
export async function saveDashboardLayout(tileOrder: string[]): Promise<void> {
  await apiClient.patch("/users/me/", {
    dashboard_layout: { tile_order: tileOrder }
  })
}
```

### Anti-Patterns to Avoid
- **Multiple SortableContext for cross-dragging:** The current pattern of 3 separate SortableContext blocks prevents cross-section dragging. Merging into one is essential.
- **onDragEnd-only with mixed-size grid:** For grids with variable-size items, the standard sorting strategies may produce visual glitches. Use `onDragOver` for reordering to get smoother feedback.
- **Saving layout on every drag:** Debounce or save only on `onDragEnd` to avoid excessive API calls.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-and-drop reordering | Custom mouse event handlers | @dnd-kit SortableContext + useSortable | Handles touch, keyboard, accessibility, scroll containers |
| Chart rendering | Custom SVG/Canvas chart | Recharts BarChart/LineChart | Both accept identical data props; just swap the container component |
| Array reordering | Manual splice logic | arrayMove from @dnd-kit/sortable | Already handles edge cases and returns new array |
| JSON persistence | Custom serialization | Django JSONField | Built-in validation, queryable, no extra dependency |

**Key insight:** Both dnd-kit and Recharts are already fully set up in this project. The work is restructuring how they're used (single context vs multiple, chart toggle), not integrating new libraries.

## Common Pitfalls

### Pitfall 1: Mixed-Size Grid Sorting Glitches
**What goes wrong:** `rectSortingStrategy` calculates expected positions based on uniform grid cells. With mixed col-span items, the visual indicators and drop positions can be wrong.
**Why it happens:** The strategy assumes all items occupy the same grid cell dimensions.
**How to avoid:** Either (a) pass an empty function as the sorting strategy and handle reordering in `onDragOver`, or (b) test thoroughly with mixed arrangements. The `rectSortingStrategy` may work well enough with a 4-column grid where items are 1 or 2 columns wide.
**Warning signs:** Items "jumping" to unexpected positions during drag; visual overlay not matching the actual drop position.

### Pitfall 2: Stale Tile Order After Journal Activity Removal
**What goes wrong:** Users who already have a saved layout containing "journal-activity" will get errors or broken renders after the tile is removed from the code.
**Why it happens:** Saved layout JSON references a tile ID that no longer exists.
**How to avoid:** When loading saved layout, filter out any tile IDs that aren't in the current valid tile list. Also add any new tiles that aren't in the saved layout (future-proofing).
**Warning signs:** Console errors about missing tile IDs; blank spaces in the grid.

### Pitfall 3: DragOverlay Rendering Wrong Size
**What goes wrong:** The ghost overlay that follows the cursor renders at the wrong width because it's outside the CSS grid context.
**Why it happens:** `DragOverlay` renders a portal outside the grid, so `col-span-2` doesn't apply.
**How to avoid:** Give the DragOverlay content explicit width matching the tile's actual rendered width, or use a simpler semi-transparent copy approach.
**Warning signs:** The dragged ghost appears full-width or misshapen.

### Pitfall 4: Race Condition Between localStorage and Backend Layout
**What goes wrong:** Chart type preference (localStorage) and tile layout (backend) can get out of sync if the user changes devices.
**Why it happens:** Two different persistence mechanisms for related preferences.
**How to avoid:** Chart type preference is intentionally localStorage-only (per CONTEXT.md). Tile layout is backend-only. Keep them separate and document the distinction.
**Warning signs:** None if the distinction is clear; this is by design.

### Pitfall 5: Responsive Grid Breakpoints
**What goes wrong:** A 4-column grid doesn't work on mobile; tiles overflow or stack oddly.
**Why it happens:** The current layout already has responsive breakpoints (`md:grid-cols-2`, `lg:grid-cols-4`).
**How to avoid:** Use responsive Tailwind classes: `grid-cols-2 lg:grid-cols-4`. On mobile (2 cols), half-width tiles take `col-span-2` (full width) and stat cards take `col-span-1` (half width). This maintains readability on small screens.
**Warning signs:** Horizontal scroll on mobile; tiles clipped or overlapping.

## Code Examples

### Recharts LineChart with Same Data Shape
```typescript
// Source: Existing project pattern in TrendCharts.tsx + Recharts API
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, ReferenceLine } from "recharts"

// Both charts use identical data structure:
// data.months = [{ month: "2026-01", short_label: "Jan", total: 5000 }, ...]

// Shared components between both chart types:
const sharedAxes = (
  <>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="short_label" tickLine={false} tickMargin={10} axisLine={false} />
    <YAxis
      tickFormatter={(v) => `$${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`}
      tickLine={false}
      axisLine={false}
    />
  </>
)
```

### Updating SortableDashboardTile with col-span
```typescript
// Source: Current SortableDashboardTile.tsx pattern
interface SortableDashboardTileProps {
  id: string
  children: React.ReactNode
  className?: string  // NEW: accept className for col-span
}

export function SortableDashboardTile({ id, children, className }: SortableDashboardTileProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "group relative",
        isDragging && "opacity-40 border-2 border-dashed border-border rounded-lg",
        className  // col-span-1 or col-span-2
      )}
    >
      {/* drag handle */}
      <button
        className="absolute top-3 left-1 z-10 p-0.5 rounded cursor-grab active:cursor-grabbing text-muted-foreground/0 group-hover:text-muted-foreground hover:text-foreground transition-colors duration-150"
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      {children}
    </div>
  )
}
```

### Backend Layout Persistence Endpoint
```python
# Add to UserUpdateSerializer.Meta.fields:
# 'dashboard_layout'

# Add to User model:
dashboard_layout = models.JSONField(
    'dashboard layout',
    default=dict,
    blank=True,
)

# The CurrentUserView.patch already handles partial updates via UserUpdateSerializer
# Just add 'dashboard_layout' to the allowed fields
```

### Layout Validation on Load
```typescript
// Filter saved layout to only include currently valid tiles
const VALID_TILES = new Set([
  "giving-summary", "monthly-gifts",
  "thank-you", "recent-donations-stat", "active-pledges", "needs-attention-stat",
  "needs-attention", "support-progress", "recent-donations", "late-donations",
])

function loadTileOrder(savedOrder: string[] | undefined): string[] {
  const DEFAULT_ORDER = [
    "giving-summary", "monthly-gifts",
    "thank-you", "recent-donations-stat", "active-pledges", "needs-attention-stat",
    "needs-attention", "support-progress", "recent-donations", "late-donations",
  ]

  if (!savedOrder || savedOrder.length === 0) return DEFAULT_ORDER

  // Keep only valid tiles from saved order
  const filtered = savedOrder.filter((id) => VALID_TILES.has(id))

  // Add any missing tiles (new tiles added after user saved layout)
  const missing = DEFAULT_ORDER.filter((id) => !filtered.includes(id))

  return [...filtered, ...missing]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Multiple SortableContext per section | Single SortableContext for flat grid | This phase | Enables cross-section dragging |
| BarChart only | BarChart/LineChart toggle | This phase | User choice for data visualization preference |
| gap-6 (24px) spacing | gap-3 (12px) spacing | This phase | Visually denser dashboard |
| 3 visual sections with headers | Flat headerless grid | This phase | Cleaner, more flexible layout |

**Deprecated/outdated after this phase:**
- `DEFAULT_GIVING_ORDER`, `DEFAULT_STATS_ORDER`, `DEFAULT_CONTENT_ORDER` -- replaced by single `DEFAULT_TILE_ORDER`
- `RecentJournalActivity` component and backend service -- permanently removed
- `RecentJournalActivityView` and its URL -- permanently removed
- `journal_activity` key in dashboard summary API response -- removed from backend

## Open Questions

1. **MPD Section Placement in Flat Grid**
   - What we know: The MPD section is conditional (`mpdData?.has_data`), not draggable, and renders as 3 stat-sized cards with its own heading. It sits between the stats and content sections currently.
   - What's unclear: Should it remain a separate non-draggable section above/below the flat grid, or should its cards become draggable tiles?
   - Recommendation: Keep MPD as a separate non-draggable section below the flat grid. It's conditional (most users won't see it), has its own heading, and including it in the flat grid would complicate the tile order for users who don't have MPD data. This avoids phantom tiles.

2. **Responsive Breakpoints for Unified Grid**
   - What we know: Current dashboard uses `lg:grid-cols-2` for giving/content and `md:grid-cols-2 lg:grid-cols-4` for stats.
   - What's unclear: Exact breakpoint behavior when mixing half-width and quarter-width tiles in one grid.
   - Recommendation: Use `grid-cols-2 lg:grid-cols-4` with responsive col-span: stat cards `col-span-1`, content cards `col-span-2 lg:col-span-2`. On mobile (2-col), stat cards are half-width, content cards are full-width. Test edge case: 4 stat cards in a row on mobile.

3. **DASH-07 vs CONTEXT.md Decision**
   - What we know: REQUIREMENTS.md lists DASH-07 (dashboard persistence) as a "Future Requirement" under Out of Scope, but CONTEXT.md (user decisions) explicitly says "Save tile layout to backend (user profile) so arrangement persists across devices/browsers."
   - What's unclear: Whether DASH-07 should be updated in REQUIREMENTS.md to reflect the user's in-scope decision.
   - Recommendation: Implement backend persistence as the user decided. The CONTEXT.md decision takes priority -- the user explicitly requested this during the discussion phase. REQUIREMENTS.md can be updated by the planner to reflect the expanded scope.

## Sources

### Primary (HIGH confidence)
- Project codebase: `frontend/src/pages/Dashboard.tsx` -- current dashboard structure with 3 SortableContext regions
- Project codebase: `frontend/src/components/dashboard/MonthlyGiftsCard.tsx` -- BarChart implementation, "Updated today" text location
- Project codebase: `frontend/src/components/dashboard/GivingSummaryCard.tsx` -- "calendar year" text location (line 135)
- Project codebase: `frontend/src/components/dashboard/RecentJournalActivity.tsx` -- component to remove
- Project codebase: `apps/dashboard/services.py` -- `get_recent_journal_activity()`, `get_dashboard_summary()` journal_activity key
- Project codebase: `apps/dashboard/views.py` -- `RecentJournalActivityView`
- Project codebase: `apps/dashboard/urls.py` -- journal-activity URL
- Project codebase: `apps/users/models.py` -- User model (no dashboard_layout field yet)
- Project codebase: `apps/users/serializers.py` -- `UserUpdateSerializer` fields list
- Project codebase: `frontend/src/pages/admin/analytics/components/TrendCharts.tsx` -- existing LineChart usage pattern
- `frontend/package.json` -- @dnd-kit/core 6.3.1, @dnd-kit/sortable 10.0.0, recharts 3.6.0

### Secondary (MEDIUM confidence)
- [dnd-kit Sortable docs](https://docs.dndkit.com/presets/sortable) -- rectSortingStrategy for grids
- [dnd-kit mixed-size grid issues](https://github.com/clauderic/dnd-kit/issues/720) -- challenges with variable-size items; recommend custom strategy or onDragOver reordering
- [Recharts API](https://recharts.github.io/en-US/api/LineChart/) -- LineChart and BarChart share data structure

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in the project
- Architecture: HIGH -- direct inspection of current codebase; clear transformation path
- Pitfalls: HIGH -- dnd-kit mixed-size grid is a well-documented challenge; stale layout IDs are a standard data migration concern

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (stable libraries, no breaking changes expected)
