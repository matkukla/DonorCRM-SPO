# Phase 6: Reporting & Integration - Research

**Researched:** 2026-01-24
**Domain:** React data visualization and Django query optimization
**Confidence:** HIGH

## Summary

Phase 6 implements analytics reports with charting, contact-journal integration, and task system extension. The standard approach uses shadcn/ui's Chart components (built on Recharts v2) for data visualization, Django ORM aggregation for analytics queries, and TanStack Query for data fetching and caching. The existing codebase already has shadcn/ui components (Tabs, Card, Badge) and TanStack Query patterns established, making integration straightforward.

The critical technical challenges are: (1) preventing N+1 queries in report endpoints using select_related/prefetch_related, (2) implementing performant aggregation queries for cross-missionary analytics, and (3) extending the Task model with an optional journal_id foreign key following Django best practices.

**Primary recommendation:** Use shadcn/ui Chart components with Recharts for all visualizations, implement Django aggregation in ViewSet get_queryset() methods with proper eager loading, and verify query performance with django-debug-toolbar before UAT.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Recharts | 2.x (stable) | React charting library | De facto standard for React charts, D3-powered, declarative API, shadcn/ui uses it |
| shadcn/ui Chart | Latest | Chart component wrapper | Composable Chart components with Radix primitives, matches existing UI library |
| Django ORM | 5.0+ | Database aggregation | Native aggregation functions (Count, Sum, Avg) with efficient SQL generation |
| TanStack Query | ^5.90.17 | Data fetching | Already in codebase, handles caching and background updates for chart data |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-debug-toolbar | Latest | N+1 detection | Development only - verify no duplicate queries in report endpoints |
| @radix-ui/react-tabs | ^1.1.13 | Tab primitives | Already installed - for Contact detail Journals tab |
| date-fns | ^4.1.0 | Date formatting | Already in codebase - for chart axis labels and aggregation grouping |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Recharts | TanStack React Charts | TanStack has cleaner API but immature ecosystem, Recharts has more examples/support |
| Recharts | Chart.js | Chart.js is canvas-based (not SVG), harder to customize, not composable with React |
| Django ORM | django-rest-framework-aggregates | DRF package adds complexity, native ORM aggregation is more maintainable |

**Installation:**
```bash
# Frontend (shadcn/ui CLI adds Recharts automatically)
pnpm dlx shadcn@latest add chart

# Backend (debug toolbar for development)
pip install django-debug-toolbar
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── pages/
│   ├── journals/
│   │   └── components/
│   │       └── ReportCharts.tsx       # Chart components for Report tab
│   └── contacts/
│       └── ContactDetail.tsx          # Add Journals tab here
├── components/ui/
│   ├── chart.tsx                      # shadcn/ui chart primitives (auto-added)
│   └── tabs.tsx                       # Already exists
└── hooks/
    └── useJournals.ts                 # Add analytics query hooks

backend/apps/
├── journals/
│   ├── views.py                       # Add analytics ViewSets
│   └── serializers.py                 # Analytics serializers
└── tasks/
    └── models.py                      # Add journal ForeignKey
```

### Pattern 1: shadcn/ui Chart with Recharts
**What:** shadcn/ui provides ChartContainer wrapper with ChartConfig for theming, wrapping native Recharts components
**When to use:** All chart rendering (bar, area, pie charts)
**Example:**
```typescript
// Source: https://ui.shadcn.com/docs/components/chart (verified)
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts"
import { ChartContainer, ChartConfig } from "@/components/ui/chart"

const chartConfig = {
  decisions: {
    label: "Decisions",
    color: "hsl(var(--chart-1))",
  },
} satisfies ChartConfig

export function DecisionTrendsChart({ data }: { data: Array<{month: string, count: number}> }) {
  return (
    <ChartContainer config={chartConfig} className="min-h-[300px] w-full">
      <BarChart data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="month" />
        <YAxis />
        <Bar dataKey="count" fill="var(--color-decisions)" />
      </BarChart>
    </ChartContainer>
  )
}
```

**Key requirements:**
- Set `min-h-[VALUE]` on ChartContainer for responsive behavior
- Use `var(--color-KEY)` pattern to reference chartConfig colors
- ChartConfig defines labels and CSS variable colors

### Pattern 2: Django Aggregation in ViewSets
**What:** Use Django ORM aggregate() and annotate() in get_queryset() to prevent N+1 queries
**When to use:** Analytics endpoints that compute totals, averages, counts
**Example:**
```python
# Source: https://docs.djangoproject.com/en/6.0/topics/db/aggregation/ (verified)
from django.db.models import Count, Sum, Avg, Q
from rest_framework import viewsets

class JournalAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        # Aggregate across user's journals
        return Journal.objects.filter(
            owner=self.request.user
        ).aggregate(
            total_journals=Count('id'),
            total_decisions=Count('journal_contacts__decisions', distinct=True),
            avg_stage_completion=Avg('journal_contacts__stage_events__count')
        )

    def list(self, request):
        # For decision trends (time-series)
        decisions_by_month = Decision.objects.filter(
            journal_contact__journal__owner=request.user
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        # Returns: [{'month': '2025-01-01', 'count': 5}, ...]
```

**Critical notes:**
- Use `distinct=True` with Count when joining across relationships
- Filter BEFORE annotate to constrain what's counted
- Filter AFTER annotate to filter results based on aggregated values
- Use `default=0` for Sum/Avg to avoid None values

### Pattern 3: Optimized List Queries with select_related/prefetch_related
**What:** Eager load relationships in get_queryset() to prevent N+1 queries
**When to use:** Any list endpoint that accesses related models in serializer
**Example:**
```python
# Source: https://www.django-rest-framework.org/api-guide/generic-views/ (verified)
class JournalContactViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # For Contact detail Journals tab
        return JournalContact.objects.filter(
            contact_id=self.kwargs['contact_id']
        ).select_related(
            'journal',  # ForeignKey - use select_related
        ).prefetch_related(
            'decisions',  # Reverse FK - use prefetch_related
            'stage_events'  # Reverse FK
        )
```

**Rule of thumb:**
- `select_related()` for ForeignKey and OneToOneField (SQL JOIN)
- `prefetch_related()` for reverse FK and ManyToMany (separate query)
- Combine both when serializer spans multiple relationship types

### Pattern 4: TanStack Query for Chart Data
**What:** Use useQuery with specific query keys for chart data fetching and caching
**When to use:** Fetching analytics data from backend for charts
**Example:**
```typescript
// Follows existing codebase pattern from useContacts.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'

export function useDecisionTrends(journalId?: string) {
  return useQuery({
    queryKey: ['journals', 'analytics', 'decisions', journalId],
    queryFn: async () => {
      const params = journalId ? { journal_id: journalId } : {}
      const response = await api.get('/api/journals/analytics/decision-trends/', { params })
      return response.data
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - analytics can be slightly stale
  })
}
```

**Key patterns:**
- Query keys: `['journals', 'analytics', <metric>, ...filters]`
- Set `staleTime` for analytics (data doesn't change every second)
- Use `refetchOnWindowFocus: false` for expensive aggregations

### Pattern 5: Adding Journals Tab to Contact Detail
**What:** Extend existing Tabs component with new TabsTrigger and TabsContent
**When to use:** Adding Journals tab to Contact detail page
**Example:**
```typescript
// Source: https://ui.shadcn.com/docs/components/tabs (verified)
// In ContactDetail.tsx (already has Tabs for Overview, Donations, Pledges, Tasks)
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="donations">Donations ({donations?.length || 0})</TabsTrigger>
    <TabsTrigger value="pledges">Pledges ({pledges?.length || 0})</TabsTrigger>
    <TabsTrigger value="tasks">Tasks ({tasks?.length || 0})</TabsTrigger>
    <TabsTrigger value="journals">Journals ({journals?.length || 0})</TabsTrigger>
  </TabsList>

  {/* Existing tabs... */}

  <TabsContent value="journals" className="mt-6">
    <Card>
      <CardHeader>
        <CardTitle>Journal Memberships</CardTitle>
        <CardDescription>
          Journals this contact is currently enrolled in
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* List of journals with stage and decision */}
      </CardContent>
    </Card>
  </TabsContent>
</Tabs>
```

**Integration notes:**
- Tabs component already imported and used in ContactDetail.tsx
- Follow existing pattern: TabsTrigger shows count, TabsContent wraps Card
- Use existing Badge component to show stage/decision status

### Pattern 6: Optional ForeignKey for Task.journal_id
**What:** Add nullable ForeignKey to Task model following Django best practices
**When to use:** Extending Task model to link tasks to journals
**Example:**
```python
# Source: https://docs.djangoproject.com/en/5.1/ref/models/fields/ (verified)
from django.db import models

class Task(TimeStampedModel):
    # Existing fields...
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks'
    )

    # NEW: Optional journal link
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
        help_text='Optional journal this task belongs to'
    )
```

**Key requirements:**
- `null=True` - allows NULL in database
- `blank=True` - allows empty in forms/serializers
- `on_delete=models.CASCADE` - delete tasks when journal deleted (or use SET_NULL if tasks should persist)
- Add to existing indexes if filtering by journal_id

### Anti-Patterns to Avoid
- **Don't use aggregate() for per-object data:** aggregate() returns a single dict, use annotate() for per-object aggregations
- **Don't filter after aggregate():** aggregate() is terminal, filter BEFORE aggregating or use annotate() then filter
- **Don't skip ChartContainer:** Recharts charts need ChartContainer wrapper for responsive sizing
- **Don't hand-roll chart legends:** Use ChartLegend component from shadcn/ui
- **Don't fetch chart data on every render:** Use TanStack Query with staleTime to cache

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart rendering | Custom SVG/canvas charting | Recharts + shadcn/ui Chart | Recharts handles responsive sizing, tooltips, legends, accessibility, animations - custom solution would be 1000+ LOC |
| N+1 query detection | Manual SQL logging | django-debug-toolbar | Toolbar automatically highlights duplicate queries, shows SQL panel with query count and timing |
| Date grouping in SQL | Manual date parsing | Django's Trunc functions (TruncMonth, TruncDay) | Trunc functions generate correct SQL for date truncation across databases |
| Chart color theming | Hardcoded colors | CSS variables via ChartConfig | shadcn/ui uses CSS variables for dark mode support and consistent theming |
| Query caching | Manual cache invalidation | TanStack Query | Query handles stale-while-revalidate, background refetching, cache invalidation automatically |

**Key insight:** Data visualization and query optimization are solved problems in the React/Django ecosystem. The value is in composing existing tools correctly, not building from scratch.

## Common Pitfalls

### Pitfall 1: N+1 Queries in List Endpoints
**What goes wrong:** Serializer accesses related objects (journal.owner_name, decisions.amount) triggering 1 query per item
**Why it happens:** Django lazy-loads relationships - each access is a separate query
**How to avoid:**
- Always override `get_queryset()` with select_related/prefetch_related
- Use django-debug-toolbar to verify query count BEFORE UAT
- Rule: For N items, should see ~1-3 queries max (not N+1)
**Warning signs:**
- "100 similar queries" in debug toolbar SQL panel
- API response time increases linearly with result count

### Pitfall 2: Incorrect Count() with Multiple Relationships
**What goes wrong:** `Count('authors') + Count('stores')` returns inflated counts due to SQL JOINs
**Why it happens:** Joining two many-to-many tables creates cartesian product
**How to avoid:** Use `distinct=True` parameter: `Count('authors', distinct=True)`
**Warning signs:** Count values seem 2x-10x higher than expected

### Pitfall 3: aggregate() vs annotate() Confusion
**What goes wrong:** Using aggregate() expecting per-object results, getting single dict instead
**Why it happens:** aggregate() is terminal clause, returns one summary value
**How to avoid:**
- Use aggregate() for single summary (e.g., total across all journals)
- Use annotate() for per-object summaries (e.g., total per journal)
**Warning signs:** QuerySet doesn't support further filtering after aggregate()

### Pitfall 4: Missing ChartContainer min-height
**What goes wrong:** Chart renders at 0px height, appears broken
**Why it happens:** Recharts needs explicit height, ChartContainer requires min-h class
**How to avoid:** Always set `className="min-h-[300px]"` or similar on ChartContainer
**Warning signs:** Chart works in examples but disappears when integrated

### Pitfall 5: Over-fetching in Analytics Queries
**What goes wrong:** Analytics endpoint returns all journal data instead of aggregated summary
**Why it happens:** Serializing full objects instead of aggregate dict
**How to avoid:**
- Use `.values()` and `.annotate()` to return specific fields
- Create custom serializer for analytics (not ModelSerializer)
**Warning signs:** API response is megabytes for simple chart data

### Pitfall 6: Stale Chart Data
**What goes wrong:** User updates decision, chart doesn't update until page reload
**Why it happens:** TanStack Query caches data, mutations don't invalidate chart queries
**How to avoid:**
- Invalidate analytics queries in mutation onSuccess: `queryClient.invalidateQueries({ queryKey: ['journals', 'analytics'] })`
- Set appropriate staleTime (5-10 minutes for analytics)
**Warning signs:** User reports "chart shows old numbers"

## Code Examples

Verified patterns from official sources:

### Bar Chart for Decision Trends
```typescript
// Source: https://ui.shadcn.com/docs/components/chart
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { ChartContainer, ChartConfig, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"

const chartConfig = {
  count: {
    label: "Decisions",
    color: "hsl(var(--chart-1))",
  },
} satisfies ChartConfig

interface DecisionTrendsProps {
  data: Array<{ month: string; count: number }>
}

export function DecisionTrendsChart({ data }: DecisionTrendsProps) {
  return (
    <ChartContainer config={chartConfig} className="min-h-[300px] w-full">
      <BarChart data={data}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="month"
          tickLine={false}
          tickMargin={10}
          axisLine={false}
        />
        <YAxis />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Bar dataKey="count" fill="var(--color-count)" radius={4} />
      </BarChart>
    </ChartContainer>
  )
}
```

### Area Chart for Stage Activity
```typescript
// Source: https://ui.shadcn.com/charts/area
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { ChartContainer, ChartConfig, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"

const chartConfig = {
  contact: { label: "Contact", color: "hsl(var(--chart-1))" },
  meet: { label: "Meet", color: "hsl(var(--chart-2))" },
  close: { label: "Close", color: "hsl(var(--chart-3))" },
  decision: { label: "Decision", color: "hsl(var(--chart-4))" },
} satisfies ChartConfig

export function StageActivityChart({ data }: { data: Array<{date: string, contact: number, meet: number, close: number, decision: number}> }) {
  return (
    <ChartContainer config={chartConfig} className="min-h-[300px] w-full">
      <AreaChart data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="date" />
        <YAxis />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Area dataKey="contact" fill="var(--color-contact)" stroke="var(--color-contact)" stackId="1" />
        <Area dataKey="meet" fill="var(--color-meet)" stroke="var(--color-meet)" stackId="1" />
        <Area dataKey="close" fill="var(--color-close)" stroke="var(--color-close)" stackId="1" />
        <Area dataKey="decision" fill="var(--color-decision)" stroke="var(--color-decision)" stackId="1" />
      </AreaChart>
    </ChartContainer>
  )
}
```

### Pie Chart for Pipeline Breakdown
```typescript
// Source: Community pattern verified with official Recharts docs
import { Pie, PieChart } from "recharts"
import { ChartContainer, ChartConfig, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"

const chartConfig = {
  contact: { label: "Contact", color: "hsl(var(--chart-1))" },
  meet: { label: "Meet", color: "hsl(var(--chart-2))" },
  close: { label: "Close", color: "hsl(var(--chart-3))" },
  decision: { label: "Decision", color: "hsl(var(--chart-4))" },
  thank: { label: "Thank", color: "hsl(var(--chart-5))" },
  next_steps: { label: "Next Steps", color: "hsl(var(--chart-6))" },
} satisfies ChartConfig

export function PipelineBreakdownChart({ data }: { data: Array<{stage: string, count: number}> }) {
  return (
    <ChartContainer config={chartConfig} className="min-h-[300px] w-full">
      <PieChart>
        <ChartTooltip content={<ChartTooltipContent />} />
        <Pie
          data={data}
          dataKey="count"
          nameKey="stage"
          cx="50%"
          cy="50%"
          outerRadius={100}
          label
        />
      </PieChart>
    </ChartContainer>
  )
}
```

### Django Aggregation for Admin Analytics
```python
# Source: https://docs.djangoproject.com/en/6.0/topics/db/aggregation/
from django.db.models import Count, Sum, Avg, F
from rest_framework.decorators import action
from rest_framework.response import Response

class JournalViewSet(viewsets.ModelViewSet):
    @action(detail=False, methods=['get'], url_path='analytics/summary')
    def analytics_summary(self, request):
        """Cross-missionary aggregation (admin only)."""
        # Total journals by user
        journals_by_user = Journal.objects.values(
            'owner__username'
        ).annotate(
            total_journals=Count('id'),
            total_decisions=Count('journal_contacts__decisions', distinct=True),
            avg_contacts_per_journal=Avg('journal_contacts__count')
        ).order_by('-total_journals')

        return Response({
            'by_user': journals_by_user,
        })

    @action(detail=False, methods=['get'], url_path='analytics/decision-trends')
    def decision_trends(self, request):
        """Decision trends over time (bar chart data)."""
        from django.db.models.functions import TruncMonth

        trends = Decision.objects.filter(
            journal_contact__journal__owner=request.user
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        return Response([
            {
                'month': item['month'].strftime('%Y-%m'),
                'count': item['count']
            }
            for item in trends
        ])
```

### Optimized Query for Contact Journals Tab
```python
# Source: https://www.django-rest-framework.org/api-guide/generic-views/
from rest_framework import viewsets
from rest_framework.decorators import action

class ContactViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=['get'], url_path='journals')
    def journals(self, request, pk=None):
        """List all journals this contact belongs to."""
        journal_memberships = JournalContact.objects.filter(
            contact_id=pk
        ).select_related(
            'journal'  # ForeignKey to Journal
        ).prefetch_related(
            'decisions',  # Reverse FK - Decision.journal_contact
            'stage_events'  # For current stage calculation
        )

        serializer = ContactJournalSerializer(journal_memberships, many=True)
        return Response(serializer.data)
```

### TanStack Query Hook for Analytics
```typescript
// Follows existing pattern from frontend/src/hooks/useContacts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'

export function useDecisionTrends() {
  return useQuery({
    queryKey: ['journals', 'analytics', 'decision-trends'],
    queryFn: async () => {
      const response = await api.get('/api/journals/analytics/decision-trends/')
      return response.data
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useStageActivity() {
  return useQuery({
    queryKey: ['journals', 'analytics', 'stage-activity'],
    queryFn: async () => {
      const response = await api.get('/api/journals/analytics/stage-activity/')
      return response.data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function usePipelineBreakdown() {
  return useQuery({
    queryKey: ['journals', 'analytics', 'pipeline-breakdown'],
    queryFn: async () => {
      const response = await api.get('/api/journals/analytics/pipeline-breakdown/')
      return response.data
    },
    staleTime: 5 * 60 * 1000,
  })
}

// Invalidate analytics on decision mutations
export function useCreateDecision() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: DecisionCreate) => {
      const response = await api.post('/api/decisions/', data)
      return response.data
    },
    onSuccess: () => {
      // Invalidate all analytics queries
      queryClient.invalidateQueries({ queryKey: ['journals', 'analytics'] })
      queryClient.invalidateQueries({ queryKey: ['journals'] })
    },
  })
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Chart.js with canvas | Recharts with SVG | ~2020 | React ecosystem standardized on declarative SVG charts, better composability |
| Custom chart wrappers | shadcn/ui Chart components | 2024-2025 | No vendor lock-in, use native Recharts with minimal wrapper |
| Manual eager loading | select_related/prefetch_related in get_queryset() | Django 1.4+ | DRF best practice since 2015, prevents N+1 by default |
| Raw SQL for analytics | Django ORM aggregation | Django 1.1+ | Aggregate/annotate handles complex queries, cross-database compatible |
| Recharts v1 | Recharts v2 | 2023 | Better TypeScript support, improved performance |

**Deprecated/outdated:**
- Victory Charts: Maintenance mode, community moved to Recharts
- django-chartjs: Server-side chart generation, modern apps use client-side React charts
- Prefetching in serializers: Should happen in ViewSet get_queryset(), not serializer
- Recharts v3: In beta (as of Jan 2026), shadcn/ui still on v2 stable

## Open Questions

Things that couldn't be fully resolved:

1. **Recharts v3 Timeline**
   - What we know: shadcn/ui is working on upgrading to Recharts v3, currently testing
   - What's unclear: Release date for stable v3 support in shadcn/ui
   - Recommendation: Use Recharts v2 (current shadcn/ui default), upgrade path is straightforward when v3 stabilizes

2. **Next Steps Queue Implementation**
   - What we know: Requirement is "upcoming actions across all contacts"
   - What's unclear: Is this journal-specific next steps, or task-based, or both?
   - Recommendation: Aggregate NextStep records with due_date in next 7-30 days, grouped by journal_contact

3. **Admin Analytics Scope**
   - What we know: Cross-missionary aggregation needed (total journals, decision totals, stage averages)
   - What's unclear: Permission model (superuser only? team leaders?)
   - Recommendation: Start with is_staff check, plan permission groups in Phase 7

## Sources

### Primary (HIGH confidence)
- shadcn/ui Chart Component Docs - https://ui.shadcn.com/docs/components/chart - Installation, ChartContainer usage, ChartConfig structure
- shadcn/ui Tabs Component Docs - https://ui.shadcn.com/docs/components/tabs - Tab integration patterns
- Django Aggregation Documentation - https://docs.djangoproject.com/en/6.0/topics/db/aggregation/ - Count/Sum/Avg best practices, annotate vs aggregate, distinct parameter
- Django REST Framework Generic Views - https://www.django-rest-framework.org/api-guide/generic-views/ - get_queryset() optimization, select_related/prefetch_related patterns
- Django Model Field Reference - https://docs.djangoproject.com/en/5.1/ref/models/fields/ - ForeignKey null/blank best practices

### Secondary (MEDIUM confidence)
- [8 Best React Chart Libraries for Visualizing Data in 2025](https://embeddable.com/blog/react-chart-libraries) - Recharts ecosystem position
- [TanStack in 2026: From Query to Full-Stack](https://www.codewithseb.com/blog/tanstack-ecosystem-complete-guide-2026) - TanStack Query patterns for chart data
- [Optimizing Django REST Framework - fix the n+1 problem](https://ahmadsalah.hashnode.dev/optimizing-django-rest-framework-fix-the-n1-problem) - DRF N+1 prevention patterns
- [How to Make the Foreign Key Field Optional in Django Model](https://www.geeksforgeeks.org/python/how-to-make-the-foreign-key-field-optional-in-django-model/) - null=True/blank=True patterns
- [Analyzing Django Query Performance with Django Debug Toolbar](https://www.pythontutorials.net/django/analyzing-django-query-performance-with-django-debug-toolbar/) - N+1 detection workflow

### Tertiary (LOW confidence)
- [React Server Components + TanStack Query: The 2026 Data-Fetching Power Duo](https://dev.to/krish_kakadiya_5f0eaf6342/react-server-components-tanstack-query-the-2026-data-fetching-power-duo-you-cant-ignore-21fj) - Modern patterns (but DonorCRM uses SPA not RSC)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Recharts verified via shadcn/ui official docs, Django aggregation verified via Django 6.0 docs
- Architecture: HIGH - All patterns verified with official documentation or existing codebase
- Pitfalls: HIGH - Django N+1 and aggregation gotchas documented in official Django docs

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - stable ecosystem)
