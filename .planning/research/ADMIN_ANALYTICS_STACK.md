# Technology Stack - Admin Analytics Dashboard

**Project:** DonorCRM v1.2 - Admin Analytics Dashboard
**Researched:** 2026-02-12
**Confidence:** HIGH

## Executive Summary

The admin analytics dashboard requires **minimal stack additions** to the existing DonorCRM setup. Most capabilities (Recharts, Radix UI, TanStack Query/Table) are already in place. Key additions are a heatmap calendar library and optionally a drawer component with enhanced UX. Backend leverages native Django ORM aggregation with window functions (no new dependencies required).

## Recommended Stack Additions

### Frontend - NEW Libraries

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `react-activity-calendar` | ^3.0.5 | Activity heatmap calendar | GitHub-style contribution heatmap for user activity visualization. Lightweight (SVG-based), SSR-compatible, actively maintained (last published 19 days ago). React 19 compatible. |
| `vaul` | ^1.1.2 | Enhanced drawer/slide-in panel | Superior mobile UX with drag gestures and snap points. Built on Radix Dialog primitive for accessibility. React 19 compatible (v1.1.1+). More mobile-optimized than existing Sheet component. |

### Frontend - EXISTING Libraries (No Changes)

| Library | Current Version | New Use Cases |
|---------|----------------|---------------|
| `recharts` | ^3.6.0 | **FunnelChart** for conversion funnel, **ComposedChart** for multi-series comparison views, **BarChart/LineChart** for trend charts. All natively supported. |
| `@radix-ui/react-dialog` | ^1.1.15 | Base primitive for Sheet (already used) and Vaul (peer dependency). No upgrade needed. |
| `@tanstack/react-query` | ^5.90.17 | Analytics data fetching/caching. Current version is excellent. |
| `@tanstack/react-table` | ^8.21.3 | Team activity table with sorting/filtering/pagination. Already handles complex tables. |
| `lucide-react` | ^0.562.0 | Icons for trend indicators, summary cards. Existing dependency. |
| `date-fns` | ^4.1.0 | Date formatting for time-based analytics. Already in use. |

### Backend - NO New Dependencies

| Technology | Existing Version | Analytics Use Cases |
|------------|-----------------|---------------------|
| Django ORM | 4.2 | **Trunc functions** (`TruncDay`, `TruncWeek`, `TruncMonth`) for time-series aggregation. **Window functions** (`RowNumber`, `Rank`, `Lag`, `Lead`) for ranking and comparison analytics. Native since Django 2.0+. |
| PostgreSQL | (current) | Window functions (RANK, LAG, LEAD, PARTITION BY) for user comparisons. Date/time functions for period-over-period analysis. Already in use. |
| Django REST Framework | (current) | Aggregation endpoints via standard `APIView` with ORM `.annotate()` and `.aggregate()`. No library needed. |

## Installation

### Frontend Additions Only

```bash
# Required for activity heatmap
npm install react-activity-calendar@^3.0.5

# Optional (recommended) for enhanced slide-in panels
npm install vaul@^1.1.2
```

**Total bundle size impact:** ~25KB gzipped (react-activity-calendar: ~15KB, vaul: ~10KB)

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Heatmap Calendar | react-activity-calendar | react-calendar-heatmap | react-calendar-heatmap last published 1 year ago (stale). react-activity-calendar actively maintained with v3 recently released. |
| Heatmap Calendar | react-activity-calendar | @uiwjs/react-heat-map | More dependencies, larger bundle. react-activity-calendar is simpler and lighter. |
| Slide-in Panel | vaul | Existing Sheet component | Sheet works but lacks mobile gestures (drag to close, snap points). Vaul provides better mobile UX for analytics drilldown. |
| Slide-in Panel | vaul | Build custom with Radix Dialog | Vaul is built on Radix Dialog and is battle-tested (7.4k GitHub stars, used by shadcn/ui). Don't reinvent. |
| Funnel Chart | Recharts FunnelChart | Custom SVG implementation | Recharts FunnelChart is native and supported. No need for custom implementation. |
| Funnel Chart | Recharts FunnelChart | Syncfusion/MUI X | Recharts already in stack. Commercial libraries add cost/complexity. |
| Backend Aggregation | Django ORM native | django-rest-framework-aggregates | DRF aggregates library adds minimal value over native ORM `.annotate()` and `.aggregate()`. Keep it simple. |
| Time Series | Django ORM Trunc | TimescaleDB | TimescaleDB is overkill for 10-20 users with moderate analytics needs. PostgreSQL + Django ORM handles this scale easily. |

## Integration Points with Existing Stack

### Recharts Ecosystem

**Existing pattern (from `ReportCharts.tsx`):**
- Uses `ChartContainer`, `ChartTooltip`, `ChartTooltipContent` wrappers
- `ChartConfig` for theme-aware colors
- BarChart, AreaChart, PieChart already in use

**New chart types to add:**
1. **FunnelChart** for conversion funnel visualization
   - Native Recharts component: `<FunnelChart>` with `<Funnel>`
   - API: https://recharts.github.io/en-US/api/FunnelChart
   - Same pattern as existing BarChart/PieChart

2. **ComposedChart** for comparison views (period vs period, user vs user)
   - Native Recharts component: `<ComposedChart>` with multiple `<Line>`, `<Bar>`, `<Area>` children
   - API: https://recharts.github.io/en-US/api/ComposedChart
   - Allows mixing chart types in single view
   - **Critical:** All data series must be in single data structure (not separate datasets per series)

**Example pattern:**
```typescript
import { FunnelChart, Funnel, ComposedChart, Line, Bar } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"

// Funnel for conversion
<ChartContainer config={funnelConfig}>
  <FunnelChart data={conversionData}>
    <Funnel dataKey="count" />
    <ChartTooltip content={<ChartTooltipContent />} />
  </FunnelChart>
</ChartContainer>

// Composed for comparisons (multiple series)
<ChartContainer config={comparisonConfig}>
  <ComposedChart data={comparisonData}>
    <CartesianGrid />
    <XAxis dataKey="month" />
    <YAxis />
    <Line dataKey="currentPeriod" stroke="var(--color-current)" />
    <Line dataKey="previousPeriod" stroke="var(--color-previous)" />
    <ChartTooltip content={<ChartTooltipContent />} />
  </ComposedChart>
</ChartContainer>
```

### Radix UI Ecosystem

**Existing Sheet component:**
- Located: `frontend/src/components/ui/sheet.tsx`
- Built on `@radix-ui/react-dialog`
- Supports 4 sides: top, bottom, left, right
- Animation via Tailwind classes

**Vaul integration (optional enhancement):**
- Also built on `@radix-ui/react-dialog` (same peer dependency)
- API similar to Sheet but with enhanced mobile UX
- Can coexist with Sheet: use Sheet for simple panels, Vaul for drill-down analytics where mobile UX matters

**Decision point:**
- If mobile experience is important for coaches/leadership → Add Vaul
- If desktop-only or simple panels → Use existing Sheet
- Recommendation: **Add Vaul** - mobile analytics access is valuable for on-the-go leadership

### TanStack Ecosystem

**React Query (existing):**
- All analytics endpoints follow existing pattern
- Example: `useDecisionTrends()`, `useStageActivity()` hooks
- Cache analytics queries with appropriate `staleTime` (e.g., 5-10 minutes for aggregate data)

**React Table (existing):**
- Team activity table reuses `DataTable` component
- Located: `frontend/src/components/shared/DataTable.tsx`
- Sorting, filtering, pagination already implemented

### Backend Data Flow

**Analytics endpoint pattern (no new libraries):**

```python
from django.db.models import Count, F, Window
from django.db.models.functions import TruncDay, TruncWeek, Lag, Rank
from rest_framework.views import APIView

class TeamActivityView(APIView):
    def get(self, request):
        # Time-series aggregation with Trunc
        activity = Contact.objects.annotate(
            day=TruncDay('created_at')
        ).values('day', 'owner__name').annotate(
            count=Count('id')
        ).order_by('day')

        # Window functions for ranking
        ranked_users = Contact.objects.annotate(
            rank=Window(
                expression=Rank(),
                partition_by=[F('owner')],
                order_by=F('created_at').desc()
            )
        )

        return Response(activity)
```

**Key Django ORM capabilities to leverage:**
1. **Trunc functions** (`TruncDay`, `TruncWeek`, `TruncMonth`) - Time-series aggregation
2. **Window functions** (`Window` with `Rank`, `RowNumber`, `Lag`, `Lead`) - User comparisons, period-over-period
3. **Annotate/Aggregate** - Summary statistics for cards

**Sources:**
- [Time-Series Data with Django ORM](https://medium.com/django-unleashed/time-series-data-with-django-orm-monthly-weekly-daily-aggregations-b5ddfa1e194e)
- [Window Functions with Django ORM](https://medium.com/django-unleashed/unpacking-djangos-window-functions-analytics-made-easy-7e4a2ce1f470)
- [Advanced SQL Window Functions in Django](https://bluetickconsultants.medium.com/advanced-sql-part-3-window-functions-with-django-orm-rank-row-number-ntile-first-value-4778ea7616f2)

## What NOT to Add

| Library/Tool | Why Avoid |
|--------------|-----------|
| react-heatmap (generic) | Not calendar-specific. Would need custom calendar layout. react-activity-calendar provides calendar out-of-box. |
| Recharts plugins/extensions | Recharts core has FunnelChart and ComposedChart natively. No plugins needed. |
| Chart.js, Victory, Nivo | Recharts already in stack and handles all use cases. Don't fragment charting libraries. |
| django-rest-framework-aggregates | Adds abstraction layer over native Django ORM. Team already uses ORM directly. Keep patterns consistent. |
| Celery for analytics | 10-20 admin users, moderate query complexity. On-demand queries are fine. Premature optimization. |
| Redis caching layer | React Query + DRF provides sufficient caching. Add if query times exceed 2-3 seconds (unlikely at this scale). |
| TimescaleDB, ClickHouse | Overkill for scale. PostgreSQL handles time-series analytics fine for this user count and data volume. |
| Separate analytics service | Monolithic Django app serves user base well. Microservices add complexity without benefit at this scale. |

## Technology Versions - Verified

**Frontend libraries verified via:**
- vaul: [npm search results](https://www.npmjs.com/package/vaul) - v1.1.2, React 19 support confirmed in v1.1.1+
- react-activity-calendar: [npm search results](https://www.npmjs.com/package/react-activity-calendar) - v3.0.5, last published 19 days ago
- Recharts FunnelChart: [API documentation](https://recharts.github.io/en-US/api/FunnelChart) - Available in Recharts 3.x

**Backend capabilities verified via:**
- Django Window functions: Available since Django 2.0, current project uses Django 4.2
- Django Trunc functions: Native to Django ORM

## Performance Considerations

| Component | Optimization Strategy |
|-----------|----------------------|
| Heatmap Calendar | SVG-based, renders ~365 cells. Performant even on mobile. No virtualization needed. |
| Funnel Chart | Small dataset (6 stages). Recharts handles easily. |
| Team Activity Table | TanStack Table with pagination. Limit to 50 rows per page. Backend pagination if >500 users (unlikely). |
| Analytics Queries | Django ORM with indexes on `created_at`, `owner`, `stage`. Query time <100ms expected. |
| Comparison Charts | ComposedChart handles 2-3 series easily. Avoid >5 concurrent series. |

## Summary Recommendations

**Add to package.json:**
- `react-activity-calendar@^3.0.5` (required for heatmap)
- `vaul@^1.1.2` (recommended for enhanced mobile UX)

**Do NOT add:**
- No backend Python packages
- No additional charting libraries
- No analytics/aggregation libraries

**Leverage existing stack:**
- Recharts for all charts (FunnelChart, ComposedChart, BarChart, LineChart)
- Radix UI for base primitives (Dialog for Sheet/Vaul)
- TanStack Query for data fetching
- TanStack Table for team activity table
- Django ORM for all aggregations (Trunc, Window, Annotate)

**Why this approach:**
1. **Minimal dependencies** - Only 1-2 small libraries needed
2. **Pattern consistency** - Reuses existing component patterns
3. **Bundle size** - <25KB total addition
4. **Performance** - PostgreSQL + Django ORM scales to 10-20 users with millions of records
5. **Maintenance** - Fewer dependencies = less upgrade churn

## Sources

**Frontend Libraries:**
- [Vaul GitHub Repository](https://github.com/emilkowalski/vaul)
- [Vaul npm Package](https://www.npmjs.com/package/vaul)
- [react-activity-calendar GitHub](https://github.com/grubersjoe/react-activity-calendar)
- [react-activity-calendar npm](https://www.npmjs.com/package/react-activity-calendar)
- [Recharts FunnelChart API](https://recharts.github.io/en-US/api/FunnelChart/)
- [Recharts ComposedChart API](https://recharts.github.io/en-US/api/ComposedChart/)
- [Best React Chart Libraries 2026](https://www.syncfusion.com/blogs/post/top-5-react-chart-libraries)
- [Building a Drawer Component (Vaul)](https://emilkowal.ski/ui/building-a-drawer-component)
- [shadcn/ui Drawer (uses Vaul)](https://ui.shadcn.com/docs/components/radix/drawer)

**Backend Django/PostgreSQL:**
- [Time-Series Data with Django ORM](https://medium.com/django-unleashed/time-series-data-with-django-orm-monthly-weekly-daily-aggregations-b5ddfa1e194e)
- [Handling Statistical Data in DRF](https://medium.com/django-unleashed/handling-statistical-data-in-django-rest-framework-for-data-visualization-0b7b0c62a158)
- [Window Functions in Django ORM](https://medium.com/django-unleashed/unpacking-djangos-window-functions-analytics-made-easy-7e4a2ce1f470)
- [Advanced SQL Window Functions with Django](https://bluetickconsultants.medium.com/advanced-sql-part-3-window-functions-with-django-orm-rank-row-number-ntile-first-value-4778ea7616f2)
- [SQL Window Functions in Django](https://sophilabs.com/blog/sql-window-functions-in-django)
- [DRF Aggregates Library](https://github.com/uptick/django-rest-framework-aggregates) (evaluated but not recommended)
