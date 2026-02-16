# Phase 18: Interactive Visualizations & Drill-Down - Research

**Researched:** 2026-02-14
**Domain:** React interactive visualizations, Recharts click handlers, Radix UI modals, drill-down UI patterns
**Confidence:** HIGH

## Summary

This phase implements interactive chart drill-downs and side panel overlays for data exploration. The standard approach uses Recharts onClick handlers to capture user interactions, Radix UI Dialog (as Sheet) for accessible slide-in panels, and TanStack Query's `enabled` option for conditional data fetching.

The established stack already includes all required libraries: Recharts 3.6 for chart interactivity, Radix UI Dialog for the Sheet component, and TanStack Query 5.90 for conditional fetching. The key pattern is coordinating three state concerns: (1) panel open/close state, (2) selected drill-down parameters (stage, user ID), and (3) conditional data fetching triggered by those parameters.

The main architectural decision is **local component state for drill-down UI** (not URL state). Drill-downs are transient exploration actions that shouldn't be bookmarkable or shareable. Modal open/close state and selected parameters live in React useState, with TanStack Query's `enabled` option preventing data fetches until parameters exist.

**Primary recommendation:** Use Recharts onClick on Funnel component for stage drill-down, Radix UI Sheet with controlled open state for slide-in panels, and TanStack Query's `enabled: !!parameter` pattern for conditional fetching.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Recharts | 3.6.0 | Chart click handlers | Already used, supports onClick/onMouseEnter events on all chart components |
| @radix-ui/react-dialog | 1.1.15 | Sheet/slide-in panel | Already used, provides accessible modal with controlled state, keyboard navigation, focus trapping |
| @tanstack/react-query | 5.90.17 | Conditional data fetching | Already used, `enabled` option prevents fetches until params ready |
| React useState | Built-in | Local UI state management | Standard for transient UI state (modal open/close, selected IDs) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-table | 8.21.3 | Drill-down contact lists | Already used, provides sorting/pagination for contact tables |
| lucide-react | 0.562.0 | Close icons, arrows | Already used, provides X icon for close buttons |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Local state | URL query params | URL state makes drill-downs bookmarkable but adds complexity; only needed if users share drill-down views |
| Radix Dialog as Sheet | Separate sheet library | Radix Dialog with side="right" prop already provides sheet behavior |
| enabled option | skipToken | skipToken is TypeScript-specific, enabled is more universal and works with refetch |

**Installation:**
```bash
# No new packages needed - all dependencies already installed
```

## Architecture Patterns

### Recommended Component Structure
```
src/pages/admin/analytics/
├── components/
│   ├── ConversionFunnelChart.tsx          # Add onClick handler
│   ├── TeamActivityTable.tsx              # Add row onClick or drill-down button
│   ├── FunnelDrilldownPanel.tsx           # New: Sheet for stage contacts
│   └── UserDrilldownPanel.tsx             # New: Sheet for user quick view
└── AdminAnalyticsDashboard.tsx            # Coordinate panel state
```

### Pattern 1: Recharts Click Handler with Data Access
**What:** Capture chart segment clicks and access underlying data
**When to use:** Funnel stage drill-down - clicking a stage opens contact list

**Implementation approach:**
```typescript
// In ConversionFunnelChart.tsx
import { Funnel } from "recharts"

// Define handler that receives data, index, and event
const handleFunnelClick = (data: any, index: number, e: React.MouseEvent) => {
  // data contains the clicked segment's data object
  // Access stage name and count from data
  const stageName = data.name  // or data.stage, depending on data structure
  const count = data.value

  // Call parent handler with stage parameter
  onStageClick?.(stageName)
}

<Funnel
  dataKey="value"
  data={chartData}
  onClick={handleFunnelClick}
  cursor="pointer"  // Visual feedback
>
```

**Key insight from Recharts API:** The onClick callback signature is `(data: any, index: number, e: React.MouseEvent) => void`. The first parameter contains the data object for the clicked segment, which includes all properties from the original data point.

**Source:** [Recharts FunnelChart API](https://recharts.github.io/en-US/api/FunnelChart/)

### Pattern 2: Radix UI Dialog as Controlled Sheet
**What:** Slide-in sidebar panel for drill-down details
**When to use:** Both funnel stage contacts and user drilldown panels

**Implementation approach:**
```typescript
// In parent component (AdminAnalyticsDashboard.tsx)
const [drilldownState, setDrilldownState] = useState<{
  open: boolean
  stage: string | null
}>({ open: false, stage: null })

const handleStageClick = (stage: string) => {
  setDrilldownState({ open: true, stage })
}

const handleClose = () => {
  setDrilldownState({ open: false, stage: null })
}

// In FunnelDrilldownPanel.tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"

function FunnelDrilldownPanel({ open, stage, onClose }) {
  return (
    <Sheet open={open} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Contacts in {stage}</SheetTitle>
        </SheetHeader>
        {/* Contact list content */}
      </SheetContent>
    </Sheet>
  )
}
```

**Key insight from Radix UI:** Use controlled mode (`open` + `onOpenChange`) to programmatically manage sheet state. The `onOpenChange` callback fires when user closes via Esc or overlay click, enabling cleanup in parent component.

**Source:** [Radix UI Dialog Documentation](https://www.radix-ui.com/primitives/docs/components/dialog)

### Pattern 3: Conditional Data Fetching with TanStack Query
**What:** Only fetch drill-down data when panel is open and parameters exist
**When to use:** Loading contact lists for stage drill-down, user stats for user panel

**Implementation approach:**
```typescript
// In FunnelDrilldownPanel.tsx
import { useQuery } from "@tanstack/react-query"

function FunnelDrilldownPanel({ open, stage, onClose }) {
  // Query only runs when stage exists (panel open)
  const { data, isLoading } = useQuery({
    queryKey: ["insights", "stage-contacts", stage],
    queryFn: () => getContactsByStage(stage!),
    enabled: !!stage,  // Critical: prevents fetch when stage is null
    staleTime: 5 * 60 * 1000,
  })

  return (
    <Sheet open={open} onOpenChange={(open) => !open && onClose()}>
      <SheetContent>
        {isLoading ? <LoadingSkeleton /> : <ContactTable data={data} />}
      </SheetContent>
    </Sheet>
  )
}
```

**Key insight from TanStack Query:** The `enabled` option prevents automatic fetching, background refetches, and invalidation/refetch calls when false. When enabled switches to true, the query fetches immediately. This is ideal for drill-down panels where data shouldn't load until the panel opens.

**Important caveat:** A disabled query may still return cached data from previous fetches. Don't assume `data` is undefined when enabled is false.

**Source:** [TanStack Query Disabling/Pausing Queries](https://tanstack.com/query/v4/docs/react/guides/disabling-queries)

### Pattern 4: Table Row Click vs Action Button
**What:** Two approaches for triggering user drilldown from Team Activity Table
**When to use:** Team Activity Table user drilldown

**Option A: Row click (simpler, better UX)**
```typescript
<TableRow
  key={row.id}
  onClick={() => onUserClick(row.original.user_id)}
  className="cursor-pointer hover:bg-muted/50"
>
```

**Option B: Action button in column (more explicit)**
```typescript
columnHelper.display({
  id: "actions",
  cell: (info) => (
    <Button
      variant="ghost"
      size="sm"
      onClick={(e) => {
        e.stopPropagation()  // Prevent row click if both used
        onUserClick(info.row.original.user_id)
      }}
    >
      View Details
    </Button>
  )
})
```

**Recommendation:** Use action button for clarity, especially if table has other clickable elements. This matches established pattern from existing admin detail pages.

### Anti-Patterns to Avoid
- **Don't use URL state for transient drill-downs:** URL query params add complexity and make accidental bookmarking possible. Use local state unless drill-down views need to be shareable.
- **Don't fetch drill-down data eagerly:** Loading all possible drill-down data upfront wastes bandwidth and slows initial page load. Use conditional fetching.
- **Don't forget cleanup in useEffect:** Event listeners added for keyboard shortcuts or custom interactions must be removed on unmount to prevent memory leaks.
- **Don't use enabled: false permanently:** This opts out of background refetches and invalidation. Only use for conditional fetching, not to defer initial load.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accessible modal/sheet | Custom overlay + portal + focus trap | Radix UI Dialog | Focus trapping, keyboard navigation (Esc to close, Tab cycling), screen reader announcements, and WAI-ARIA compliance are complex |
| Conditional data fetching | Manual flags + useEffect + fetch | TanStack Query enabled option | Handles race conditions, automatic retries, caching, and background refetches correctly |
| Chart click detection | Custom SVG event listeners | Recharts onClick prop | Recharts already provides data context, handles touch events, and normalizes event handling |
| Contact list pagination/sorting | Custom table state | @tanstack/react-table (already used) | Handles complex sorting, filtering, pagination state correctly |

**Key insight:** Drill-down UI appears simple but has many edge cases. Accessible keyboard navigation, focus management when opening/closing panels, race conditions from rapid clicks, and memory leaks from event listeners all require careful handling. Using established patterns prevents these issues.

## Common Pitfalls

### Pitfall 1: Memory Leaks from Event Listeners
**What goes wrong:** Adding event listeners in useEffect without cleanup causes memory leaks when components unmount or re-render.

**Why it happens:** Modals/panels often add keyboard event listeners (e.g., Esc to close). If the cleanup function is missing, these listeners persist after unmount.

**How to avoid:**
```typescript
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }

  window.addEventListener('keydown', handleKeyDown)

  // Critical: cleanup function
  return () => {
    window.removeEventListener('keydown', handleKeyDown)
  }
}, [onClose])
```

**Note:** Radix UI Dialog handles Esc key automatically, so this is only needed for custom keyboard shortcuts.

**Warning signs:** Increasing memory usage in Chrome DevTools Performance tab when repeatedly opening/closing panels. Multiple handler invocations when pressing Esc.

**Source:** [How to fix the React memory leak warning](https://jexperton.dev/en/blog/how-to-fix-react-memory-leak-warning/)

### Pitfall 2: Race Conditions from Rapid Clicks
**What goes wrong:** User clicks multiple funnel stages rapidly, causing multiple drill-down panels to fight for display or data to load out of order.

**Why it happens:** Each click triggers state update and data fetch. Fast clicks queue multiple state updates, leading to inconsistent UI state.

**How to avoid:**
```typescript
// Option 1: Close existing panel before opening new one (recommended)
const handleStageClick = (newStage: string) => {
  setDrilldownState({ open: true, stage: newStage })  // New stage replaces old
}

// Option 2: Debounce clicks if needed (for very rapid clicks)
import { useMemo } from 'react'
import debounce from 'lodash/debounce'

const handleStageClick = useMemo(
  () => debounce((stage: string) => {
    setDrilldownState({ open: true, stage })
  }, 100),
  []
)
```

**Recommendation:** Option 1 is sufficient. The state replacement pattern naturally handles rapid clicks by replacing the previous drill-down with the new one.

**Warning signs:** Panel flickering between different drill-down views. Console errors about state updates on unmounted components.

### Pitfall 3: Assuming Disabled Query Returns No Data
**What goes wrong:** Developers expect `data` to be undefined when `enabled: false`, but cached data from previous fetches may still be returned.

**Why it happens:** TanStack Query caches successful fetch results. Setting `enabled: false` prevents new fetches but doesn't clear the cache.

**How to avoid:**
```typescript
// Don't rely on data being undefined
const { data, isLoading } = useQuery({
  queryKey: ["stage-contacts", stage],
  queryFn: () => getContactsByStage(stage!),
  enabled: !!stage,
})

// Instead, check if stage exists
if (!stage) {
  return <div>Select a stage to view contacts</div>
}

// Or use isLoading to show loading state
if (isLoading) {
  return <LoadingSkeleton />
}
```

**Warning signs:** Drill-down panel shows contacts from previous stage when opened with new stage. Stale data displayed briefly before fresh data loads.

**Source:** [TanStack Query Disabling Queries Documentation](https://tanstack.com/query/v4/docs/react/guides/disabling-queries)

### Pitfall 4: Missing TypeScript Types for Recharts onClick
**What goes wrong:** TypeScript errors when typing Recharts onClick handlers because RechartsFunction type has unclear signatures.

**Why it happens:** The @types/recharts definitions for onClick historically had incomplete type signatures (data: any, index: number, event: MouseEvent).

**How to avoid:**
```typescript
// Use explicit types based on your data structure
interface FunnelDataPoint {
  name: string
  value: number
  percentage: number
  stage: string | null
}

const handleFunnelClick = (
  data: FunnelDataPoint,
  index: number,
  e: React.MouseEvent
) => {
  onStageClick?.(data.stage || data.name)
}

// Or use a more permissive type for flexibility
const handleFunnelClick = (
  data: any,  // Recharts doesn't provide strict typing
  index: number,
  e: React.MouseEvent
) => {
  // Type-guard to ensure safety
  if (data && typeof data.stage === 'string') {
    onStageClick(data.stage)
  }
}
```

**Recommendation:** Define your own data interface based on chartData structure. Recharts onClick types are loose by design since data shape varies by use case.

**Warning signs:** TypeScript errors like "Type 'any' is not assignable to type..." when accessing data properties.

**Source:** [DefinitelyTyped Recharts Issue #20722](https://github.com/DefinitelyTyped/DefinitelyTyped/issues/20722)

### Pitfall 5: Accessibility Issues with Drill-Down Panels
**What goes wrong:** Keyboard users can't navigate drill-down panels, screen readers don't announce panel content, focus isn't trapped in modal.

**Why it happens:** Custom panels without proper ARIA attributes, focus management, and keyboard handlers fail accessibility requirements.

**How to avoid:**
```typescript
// Use Radix UI Dialog which handles this automatically
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"

<Sheet open={open} onOpenChange={onOpenChange}>
  <SheetContent>
    <SheetHeader>
      <SheetTitle>Contacts in {stageName}</SheetTitle>
      <SheetDescription>
        {contactCount} contacts currently in this pipeline stage
      </SheetDescription>
    </SheetHeader>
    {/* Content */}
  </SheetContent>
</Sheet>
```

**Key accessibility features from Radix UI:**
- Esc key to close (automatic)
- Tab key cycles through interactive elements within panel (focus trap)
- Overlay click to close (customizable)
- Screen reader announcements for title and description
- Proper ARIA roles and attributes (dialog, aria-modal, aria-labelledby, aria-describedby)

**Optionally hide description visually:**
```typescript
import { VisuallyHidden } from "@radix-ui/react-visually-hidden"

<SheetDescription asChild>
  <VisuallyHidden>Panel description for screen readers</VisuallyHidden>
</SheetDescription>
```

**Warning signs:** Keyboard users report inability to close panel or navigate content. Screen reader users don't hear panel announcements. Focus jumps outside panel during Tab navigation.

**Source:** [Radix UI Dialog Accessibility](https://www.radix-ui.com/primitives/docs/components/dialog)

## Code Examples

Verified patterns from official sources and existing codebase:

### Example 1: Funnel Chart with Click Handler
```typescript
// ConversionFunnelChart.tsx - Add interactivity
import { useState } from "react"
import { FunnelChart, Funnel, LabelList, Tooltip } from "recharts"

interface FunnelDataPoint {
  name: string
  value: number
  percentage: number
  fill: string
  stage: string | null  // Backend stage identifier
}

interface ConversionFunnelChartProps {
  onStageClick?: (stage: string) => void  // New prop
}

export function ConversionFunnelChart({ onStageClick }: ConversionFunnelChartProps) {
  const { data, isLoading } = useAdminConversionFunnel()

  const chartData = useMemo(() => {
    if (!data?.funnel) return []
    return data.funnel.map((stage, index) => ({
      name: stage.label,
      value: stage.count,
      percentage: stage.percentage,
      stage: stage.stage,  // Include backend identifier
      fill: FUNNEL_COLORS[index % FUNNEL_COLORS.length],
    }))
  }, [data])

  const handleClick = (data: any, index: number, e: React.MouseEvent) => {
    if (data.stage && onStageClick) {
      onStageClick(data.stage)
    }
  }

  if (isLoading) return <ChartSkeleton />
  if (!chartData.length) return <EmptyChart />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Funnel</CardTitle>
        <CardDescription>Click a stage to view contacts</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={{}} className="min-h-[400px] w-full">
          <FunnelChart>
            <Tooltip content={/* ... */} />
            <Funnel
              dataKey="value"
              data={chartData}
              isAnimationActive
              onClick={handleClick}
              cursor="pointer"  // Visual feedback
            >
              <LabelList
                position="right"
                fill="hsl(var(--foreground))"
                stroke="none"
                dataKey="name"
              />
            </Funnel>
          </FunnelChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
```

**Source:** Existing codebase pattern + [Recharts FunnelChart API](https://recharts.github.io/en-US/api/FunnelChart/)

### Example 2: Funnel Drill-Down Panel Component
```typescript
// components/FunnelDrilldownPanel.tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { useQuery } from "@tanstack/react-query"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

interface FunnelDrilldownPanelProps {
  open: boolean
  stage: string | null
  onClose: () => void
}

export function FunnelDrilldownPanel({ open, stage, onClose }: FunnelDrilldownPanelProps) {
  // Conditional fetch - only runs when stage exists
  const { data, isLoading } = useQuery({
    queryKey: ["insights", "stage-contacts", stage],
    queryFn: () => getContactsByStage(stage!),
    enabled: !!stage,
    staleTime: 5 * 60 * 1000,
  })

  return (
    <Sheet open={open} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>
            {stage ? `Contacts in ${stage}` : "Stage Contacts"}
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6">
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-muted rounded animate-pulse" />
              ))}
            </div>
          ) : !data?.contacts || data.contacts.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              No contacts in this stage
            </p>
          ) : (
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Owner</TableHead>
                    <TableHead>Last Activity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.contacts.map((contact) => (
                    <TableRow key={contact.id}>
                      <TableCell>{contact.full_name}</TableCell>
                      <TableCell>{contact.owner_name}</TableCell>
                      <TableCell>
                        {contact.last_activity_date
                          ? format(new Date(contact.last_activity_date), "MMM d, yyyy")
                          : "No activity"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
```

**Source:** Existing codebase patterns + [Radix UI Dialog](https://www.radix-ui.com/primitives/docs/components/dialog)

### Example 3: User Drilldown from Table
```typescript
// TeamActivityTable.tsx - Add user drilldown trigger
import { Button } from "@/components/ui/button"
import { Eye } from "lucide-react"

const columns = [
  // ... existing columns ...
  columnHelper.display({
    id: "actions",
    header: "Actions",
    cell: (info) => (
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onUserDrilldown?.(info.row.original.user_email)}
      >
        <Eye className="h-4 w-4 mr-2" />
        Quick View
      </Button>
    ),
  }),
]

export function TeamActivityTable({
  onUserDrilldown
}: {
  onUserDrilldown?: (userEmail: string) => void
}) {
  // ... existing implementation ...
}
```

**Source:** Existing codebase patterns + [TanStack Table display columns](https://tanstack.com/table/latest/docs/guide/column-defs)

### Example 4: Coordinating Panel State in Parent
```typescript
// AdminAnalyticsDashboard.tsx - Coordinate drill-down state
import { useState } from "react"

export function AdminAnalyticsDashboard() {
  // Funnel drill-down state
  const [funnelDrilldown, setFunnelDrilldown] = useState<{
    open: boolean
    stage: string | null
  }>({ open: false, stage: null })

  // User drill-down state
  const [userDrilldown, setUserDrilldown] = useState<{
    open: boolean
    userId: string | null
  }>({ open: false, userId: null })

  return (
    <div>
      {/* Existing dashboard widgets */}
      <ConversionFunnelChart
        onStageClick={(stage) => setFunnelDrilldown({ open: true, stage })}
      />

      <TeamActivityTable
        onUserDrilldown={(userId) => setUserDrilldown({ open: true, userId })}
      />

      {/* Drill-down panels */}
      <FunnelDrilldownPanel
        open={funnelDrilldown.open}
        stage={funnelDrilldown.stage}
        onClose={() => setFunnelDrilldown({ open: false, stage: null })}
      />

      <UserDrilldownPanel
        open={userDrilldown.open}
        userId={userDrilldown.userId}
        onClose={() => setUserDrilldown({ open: false, userId: null })}
      />
    </div>
  )
}
```

**Source:** React state management best practices

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Imperative modal APIs (`modal.open()`) | Declarative controlled components (`open={state}`) | React 16+ hooks era | Clearer data flow, easier testing, no imperative refs |
| Custom fetch flags | TanStack Query enabled option | TanStack Query v3+ (2021) | Automatic caching, retries, background refetches, race condition handling |
| Custom focus trapping | Radix UI Dialog primitives | Radix UI v1.0 (2022) | WAI-ARIA compliance, keyboard navigation, accessibility |
| Chart.js (requires canvas) | Recharts (SVG-based) | Recharts maturity ~2020 | Better React integration, declarative API, responsive by default |

**Deprecated/outdated:**
- **react-modal:** Popular but requires manual focus trapping, ARIA attributes, and body scroll lock. Radix UI Dialog handles this automatically.
- **URL state for all UI:** Pre-hooks era pattern of storing modal state in URL params. Modern approach uses local state for transient UI, reserves URL for shareable/bookmarkable state.

## Open Questions

Things that couldn't be fully resolved:

1. **Backend endpoint for stage contacts**
   - What we know: Need GET endpoint that accepts `stage` parameter and returns contact list
   - What's unclear: Exact endpoint path, parameter name (stage vs stage_id), response pagination
   - Recommendation: Define endpoint in Phase 18 backend task. Likely `/insights/admin/stage-contacts/?stage={stage_name}` following existing pattern

2. **User drill-down data requirements**
   - What we know: Need key stats, recent journal activity, stalled contact count for selected user
   - What's unclear: Whether this needs new endpoint or can reuse existing user-detail endpoints from Phase 17
   - Recommendation: Check Phase 17 implementation. If user detail page already loads this data, reuse those hooks with conditional enabled pattern

3. **Stage naming consistency**
   - What we know: Funnel data has both `stage` (backend identifier, may be null) and `label` (display name)
   - What's unclear: Whether to use `stage` or `label` for filtering contacts
   - Recommendation: Use `stage` for backend filtering (consistent with database field), use `label` for UI display

## Sources

### Primary (HIGH confidence)
- Recharts FunnelChart API - https://recharts.github.io/en-US/api/FunnelChart/ - Event handler signatures verified
- Radix UI Dialog Documentation - https://www.radix-ui.com/primitives/docs/components/dialog - Controlled state, accessibility features
- TanStack Query Disabling Queries - https://tanstack.com/query/v4/docs/react/guides/disabling-queries - enabled option behavior
- Existing codebase - /frontend/src/api/insights.ts, /frontend/src/hooks/useInsights.ts - Established patterns verified

### Secondary (MEDIUM confidence)
- [Create Interactive Charts With Recharts](https://medium.com/weekly-webtips/create-interactive-charts-with-recharts-5e947b76b5b8) - Event handler patterns
- [React State Management in 2025](https://www.developerway.com/posts/react-state-management-2025) - Local state vs global state guidance
- [Performance & Request Waterfalls | TanStack Query](https://tanstack.com/query/latest/docs/framework/react/guides/request-waterfalls) - Conditional fetching performance
- [How to fix the React memory leak warning](https://jexperton.dev/en/blog/how-to-fix-react-memory-leak-warning/) - useEffect cleanup patterns

### Tertiary (LOW confidence)
- WebSearch: "React drill-down UI patterns" - General guidance only, not Recharts-specific
- WebSearch: "React admin dashboard drill-down best practices 2026" - Framework-agnostic patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and in use, versions verified from package.json
- Architecture: HIGH - Recharts onClick API verified, Radix Dialog patterns verified, TanStack Query enabled pattern verified with official docs
- Pitfalls: HIGH - Memory leaks, race conditions, disabled query caching, TypeScript typing, accessibility all documented with authoritative sources

**Research date:** 2026-02-14
**Valid until:** 2026-03-16 (30 days - stable domain, libraries mature)
