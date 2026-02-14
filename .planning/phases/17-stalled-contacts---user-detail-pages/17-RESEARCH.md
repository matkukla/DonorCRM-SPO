# Phase 17: Stalled Contacts & User Detail Pages - Research

**Researched:** 2026-02-14
**Domain:** React data tables with server-side pagination/sorting, Recharts time series visualization, React Query state management
**Confidence:** HIGH

## Summary

This phase enhances two stub pages created in Phase 15 by adding interactive UI controls (pagination, sorting) and data visualization. The backend endpoints already exist and return properly formatted data - this is a frontend-focused enhancement phase.

The Stalled Contacts page needs server-side pagination controls and sortable column headers. The backend already supports `limit`, `offset`, `sort_by`, and `sort_dir` parameters. The UserDetail page needs new backend endpoints for user-specific trend data and journal listings, plus Recharts visualizations similar to the dashboard trends.

Established patterns from Phases 15-16 provide the foundation: TanStack React Table for sorting, React Query for data fetching with proper cache keys, Recharts for trend charts, and the admin sub-navigation pattern. The project uses @tanstack/react-table 8.21.3, recharts 3.6.0, and @tanstack/react-query 5.90.17.

**Primary recommendation:** Use TanStack React Table with manual server-side pagination/sorting for Stalled Contacts, create dedicated backend endpoints for user-specific metrics (not client-side filtering from aggregate data), and follow the established LineChart pattern from TrendCharts component.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-table | 8.21.3 | Data table management | Project standard for all tables, supports server-side pagination/sorting |
| recharts | 3.6.0 | Chart visualization | Project standard established in Phase 15, used throughout admin analytics |
| @tanstack/react-query | 5.90.17 | Server state management | Project standard for all API data fetching |
| lucide-react | 0.562.0 | Icon library | Project standard for all UI icons |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| date-fns | 4.1.0 | Date formatting | Formatting timestamps in tables and charts |
| react-router-dom | 6.30.3 | Routing and navigation | URL parameter extraction (userId from route) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TanStack React Table | Manual pagination state | Table library provides sorting UI, loading states, type safety |
| Recharts | Chart.js | Project already standardized on Recharts for all visualizations |
| Server-side pagination | Client-side pagination | Backend already handles 1000s of stalled contacts, client-side would be inefficient |

**Installation:**
```bash
# All dependencies already installed in frontend/package.json
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── pages/admin/analytics/
│   ├── StalledContacts.tsx        # Enhanced with pagination/sorting
│   ├── UserDetail.tsx             # Enhanced with charts and journal list
│   └── components/
│       └── (no new components needed, use existing patterns)
├── hooks/
│   └── useInsights.ts             # Add new hooks for user-specific endpoints
└── api/
    └── insights.ts                # Add new API functions and types
```

Backend structure:
```
apps/insights/
├── views.py                       # Add UserTrendsView, UserJournalsView
├── services.py                    # Add get_user_trends(), get_user_journals()
├── serializers.py                 # Add serializers for new endpoints
└── urls.py                        # Add new URL patterns
```

### Pattern 1: Server-Side Pagination with TanStack React Table
**What:** Manual pagination mode where table controls trigger API calls with new offset/limit parameters
**When to use:** Large datasets (50+ items) where server already supports pagination
**Example:**
```typescript
// Source: Existing DataTable.tsx pattern + TanStack docs
const [pageIndex, setPageIndex] = useState(0)
const pageSize = 50

// Query with pagination params
const { data } = useAdminStalledContacts({
  limit: pageSize,
  offset: pageIndex * pageSize,
  sort_by: 'days_stalled',
  sort_dir: 'desc'
})

// Table with manual pagination
const table = useReactTable({
  data: data?.stalled_contacts || [],
  columns,
  manualPagination: true,
  pageCount: Math.ceil((data?.total_count || 0) / pageSize),
})
```

### Pattern 2: Server-Side Sorting with Column Headers
**What:** Sortable column headers that trigger API calls with sort_by/sort_dir parameters
**When to use:** When backend supports sorting and dataset is too large for client-side sorting
**Example:**
```typescript
// Source: TeamActivityTable.tsx (client-side pattern adapted for server-side)
// For server-side sorting, don't use getSortedRowModel()
// Instead, track sort state and pass to API

const [sortBy, setSortBy] = useState('days_stalled')
const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

const { data } = useAdminStalledContacts({
  limit: 50,
  offset: 0,
  sort_by: sortBy,
  sort_dir: sortDir
})

// Column definition with manual sort toggle
columnHelper.accessor("days_stalled", {
  header: ({ column }) => (
    <button
      className="flex items-center gap-2 hover:text-foreground cursor-pointer"
      onClick={() => {
        // Toggle sort direction if same column, else default to desc
        if (sortBy === 'days_stalled') {
          setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
        } else {
          setSortBy('days_stalled')
          setSortDir('desc')
        }
      }}
    >
      Days Stalled
      <ArrowUpDown className="h-4 w-4" />
    </button>
  ),
  // ... cell definition
})
```

### Pattern 3: User-Specific Backend Endpoints
**What:** Dedicated endpoints that filter data by user_id parameter, not client-side filtering
**When to use:** User detail pages that need metrics/lists for one specific user
**Example:**
```python
# Source: Existing admin analytics endpoint patterns
class UserTrendsView(APIView):
    """
    GET: Get trend data for a specific user (donations, decisions, stage progressions)
    Admin-only endpoint.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=['insights'],
        summary='Get user-specific trends (admin only)',
        parameters=[
            OpenApiParameter(name='user_id', description='User ID', type=str, required=True),
            OpenApiParameter(name='weeks', description='Number of weeks (default: 12)', type=int),
        ],
    )
    def get(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=400)
        weeks = get_safe_int_param(request, 'weeks', default=12, min_val=1, max_val=52)
        data = get_user_trends(user_id=user_id, weeks=weeks)
        return Response(data)
```

### Pattern 4: Recharts Time Series for User Trends
**What:** LineChart with weekly data points showing user-specific activity over time
**When to use:** Visualizing individual missionary performance trends
**Example:**
```typescript
// Source: TrendCharts.tsx established pattern
const trendConfig = {
  donations_received: { label: "Donations", color: "hsl(var(--chart-1))" },
  decisions_logged: { label: "Decisions", color: "hsl(var(--chart-2))" },
  stage_progressions: { label: "Stage Changes", color: "hsl(var(--chart-3))" },
} satisfies ChartConfig

<ChartContainer config={trendConfig} className="min-h-[300px] w-full">
  <LineChart data={data.trends}>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="week_label" tickLine={false} axisLine={false} />
    <YAxis tickLine={false} axisLine={false} />
    <ChartTooltip content={<ChartTooltipContent />} />
    <Line
      dataKey="donations_received"
      stroke="var(--color-donations_received)"
      strokeWidth={2}
      dot={{ r: 4 }}
      isAnimationActive={false}
    />
    {/* ... additional lines */}
  </LineChart>
</ChartContainer>
```

### Pattern 5: React Query Keys for User-Specific Data
**What:** Hierarchical query keys that include user_id for proper cache separation
**When to use:** Fetching data scoped to a specific user in admin context
**Example:**
```typescript
// Source: Established pattern from useInsights.ts
export function useAdminUserTrends(userId: string, weeks = 12) {
  return useQuery({
    queryKey: ["insights", "admin", "user-trends", userId, weeks],
    queryFn: () => getAdminUserTrends({ user_id: userId, weeks }),
    staleTime: STALE_TIME,
    enabled: !!userId, // Don't fetch if userId is empty
  })
}
```

### Anti-Patterns to Avoid
- **Client-side filtering from aggregate data:** Don't fetch all user performance data and filter on frontend. Creates new endpoint instead.
- **Mixing client-side and server-side pagination:** Don't use React Table's built-in pagination with server-side data - causes confusion and bugs.
- **Missing enabled guard on queries:** Don't fetch user-specific data when userId is undefined - React Query will retry failed requests.
- **Hardcoded page sizes:** Don't use different pagination sizes across pages - stick to established 50/page default for consistency.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sortable table headers | Custom click handlers and sort icons | TanStack React Table column.toggleSorting() | Handles sort direction toggle, accessibility, type safety |
| Pagination controls | Custom prev/next buttons | Existing DataTable component or pattern | Already handles page bounds, displays "X of Y", loading states |
| Sort direction indicators | Conditional up/down arrows | lucide-react ArrowUpDown icon | Consistent with TeamActivityTable pattern, single icon for both states |
| Time series zero-filling | Manual date iteration | Established zero-fill pattern from Phase 16-01 | Handles edge cases like missing weeks, timezone normalization |
| Chart tooltip formatting | Custom HTML tooltips | ChartTooltip with ChartTooltipContent | Consistent styling, accessibility, responsive |
| React Query cache keys | String or number keys | Hierarchical array keys | Enables partial cache invalidation, better DevTools, type safety |

**Key insight:** The project has already established patterns for all the needed functionality. Don't create new patterns - follow existing TeamActivityTable, TrendCharts, and DataTable patterns.

## Common Pitfalls

### Pitfall 1: Pagination State Reset on Sort Change
**What goes wrong:** User sorts table, pagination resets to page 1 but they expect to stay on current page with new sort order
**Why it happens:** Separate state for page and sort, no coordination between them
**How to avoid:** Always reset pageIndex to 0 when sort changes
**Warning signs:** User complaints about "losing their place" when sorting

```typescript
// Bad
const handleSortChange = (newSortBy: string) => {
  setSortBy(newSortBy)
  // pageIndex stays at current value - wrong page of data
}

// Good
const handleSortChange = (newSortBy: string) => {
  setSortBy(newSortBy)
  setPageIndex(0) // Reset to first page
}
```

### Pitfall 2: Query Key Missing Parameters
**What goes wrong:** User changes sort/pagination but sees stale data from cache
**Why it happens:** React Query cache key doesn't include sort/pagination params
**How to avoid:** Include all query parameters in the query key array
**Warning signs:** Data doesn't update when clicking sort or pagination buttons

```typescript
// Bad - missing sort params in key
const { data } = useQuery({
  queryKey: ["insights", "admin", "stalled-contacts"],
  queryFn: () => getAdminStalledContacts({ sort_by: sortBy })
})

// Good - all params in key
const { data } = useQuery({
  queryKey: ["insights", "admin", "stalled-contacts", { limit, offset, sort_by, sort_dir }],
  queryFn: () => getAdminStalledContacts({ limit, offset, sort_by, sort_dir })
})
```

### Pitfall 3: Client-Side Filtering of Aggregate Data
**What goes wrong:** UserDetail page filters useAdminUserPerformance() by ID, causing unnecessary data transfer and stale metrics
**Why it happens:** Seems easier to reuse existing endpoint than create new one
**How to avoid:** Create dedicated user-specific endpoints that return only needed data
**Warning signs:** Large payload sizes, metrics don't match when viewing individual user

```typescript
// Bad - filtering client-side
const { data: allUsers } = useAdminUserPerformance()
const user = allUsers?.users.find(u => u.id === userId)
// Problem: Fetches all users, trends not available, can't get journal list

// Good - dedicated endpoint
const { data: userDetail } = useAdminUserDetail(userId)
// Returns: user metrics, trends, journal list - all user-specific data
```

### Pitfall 4: Missing Loading States During Page/Sort Changes
**What goes wrong:** Table content flashes or shows stale data while loading new page
**Why it happens:** Not checking isLoading or isFetching during pagination/sort changes
**How to avoid:** Show loading skeleton or disable controls during fetch
**Warning signs:** Brief flash of wrong data, double-clicks because button didn't disable

```typescript
// Check both isLoading (initial) and isFetching (subsequent)
const { data, isLoading, isFetching } = useAdminStalledContacts(params)

// Disable pagination buttons during fetch
<Button
  onClick={() => setPageIndex(p => p + 1)}
  disabled={isFetching || pageIndex >= pageCount - 1}
>
  Next
</Button>
```

### Pitfall 5: Missing Null Checks on URL Parameters
**What goes wrong:** UserDetail page crashes when userId is undefined from URL params
**Why it happens:** useParams() returns string | undefined, not validated
**How to avoid:** Check for undefined before fetching, show error state
**Warning signs:** Console errors about undefined in API calls, React Query retrying failed requests

```typescript
// Bad - no null check
const { id } = useParams<{ id: string }>()
const { data } = useAdminUserDetail(id) // id might be undefined

// Good - validate first
const { id } = useParams<{ id: string }>()
if (!id) {
  return <ErrorMessage>User not found</ErrorMessage>
}
const { data } = useAdminUserDetail(id) // id is guaranteed string
```

## Code Examples

Verified patterns from official sources:

### Server-Side Pagination State Management
```typescript
// Pattern: Manual pagination with React Query
// Source: Existing DataTable.tsx + TanStack React Table docs
import { useState } from "react"
import { useAdminStalledContacts } from "@/hooks/useInsights"

const PAGE_SIZE = 50

export default function StalledContacts() {
  const [pageIndex, setPageIndex] = useState(0)
  const [sortBy, setSortBy] = useState('days_stalled')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const params = {
    limit: PAGE_SIZE,
    offset: pageIndex * PAGE_SIZE,
    sort_by: sortBy,
    sort_dir: sortDir,
  }

  const { data, isLoading, isFetching } = useAdminStalledContacts(params)

  const pageCount = Math.ceil((data?.total_count || 0) / PAGE_SIZE)

  const handlePageChange = (newPage: number) => {
    setPageIndex(newPage)
  }

  const handleSortChange = (column: string) => {
    if (sortBy === column) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortDir('desc')
    }
    setPageIndex(0) // Reset to first page on sort change
  }

  // ... render table with pagination controls
}
```

### Sortable Column Header Component
```typescript
// Pattern: Server-side sortable column
// Source: TeamActivityTable.tsx adapted for server-side sorting
import { ArrowUpDown } from "lucide-react"

// In column definition
const columns = [
  columnHelper.accessor("days_stalled", {
    header: ({ column }) => (
      <button
        className="flex items-center gap-2 hover:text-foreground cursor-pointer"
        onClick={() => handleSortChange('days_stalled')}
      >
        Days Stalled
        <ArrowUpDown className="h-4 w-4" />
      </button>
    ),
    cell: (info) => {
      const days = info.getValue()
      return days !== null ? `${days} days` : 'N/A'
    }
  }),
  // ... more columns
]
```

### User-Specific Trends Hook
```typescript
// Pattern: User-scoped data fetching with React Query
// Source: Existing useInsights.ts pattern
import { useQuery } from "@tanstack/react-query"
import { getAdminUserTrends } from "@/api/insights"

const STALE_TIME = 5 * 60 * 1000 // 5 minutes

export function useAdminUserTrends(userId: string, weeks = 12) {
  return useQuery({
    queryKey: ["insights", "admin", "user-trends", userId, weeks],
    queryFn: () => getAdminUserTrends({ user_id: userId, weeks }),
    staleTime: STALE_TIME,
    enabled: !!userId, // Don't fetch if userId is missing
  })
}

export function useAdminUserJournals(userId: string) {
  return useQuery({
    queryKey: ["insights", "admin", "user-journals", userId],
    queryFn: () => getAdminUserJournals({ user_id: userId }),
    staleTime: STALE_TIME,
    enabled: !!userId,
  })
}
```

### Backend User Trends Service Function
```python
# Pattern: User-scoped analytics query
# Source: Existing get_team_trends() pattern adapted for single user
from datetime import timedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone
from apps.journals.models import Decision, Donation, StageEvent

def get_user_trends(user_id: str, weeks: int = 12) -> dict:
    """
    Get weekly trend data for a specific user.
    Returns time series of decisions, donations, stage progressions.
    """
    cutoff_date = timezone.now() - timedelta(weeks=weeks)

    # Query decisions for this user
    decision_trends = (
        Decision.objects
        .filter(journal_contact__journal__owner_id=user_id, created_at__gte=cutoff_date)
        .annotate(week=TruncWeek('created_at'))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )

    # Query donations for this user's contacts
    donation_trends = (
        Donation.objects
        .filter(contact__owner_id=user_id, date__gte=cutoff_date)
        .annotate(week=TruncWeek('date'))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )

    # Query stage events for this user
    stage_trends = (
        StageEvent.objects
        .filter(journal_contact__journal__owner_id=user_id, timestamp__gte=cutoff_date)
        .annotate(week=TruncWeek('timestamp'))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )

    # Zero-fill weeks and merge (follow Phase 16-01 pattern)
    # ... implementation similar to get_team_trends()

    return {
        'trends': trends_list,
        'weeks': weeks
    }
```

### User Journals List Service Function
```python
# Pattern: User-scoped journal listing with progress indicators
# Source: Existing journal query patterns
from django.db.models import Count, Q
from apps.journals.models import Journal

def get_user_journals(user_id: str) -> dict:
    """
    Get journals owned by user with progress indicators.
    Returns journal list with member counts and decision counts.
    """
    journals = (
        Journal.objects
        .filter(owner_id=user_id, is_archived=False)
        .annotate(
            member_count=Count('journalcontact', distinct=True),
            decision_count=Count('journalcontact__decisions', distinct=True),
            active_member_count=Count(
                'journalcontact',
                filter=Q(journalcontact__decisions__isnull=False),
                distinct=True
            )
        )
        .order_by('-created_at')
    )

    return {
        'journals': [
            {
                'id': j.id,
                'name': j.name,
                'member_count': j.member_count,
                'decision_count': j.decision_count,
                'active_member_count': j.active_member_count,
                'created_at': j.created_at.isoformat(),
            }
            for j in journals
        ]
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Client-side pagination for all tables | Server-side pagination for large datasets | Phase 14 (stalled contacts backend) | Better performance, scales to 1000s of contacts |
| Client-side sorting only | Server-side sorting with Expression-based ordering | Phase 14-02 | Null-safe sorting, consistent ordering |
| Aggregate endpoints + client filtering | Dedicated user-specific endpoints | Phase 17 (this phase) | Reduced payload, user-specific trends available |
| Props drilling for user data | React Query with userId in cache key | Phase 15 onward | Automatic refetch on user change, better caching |

**Deprecated/outdated:**
- Client-side filtering from useAdminUserPerformance for UserDetail page: Creates new dedicated endpoint instead
- Manual pagination controls without DataTable pattern: Use established pattern with proper bounds checking and disabled states

## Open Questions

Things that couldn't be fully resolved:

1. **Journal Progress Indicator Definition**
   - What we know: Requirements say "journals with progress indicators" but don't specify metrics
   - What's unclear: Which progress metrics to show (% with decisions? avg stage? completion rate?)
   - Recommendation: Use simple metrics available from existing data - member_count, decision_count, active_member_count (members with at least one decision). Mirrors dashboard's "active journals" concept.

2. **User Trends Time Range**
   - What we know: Dashboard shows 12 weeks of team trends
   - What's unclear: Should user detail match (12 weeks) or show longer history for individual tracking?
   - Recommendation: Start with 12 weeks for consistency, backend parameter allows future UI toggle if needed

3. **Stalled Contacts Default Sort**
   - What we know: Backend supports days_stalled, contact_name, owner_name, last_activity_date
   - What's unclear: Which sort order is most useful for admins?
   - Recommendation: Default to days_stalled DESC (most stalled first) - matches "stalled contacts" monitoring use case

## Sources

### Primary (HIGH confidence)
- Project codebase:
  - `frontend/src/components/shared/DataTable.tsx` - Pagination pattern
  - `frontend/src/pages/admin/analytics/components/TeamActivityTable.tsx` - Client-side sorting pattern
  - `frontend/src/pages/admin/analytics/components/TrendCharts.tsx` - Recharts LineChart pattern
  - `frontend/src/hooks/useInsights.ts` - React Query hook patterns
  - `apps/insights/views.py` - Backend endpoint patterns, StalledContactsView parameters
  - `apps/insights/services.py` - Backend service function patterns (inferred from imports)
- Project package.json - Exact library versions verified

### Secondary (MEDIUM confidence)
- [TanStack React Table Discussions - Server-side pagination implementation](https://github.com/TanStack/table/discussions/5394)
- [TanStack Query Docs - Paginated Queries](https://tanstack.com/query/v4/docs/framework/react/guides/paginated-queries)
- [React Table Sort with Column Header Clicks](https://www.bacancytechnology.com/qanda/react/react-table-sort)

### Tertiary (LOW confidence)
- [Recharts Performance Best Practices](https://refine.dev/blog/recharts/) - General guidance, not version-specific
- [Time Series with Recharts](https://github.com/recharts/recharts/issues/956) - Community discussion, pattern verified in TrendCharts.tsx

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified in package.json, versions confirmed
- Architecture: HIGH - Patterns verified in existing codebase files
- Pitfalls: HIGH - Based on common patterns and existing code structure

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (30 days - stable libraries, established patterns)
