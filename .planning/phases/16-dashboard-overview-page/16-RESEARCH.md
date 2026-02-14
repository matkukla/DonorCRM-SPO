# Phase 16: Dashboard Overview Page - Research

**Researched:** 2026-02-14
**Domain:** React dashboard UI with Recharts visualizations, sortable tables, and alert panels
**Confidence:** HIGH

## Summary

Phase 16 enhances the existing AdminAnalyticsDashboard page (created in Phase 15) with five core widgets: summary cards (already implemented), Team Activity Table, Alerts Panel, Trend Charts, and Conversion Funnel visualization. The backend already provides all necessary data through five admin analytics endpoints built in Phases 13-14, except for trend data which needs a new endpoint or client-side computation.

The project already uses Recharts 3.6.0 for all visualizations, has a ChartContainer wrapper for consistent styling, uses TanStack Table v8 for sortable tables, and follows established patterns for dashboard alerts (NeedsAttention component). The standard approach is to add widgets incrementally to the existing AdminAnalyticsDashboard.tsx page, creating reusable chart components following the pattern in ReportCharts.tsx.

**Primary recommendation:** Build trend endpoint backend-first, then implement widgets as separate components (TeamActivityTable, AlertsPanel, TrendCharts, FunnelChart) following existing project patterns, integrating them into the existing AdminAnalyticsDashboard page.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Recharts | 3.6.0 | Data visualization | Already project standard, composable React charts with declarative API |
| @tanstack/react-table | 8.21.3 | Sortable tables | Already in use for ContactList, TaskList; headless UI for tables |
| @tanstack/react-query | 5.90.17 | Data fetching | Already used for all admin analytics hooks |
| Radix UI | Latest | UI primitives | Already project standard for Card, Badge, Table components |
| Tailwind CSS | 3.4.19 | Styling | Project standard for all UI styling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | 0.562.0 | Icons | Alert icons (AlertTriangle, TrendingUp, etc.) |
| date-fns | 4.1.0 | Date formatting | Formatting timestamps in Team Activity Table |
| class-variance-authority | 0.7.1 | Component variants | Badge variants for alert severity levels |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Recharts FunnelChart | Custom BarChart horizontal | FunnelChart API exists but custom may give more control over funnel shape |
| TanStack Table | Simple HTML table with onClick sorting | TanStack provides better performance, accessibility, but simple table may suffice for small datasets |
| Client-side trend computation | New backend endpoint | Backend endpoint is cleaner but adds API complexity |

**Installation:**
All required libraries already installed. No new dependencies needed.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/pages/admin/analytics/
├── AdminAnalyticsDashboard.tsx           # Main page (already exists)
└── components/                           # New: dashboard widgets
    ├── TeamActivityTable.tsx             # Sortable table widget
    ├── AlertsPanel.tsx                   # Rule-based coaching prompts
    ├── TrendCharts.tsx                   # 12-week line chart
    └── ConversionFunnelChart.tsx         # Funnel visualization
```

### Pattern 1: Widget Components with ChartContainer
**What:** Each visualization is a separate component that consumes React Query hooks and renders within ChartContainer
**When to use:** For all Recharts visualizations (Trend Charts, Funnel Chart)
**Example:**
```typescript
// Source: frontend/src/pages/journals/components/ReportCharts.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const trendConfig = {
  decisions: { label: "Decisions", color: "hsl(var(--chart-1))" },
  donations: { label: "Donations", color: "hsl(var(--chart-2))" },
} satisfies ChartConfig

export function TrendCharts() {
  const { data, isLoading } = useAdminTrendData() // New hook

  if (isLoading) return <ChartSkeleton title="Team Trends" />
  if (!data?.length) return <EmptyChart title="Team Trends" />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Team Metrics (12 Weeks)</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={trendConfig} className="min-h-[300px] w-full">
          <LineChart data={data}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="week" tickLine={false} tickMargin={10} axisLine={false} />
            <YAxis />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Line dataKey="decisions" stroke="var(--color-decisions)" strokeWidth={2} />
            <Line dataKey="donations" stroke="var(--color-donations)" strokeWidth={2} />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
```

### Pattern 2: Alerts Panel with Colored Alert Boxes
**What:** Panel displays rule-based coaching prompts using colored boxes similar to NeedsAttention component
**When to use:** For Alerts Panel widget (DASH-03)
**Example:**
```typescript
// Source: Adapted from frontend/src/components/dashboard/NeedsAttention.tsx
export function AlertsPanel() {
  const { data: overview } = useAdminDashboardOverview()
  const { data: users } = useAdminUserPerformance()

  const alerts = computeAlerts(overview, users) // Client-side alert rules

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <CardTitle>Coaching Alerts</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={cn(
                "p-4 rounded-lg border",
                alert.severity === "high" && "bg-red-50 border-red-100",
                alert.severity === "medium" && "bg-amber-50 border-amber-100",
                alert.severity === "low" && "bg-blue-50 border-blue-100"
              )}
            >
              <p className="font-medium text-sm">{alert.message}</p>
              {alert.actionLink && (
                <Button variant="link" size="sm" asChild>
                  <Link to={alert.actionLink}>View details</Link>
                </Button>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
```

### Pattern 3: Sortable Table with TanStack Table
**What:** Team Activity Table using existing DataTable component or custom TanStack Table implementation
**When to use:** For Team Activity Table widget (DASH-02)
**Example:**
```typescript
// Source: Pattern from frontend/src/components/shared/DataTable.tsx
import { createColumnHelper } from "@tanstack/react-table"
import type { TeamActivityItem } from "@/api/insights"

const columnHelper = createColumnHelper<TeamActivityItem>()

const columns = [
  columnHelper.accessor("created_at", {
    header: "Date",
    cell: (info) => format(new Date(info.getValue()), "MMM d, yyyy HH:mm"),
  }),
  columnHelper.accessor("user_name", {
    header: "User",
  }),
  columnHelper.accessor("event_type", {
    header: "Event",
  }),
  columnHelper.accessor("title", {
    header: "Description",
  }),
]

export function TeamActivityTable() {
  const { data, isLoading } = useAdminTeamActivity({ limit: 50 })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Team Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <DataTable
          columns={columns}
          data={data?.activities || []}
          isLoading={isLoading}
        />
      </CardContent>
    </Card>
  )
}
```

### Pattern 4: Funnel Chart with Recharts or Custom Bars
**What:** Conversion funnel using Recharts FunnelChart or horizontal BarChart styled as funnel
**When to use:** For Conversion Funnel visualization (PIPE-01)
**Example:**
```typescript
// Source: Recharts FunnelChart API (https://recharts.github.io/en-US/api/FunnelChart)
import { FunnelChart, Funnel, LabelList, Tooltip } from "recharts"

export function ConversionFunnelChart() {
  const { data, isLoading } = useAdminConversionFunnel()

  if (isLoading) return <ChartSkeleton title="Conversion Funnel" />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Funnel</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={funnelConfig} className="min-h-[400px] w-full">
          <FunnelChart>
            <Tooltip content={<ChartTooltipContent />} />
            <Funnel
              dataKey="count"
              data={data?.funnel}
              isAnimationActive
            >
              <LabelList
                position="right"
                fill="#000"
                stroke="none"
                dataKey="label"
              />
            </Funnel>
          </FunnelChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
```

### Anti-Patterns to Avoid
- **Inline chart configuration:** Don't embed chart config objects directly in JSX; define ChartConfig objects outside component
- **Mixed data fetching:** Don't mix backend data fetching with client-side computation in same component; separate concerns
- **Hardcoded sort state:** Don't manage sort state manually in Team Activity Table; use TanStack Table's built-in sorting or delegate to backend
- **Monolithic dashboard component:** Don't build all widgets in AdminAnalyticsDashboard.tsx; extract to separate widget components

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Funnel visualization | Custom SVG funnel from scratch | Recharts FunnelChart component | Handles responsive sizing, animations, tooltips, accessibility |
| Sortable table | Manual onClick handlers for sorting | TanStack Table getSortedRowModel | Handles multi-column sort, sort direction, type-aware sorting |
| Chart responsiveness | Custom resize observers | ChartContainer with ResponsiveContainer | Already wraps Recharts ResponsiveContainer for 100% width/height |
| Alert severity styling | Inline conditional classes | CVA (class-variance-authority) Badge variants | Already established pattern in project (badge.tsx has warning/destructive variants) |
| Date formatting | String manipulation | date-fns format() | Already in package.json; handles timezones, locales, edge cases |
| Trend data aggregation | Manual array reduce loops | Backend endpoint with database GROUP BY | Database is faster, handles timezones, avoids transferring raw data |

**Key insight:** Dashboard visualizations have many edge cases (empty states, loading states, responsive breakpoints, accessibility). Recharts and TanStack Table handle these; custom solutions miss them.

## Common Pitfalls

### Pitfall 1: Missing Trend Data Endpoint
**What goes wrong:** Phase 16 requires 12-week trend chart (DASH-04) but backend has no trend endpoint; attempting to compute trends client-side from existing data fails when data doesn't include time-series information
**Why it happens:** Backend endpoints return current snapshot data (total contacts, active journals), not historical trends
**How to avoid:** Add backend endpoint `/api/v1/insights/admin/team-trends/` that returns weekly aggregated metrics (decisions_logged, donations_received, stage_progressions) for past 12 weeks using Django annotate with TruncWeek
**Warning signs:** React Query hook returns data but no time-series fields; client-side code attempts to fetch historical data multiple times

### Pitfall 2: Funnel Chart Data Format Mismatch
**What goes wrong:** Recharts FunnelChart expects specific data shape (array with numeric dataKey), but backend ConversionFunnelResponse has nested structure
**Why it happens:** Backend response shape designed for table display, not funnel chart
**How to avoid:** Transform data in React Query hook or component: `data.funnel.map(stage => ({ name: stage.label, value: stage.count, fill: STAGE_COLORS[index] }))`
**Warning signs:** FunnelChart renders empty or shows wrong values; console errors about missing dataKey

### Pitfall 3: Alert Rules Hardcoded in Component
**What goes wrong:** Alert logic scattered in AlertsPanel component makes rules hard to test, modify, or reuse
**Why it happens:** Temptation to compute alerts inline during render
**How to avoid:** Extract alert rules to separate utility function `computeAlerts(overview, users)` that can be unit tested; rules as data-driven configuration
**Warning signs:** AlertsPanel component has complex conditional logic; alerts change but tests don't fail

### Pitfall 4: Team Activity Table Re-fetches on Every Sort
**What goes wrong:** Clicking column header to sort causes new API call, making sort feel slow
**Why it happens:** Confusing server-side sorting (stalled contacts endpoint has sort_by param) with client-side sorting (Team Activity)
**How to avoid:** Team Activity endpoint returns all 50 items; use TanStack Table's getSortedRowModel for client-side sorting (no API calls)
**Warning signs:** Network tab shows API request on every sort click; sort takes >500ms

### Pitfall 5: Inconsistent Widget Loading States
**What goes wrong:** Some widgets show loading skeletons, others show empty divs, making dashboard feel broken during load
**Why it happens:** Each widget component handles loading differently
**How to avoid:** Standardize on loading skeleton pattern from existing code: `if (isLoading) return <ChartSkeleton title="..." />` for charts, skeleton rows for tables
**Warning signs:** Dashboard flickers or jumps during load; some widgets invisible until data loads

### Pitfall 6: Overusing Recharts Animations
**What goes wrong:** Every chart animates on mount, dashboard feels sluggish with 5 widgets animating simultaneously
**Why it happens:** Recharts components have `isAnimationActive={true}` by default
**How to avoid:** Set `isAnimationActive={false}` on all charts except Funnel (which benefits from animation), or coordinate animations with stagger delay
**Warning signs:** Dashboard feels slow to load even with data cached; CPU usage spikes on page load

## Code Examples

Verified patterns from official sources:

### Alert Rules Computation
```typescript
// Source: Derived from dashboard alert patterns (NeedsAttention.tsx)
interface CoachingAlert {
  id: string
  message: string
  severity: "high" | "medium" | "low"
  actionLink?: string
}

function computeAlerts(
  overview?: DashboardOverviewResponse,
  users?: UserPerformanceItem[]
): CoachingAlert[] {
  if (!overview || !users) return []

  const alerts: CoachingAlert[] = []

  // Rule: High stalled contact count
  if (overview.stalled_contacts > 20) {
    alerts.push({
      id: "stalled-contacts-high",
      message: `${overview.stalled_contacts} contacts stalled >14 days across team`,
      severity: "high",
      actionLink: "/admin/analytics/stalled-contacts",
    })
  }

  // Rule: Individual user with many stalled contacts
  users.forEach((user) => {
    const stalledCount = computeStalledForUser(user.id) // Would need separate data
    if (stalledCount > 8) {
      alerts.push({
        id: `user-stalled-${user.id}`,
        message: `${user.name} has ${stalledCount} contacts stalled >21 days`,
        severity: "medium",
        actionLink: `/admin/analytics/users/${user.id}`,
      })
    }
  })

  // Rule: Low team conversion rate
  if (overview.conversion_rate < 15) {
    alerts.push({
      id: "conversion-rate-low",
      message: `Team conversion rate at ${overview.conversion_rate.toFixed(1)}% (below 15% threshold)`,
      severity: "low",
    })
  }

  return alerts
}
```

### Multi-Line Trend Chart
```typescript
// Source: Recharts LineChart API + project pattern (ReportCharts.tsx)
interface TrendDataPoint {
  week: string        // e.g., "Week of Jan 1"
  decisions: number
  donations: number
  progressions: number
}

const trendConfig = {
  decisions: { label: "Decisions", color: "hsl(var(--chart-1))" },
  donations: { label: "Donations", color: "hsl(var(--chart-2))" },
  progressions: { label: "Stage Changes", color: "hsl(var(--chart-3))" },
} satisfies ChartConfig

export function TrendCharts() {
  const { data, isLoading } = useAdminTrendData()

  if (isLoading) return <ChartSkeleton title="Team Trends (12 Weeks)" />
  if (!data?.trends.length) return <EmptyChart title="Team Trends" message="No trend data available" />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Team Metrics (12 Weeks)</CardTitle>
        <CardDescription>Decisions, donations, and stage progressions</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={trendConfig} className="min-h-[300px] w-full">
          <LineChart data={data.trends}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="week"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
              tick={{ fontSize: 12 }}
            />
            <YAxis tickLine={false} axisLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Line
              dataKey="decisions"
              stroke="var(--color-decisions)"
              strokeWidth={2}
              dot={{ r: 4 }}
              isAnimationActive={false}
            />
            <Line
              dataKey="donations"
              stroke="var(--color-donations)"
              strokeWidth={2}
              dot={{ r: 4 }}
              isAnimationActive={false}
            />
            <Line
              dataKey="progressions"
              stroke="var(--color-progressions)"
              strokeWidth={2}
              dot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
```

### Funnel Chart Data Transformation
```typescript
// Source: Recharts FunnelChart examples + project ConversionFunnelResponse type
import { FunnelChart, Funnel, LabelList, Tooltip } from "recharts"

const FUNNEL_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--chart-6))",
]

export function ConversionFunnelChart() {
  const { data, isLoading } = useAdminConversionFunnel()

  const chartData = useMemo(() => {
    if (!data?.funnel) return []
    return data.funnel.map((stage, index) => ({
      name: stage.label,
      value: stage.count,
      percentage: stage.percentage,
      fill: FUNNEL_COLORS[index],
    }))
  }, [data])

  if (isLoading) return <ChartSkeleton title="Conversion Funnel" />
  if (!chartData.length) return <EmptyChart title="Conversion Funnel" />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Funnel</CardTitle>
        <CardDescription>
          {data?.total_contacts_in_pipeline} contacts in pipeline
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={{}} className="min-h-[400px] w-full">
          <FunnelChart width={600} height={400}>
            <Tooltip
              content={({ payload }) => {
                if (!payload?.[0]) return null
                const data = payload[0].payload
                return (
                  <div className="bg-background border rounded-lg p-2 shadow-lg">
                    <p className="font-medium">{data.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {data.value} contacts ({data.percentage.toFixed(1)}%)
                    </p>
                  </div>
                )
              }}
            />
            <Funnel
              dataKey="value"
              data={chartData}
              isAnimationActive
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

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Simple HTML tables with inline sort | TanStack Table v8 with headless UI | 2024+ | Better performance, accessibility, type safety |
| Chart.js with class components | Recharts with hooks | 2023+ | Composable, React-native API, easier theming |
| Custom tooltip components | Recharts ChartTooltip + ChartTooltipContent | Project established | Consistent styling, dark mode support |
| Global alert state management | Client-side computed alerts from query data | 2025+ | Simpler, no extra state, re-computes on data change |
| Manual responsive chart sizing | ResponsiveContainer in ChartContainer | Recharts standard | Automatic width/height, no resize listeners needed |

**Deprecated/outdated:**
- Manual sort state management: Use TanStack Table's sorting features instead
- Chart.js: Recharts is project standard
- Custom CSS Grid for dashboard layout: Use Tailwind grid classes following project patterns

## Open Questions

Things that couldn't be fully resolved:

1. **Trend data backend endpoint design**
   - What we know: No existing trend endpoint; need weekly aggregated metrics for 12 weeks
   - What's unclear: Should endpoint return 12 data points (one per week) or allow flexible date ranges? Should it aggregate by week-start Monday or week-start Sunday?
   - Recommendation: Create `/api/v1/insights/admin/team-trends/` endpoint that returns fixed 12 weeks (most recent), aggregated by week-start Monday (ISO standard), with metrics: decisions_logged, donations_received, stage_progressions

2. **Alert rules data source**
   - What we know: DASH-03 requires rule-based coaching prompts like "Sarah has 8 contacts stalled >21 days"
   - What's unclear: Should alerts be computed client-side from existing data or require new backend endpoint with per-user stalled counts?
   - Recommendation: Compute alerts client-side for Phase 16 using existing dashboard overview and user performance data; extract user-specific stalled counts to Phase 17 when building User Detail page

3. **Funnel chart interaction (PIPE-02)**
   - What we know: Phase 18 requires drill-down on funnel click to see contacts in that stage
   - What's unclear: Should Phase 16 funnel chart be built with click handlers or defer all interactivity to Phase 18?
   - Recommendation: Build static funnel chart in Phase 16; add click handlers in Phase 18 to avoid premature complexity

## Sources

### Primary (HIGH confidence)
- Recharts FunnelChart API - https://recharts.github.io/en-US/api/FunnelChart
- Recharts LineChart API - https://recharts.github.io/en-US/api/LineChart
- Project codebase: frontend/src/components/ui/chart.tsx (ChartContainer pattern)
- Project codebase: frontend/src/pages/journals/components/ReportCharts.tsx (chart component examples)
- Project codebase: frontend/src/components/shared/DataTable.tsx (TanStack Table pattern)
- Project codebase: frontend/src/components/dashboard/NeedsAttention.tsx (alert panel pattern)
- Project codebase: frontend/src/api/insights.ts (API types and hooks)
- Project codebase: apps/insights/views.py (backend endpoints)

### Secondary (MEDIUM confidence)
- [Creating a React sortable table - LogRocket Blog](https://blog.logrocket.com/creating-react-sortable-table/) - TanStack Table best practices verified with official docs
- [Dashboard Design Principles 2026 - DesignRush](https://www.designrush.com/agency/ui-ux-design/dashboard/trends/dashboard-design-principles) - Alert panel UX patterns
- [React Admin Dashboard Guide - Refine](https://refine.dev/blog/react-admin-dashboard/) - Dashboard component structure patterns

### Tertiary (LOW confidence)
- Web search: "Recharts funnel chart 2026" - Confirmed FunnelChart component exists in Recharts API
- Web search: "React sortable table patterns 2026" - TanStack Table mentioned as current standard

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in package.json and actively used in codebase
- Architecture: HIGH - Patterns verified from existing project code (ReportCharts.tsx, NeedsAttention.tsx, DataTable.tsx)
- Pitfalls: HIGH - Based on project patterns and Recharts/TanStack Table documentation
- Trend endpoint design: MEDIUM - Backend pattern clear but specifics (12 weeks, aggregation) inferred from requirement text

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (30 days - stable libraries, established project patterns)
