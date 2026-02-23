# Phase 34: Dashboard Polish - Research

**Researched:** 2026-02-23
**Domain:** React drag-and-drop, dashboard tile reordering
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Grip icon handle (6-dot pattern) in top-left of each card header, before the title text
- Drag starts only from the handle -- links, buttons, and charts inside tiles remain fully clickable
- While dragging: tile follows cursor at ~60% opacity (semi-transparent ghost)
- Drop zone shown as dashed-border placeholder in the gap where the tile will land
- Desktop only -- no mobile/touch drag support (avoids scroll gesture conflicts)

### Claude's Discretion
- Tile grouping and constraints -- whether tiles can move between sections (stat row vs left/right columns) or only reorder within their section
- Layout reset behavior -- whether to show a reset button, discoverability hints for dragging
- Visual feedback details -- exact animation timing, hover states, drop zone styling
- Which drag-and-drop library to use
- Session persistence mechanism (React state vs sessionStorage)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | Dashboard tiles can be rearranged via drag-and-drop (session-only, resets on refresh) | dnd-kit sortable preset provides DndContext + SortableContext + useSortable hook for tile reordering; arrayMove utility handles state updates; React useState sufficient for session-only persistence |
</phase_requirements>

## Summary

Phase 34 adds drag-and-drop tile reordering to the existing Dashboard page. The dashboard currently has three visual sections: (1) a 2-column giving widgets row (GivingSummaryCard + MonthlyGiftsCard), (2) a 4-column stat cards row, and (3) a 2-column main content grid (left: NeedsAttention + SupportProgress; right: RecentDonations + RecentJournalActivity + LateDonations). There is also a conditional MPD section that only appears when data exists.

The recommended approach uses `@dnd-kit/core` + `@dnd-kit/sortable` (stable v6.3.1/v10.0.0), which supports React >=16.8.0 (includes React 19), provides built-in sortable grid support via `rectSortingStrategy`, and has excellent DragOverlay support for the ghost preview. The library is well-documented, battle-tested (16.6k GitHub stars, 152k dependents), and adds ~13KB gzipped total. Session persistence is simplest with React `useState` since the requirement explicitly states order resets on page refresh.

**Primary recommendation:** Use `@dnd-kit/core` + `@dnd-kit/sortable` with per-section SortableContext containers. Tiles reorder within their section only (no cross-section dragging). Use React `useState` for tile order -- no persistence needed.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @dnd-kit/core | 6.3.1 | DnD context, sensors, collision detection, DragOverlay | Most popular React DnD toolkit; 16.6k stars; stable API; framework for custom DnD |
| @dnd-kit/sortable | 10.0.0 | Sortable preset with useSortable hook, sorting strategies, arrayMove | Purpose-built sortable layer on top of @dnd-kit/core; handles reorder animations |
| @dnd-kit/utilities | 3.2.2 | CSS.Transform helper for applying transforms | Required by useSortable for transform-to-CSS conversion |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react (GripVertical) | already installed | 6-dot grip drag handle icon | Render in card headers as drag handle |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @dnd-kit/core + sortable | @hello-pangea/dnd 18.0.1 | Supports React 19, but explicitly lacks grid layout support; designed for lists/kanban only |
| @dnd-kit/core + sortable | @dnd-kit/react 0.3.2 (new rewrite) | Newer API but still v0.x pre-release; no community clarity on stability timeline; unanswered roadmap questions |
| @dnd-kit/core + sortable | react-beautiful-dnd | Deprecated Aug 2025, archived, no React 19 support |
| @dnd-kit/core + sortable | pragmatic-drag-and-drop | Atlassian's newer lib; less React-specific; smaller ecosystem |

**Installation:**
```bash
cd frontend && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

## Architecture Patterns

### Current Dashboard Layout (Before Changes)

```
Dashboard.tsx
├── Header (h1 + welcome)
├── Giving Widgets (2-col grid)
│   ├── GivingSummaryCard (self-contained, fetches own data)
│   └── MonthlyGiftsCard (self-contained, fetches own data)
├── Stat Cards (4-col grid)
│   ├── StatCard: Thank You Queue
│   ├── StatCard: Recent Donations
│   ├── StatCard: Active Pledges
│   └── StatCard: Items Needing Attention
├── MPD Section (conditional, 3-col grid) -- only if mpdData.has_data
│   └── MPDStatsInline (renders 3 Card fragments)
└── Main Content (2-col grid)
    ├── Left Column
    │   ├── NeedsAttention
    │   └── SupportProgress
    └── Right Column
        ├── RecentDonations
        ├── RecentJournalActivity
        └── LateDonations
```

### Recommended Drag Architecture

**Key design choice: Per-section reordering only.** Tiles reorder within their visual section but cannot move between sections. This preserves the dashboard's visual hierarchy (giving charts stay together, stat cards stay together, content cards stay together) and avoids complex cross-container collision detection.

**Draggable sections:**
1. **Giving Widgets** -- 2 items, 2-column grid: GivingSummaryCard, MonthlyGiftsCard
2. **Stat Cards** -- 4 items, 4-column grid (collapses to 2-col on md): the four StatCards
3. **Main Content Cards** -- 5 items in a single flat list rendered as 2-column grid: NeedsAttention, SupportProgress, RecentDonations, RecentJournalActivity, LateDonations

**Non-draggable sections (excluded):**
- Header (not a tile)
- MPD Section (conditional, renders Fragment children into parent grid -- not a standalone Card)

For the main content section, the current left/right column split should be flattened into a single SortableContext with `rectSortingStrategy`. CSS Grid with `grid-template-columns: repeat(2, 1fr)` handles the visual 2-column layout, while dnd-kit handles the logical ordering. This allows tiles to flow naturally into the grid based on their array position.

### Pattern 1: SortableSection Wrapper Component

**What:** A reusable component that wraps a section of tiles with DnD sorting capability.
**When to use:** Each draggable section of the dashboard.

```typescript
// Source: @dnd-kit/sortable official docs (dndkit.com/presets/sortable)
import { SortableContext, rectSortingStrategy } from '@dnd-kit/sortable';

interface SortableSectionProps {
  id: string;
  items: string[];
  children: React.ReactNode;
  strategy?: typeof rectSortingStrategy;
}

function SortableSection({ id, items, children, strategy = rectSortingStrategy }: SortableSectionProps) {
  return (
    <SortableContext id={id} items={items} strategy={strategy}>
      {children}
    </SortableContext>
  );
}
```

### Pattern 2: SortableTile Wrapper Component

**What:** A wrapper that makes any dashboard card sortable with a drag handle.
**When to use:** Wrapping each dashboard tile component.

```typescript
// Source: @dnd-kit/sortable official docs
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical } from 'lucide-react';

interface SortableTileProps {
  id: string;
  children: React.ReactNode;
}

function SortableTile({ id, children }: SortableTileProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="relative">
      {/* Drag handle */}
      <button
        className="absolute top-4 left-2 z-10 cursor-grab active:cursor-grabbing
                   text-muted-foreground hover:text-foreground p-1 rounded
                   opacity-0 group-hover:opacity-100 transition-opacity"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      {children}
    </div>
  );
}
```

### Pattern 3: DragOverlay Ghost Preview

**What:** Renders a semi-transparent copy of the dragged tile at the cursor position.
**When to use:** In the main DndContext to show drag feedback.

```typescript
// Source: dnd-kit docs (drag overlay)
import { DndContext, DragOverlay, closestCenter } from '@dnd-kit/core';

function Dashboard() {
  const [activeId, setActiveId] = useState<string | null>(null);

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={({ active }) => setActiveId(active.id as string)}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setActiveId(null)}
    >
      {/* ... sections ... */}
      <DragOverlay>
        {activeId ? (
          <div className="opacity-60 shadow-lg rounded-lg">
            {renderTileById(activeId)}
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
```

### Pattern 4: Drag Handle with PointerSensor Activation Constraint

**What:** Prevent accidental drags by requiring minimum movement distance.
**When to use:** Sensor configuration.

```typescript
// Source: @dnd-kit/core docs
import { PointerSensor, useSensor, useSensors } from '@dnd-kit/core';

const sensors = useSensors(
  useSensor(PointerSensor, {
    activationConstraint: {
      distance: 8, // 8px minimum movement before drag activates
    },
  })
);
```

### Anti-Patterns to Avoid
- **Using touch sensors for desktop-only:** The user explicitly decided no mobile/touch support. Do not add TouchSensor -- it avoids scroll gesture conflicts.
- **Cross-container sorting:** Do not implement `SortableContext` with multiple containers and item transfer. Keep each section independent.
- **Persisting to sessionStorage/localStorage:** The requirement says "resets on page refresh." React `useState` is the correct choice -- any persistence mechanism would contradict the requirement.
- **Wrapping MPDStatsInline in sortable:** MPDStatsInline renders Fragment children (3 bare Cards), not a single Card wrapper. Making these sortable would require restructuring the component and is not worth the complexity for a conditional section.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reorder animations | Manual CSS transitions on position changes | @dnd-kit/sortable transform + transition from useSortable | Handles layout recalculation, sibling displacement, and drop animation automatically |
| Array reorder logic | splice/unshift/push index manipulation | arrayMove from @dnd-kit/sortable | Immutable helper, handles edge cases (same index, out of bounds) |
| Collision detection | Distance calculations between rects | closestCenter from @dnd-kit/core | Battle-tested algorithm, handles overlapping elements, variable-sized items |
| Ghost overlay positioning | Manual portal + pointer tracking | DragOverlay from @dnd-kit/core | Renders in portal, follows cursor, handles scroll offsets, drop animation |
| Drag handle isolation | stopPropagation on inner elements | useSortable listeners applied ONLY to handle element | Clean separation -- only handle triggers drag; inner elements work normally |

**Key insight:** dnd-kit's composable architecture means each concern (sensing, collision, sorting, overlay) is a separate module. The sortable preset handles the most complex part (sibling displacement animation) which is extremely hard to implement correctly from scratch.

## Common Pitfalls

### Pitfall 1: Applying listeners to the whole tile instead of the handle
**What goes wrong:** All clicks inside the tile trigger drag behavior, breaking links, buttons, and chart interactions.
**Why it happens:** The default useSortable example spreads `{...listeners}` on the outer container.
**How to avoid:** Spread `{...listeners}` and `{...attributes}` ONLY on the drag handle button, not the tile wrapper.
**Warning signs:** Links inside tiles don't navigate; buttons don't fire click handlers.

### Pitfall 2: Missing CSS.Transform.toString() for transforms
**What goes wrong:** Tiles don't visually move during drag or snap awkwardly.
**Why it happens:** useSortable returns a Transform object, not a CSS string. Must use `CSS.Transform.toString()` from `@dnd-kit/utilities`.
**How to avoid:** Always convert: `style={{ transform: CSS.Transform.toString(transform), transition }}`.
**Warning signs:** Console errors about invalid CSS values, tiles stuck in place.

### Pitfall 3: Using CSS.Translate.toString() instead of CSS.Transform.toString()
**What goes wrong:** The scaleX/scaleY values are ignored and items may visually resize during drag.
**Why it happens:** `CSS.Translate` only outputs translate3d, while `CSS.Transform` includes scale.
**How to avoid:** Use `CSS.Transform.toString(transform)` -- it outputs the full transform including scale.
**Warning signs:** Items change size when dragged over other items.

### Pitfall 4: SortableContext items array not matching render order
**What goes wrong:** Items teleport or animate incorrectly during drag.
**Why it happens:** The `items` prop must be the same array used to map children, in the same order.
**How to avoid:** Derive the render from the same state array passed to `items`.
**Warning signs:** Visual glitches during drag, items jumping to wrong positions.

### Pitfall 5: DragOverlay not rendered inside DndContext
**What goes wrong:** Ghost overlay doesn't appear during drag.
**Why it happens:** DragOverlay must be a descendant of DndContext.
**How to avoid:** Place `<DragOverlay>` as the last child inside `<DndContext>`.
**Warning signs:** Drag works (items reorder) but no visual ghost follows the cursor.

### Pitfall 6: Forgetting activation constraint causes accidental drags
**What goes wrong:** Clicking a card header with slight mouse movement triggers a drag instead of text selection or a click.
**Why it happens:** PointerSensor activates immediately on pointerdown.
**How to avoid:** Set `activationConstraint: { distance: 8 }` on PointerSensor.
**Warning signs:** Cards seem "jumpy" when clicking near the drag handle.

## Code Examples

### Complete Sortable Dashboard Tile Wrapper

```typescript
// Source: @dnd-kit/sortable docs + project Card component
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SortableDashboardTileProps {
  id: string;
  children: React.ReactNode;
}

export function SortableDashboardTile({ id, children }: SortableDashboardTileProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group relative',
        isDragging && 'opacity-40 z-0'
      )}
    >
      {/* Drag handle -- positioned in card header area */}
      <button
        className={cn(
          'absolute top-5 left-1.5 z-10 p-0.5 rounded',
          'cursor-grab active:cursor-grabbing',
          'text-muted-foreground/0 group-hover:text-muted-foreground',
          'hover:text-foreground transition-colors duration-150'
        )}
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      {children}
    </div>
  );
}
```

### Dashboard DndContext Setup

```typescript
// Source: @dnd-kit/core + @dnd-kit/sortable docs
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragStartEvent, DragEndEvent } from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
} from '@dnd-kit/sortable';

const DEFAULT_GIVING_ORDER = ['giving-summary', 'monthly-gifts'];
const DEFAULT_STATS_ORDER = ['thank-you', 'recent-donations', 'active-pledges', 'needs-attention'];
const DEFAULT_CONTENT_ORDER = ['needs-attention-card', 'support-progress', 'recent-donations-card', 'journal-activity', 'late-donations'];

function Dashboard() {
  const [givingOrder, setGivingOrder] = useState(DEFAULT_GIVING_ORDER);
  const [statsOrder, setStatsOrder] = useState(DEFAULT_STATS_ORDER);
  const [contentOrder, setContentOrder] = useState(DEFAULT_CONTENT_ORDER);
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  function handleDragStart(event: DragStartEvent) {
    setActiveId(event.active.id as string);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);

    if (!over || active.id === over.id) return;

    // Determine which section the item belongs to and reorder
    const reorder = (
      order: string[],
      setOrder: React.Dispatch<React.SetStateAction<string[]>>
    ) => {
      const oldIndex = order.indexOf(active.id as string);
      const newIndex = order.indexOf(over.id as string);
      if (oldIndex !== -1 && newIndex !== -1) {
        setOrder(arrayMove(order, oldIndex, newIndex));
      }
    };

    reorder(givingOrder, setGivingOrder);
    reorder(statsOrder, setStatsOrder);
    reorder(contentOrder, setContentOrder);
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setActiveId(null)}
    >
      {/* Giving section */}
      <SortableContext items={givingOrder} strategy={rectSortingStrategy}>
        <div className="grid gap-6 lg:grid-cols-2">
          {givingOrder.map((id) => (
            <SortableDashboardTile key={id} id={id}>
              {renderTile(id)}
            </SortableDashboardTile>
          ))}
        </div>
      </SortableContext>

      {/* Stats section */}
      <SortableContext items={statsOrder} strategy={rectSortingStrategy}>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {statsOrder.map((id) => (
            <SortableDashboardTile key={id} id={id}>
              {renderTile(id)}
            </SortableDashboardTile>
          ))}
        </div>
      </SortableContext>

      {/* Content section -- flat grid, not left/right columns */}
      <SortableContext items={contentOrder} strategy={rectSortingStrategy}>
        <div className="grid gap-6 lg:grid-cols-2">
          {contentOrder.map((id) => (
            <SortableDashboardTile key={id} id={id}>
              {renderTile(id)}
            </SortableDashboardTile>
          ))}
        </div>
      </SortableContext>

      {/* Ghost overlay */}
      <DragOverlay>
        {activeId ? (
          <div className="opacity-60 shadow-xl rounded-lg pointer-events-none">
            {renderTile(activeId)}
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
```

### Drop Zone Placeholder Styling

```css
/* Dashed border placeholder where tile will land */
/* Applied via isDragging state on the source tile */
.sortable-placeholder {
  border: 2px dashed hsl(var(--border));
  border-radius: var(--radius);
  background: hsl(var(--muted) / 0.3);
  min-height: 120px;
}
```

Note: dnd-kit handles the gap/displacement animation automatically via transforms. The "dashed-border placeholder" from user decisions can be achieved by styling the `isDragging` tile to show a dashed border outline while its content is hidden (since DragOverlay shows the ghost copy). This means the source tile becomes the visual placeholder.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-beautiful-dnd | @dnd-kit/core + sortable | 2024+ (rbd deprecated Aug 2025) | rbd archived, no React 19 support; dnd-kit is the standard |
| react-dnd (HTML5 backend) | @dnd-kit/core | 2023+ | react-dnd has React 19 issues; less maintained |
| @dnd-kit/core + sortable | @dnd-kit/react (rewrite) | In progress (v0.3.x) | New API is cleaner but still pre-release; not yet recommended for production |
| Manual state + localStorage | React state for session-only | N/A | No persistence needed per requirements; simplest approach |

**Deprecated/outdated:**
- react-beautiful-dnd: Archived Aug 2025, no React 19 support
- react-sortable-hoc: Deprecated by the same author who created dnd-kit as its successor
- react-dnd: React 19 compatibility issues (Issue #3655)

## Open Questions

1. **Stat cards visual density with drag handles**
   - What we know: Stat cards are compact (title + large number + optional description). Adding a grip handle may feel cramped.
   - What's unclear: Whether the grip handle should be visible only on hover for stat cards, or if stat cards should use a different handle treatment.
   - Recommendation: Use hover-reveal for all tiles (consistent behavior). Stat cards have enough header space for the grip icon. Planner should decide exact positioning.

2. **Content section odd-item layout**
   - What we know: The content section has 5 tiles in a 2-column grid. The 5th tile (LateDonations) will span the bottom-left, leaving the bottom-right empty.
   - What's unclear: Whether this looks acceptable or if the last tile should span full width.
   - Recommendation: Keep standard grid flow (5th item in first column of last row). This is consistent with how CSS grid works and users can reorder to put their preferred tile at the "prominent" top positions.

## Sources

### Primary (HIGH confidence)
- @dnd-kit/core npm: peerDependencies `react: >=16.8.0` -- verified via `npm view` (React 19 compatible)
- @dnd-kit/sortable npm: peerDependencies `react: >=16.8.0, @dnd-kit/core: ^6.3.0` -- verified via `npm view`
- @dnd-kit official docs (dndkit.com/presets/sortable): SortableContext, useSortable, rectSortingStrategy, arrayMove API
- @dnd-kit official docs (dndkit.com/react/guides/migration): @dnd-kit/react rewrite status
- @hello-pangea/dnd npm: peerDependencies `react: ^18.0.0 || ^19.0.0` -- verified via `npm view`

### Secondary (MEDIUM confidence)
- [Puck blog: Top 5 DnD Libraries for React 2026](https://puckeditor.com/blog/top-5-drag-and-drop-libraries-for-react) -- ecosystem overview, confirmed dnd-kit as top choice
- [GitHub Issue #1194: dnd-kit maintenance](https://github.com/clauderic/dnd-kit/issues/1194) -- author confirmed active development
- [GitHub Issue #2672: react-beautiful-dnd deprecated](https://github.com/atlassian/react-beautiful-dnd/issues/2672) -- archived Aug 2025
- [GitHub Discussion #1842: @dnd-kit/react roadmap](https://github.com/clauderic/dnd-kit/discussions/1842) -- no maintainer response, confirms unclear stability

### Tertiary (LOW confidence)
- Bundle size estimate (~13KB gzipped total for core + sortable) -- from community sources, not verified with bundlephobia

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- @dnd-kit/core + sortable is the clear ecosystem standard; versions and peer deps verified via npm CLI
- Architecture: HIGH -- per-section SortableContext is the documented pattern for multi-area sortable layouts; code examples from official docs
- Pitfalls: HIGH -- common pitfalls documented from official docs and community issues; well-known patterns

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable library, slow-moving API)
