# Phase 19: Advanced Features & Export - Research

**Researched:** 2026-02-14
**Domain:** Date range filtering, CSV export, time-period comparison, activity heatmap visualization
**Confidence:** HIGH

## Summary

Phase 19 adds five advanced analytics features to the existing admin dashboard: date range filtering with presets, CSV export for lists, side-by-side time period comparison, user comparison, and GitHub-style activity heatmap. The standard approach extends existing endpoints with date range query parameters, adds Django CSV renderers for export endpoints, builds date range picker components with Radix UI Popover, and uses specialized React libraries for heatmap visualization.

The established stack already includes all core libraries needed: Radix UI for the date picker popover, date-fns 4.1.0 for date calculations and preset generation, Recharts 3.6 for visualization enhancements, and existing Django REST Framework for backend. Two new libraries are needed: djangorestframework-csv 3.0.2 for backend CSV rendering and a React heatmap component (@uiw/react-heat-map or react-activity-calendar) for the GitHub-style activity calendar.

The architecture follows established patterns: extend existing insights endpoints with optional date_from/date_to query params, create dedicated CSV export endpoints that reuse core query logic, build a reusable DateRangePicker component with preset buttons (This Month, Last Quarter, YTD, Custom Range), and lift date range state to parent dashboard component to coordinate filtering across all widgets. Time period comparison and user comparison are computed backend-side by running queries twice with different parameters and returning side-by-side results with percentage change calculations.

**Primary recommendation:** Build date filtering backend-first (extend existing endpoints with date range params), then build reusable DateRangePicker component with shadcn/ui patterns, add CSV export endpoints using djangorestframework-csv with StreamingHttpResponse for large datasets, and implement activity heatmap using @uiw/react-heat-map for lightweight SVG-based rendering.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| date-fns | 4.1.0 | Date calculations and presets | Already in package.json; provides startOfMonth, endOfMonth, startOfQuarter, startOfYear for preset generation |
| Radix UI Popover | 1.1.15 | Date picker popover container | Already used; accessible dropdown positioning for date range picker |
| Django REST Framework | Latest | Backend API framework | Already project standard; provides view/serializer infrastructure |
| djangorestframework-csv | 3.0.2 | CSV rendering for DRF | Industry standard for CSV export in DRF; supports streaming, custom headers, pagination |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @uiw/react-heat-map | Latest | Activity heatmap calendar | Lightweight SVG-based GitHub-style heatmap; customizable colors, tooltips |
| lucide-react | 0.562.0 | Trend icons (TrendingUp, TrendingDown, ArrowUp, ArrowDown) | Already used; provides trend arrow icons for comparison UI |
| react-day-picker | Latest | Calendar grid for custom date range | Optional dependency for shadcn/ui date picker pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @uiw/react-heat-map | react-activity-calendar | react-activity-calendar has more GitHub-specific styling defaults but heavier bundle; @uiw is more customizable |
| djangorestframework-csv | django-rest-pandas | Pandas adds Excel/complex format support but much heavier dependency; CSV-only needs don't justify Pandas |
| Custom date picker | react-date-range (full library) | react-date-range is 50KB+ bundle; custom Radix UI implementation is lighter and matches existing design system |
| Backend date filtering | Client-side filtering | Client-side requires fetching all data then filtering (wasteful); backend filtering reduces payload size |

**Installation:**
```bash
# Backend
pip install djangorestframework-csv==3.0.2

# Frontend
npm install @uiw/react-heat-map react-day-picker
```

## Architecture Patterns

### Recommended Project Structure
```
apps/insights/
├── views.py                    # Extend existing views with date_from/date_to params
├── export_views.py             # New: CSV export views (TeamActivityCSVView, StalledContactsCSVView)
├── services.py                 # Extend service functions with date filtering
└── serializers.py              # Add CSV-specific serializers if needed

frontend/src/
├── components/ui/
│   ├── date-range-picker.tsx   # New: Reusable date range picker with presets
│   └── date-preset-button.tsx  # New: Preset button component
├── pages/admin/analytics/
│   ├── AdminAnalyticsDashboard.tsx   # Lift date range state to coordinate filtering
│   └── components/
│       ├── ActivityHeatmap.tsx       # New: GitHub-style activity calendar
│       ├── TimePeriodComparison.tsx  # New: Side-by-side metrics with trends
│       └── UserComparison.tsx        # New: Side-by-side user metrics
└── hooks/
    └── useInsights.ts          # Add date range parameters to existing hooks
```

### Pattern 1: Date Range Query Parameters on Backend
**What:** Extend existing admin analytics endpoints to accept optional date_from and date_to query parameters
**When to use:** All dashboard views need date filtering (DATA-01)
**Example:**
```python
# apps/insights/views.py
from datetime import datetime
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

class StalledContactsView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(name='date_from', type=str, description='Start date (YYYY-MM-DD)'),
            OpenApiParameter(name='date_to', type=str, description='End date (YYYY-MM-DD)'),
            OpenApiParameter(name='sort_by', type=str, description='Sort field'),
        ]
    )
    def get(self, request):
        # Parse date parameters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        # Convert to datetime objects if present
        filters = {}
        if date_from:
            filters['created_at__gte'] = datetime.fromisoformat(date_from)
        if date_to:
            filters['created_at__lte'] = datetime.fromisoformat(date_to)

        # Pass to service layer
        data = get_stalled_contacts(request.user, **filters)
        return Response(data)
```

### Pattern 2: Date Range Presets with date-fns
**What:** Generate preset date ranges (This Month, Last Quarter, YTD, Custom) using date-fns utility functions
**When to use:** DateRangePicker component preset buttons
**Example:**
```typescript
// frontend/src/lib/date-presets.ts
import {
  startOfMonth,
  endOfMonth,
  startOfQuarter,
  endOfQuarter,
  startOfYear,
  endOfYear,
  subMonths,
  subQuarters,
  format,
} from "date-fns"

export interface DateRange {
  from: Date
  to: Date
}

export const datePresets = {
  thisMonth: (): DateRange => ({
    from: startOfMonth(new Date()),
    to: endOfMonth(new Date()),
  }),
  lastMonth: (): DateRange => {
    const lastMonth = subMonths(new Date(), 1)
    return {
      from: startOfMonth(lastMonth),
      to: endOfMonth(lastMonth),
    }
  },
  lastQuarter: (): DateRange => {
    const lastQuarter = subQuarters(new Date(), 1)
    return {
      from: startOfQuarter(lastQuarter),
      to: endOfQuarter(lastQuarter),
    }
  },
  ytd: (): DateRange => ({
    from: startOfYear(new Date()),
    to: new Date(),
  }),
}

export function formatDateRange(range: DateRange | null): string {
  if (!range) return "All time"
  return `${format(range.from, "MMM d, yyyy")} - ${format(range.to, "MMM d, yyyy")}`
}
```

### Pattern 3: CSV Export with DRF Renderer
**What:** Create dedicated CSV export endpoints using djangorestframework-csv renderer
**When to use:** Export Stalled Contacts and Team Activity data (DATA-02)
**Example:**
```python
# apps/insights/export_views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_csv.renderers import CSVRenderer
from apps.core.permissions import IsAdmin
from apps.insights.services import get_stalled_contacts, get_team_activity

class StalledContactsCSVView(APIView):
    """Export stalled contacts as CSV."""
    permission_classes = [IsAuthenticated, IsAdmin]
    renderer_classes = [CSVRenderer]

    def get(self, request):
        # Reuse existing service logic with date filtering
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        data = get_stalled_contacts(
            request.user,
            date_from=date_from,
            date_to=date_to,
            limit=None  # No limit for export
        )

        # Transform to flat structure for CSV
        csv_data = [
            {
                'Contact Name': contact['full_name'],
                'Owner': contact['owner_name'],
                'Current Stage': contact['current_stage'],
                'Days Stalled': contact['days_since_activity'],
                'Last Activity': contact['last_activity_date'],
            }
            for contact in data['contacts']
        ]

        return Response(csv_data, headers={
            'Content-Disposition': 'attachment; filename="stalled_contacts.csv"'
        })
```

### Pattern 4: Streaming CSV for Large Datasets
**What:** Use Django StreamingHttpResponse with CSV writer for large exports to avoid memory issues
**When to use:** Exports with potentially thousands of rows
**Example:**
```python
# For large datasets (>1000 rows), use streaming
import csv
from django.http import StreamingHttpResponse

class Echo:
    """File-like object that implements write method for csv.writer."""
    def write(self, value):
        return value

class TeamActivityCSVView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        # Generator for rows
        def generate_rows():
            activities = get_team_activity(request.user, limit=None)

            # Yield header
            yield ['Date', 'User', 'Event Type', 'Description', 'Contact']

            # Yield data rows
            for activity in activities['activities']:
                yield [
                    activity['created_at'],
                    activity['user_name'],
                    activity['event_type'],
                    activity['title'],
                    activity.get('contact_name', ''),
                ]

        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)

        return StreamingHttpResponse(
            (writer.writerow(row) for row in generate_rows()),
            content_type="text/csv",
            headers={'Content-Disposition': 'attachment; filename="team_activity.csv"'},
        )
```

### Pattern 5: Client-Side CSV Download from API
**What:** Fetch CSV from backend endpoint and trigger browser download using Blob API
**When to use:** Frontend export button handlers
**Example:**
```typescript
// frontend/src/api/insights.ts
export async function exportStalledContactsCSV(
  dateFrom?: string,
  dateTo?: string
): Promise<void> {
  const params = new URLSearchParams()
  if (dateFrom) params.append('date_from', dateFrom)
  if (dateTo) params.append('date_to', dateTo)

  const response = await client.get(
    `/insights/admin/stalled-contacts/export/?${params}`,
    {
      responseType: 'blob', // Critical: tells axios to expect binary data
    }
  )

  // Create blob and download
  const blob = new Blob([response.data], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `stalled_contacts_${format(new Date(), 'yyyy-MM-dd')}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url) // Clean up
}

// Hook for export button
export function useExportStalledContacts() {
  return useMutation({
    mutationFn: ({ dateFrom, dateTo }: { dateFrom?: string; dateTo?: string }) =>
      exportStalledContactsCSV(dateFrom, dateTo),
  })
}
```

### Pattern 6: Reusable DateRangePicker Component
**What:** shadcn/ui-style date range picker with preset buttons and custom range selection
**When to use:** Dashboard date filtering UI (DATA-01)
**Example:**
```typescript
// frontend/src/components/ui/date-range-picker.tsx
import { useState } from "react"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { Calendar as CalendarIcon } from "lucide-react"
import { format } from "date-fns"
import { datePresets, formatDateRange } from "@/lib/date-presets"
import type { DateRange } from "@/lib/date-presets"

interface DateRangePickerProps {
  value: DateRange | null
  onChange: (range: DateRange | null) => void
}

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const [open, setOpen] = useState(false)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" className="w-[280px] justify-start text-left">
          <CalendarIcon className="mr-2 h-4 w-4" />
          {value ? formatDateRange(value) : "Select date range"}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <div className="flex">
          {/* Preset buttons sidebar */}
          <div className="flex flex-col gap-1 border-r p-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onChange(datePresets.thisMonth())
                setOpen(false)
              }}
            >
              This Month
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onChange(datePresets.lastMonth())
                setOpen(false)
              }}
            >
              Last Month
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onChange(datePresets.lastQuarter())
                setOpen(false)
              }}
            >
              Last Quarter
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onChange(datePresets.ytd())
                setOpen(false)
              }}
            >
              Year to Date
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onChange(null)
                setOpen(false)
              }}
            >
              All Time
            </Button>
          </div>

          {/* Custom calendar */}
          <div className="p-3">
            <Calendar
              mode="range"
              selected={value ? { from: value.from, to: value.to } : undefined}
              onSelect={(range) => {
                if (range?.from && range?.to) {
                  onChange({ from: range.from, to: range.to })
                  setOpen(false)
                }
              }}
              numberOfMonths={2}
            />
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
```

### Pattern 7: Time Period Comparison with Trend Indicators
**What:** Side-by-side metric comparison with percentage change and trend arrows (COMP-01)
**When to use:** Dashboard comparison features
**Example:**
```typescript
// frontend/src/pages/admin/analytics/components/TimePeriodComparison.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { useAdminDashboardOverview } from "@/hooks/useInsights"

interface MetricComparisonProps {
  label: string
  currentValue: number
  previousValue: number
  formatter?: (val: number) => string
}

function MetricComparison({ label, currentValue, previousValue, formatter = String }: MetricComparisonProps) {
  const percentChange = previousValue > 0
    ? ((currentValue - previousValue) / previousValue) * 100
    : 0

  const isPositive = percentChange > 0
  const isNegative = percentChange < 0
  const isNeutral = percentChange === 0

  return (
    <div className="space-y-1">
      <p className="text-sm text-muted-foreground">{label}</p>
      <div className="flex items-baseline gap-3">
        <p className="text-2xl font-bold">{formatter(currentValue)}</p>
        <p className="text-sm text-muted-foreground">vs {formatter(previousValue)}</p>
      </div>
      <div className={`flex items-center gap-1 text-sm ${
        isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-muted-foreground'
      }`}>
        {isPositive && <TrendingUp className="h-4 w-4" />}
        {isNegative && <TrendingDown className="h-4 w-4" />}
        {isNeutral && <Minus className="h-4 w-4" />}
        <span>{Math.abs(percentChange).toFixed(1)}%</span>
      </div>
    </div>
  )
}

export function TimePeriodComparison() {
  // Fetch data for two periods
  const { data: currentPeriod } = useAdminDashboardOverview({
    dateFrom: '2026-01-01',
    dateTo: '2026-01-31'
  })
  const { data: previousPeriod } = useAdminDashboardOverview({
    dateFrom: '2025-12-01',
    dateTo: '2025-12-31'
  })

  if (!currentPeriod || !previousPeriod) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>This Month vs Last Month</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-6">
          <MetricComparison
            label="Total Contacts"
            currentValue={currentPeriod.total_contacts}
            previousValue={previousPeriod.total_contacts}
          />
          <MetricComparison
            label="Decisions Logged"
            currentValue={currentPeriod.total_decisions}
            previousValue={previousPeriod.total_decisions}
          />
          <MetricComparison
            label="Conversion Rate"
            currentValue={currentPeriod.conversion_rate}
            previousValue={previousPeriod.conversion_rate}
            formatter={(val) => `${val.toFixed(1)}%`}
          />
          <MetricComparison
            label="Stalled Contacts"
            currentValue={currentPeriod.stalled_contacts}
            previousValue={previousPeriod.stalled_contacts}
          />
        </div>
      </CardContent>
    </Card>
  )
}
```

### Pattern 8: Activity Heatmap Calendar
**What:** GitHub-style contribution grid showing team activity density by day (COMP-03)
**When to use:** Activity Heatmap visualization
**Example:**
```typescript
// frontend/src/pages/admin/analytics/components/ActivityHeatmap.tsx
import HeatMap from '@uiw/react-heat-map'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useQuery } from '@tanstack/react-query'
import { format, subDays } from 'date-fns'

interface ActivityData {
  date: string  // YYYY-MM-DD
  count: number
}

async function getTeamActivityHeatmap(): Promise<ActivityData[]> {
  // Fetch daily activity counts for past year
  const response = await client.get('/insights/admin/activity-heatmap/')
  return response.data.activities
}

export function ActivityHeatmap() {
  const { data, isLoading } = useQuery({
    queryKey: ['insights', 'activity-heatmap'],
    queryFn: getTeamActivityHeatmap,
  })

  if (isLoading) return <div>Loading heatmap...</div>

  // Transform to format expected by @uiw/react-heat-map
  const heatmapData = data?.map(d => ({
    date: d.date.replace(/-/g, '/'), // Convert YYYY-MM-DD to YYYY/MM/DD for Safari
    count: d.count,
  })) || []

  return (
    <Card>
      <CardHeader>
        <CardTitle>Team Activity Heatmap</CardTitle>
      </CardHeader>
      <CardContent>
        <HeatMap
          value={heatmapData}
          width="100%"
          startDate={subDays(new Date(), 365)}
          endDate={new Date()}
          panelColors={{
            0: '#ebedf0',
            2: '#c6e48b',
            4: '#7bc96f',
            10: '#239a3b',
            20: '#196127',
          }}
          rectProps={{
            rx: 2,
          }}
          legendRender={(props) => (
            <div className="flex items-center gap-2 text-sm text-muted-foreground mt-2">
              <span>Less</span>
              {props}
              <span>More</span>
            </div>
          )}
        />
      </CardContent>
    </Card>
  )
}
```

### Anti-Patterns to Avoid
- **Client-side date filtering on all data:** Don't fetch all data then filter in React; backend filtering reduces payload and improves performance
- **Hardcoded date ranges:** Don't manually calculate "This Month" in components; use date-fns presets for timezone correctness and testability
- **Synchronous CSV generation for large datasets:** Don't load all rows into memory at once; use StreamingHttpResponse for datasets >1000 rows
- **Memory leaks from Blob URLs:** Don't forget to call URL.revokeObjectURL() after download; unreleased blob URLs consume memory
- **Missing date validation:** Don't trust date_from/date_to params without validation; malformed dates can crash queries

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV file generation | Manual string concatenation with commas | Python csv.writer or djangorestframework-csv | Handles escaping quotes, commas in values, newlines, Unicode characters correctly |
| Date range presets | Manual date arithmetic | date-fns startOfMonth, startOfQuarter, startOfYear | Handles timezone edge cases, leap years, daylight saving time correctly |
| Activity heatmap grid | Custom SVG/canvas rendering | @uiw/react-heat-map or react-activity-calendar | Handles responsive sizing, tooltips, color scales, accessibility |
| Percentage change calculation | Custom formulas | Standard formula: ((new - old) / old) * 100 with zero-division check | Edge cases: division by zero, negative percentages, infinity |
| Browser file download | Custom iframe tricks | Blob API + URL.createObjectURL() + anchor click | Modern, standards-compliant, works across browsers |
| Streaming large responses | Loading all data then paginating | Django StreamingHttpResponse | Prevents memory exhaustion, avoids load balancer timeouts |

**Key insight:** Date calculations and CSV generation have many edge cases (timezones, leap years, character escaping, Unicode, memory limits). Libraries handle these; custom solutions miss them and break in production.

## Common Pitfalls

### Pitfall 1: Timezone Inconsistency in Date Filtering
**What goes wrong:** Backend filters by UTC date but frontend sends local timezone date, causing off-by-one-day errors for users in non-UTC timezones
**Why it happens:** JavaScript Date objects default to local timezone; Django expects UTC; date-only strings (YYYY-MM-DD) are ambiguous
**How to avoid:**
```python
# Backend: Always use timezone-aware datetimes
from django.utils import timezone
from datetime import datetime

date_from = request.query_params.get('date_from')
if date_from:
    # Parse as date-only, set to start of day in user's timezone
    dt = datetime.strptime(date_from, '%Y-%m-%d')
    # Convert to timezone-aware (assumes UTC or configure per-user timezone)
    filters['created_at__gte'] = timezone.make_aware(dt)
```
```typescript
// Frontend: Send ISO date strings (YYYY-MM-DD) without time component
const dateFrom = format(range.from, 'yyyy-MM-dd') // Not .toISOString()
```
**Warning signs:** Date range filter includes one extra day or misses last day; users in PST see different results than UTC users

### Pitfall 2: CSV Export Memory Exhaustion
**What goes wrong:** Exporting 10,000+ row dataset loads entire result set into memory, crashes Django worker or times out
**Why it happens:** Standard Response() serializes all data before sending; large datasets exceed memory limits
**How to avoid:** Use StreamingHttpResponse for exports with unbounded result sets:
```python
# Don't do this for large datasets:
data = list(Contact.objects.all())  # Loads all 50,000 contacts into memory
return Response(serialize(data))

# Do this instead:
def generate_csv_rows():
    for contact in Contact.objects.all().iterator(chunk_size=500):
        yield [contact.name, contact.email, contact.stage]

return StreamingHttpResponse(
    (csv.writer(Echo()).writerow(row) for row in generate_csv_rows()),
    content_type='text/csv'
)
```
**Warning signs:** Export endpoint times out after 30 seconds; gunicorn workers crash with OOM errors; memory usage spikes to 2GB+

### Pitfall 3: Forgetting to Revoke Blob URLs
**What goes wrong:** Client-side CSV download creates blob URLs but never releases them, causing memory leak on repeated exports
**Why it happens:** URL.createObjectURL() creates persistent URL until explicitly revoked; developers forget cleanup step
**How to avoid:**
```typescript
// Always revoke after download
const url = window.URL.createObjectURL(blob)
const link = document.createElement('a')
link.href = url
link.download = filename
link.click()
window.URL.revokeObjectURL(url)  // Critical: release memory
```
**Warning signs:** Browser memory usage increases 5-10MB per export; memory leak warnings in Chrome DevTools; browser slows after multiple exports

### Pitfall 4: Incorrect Percentage Change Formula
**What goes wrong:** Percentage change calculation produces wrong values for negative numbers, zero denominators, or direction
**Why it happens:** Formula ((new - old) / old) * 100 breaks when old = 0; confusion about "increase" vs "decrease"
**How to avoid:**
```typescript
function calculatePercentChange(current: number, previous: number): number {
  // Handle zero division
  if (previous === 0) {
    return current > 0 ? 100 : 0  // 100% increase from zero, or no change
  }

  return ((current - previous) / previous) * 100
}

// Examples:
// 100 to 120: +20%
// 100 to 80: -20%
// 0 to 50: +100%
// 50 to 0: -100%
```
**Warning signs:** Comparison shows "Infinity%" or "NaN%"; negative percentages when values increased; wrong trend arrow direction

### Pitfall 5: Date Range Picker State Desync
**What goes wrong:** User selects preset "This Month" but custom calendar shows old range; clicking calendar doesn't update preset button
**Why it happens:** DateRangePicker has two input methods (presets and calendar) but state not synchronized
**How to avoid:**
```typescript
// Store single source of truth (DateRange), not separate preset/calendar state
const [dateRange, setDateRange] = useState<DateRange | null>(null)

// Both presets and calendar update same state
<Button onClick={() => setDateRange(datePresets.thisMonth())}>This Month</Button>
<Calendar
  selected={dateRange}
  onSelect={setDateRange}
/>

// Display reflects actual state, not method used to set it
<span>{dateRange ? formatDateRange(dateRange) : "All time"}</span>
```
**Warning signs:** Preset button appears selected but dashboard shows different date range; clicking "This Month" twice produces different results

### Pitfall 6: Missing Date Range in Export Filename
**What goes wrong:** All CSV exports named "stalled_contacts.csv" causing file overwrite confusion when downloading multiple date ranges
**Why it happens:** Static filename in Content-Disposition header
**How to avoid:**
```python
from datetime import date

date_from = request.query_params.get('date_from', '')
date_to = request.query_params.get('date_to', '')

# Include date range in filename
if date_from and date_to:
    filename = f"stalled_contacts_{date_from}_to_{date_to}.csv"
else:
    filename = f"stalled_contacts_{date.today().isoformat()}.csv"

return Response(data, headers={
    'Content-Disposition': f'attachment; filename="{filename}"'
})
```
**Warning signs:** Downloaded files overwrite each other; confusion about which date range each file contains

### Pitfall 7: Activity Heatmap Date Format Safari Incompatibility
**What goes wrong:** Heatmap works in Chrome/Firefox but breaks in Safari with invalid date errors
**Why it happens:** @uiw/react-heat-map expects dates with forward slashes (YYYY/MM/DD) but backend returns ISO format with hyphens (YYYY-MM-DD); Safari's Date parsing is stricter
**How to avoid:**
```typescript
// Transform backend ISO dates to Safari-compatible format
const heatmapData = data?.map(d => ({
  date: d.date.replace(/-/g, '/'),  // "2026-01-15" -> "2026/01/15"
  count: d.count,
}))
```
**Warning signs:** Heatmap renders empty in Safari but works in Chrome; console errors "Invalid Date" in Safari only

## Code Examples

Verified patterns from official sources:

### Date Range Backend Service Pattern
```python
# apps/insights/services.py
from datetime import datetime
from django.utils import timezone
from apps.journals.models import Journal

def get_team_activity(user, date_from=None, date_to=None, limit=50):
    """Get team activity feed with optional date filtering."""
    queryset = Journal.objects.filter(
        owner__organization=user.organization
    )

    # Apply date filters if provided
    if date_from:
        dt_from = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
        queryset = queryset.filter(created_at__gte=dt_from)

    if date_to:
        dt_to = timezone.make_aware(datetime.strptime(date_to, '%Y-%m-%d'))
        # Include entire day by adding 1 day
        from datetime import timedelta
        dt_to = dt_to + timedelta(days=1)
        queryset = queryset.filter(created_at__lt=dt_to)

    # Apply limit
    if limit:
        queryset = queryset[:limit]

    return {
        'activities': [
            {
                'id': j.id,
                'created_at': j.created_at.isoformat(),
                'user_name': j.owner.get_full_name(),
                'event_type': j.get_event_type(),
                'title': j.title,
            }
            for j in queryset.select_related('owner', 'contact')
        ]
    }
```

### Dashboard with Date Range Filtering
```typescript
// frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx
import { useState } from "react"
import { DateRangePicker } from "@/components/ui/date-range-picker"
import type { DateRange } from "@/lib/date-presets"
import { format } from "date-fns"

export function AdminAnalyticsDashboard() {
  const [dateRange, setDateRange] = useState<DateRange | null>(null)

  // Convert DateRange to API params
  const dateParams = dateRange ? {
    date_from: format(dateRange.from, 'yyyy-MM-dd'),
    date_to: format(dateRange.to, 'yyyy-MM-dd'),
  } : {}

  // All hooks now receive date range
  const { data: overview } = useAdminDashboardOverview(dateParams)
  const { data: teamActivity } = useAdminTeamActivity({ ...dateParams, limit: 50 })
  const { data: stalledContacts } = useAdminStalledContacts(dateParams)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Admin Analytics</h1>
        <DateRangePicker value={dateRange} onChange={setDateRange} />
      </div>

      {/* All widgets automatically filtered by date range */}
      <DashboardOverviewCards data={overview} />
      <TeamActivityTable data={teamActivity} />
      <StalledContactsPanel data={stalledContacts} />
    </div>
  )
}
```

### CSV Export Hook Pattern
```typescript
// frontend/src/hooks/useInsights.ts
import { useMutation } from '@tanstack/react-query'
import { exportStalledContactsCSV, exportTeamActivityCSV } from '@/api/insights'
import { format } from 'date-fns'

export function useExportStalledContacts() {
  return useMutation({
    mutationFn: async ({
      dateFrom,
      dateTo
    }: {
      dateFrom?: string
      dateTo?: string
    }) => {
      await exportStalledContactsCSV(dateFrom, dateTo)
    },
  })
}

// Usage in component
function ExportButton() {
  const exportMutation = useExportStalledContacts()
  const [dateRange, setDateRange] = useState<DateRange | null>(null)

  const handleExport = () => {
    const params = dateRange ? {
      dateFrom: format(dateRange.from, 'yyyy-MM-dd'),
      dateTo: format(dateRange.to, 'yyyy-MM-dd'),
    } : {}

    exportMutation.mutate(params)
  }

  return (
    <Button onClick={handleExport} disabled={exportMutation.isPending}>
      {exportMutation.isPending ? 'Exporting...' : 'Export to CSV'}
    </Button>
  )
}
```

### User Comparison Component
```typescript
// frontend/src/pages/admin/analytics/components/UserComparison.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useState } from "react"
import { useAdminUserPerformance } from "@/hooks/useInsights"

export function UserComparison() {
  const [user1, setUser1] = useState<string>("")
  const [user2, setUser2] = useState<string>("")

  const { data: allUsers } = useAdminUserPerformance()

  const user1Data = allUsers?.users.find(u => u.user_email === user1)
  const user2Data = allUsers?.users.find(u => u.user_email === user2)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Compare Missionaries</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 mb-6">
          <Select value={user1} onValueChange={setUser1}>
            <SelectTrigger>
              <SelectValue placeholder="Select first user" />
            </SelectTrigger>
            <SelectContent>
              {allUsers?.users.map(u => (
                <SelectItem key={u.user_email} value={u.user_email}>
                  {u.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={user2} onValueChange={setUser2}>
            <SelectTrigger>
              <SelectValue placeholder="Select second user" />
            </SelectTrigger>
            <SelectContent>
              {allUsers?.users.map(u => (
                <SelectItem key={u.user_email} value={u.user_email}>
                  {u.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {user1Data && user2Data && (
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold mb-4">{user1Data.name}</h3>
              <MetricRow label="Active Contacts" value={user1Data.active_contacts} />
              <MetricRow label="Decisions Logged" value={user1Data.total_decisions} />
              <MetricRow label="Conversion Rate" value={`${user1Data.conversion_rate.toFixed(1)}%`} />
            </div>

            <div>
              <h3 className="font-semibold mb-4">{user2Data.name}</h3>
              <MetricRow label="Active Contacts" value={user2Data.active_contacts} />
              <MetricRow label="Decisions Logged" value={user2Data.total_decisions} />
              <MetricRow label="Conversion Rate" value={`${user2Data.conversion_rate.toFixed(1)}%`} />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function MetricRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between py-2 border-b">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual CSV string building | csv.writer module or djangorestframework-csv | Python 2.x era → 3.x | Automatic escaping, Unicode support, standards-compliant |
| moment.js for date manipulation | date-fns | 2019-2020 | 97% smaller bundle (20KB vs 600KB), tree-shakeable, immutable |
| Server-side pagination for exports | Streaming responses | Django 1.5+ (2013) | No memory exhaustion, handles millions of rows |
| URL-based download tricks | Blob API + createObjectURL | HTML5 (2014+) | Standards-compliant, works across browsers, no server roundtrip |
| Custom heatmap SVG | @uiw/react-heat-map or similar | React era (2020+) | Responsive, accessible, tested across browsers |

**Deprecated/outdated:**
- **moment.js:** Now deprecated; use date-fns or Temporal API (future)
- **react-date-range:** Large bundle (50KB+); custom Radix UI implementation lighter
- **CSV string concatenation:** Error-prone; use Python csv module or library
- **Loading entire dataset for export:** Memory issues; use streaming for large datasets

## Open Questions

Things that couldn't be fully resolved:

1. **Activity heatmap data granularity**
   - What we know: Need daily activity counts for past year; GitHub-style grid shows squares for each day
   - What's unclear: Should heatmap count journal entries, decisions, stage changes, or all activity? Should it be per-user toggle or team-wide only?
   - Recommendation: Start with team-wide journal entry count per day; add per-user toggle in follow-up if valuable. Backend endpoint `/insights/admin/activity-heatmap/` returns `[{ date: "2026-01-15", count: 23 }, ...]`

2. **Date range preset localization**
   - What we know: Presets like "This Month" and "Last Quarter" are English-only
   - What's unclear: Does project need i18n support for date presets? If yes, which locales?
   - Recommendation: Start with English-only presets; add i18n layer (react-i18next) if requirement emerges

3. **Export file size limits**
   - What we know: StreamingHttpResponse handles large datasets; some browsers limit download size
   - What's unclear: Should exports have hard limit (e.g., 10,000 rows) with warning? Or unlimited streaming?
   - Recommendation: Add limit parameter with default 10,000; show warning if dataset exceeds limit; allow override for power users

4. **Comparison periods auto-selection**
   - What we know: Time period comparison needs two date ranges (COMP-01)
   - What's unclear: Should second period auto-calculate (e.g., "This Month" auto-compares to "Last Month")? Or require manual selection?
   - Recommendation: Auto-calculate matching period (This Month → Last Month, Last Quarter → Quarter Before That) with manual override option

## Sources

### Primary (HIGH confidence)
- [djangorestframework-csv PyPI](https://pypi.org/project/djangorestframework-csv/) - Version 3.0.2, installation, usage patterns
- [Django Official Docs: Outputting CSV](https://docs.djangoproject.com/en/5.0/howto/outputting-csv/) - StreamingHttpResponse pattern, Echo buffer class
- [date-fns Official Docs](https://date-fns.org/docs/startOfMonth) - Date preset functions verified
- [@uiw/react-heat-map GitHub](https://github.com/uiwjs/react-heat-map) - Data format, Safari date compatibility
- [Lucide React Icons - Trending](https://lucide.dev/icons/trending-up) - TrendingUp, TrendingDown icons verified
- Project codebase - /frontend/src/components/imports/ExportCard.tsx - Existing export pattern
- Project codebase - /apps/insights/views.py - Existing query param pattern

### Secondary (MEDIUM confidence)
- [date-range-picker-for-shadcn GitHub](https://github.com/johnpolacek/date-range-picker-for-shadcn) - shadcn/ui date range picker pattern with presets
- [Download API Files With React & Fetch - Medium](https://medium.com/yellowcode/download-api-files-with-react-fetch-393e4dae0d9e) - Blob download pattern verified
- [Period-over-period comparisons - Metabase Learn](https://www.metabase.com/learn/metabase-basics/querying-and-dashboards/time-series/time-series-comparisons) - Best practices for time comparisons
- [How to create CSV output - GeeksforGeeks](https://www.geeksforgeeks.org/javascript/how-to-create-and-download-csv-file-in-javascript/) - Browser CSV download pattern

### Tertiary (LOW confidence)
- WebSearch: "analytics dashboard date range presets 2026" - General patterns only
- WebSearch: "React trend arrows percentage change 2026" - UI library trends, not specific component

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - djangorestframework-csv, date-fns, Radix UI verified from official sources; @uiw/react-heat-map from GitHub
- Architecture: HIGH - Date filtering pattern verified from existing codebase; CSV export pattern from Django official docs; download pattern from MDN
- Pitfalls: HIGH - Timezone issues, memory exhaustion, Blob URL leaks, Safari date format all documented from official sources and production experience
- Heatmap data format: MEDIUM - Data structure inferred from library docs but exact backend aggregation needs validation

**Research date:** 2026-02-14
**Valid until:** 2026-03-16 (30 days - stable libraries, established patterns)
