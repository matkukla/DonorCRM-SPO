# Phase 4: Grid UI Core - Research

**Researched:** 2026-01-24
**Domain:** React grid UI with sticky columns/headers, event timeline drawer, TanStack Table
**Confidence:** HIGH

## Summary

Phase 4 requires building a functional grid displaying contacts as rows and pipeline stages as columns, with sticky headers, color-coded freshness indicators, hover tooltips, and a clickable drawer for event timelines. The codebase already uses TanStack Table v8.21.3, React 19, Tailwind CSS, and Radix UI primitives, providing a solid foundation.

The standard approach is to extend the existing DataTable component with TanStack Table's column pinning feature using CSS position: sticky, implement cell components wrapped in React.memo to prevent re-render cascades, add Radix UI Tooltip for hover summaries, and use the existing Sheet (Radix Dialog) component for the timeline drawer with TanStack Query's useInfiniteQuery for pagination.

Key performance optimizations include memoizing column definitions, data transformations, and cell components; using stable references for props; and avoiding N+1 renders through proper useCallback/useMemo dependencies. The grid will use CSS sticky positioning rather than virtualization for the initial implementation, as the dataset size (contacts per journal) is manageable without full virtualization.

**Primary recommendation:** Extend existing DataTable with TanStack Table column pinning + sticky CSS, implement memoized cell components for stage indicators, use Radix Tooltip for hover states, Sheet for drawer, and TanStack Query infinite scroll for event pagination.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-table | 8.21.3 | Grid/table state management | Already in codebase, official TanStack solution for complex tables, excellent TypeScript support, active development |
| React | 19.2.0 | UI framework | Latest version with concurrent features for smooth scrolling, already in codebase |
| Tailwind CSS | 3.4.19 | Styling and layout | Already in codebase, excellent support for position: sticky, overflow utilities, responsive design |
| @radix-ui/react-dialog | 1.1.15 | Sheet/drawer primitive | Already in codebase as Sheet component, accessible, properly implements ARIA for dialogs |
| @radix-ui/react-tooltip | TBD | Tooltip hover states | Not yet in codebase, official Radix primitive for accessible tooltips, integrates with existing Radix components |
| @tanstack/react-query | 5.90.17 | Data fetching and pagination | Already in codebase, official solution for infinite scroll with useInfiniteQuery hook |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| date-fns | TBD | Relative time formatting | For "3 days ago" style timestamps in event timeline and freshness calculations |
| class-variance-authority | 0.7.1 | Component variants | Already in codebase for Badge variants, use for color-coded indicators |
| lucide-react | 0.562.0 | Icons | Already in codebase, use for checkmarks, chevrons, close buttons |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TanStack Table | AG Grid, MUI DataGrid | Commercial/heavier alternatives, TanStack Table already integrated and sufficient |
| CSS sticky | TanStack Virtual | Virtualization adds complexity, not needed for expected dataset size (dozens of contacts) |
| date-fns | Day.js, Moment.js | Day.js is smaller but date-fns has better tree-shaking and functional API, Moment.js is deprecated |
| Radix Tooltip | Custom tooltip | Hand-rolling loses accessibility, focus management, and ARIA compliance |

**Installation:**
```bash
npm install @radix-ui/react-tooltip date-fns
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── pages/journals/
│   ├── JournalDetail.tsx          # Main journal page with tabs
│   └── components/
│       ├── JournalGrid.tsx        # Grid container with sticky layout
│       ├── GridCell.tsx           # Memoized cell component
│       ├── StageCell.tsx          # Stage-specific cell with indicator
│       ├── ContactNameCell.tsx    # Sticky first column cell
│       └── EventTimelineDrawer.tsx # Sheet with infinite scroll
├── hooks/
│   └── useJournals.ts             # TanStack Query hooks for journal data
└── components/ui/
    └── tooltip.tsx                # Radix Tooltip component (new)
```

### Pattern 1: Sticky Column + Header with TanStack Table

**What:** Use TanStack Table's column pinning state with CSS position: sticky for fixed columns and headers

**When to use:** Grid needs sticky first column (contact names) and sticky header row (stage names)

**Example:**
```typescript
// Source: TanStack Table Column Pinning Guide
// https://tanstack.com/table/latest/docs/guide/column-pinning

const table = useReactTable({
  data,
  columns,
  getCoreRowModel: getCoreRowModel(),
  state: {
    columnPinning: {
      left: ['contact_name'], // Pin first column to left
    },
  },
})

// In component render:
<TableHead
  className="sticky left-0 z-20 bg-background"
  style={{ left: 0 }}
>
  Contact Name
</TableHead>

<TableHead className="sticky top-0 z-10 bg-background">
  Stage Name
</TableHead>
```

**Key requirements:**
- Set `position: sticky` on header cells (use Tailwind `sticky` utility)
- Apply explicit `left` or `top` values
- Use z-index hierarchy: sticky headers z-10, sticky columns z-20
- Set background color on sticky elements to cover scrolling content
- Parent container must have `overflow-auto` or `overflow-x-auto`

### Pattern 2: Memoized Grid Cells

**What:** Wrap cell components in React.memo with stable prop references to prevent cascade re-renders

**When to use:** Grid has many cells that don't need to re-render when unrelated cells change

**Example:**
```typescript
// Source: Material React Table Memoization Guide
// https://www.material-react-table.com/docs/guides/memoization

const StageCell = React.memo<StageCellProps>(({
  stageEvents,
  onCellClick
}) => {
  // Cell rendering logic
  return (
    <div onClick={onCellClick}>
      {stageEvents.length > 0 && <CheckIcon />}
    </div>
  )
}, (prevProps, nextProps) => {
  // Custom comparison: only re-render if events changed
  return prevProps.stageEvents === nextProps.stageEvents
})

// In column definition:
const columns = useMemo(() => [
  {
    id: 'contact_stage',
    cell: ({ row }) => (
      <StageCell
        stageEvents={row.original.contact_events}
        onCellClick={handleCellClick} // Must be useCallback wrapped
      />
    )
  }
], [handleCellClick]) // Stable dependency array
```

**Critical:** All function props must be wrapped in useCallback with stable dependencies

### Pattern 3: Tooltip on Hover

**What:** Use Radix Tooltip primitive for accessible hover tooltips on stage cells

**When to use:** Show event summary on hover without opening full drawer

**Example:**
```typescript
// Source: Radix UI Tooltip Documentation
// https://www.radix-ui.com/primitives/docs/components/tooltip

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

<TooltipProvider>
  <Tooltip delayDuration={300}>
    <TooltipTrigger asChild>
      <div className="cursor-pointer">
        <CheckIcon className="text-green-600" />
      </div>
    </TooltipTrigger>
    <TooltipContent>
      <p className="text-sm">Last event: Call logged</p>
      <p className="text-xs text-muted-foreground">3 days ago</p>
    </TooltipContent>
  </Tooltip>
</TooltipProvider>
```

**Important:** Use `asChild` prop to compose Tooltip with cell click handlers (prevents tooltip from blocking clicks)

### Pattern 4: Infinite Scroll Event Timeline

**What:** Use TanStack Query's useInfiniteQuery with Sheet drawer for paginated event loading

**When to use:** Event timeline drawer with "Load More" pagination

**Example:**
```typescript
// Source: TanStack Query Infinite Queries Guide
// https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries

const {
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage
} = useInfiniteQuery({
  queryKey: ['stage-events', journalContactId, stage],
  queryFn: ({ pageParam = 1 }) =>
    fetchStageEvents(journalContactId, stage, pageParam),
  getNextPageParam: (lastPage) => lastPage.nextPage,
  initialPageParam: 1,
})

// In component:
<Sheet>
  <SheetContent side="right" className="w-[400px]">
    <SheetHeader>
      <SheetTitle>Event Timeline - {stageName}</SheetTitle>
    </SheetHeader>
    <div className="space-y-4">
      {data?.pages.map(page =>
        page.events.map(event => (
          <EventCard key={event.id} event={event} />
        ))
      )}
      {hasNextPage && (
        <Button onClick={() => fetchNextPage()}>
          Load More
        </Button>
      )}
    </div>
  </SheetContent>
</Sheet>
```

### Pattern 5: Time-Based Color Coding

**What:** Calculate time since last event and apply color-coded Badge variants

**When to use:** Visual freshness indicators for stage activity

**Example:**
```typescript
// Using date-fns for time calculations
import { differenceInDays, differenceInWeeks } from 'date-fns'

function getFreshnessColor(lastEventDate: string | null): BadgeVariant {
  if (!lastEventDate) return 'secondary' // No events

  const daysSince = differenceInDays(new Date(), new Date(lastEventDate))

  if (daysSince < 7) return 'success'      // Green: <1 week
  if (daysSince < 30) return 'warning'     // Yellow: <1 month (using amber in Badge)
  if (daysSince < 90) return 'default'     // Orange: <3 months (need custom)
  return 'destructive'                     // Red: 3+ months
}

// In cell render:
const freshnessColor = getFreshnessColor(lastEventDate)
<Badge variant={freshnessColor}>
  <CheckIcon className="h-3 w-3" />
</Badge>
```

**Note:** May need to add 'orange' variant to Badge component (currently has warning=amber, destructive=red)

### Anti-Patterns to Avoid

- **Creating new functions in render:** Every function prop must be useCallback wrapped with stable deps
- **Non-memoized column definitions:** Columns array must be useMemo wrapped to prevent table re-initialization
- **Sticky without z-index:** Sticky elements overlap incorrectly without proper z-index hierarchy
- **Missing background on sticky elements:** Transparent backgrounds show scrolling content underneath
- **Tooltip wrapping click handlers:** Use asChild prop to compose properly, or preventDefault on tooltip trigger focus
- **Infinite query without getNextPageParam:** Without proper pagination config, useInfiniteQuery won't load more pages

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data table with sorting, filtering | Custom table from scratch | TanStack Table | Handles column state, sorting, filtering, pagination out of the box; already integrated |
| Tooltip positioning and accessibility | CSS-only tooltip with absolute positioning | Radix UI Tooltip | Auto-positioning, focus management, keyboard navigation, ARIA attributes, SSR-safe |
| Drawer/modal with animations | Custom overlay + transform animations | Radix UI Dialog (Sheet) | Portal rendering, focus trap, escape handling, scroll lock, ARIA dialog role, already integrated |
| Infinite scroll pagination | Manual scroll event listeners + offset tracking | TanStack Query useInfiniteQuery | Automatic page caching, optimistic updates, loading states, error handling, refetch logic |
| Relative time formatting | Custom date diff calculations | date-fns formatDistance/formatRelative | Handles edge cases (DST, leap years), i18n support, consistent formatting |
| Virtual scrolling | Custom windowing with getBoundingClientRect | TanStack Virtual (if needed later) | Maintains scroll position, handles dynamic heights, optimized render cycles |

**Key insight:** The grid interaction patterns (sticky positioning, tooltips, drawers, infinite scroll) are all solved problems with robust, accessible, well-tested solutions. Hand-rolling any of these introduces bugs, accessibility gaps, and maintenance burden.

## Common Pitfalls

### Pitfall 1: Re-render Cascade from Non-Memoized Props

**What goes wrong:** Every cell re-renders on every state change because function props have new references

**Why it happens:**
- Column definitions not wrapped in useMemo
- Cell click handlers not wrapped in useCallback
- Data transformations recalculated on every render
- Parent component re-renders propagate to all cells

**How to avoid:**
```typescript
// BAD: New column array on every render
const columns = [
  {
    id: 'stage',
    cell: ({ row }) => <StageCell onClick={() => handleClick(row.id)} /> // New function every render!
  }
]

// GOOD: Memoized columns and callbacks
const handleCellClick = useCallback((rowId: string) => {
  // handle click
}, []) // Stable dependency array

const columns = useMemo(() => [
  {
    id: 'stage',
    cell: ({ row }) => <StageCell onClick={handleCellClick} rowId={row.id} />
  }
], [handleCellClick])
```

**Warning signs:**
- Grid feels sluggish when clicking or scrolling
- React DevTools Profiler shows all cells rendering
- Console logs in cell components fire excessively

### Pitfall 2: Sticky Elements Z-Index Conflicts

**What goes wrong:** Sticky headers hide behind sticky columns, or both hide under Sheet overlay

**Why it happens:**
- Missing or incorrect z-index values
- Conflicting stacking contexts
- Sheet overlay has z-50 by default

**How to avoid:**
- Use z-index hierarchy: base cells (z-0), sticky headers (z-10), sticky columns (z-20), sticky header+column intersection (z-30), Sheet overlay (z-50)
- Apply background colors to all sticky elements
- Test scroll in both directions to verify layering

**Warning signs:**
- Headers disappear behind columns when scrolling horizontally
- Column names covered by data cells when scrolling vertically
- Sticky elements flicker or jump during scroll

### Pitfall 3: Missing Background on Sticky Elements

**What goes wrong:** Scrolling content shows through sticky headers/columns

**Why it happens:** Default table cell background is transparent

**How to avoid:**
```typescript
// Apply explicit background to sticky elements
<TableHead className="sticky left-0 z-20 bg-background">
  Contact Name
</TableHead>
```

Use `bg-background` (HSL CSS variable from theme) instead of `bg-white` for dark mode compatibility

### Pitfall 4: Tooltip Interfering with Cell Click

**What goes wrong:** Can't click cell because tooltip trigger intercepts click events

**Why it happens:** Tooltip wraps cell content without composing properly

**How to avoid:**
```typescript
// Use asChild to compose tooltip with clickable element
<Tooltip>
  <TooltipTrigger asChild>
    <button onClick={handleCellClick}>
      <CheckIcon />
    </button>
  </TooltipTrigger>
  <TooltipContent>Summary</TooltipContent>
</Tooltip>
```

Or use `onOpenAutoFocus={(e) => e.preventDefault()}` on TooltipContent to prevent focus stealing

### Pitfall 5: Infinite Query Cache Invalidation

**What goes wrong:** New events don't appear in timeline drawer after logging them

**Why it happens:** TanStack Query cache not invalidated when events are added

**How to avoid:**
```typescript
// After creating event, invalidate the infinite query
const addEventMutation = useMutation({
  mutationFn: createStageEvent,
  onSuccess: () => {
    queryClient.invalidateQueries({
      queryKey: ['stage-events', journalContactId, stage]
    })
  }
})
```

### Pitfall 6: Overflow Container Missing

**What goes wrong:** Sticky positioning doesn't work

**Why it happens:** Parent container needs overflow property for sticky to function

**How to avoid:**
```typescript
// Ensure grid container has overflow
<div className="overflow-x-auto">
  <Table>
    {/* sticky headers/columns */}
  </Table>
</div>
```

## Code Examples

Verified patterns from official sources and codebase analysis:

### Sticky Grid Layout Structure

```typescript
// Source: Existing DataTable component + TanStack Table sticky examples
// https://github.com/TanStack/table/discussions/4471

<div className="relative w-full overflow-x-auto border rounded-lg">
  <table className="w-full caption-bottom text-sm">
    <thead>
      <tr className="border-b">
        {/* Sticky header + sticky column intersection */}
        <th className="sticky top-0 left-0 z-30 bg-background h-12 px-4 text-left font-medium">
          Contact
        </th>
        {/* Sticky headers only */}
        {stages.map(stage => (
          <th key={stage} className="sticky top-0 z-10 bg-background h-12 px-4 text-left font-medium">
            {stage}
          </th>
        ))}
      </tr>
    </thead>
    <tbody>
      {contacts.map(contact => (
        <tr key={contact.id} className="border-b">
          {/* Sticky column only */}
          <td className="sticky left-0 z-20 bg-background p-4">
            {contact.name}
          </td>
          {/* Regular cells */}
          {stages.map(stage => (
            <td key={stage} className="p-4">
              <StageCell contact={contact} stage={stage} />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  </table>
</div>
```

### Memoized Stage Cell Component

```typescript
// Source: Material React Table memoization patterns
// https://www.material-react-table.com/docs/guides/memoization

interface StageCellProps {
  contactId: string
  stage: PipelineStage
  events: StageEvent[]
  onCellClick: (contactId: string, stage: PipelineStage) => void
}

export const StageCell = React.memo<StageCellProps>(({
  contactId,
  stage,
  events,
  onCellClick
}) => {
  const handleClick = useCallback(() => {
    onCellClick(contactId, stage)
  }, [contactId, stage, onCellClick])

  const lastEvent = events[0] // Assumes sorted by created_at desc
  const freshnessColor = getFreshnessColor(lastEvent?.created_at)

  if (events.length === 0) {
    return <div className="h-8 w-8" /> // Empty state
  }

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <button onClick={handleClick} className="h-8 w-8 flex items-center justify-center">
            <Badge variant={freshnessColor} className="p-1">
              <Check className="h-3 w-3" />
            </Badge>
          </button>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p className="text-sm font-medium">{lastEvent.event_type}</p>
          <p className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(lastEvent.created_at), { addSuffix: true })}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}, (prev, next) => {
  // Only re-render if events changed
  return prev.events === next.events
})
```

### Event Timeline Drawer with Infinite Scroll

```typescript
// Source: TanStack Query infinite queries documentation
// https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries

import { useInfiniteQuery } from '@tanstack/react-query'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'

interface EventTimelineDrawerProps {
  journalContactId: string
  stage: PipelineStage
  isOpen: boolean
  onClose: () => void
}

export function EventTimelineDrawer({
  journalContactId,
  stage,
  isOpen,
  onClose
}: EventTimelineDrawerProps) {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading
  } = useInfiniteQuery({
    queryKey: ['stage-events', journalContactId, stage],
    queryFn: ({ pageParam = 1 }) =>
      fetchStageEvents(journalContactId, stage, { page: pageParam, page_size: 5 }),
    getNextPageParam: (lastPage) => lastPage.next ? lastPage.page + 1 : undefined,
    initialPageParam: 1,
    enabled: isOpen, // Only fetch when drawer is open
  })

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[400px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Event Timeline - {stage}</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {isLoading && <p>Loading events...</p>}

          {data?.pages.map((page, pageIndex) => (
            <div key={pageIndex} className="space-y-3">
              {page.results.map((event) => (
                <div key={event.id} className="border-l-2 border-muted pl-4 pb-4">
                  <div className="flex items-start justify-between">
                    <p className="text-sm font-medium">{event.event_type}</p>
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(event.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  {event.notes && (
                    <p className="text-sm text-muted-foreground mt-1">{event.notes}</p>
                  )}
                </div>
              ))}
            </div>
          ))}

          {hasNextPage && (
            <Button
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              variant="outline"
              className="w-full"
            >
              {isFetchingNextPage ? 'Loading...' : 'Load More'}
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
```

### Tooltip Component (New)

```typescript
// Source: shadcn/ui Tooltip component
// https://ui.shadcn.com/docs/components/tooltip

import * as React from "react"
import * as TooltipPrimitive from "@radix-ui/react-tooltip"
import { cn } from "@/lib/utils"

const TooltipProvider = TooltipPrimitive.Provider

const Tooltip = TooltipPrimitive.Root

const TooltipTrigger = TooltipPrimitive.Trigger

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      "z-50 overflow-hidden rounded-md bg-foreground px-3 py-1.5 text-xs text-background animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
      className
    )}
    {...props}
  />
))
TooltipContent.displayName = TooltipPrimitive.Content.displayName

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-table v7 | TanStack Table v8 | 2022 | Complete rewrite with better TypeScript, hooks-based API, smaller bundle |
| react-virtualized/react-window | TanStack Virtual v3 | 2023 | More flexible, better composability, cleaner API for sticky elements |
| Moment.js for dates | date-fns v3/v4 | 2020+ | Functional API, tree-shakeable, smaller bundle, Moment in maintenance mode |
| Custom tooltip libraries | Radix UI Tooltip | 2021+ | Unstyled primitive, WAI-ARIA compliant, composable with asChild |
| Manual scroll event handlers | Intersection Observer API | 2019+ | Native browser API, better performance, used with TanStack Query infinite scroll |
| React 17 rendering | React 19 concurrent features | 2024 | Non-blocking UI updates during data fetching, smoother infinite scroll |

**Deprecated/outdated:**
- react-table v7: Replaced by TanStack Table v8, v7 no longer maintained
- react-virtualized: Maintenance mode, replaced by react-window and TanStack Virtual
- Moment.js: Officially in maintenance mode, recommends alternatives like date-fns
- Manual virtualization: Browser-native Intersection Observer + TanStack libraries handle most cases

## Open Questions

Things that couldn't be fully resolved:

1. **Exact dataset size for virtualization decision**
   - What we know: Current codebase doesn't use virtualization, typical journal has dozens of contacts
   - What's unclear: Whether 50+ contacts with 6 columns causes noticeable performance issues
   - Recommendation: Start with CSS sticky (simpler), add TanStack Virtual in Phase 5 if performance degrades with real data

2. **Orange variant for Badge component**
   - What we know: Badge has success (green), warning (amber), destructive (red) but no orange
   - What's unclear: Whether "orange" should map to existing warning or need custom variant
   - Recommendation: Add custom orange variant to Badge (bg-orange-100 text-orange-800) for <3 month freshness

3. **Tooltip positioning edge cases**
   - What we know: Radix handles auto-positioning, grid is horizontally scrollable
   - What's unclear: Whether tooltips overflow container or flip properly when cells near edges
   - Recommendation: Test with cells at far right of scroll container, may need sideOffset or collision padding config

4. **Sheet width responsiveness**
   - What we know: Current Sheet uses sm:max-w-sm for left/right, phase spec says "right-side drawer"
   - What's unclear: Optimal width for event timeline on mobile vs desktop
   - Recommendation: Use 400px (w-[400px]) on desktop, full-width (w-full) on mobile (< sm breakpoint)

5. **Grid cell interaction priority (tooltip vs click)**
   - What we know: Need both hover tooltip and click-to-open-drawer
   - What's unclear: Whether tooltip delays interfere with quick clicks
   - Recommendation: Use delayDuration={300} for tooltip (tested standard), asChild composition to prevent conflicts

## Sources

### Primary (HIGH confidence)
- [TanStack Table v8 Column Pinning Guide](https://tanstack.com/table/latest/docs/guide/column-pinning) - Official column pinning documentation
- [TanStack Table Sticky Column Example](https://tanstack.com/table/latest/docs/framework/react/examples/column-pinning-sticky) - Official sticky positioning example
- [TanStack Query Infinite Queries Guide](https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries) - Official infinite scroll documentation
- [Radix UI Tooltip Documentation](https://www.radix-ui.com/primitives/docs/components/tooltip) - Official tooltip primitive
- [Tailwind CSS Position Documentation](https://tailwindcss.com/docs/position) - Official sticky positioning utilities
- Codebase analysis (package.json, existing DataTable, Sheet, Badge components) - Verified installed versions and patterns

### Secondary (MEDIUM confidence)
- [Material React Table Memoization Guide](https://www.material-react-table.com/docs/guides/memoization) - Community best practices for TanStack Table performance
- [TanStack Table Discussion #4471](https://github.com/TanStack/table/discussions/4471) - Working Tailwind + sticky implementation
- [React.dev memo reference](https://react.dev/reference/react/memo) - Official React.memo documentation
- [date-fns documentation](https://date-fns.org/) - Official date-fns v4 with formatDistance examples
- [shadcn/ui Tooltip](https://ui.shadcn.com/docs/components/tooltip) - Radix-based tooltip implementation pattern
- [W3C ARIA Grid Pattern](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/) - Accessibility guidelines for grids

### Tertiary (LOW confidence)
- Medium articles on TanStack Virtual vs react-window comparisons (2025) - Recent performance testing
- Blog posts on React performance optimization (2026) - General best practices
- Community discussions on tooltip + dialog composition - Edge case handling

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in codebase except Tooltip and date-fns, official TanStack/Radix docs
- Architecture: HIGH - Patterns verified with official examples and existing codebase patterns
- Pitfalls: MEDIUM-HIGH - Common issues documented in GitHub discussions and Material React Table guides
- Performance: HIGH - React.memo patterns, TanStack Table memoization documented in official guides
- Accessibility: HIGH - Radix UI components follow WAI-ARIA standards, verified in official docs

**Research date:** 2026-01-24
**Valid until:** 30 days (stable ecosystem, TanStack libraries mature)

**Research flags addressed:**
- Fine-tune grid virtualization configuration for Tailwind CSS layout: Researched CSS sticky approach (simpler) vs TanStack Virtual, recommend starting without virtualization given expected dataset size
- React grid cell re-render cascade: Documented React.memo + useCallback patterns with stable references, memoized column definitions, custom comparison functions
