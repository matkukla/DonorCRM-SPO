# Phase 15: Frontend Foundation & Routing - Research

**Researched:** 2026-02-13
**Domain:** React Router v6 + TanStack Query frontend routing and data fetching
**Confidence:** HIGH

## Summary

Phase 15 establishes admin analytics frontend routes and React Query hooks for 5 existing backend endpoints. The application already uses React Router v6.30.3 and TanStack Query v5.90.17 with established patterns for protected routes, role-based access, and hierarchical query keys. Research focused on extending these patterns to add `/admin/analytics/*` routes with proper navigation, permission boundaries, and data fetching.

The standard approach follows the existing codebase pattern: define routes in App.tsx with `<ProtectedRoute requiredRole="admin">`, create React Query hooks with hierarchical query keys (e.g., `['insights', 'admin', 'dashboard']`), implement API client functions with typed responses, and add navigation items to Sidebar.tsx with role-based filtering. The backend endpoints are already built and tested, so this phase is purely additive frontend work.

**Primary recommendation:** Extend existing patterns without introducing new abstractions. Follow the established admin sub-navigation pattern from AdminUsers.tsx (Users/Import Center/Analytics tabs), use hierarchical query keys with 'insights' > 'admin' > [endpoint] structure, and implement safe query parameter parsing matching backend expectations.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-router-dom | ^6.30.3 | Client-side routing | Industry standard for React routing, already integrated |
| @tanstack/react-query | ^5.90.17 | Server state management | De facto standard for data fetching/caching in React |
| axios | ^1.13.2 | HTTP client | Already configured with JWT interceptors and refresh logic |
| TypeScript | ~5.9.3 | Type safety | Full type safety for routes, query keys, and API responses |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | ^0.562.0 | Icons | Already used for navigation icons (BarChart3, etc.) |
| Radix UI components | ^1.x - ^2.x | UI primitives | Existing navigation components (Collapsible for submenus) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-router-dom | TanStack Router | Would require full routing rewrite; no benefit for this phase |
| @tanstack/react-query | SWR, RTK Query | Already integrated; switching would break existing patterns |
| Axios | Fetch API | Would lose existing interceptor logic for JWT refresh |

**Installation:**
No new packages required. All dependencies already in package.json.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── api/
│   └── insights.ts                    # API client functions (extend existing)
├── hooks/
│   └── useInsights.ts                 # React Query hooks (extend existing)
├── pages/
│   ├── admin/
│   │   ├── AdminUsers.tsx            # Existing admin page pattern
│   │   ├── ImportCenter.tsx          # Existing admin page pattern
│   │   └── analytics/                # NEW: Admin analytics pages
│   │       ├── Dashboard.tsx
│   │       ├── StalledContacts.tsx
│   │       └── UserPerformance.tsx
│   └── insights/
│       └── index.ts                   # Re-export for barrel imports
├── components/
│   ├── auth/
│   │   └── ProtectedRoute.tsx        # Role-based access control
│   └── layout/
│       └── Sidebar.tsx               # Navigation with role filtering
└── App.tsx                            # Route definitions
```

### Pattern 1: Protected Route with Role Requirement
**What:** Wrap route element in `<ProtectedRoute requiredRole="admin">` to enforce admin-only access.
**When to use:** All `/admin/analytics/*` routes require ADMIN role.
**Example:**
```typescript
// Source: Verified in App.tsx lines 97-102
<Route
  path="/admin/analytics/dashboard"
  element={
    <ProtectedPage requiredRole="admin">
      <AdminAnalyticsDashboard />
    </ProtectedPage>
  }
/>

// ProtectedRoute checks role hierarchy: admin(4) > finance(3) > staff(2) > read_only(1)
// Returns 403 "Access Denied" if user.role level < required level
```

### Pattern 2: Hierarchical Query Keys
**What:** Structure query keys from generic to specific for efficient cache invalidation.
**When to use:** All React Query hooks should follow this pattern.
**Example:**
```typescript
// Source: Best practices from TkDodo's blog and official docs
// Generic → Specific hierarchy enables partial matching for invalidation

// Good: Hierarchical structure
['insights', 'admin', 'dashboard']
['insights', 'admin', 'stalled-contacts', { limit: 50, offset: 0 }]
['insights', 'admin', 'user-performance']

// Invalidate all admin analytics:
queryClient.invalidateQueries({ queryKey: ['insights', 'admin'] })

// Invalidate specific endpoint:
queryClient.invalidateQueries({ queryKey: ['insights', 'admin', 'dashboard'] })
```

### Pattern 3: API Client with Typed Responses
**What:** Define TypeScript interfaces for API responses and implement typed API functions.
**When to use:** All new admin analytics endpoints.
**Example:**
```typescript
// Source: Verified in api/insights.ts lines 1-203
export interface DashboardOverviewResponse {
  total_contacts: number
  active_journals: number
  stalled_count: number
  conversion_rate: number
  // ... other fields
}

export async function getDashboardOverview(): Promise<DashboardOverviewResponse> {
  const response = await apiClient.get<DashboardOverviewResponse>(
    '/insights/admin/dashboard-overview/'
  )
  return response.data
}
```

### Pattern 4: React Query Hook with Safe Defaults
**What:** Create custom hooks wrapping useQuery with staleTime and type safety.
**When to use:** All data fetching for admin analytics.
**Example:**
```typescript
// Source: Verified in hooks/useInsights.ts lines 1-74
const STALE_TIME = 5 * 60 * 1000 // 5 minutes

export function useDashboardOverview() {
  return useQuery({
    queryKey: ['insights', 'admin', 'dashboard'],
    queryFn: getDashboardOverview,
    staleTime: STALE_TIME,
  })
}

// With parameters:
export function useStalledContacts(params?: {
  limit?: number
  offset?: number
  sort_by?: string
  sort_dir?: string
}) {
  return useQuery({
    queryKey: ['insights', 'admin', 'stalled-contacts', params],
    queryFn: () => getStalledContacts(params),
    staleTime: STALE_TIME,
  })
}
```

### Pattern 5: Admin Sub-Navigation
**What:** Horizontal tab navigation pattern for admin section pages (Users, Import Center, Analytics).
**When to use:** Admin analytics pages should follow AdminUsers.tsx pattern.
**Example:**
```typescript
// Source: Verified in AdminUsers.tsx lines 183-208
<div className="flex gap-4 border-b border-border pb-2">
  <NavLink
    to="/admin"
    end
    className={({ isActive }) =>
      cn(
        "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
        isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
      )
    }
  >
    Users
  </NavLink>
  <NavLink to="/admin/imports" className={...}>
    Import Center
  </NavLink>
  <NavLink to="/admin/analytics" className={...}>
    Analytics
  </NavLink>
</div>
```

### Pattern 6: Collapsible Sidebar Navigation
**What:** Use Radix Collapsible for expandable navigation groups with localStorage persistence.
**When to use:** Adding "Analytics" submenu under Admin section in Sidebar.
**Example:**
```typescript
// Source: Verified in Sidebar.tsx lines 64-89, 131-174
// Admin section items with Collapsible
const adminItems: NavItem[] = [
  { label: "Users", href: "/admin", icon: <Users />, requiredRole: "admin" },
  { label: "Import Center", href: "/admin/imports", icon: <FileUp />, requiredRole: "admin" },
  { label: "Dashboard", href: "/admin/analytics/dashboard", icon: <BarChart3 />, requiredRole: "admin" },
  { label: "Stalled Contacts", href: "/admin/analytics/stalled", icon: <AlertCircle />, requiredRole: "admin" },
]

// Persist open/closed state
const ADMIN_OPEN_KEY = "admin-nav-open"
const [isAdminOpen, setIsAdminOpen] = React.useState(() => {
  const stored = localStorage.getItem(ADMIN_OPEN_KEY)
  return stored !== null ? stored === "true" : isAdminActive
})

// Auto-expand when navigating to admin route
React.useEffect(() => {
  if (isAdminActive && !isAdminOpen) {
    setIsAdminOpen(true)
  }
}, [isAdminActive, isAdminOpen])
```

### Anti-Patterns to Avoid

- **Hardcoding route paths in multiple places:** Use constants or navigate via to="/admin/analytics/dashboard" consistently. Don't scatter "/admin/analytics/dashboard" strings throughout code.
- **Missing query key parameters:** If query function uses limit/offset, they MUST be in query key for proper caching. Bad: `queryKey: ['stalled']` Good: `queryKey: ['stalled', { limit, offset }]`
- **Using TanStack Query for client state:** React Query is for server state. Don't use it for form inputs, UI toggles, or local component state.
- **Forgetting <Outlet /> in nested routes:** Not applicable (using flat route structure), but if switching to nested routes, parent must render `<Outlet />`.
- **Multiple BrowserRouter instances:** Already wrapped once in App.tsx. Never add another.
- **Using <a> tags for internal navigation:** Use `<Link>` or `<NavLink>` to preserve SPA behavior.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API request caching | Custom cache object with timestamps | TanStack Query (already integrated) | Handles staleness, refetching, deduplication, background updates automatically |
| JWT token refresh | Manual interceptor logic | Existing apiClient interceptors (client.ts) | Already handles 401, refresh token flow, request queue, window.location redirect |
| Role-based route protection | Custom HOC or route wrapper | Existing ProtectedRoute component | Already implements role hierarchy, loading states, 403 handling |
| Query parameter parsing | Manual parseInt with try/catch | Existing get_safe_int_param pattern | Backend uses bounded validation; frontend should match expectations |
| Navigation state persistence | Custom localStorage logic | Existing Sidebar pattern (INSIGHTS_OPEN_KEY) | Already implements open/close state with auto-expand on navigation |

**Key insight:** This codebase has mature patterns for routing, auth, and data fetching. Extending existing patterns is faster and safer than introducing new abstractions.

## Common Pitfalls

### Pitfall 1: Query Key Inconsistency
**What goes wrong:** Query keys don't match between hook calls, causing duplicate cache entries or stale data.
**Why it happens:** Developer manually types query key arrays in multiple places instead of using constants or query key factories.
**How to avoid:** Use query key factories for complex applications. For this phase, keep keys consistent: `['insights', 'admin', 'endpoint-name', params]`.
**Warning signs:** Same data fetched multiple times, cache invalidation doesn't work, stale data shown after mutation.

### Pitfall 2: Missing Dynamic Parameters in Query Keys
**What goes wrong:** Query key is static but query function uses dynamic parameters (limit, offset, sort). Same cached data shown for all parameter values.
**Why it happens:** Developer forgets that query keys identify cache entries. If parameters change but key doesn't, cache entry doesn't change.
**How to avoid:** Include ALL dynamic query function parameters in query key: `queryKey: ['insights', 'admin', 'stalled-contacts', { limit, offset, sort_by, sort_dir }]`
**Warning signs:** Pagination doesn't work, sorting shows wrong data, changing filters has no effect.

### Pitfall 3: Forgetting requiredRole Prop
**What goes wrong:** Admin-only routes are accessible to non-admin users, causing 403 errors from backend or exposing unauthorized data.
**Why it happens:** Developer copies `<ProtectedRoute>` without `requiredRole="admin"` prop.
**How to avoid:** All `/admin/*` routes MUST use `requiredRole="admin"`. Verify with non-admin test user.
**Warning signs:** Backend returns 403 errors, audit logs show unauthorized access attempts, UI renders before permission check.

### Pitfall 4: Incorrect Sidebar Role Filtering
**What goes wrong:** Analytics menu items visible to non-admin users, clicking causes navigation to 403 page.
**Why it happens:** Navigation items added without `requiredRole: "admin"` in navItems array.
**How to avoid:** Add `requiredRole: "admin"` to all admin analytics nav items. Sidebar.tsx already filters with `canAccess()` function.
**Warning signs:** Menu items visible but clicking shows "Access Denied", inconsistent UI between users.

### Pitfall 5: Not Matching Backend Parameter Expectations
**What goes wrong:** Frontend sends unbounded query parameters, backend applies different defaults or bounds, causing confusion.
**Why it happens:** Frontend doesn't check backend's get_safe_int_param bounds (min_val, max_val).
**How to avoid:** Review backend views.py for parameter bounds. StalledContactsView uses `get_safe_int_param(request, 'limit', default=50, min_val=1, max_val=100)`. Frontend should respect these bounds.
**Warning signs:** Pagination behaves unexpectedly, requesting limit=1000 returns 100 results, API returns 400 errors.

### Pitfall 6: Using Wrong HTTP Method
**What goes wrong:** Developer uses apiClient.post() for read-only admin analytics endpoints.
**Why it happens:** Copy-paste from mutation code without checking endpoint method.
**How to avoid:** All 5 admin analytics endpoints are GET-only. Verify in urls.py and views.py. Use apiClient.get() with params.
**Warning signs:** 405 Method Not Allowed errors, CSRF token errors, mutations logged for read operations.

### Pitfall 7: StaleTime Confusion
**What goes wrong:** Data refetches too often (every component mount) or stays stale too long (user sees outdated counts).
**Why it happens:** Developer doesn't understand TanStack Query defaults: staleTime=0 (always stale), gcTime=5 minutes.
**How to avoid:** Use existing STALE_TIME constant (5 minutes) from useInsights.ts. Admin analytics data can be stale for 5 minutes without user confusion.
**Warning signs:** Network tab shows excessive requests, dashboard counts don't update after mutations, users report "wrong numbers".

## Code Examples

Verified patterns from official sources and existing codebase:

### Route Definition with Admin Protection
```typescript
// Source: App.tsx pattern, verified lines 97-102
import AdminAnalyticsDashboard from "@/pages/admin/analytics/Dashboard"
import StalledContacts from "@/pages/admin/analytics/StalledContacts"
import UserPerformance from "@/pages/admin/analytics/UserPerformance"

// In <Routes>:
<Route
  path="/admin/analytics/dashboard"
  element={<ProtectedPage requiredRole="admin"><AdminAnalyticsDashboard /></ProtectedPage>}
/>
<Route
  path="/admin/analytics/stalled"
  element={<ProtectedPage requiredRole="admin"><StalledContacts /></ProtectedPage>}
/>
<Route
  path="/admin/analytics/users/:id"
  element={<ProtectedPage requiredRole="admin"><UserPerformance /></ProtectedPage>}
/>
```

### API Client Function with Query Parameters
```typescript
// Source: api/insights.ts pattern, verified lines 192-203
import { apiClient } from "./client"

export interface StalledContactsParams {
  limit?: number
  offset?: number
  sort_by?: string
  sort_dir?: string
}

export interface StalledContactItem {
  contact_id: string
  full_name: string
  owner_id: string
  owner_name: string
  last_activity_date: string
  days_stalled: number
}

export interface StalledContactsResponse {
  contacts: StalledContactItem[]
  total_count: number
  limit: number
  offset: number
}

export async function getStalledContacts(
  params?: StalledContactsParams
): Promise<StalledContactsResponse> {
  const response = await apiClient.get<StalledContactsResponse>(
    '/insights/admin/stalled-contacts/',
    { params }
  )
  return response.data
}
```

### React Query Hook with Parameters
```typescript
// Source: hooks/useInsights.ts pattern, verified lines 1-74
import { useQuery } from "@tanstack/react-query"
import { getStalledContacts, type StalledContactsParams } from "@/api/insights"

const STALE_TIME = 5 * 60 * 1000 // 5 minutes

export function useStalledContacts(params?: StalledContactsParams) {
  return useQuery({
    queryKey: ['insights', 'admin', 'stalled-contacts', params],
    queryFn: () => getStalledContacts(params),
    staleTime: STALE_TIME,
  })
}

// Usage in component:
const { data, isLoading, error } = useStalledContacts({
  limit: 50,
  offset: 0,
  sort_by: 'days_stalled',
  sort_dir: 'desc',
})
```

### Admin Sub-Navigation Component
```typescript
// Source: AdminUsers.tsx pattern, verified lines 183-208
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"

export function AdminSubNav() {
  return (
    <div className="flex gap-4 border-b border-border pb-2">
      <NavLink
        to="/admin"
        end
        className={({ isActive }) =>
          cn(
            "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
            isActive
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:text-foreground"
          )
        }
      >
        Users
      </NavLink>
      <NavLink
        to="/admin/imports"
        className={({ isActive }) =>
          cn(
            "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
            isActive
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:text-foreground"
          )
        }
      >
        Import Center
      </NavLink>
      <NavLink
        to="/admin/analytics"
        className={({ isActive }) =>
          cn(
            "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
            isActive
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:text-foreground"
          )
        }
      >
        Analytics
      </NavLink>
    </div>
  )
}
```

### Sidebar Collapsible Menu with Role Filtering
```typescript
// Source: Sidebar.tsx pattern, verified lines 91-99
interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
  requiredRole?: "admin" | "staff" | "finance" | "read_only"
}

const adminItems: NavItem[] = [
  { label: "Users", href: "/admin", icon: <Users className="h-4 w-4" />, requiredRole: "admin" },
  { label: "Import Center", href: "/admin/imports", icon: <FileUp className="h-4 w-4" />, requiredRole: "admin" },
  { label: "Analytics", href: "/admin/analytics/dashboard", icon: <BarChart3 className="h-4 w-4" />, requiredRole: "admin" },
]

// In Sidebar component:
const canAccess = (item: NavItem) => {
  if (!item.requiredRole) return true
  if (!user) return false
  const roleHierarchy: Record<string, number> = {
    admin: 4, finance: 3, staff: 2, read_only: 1
  }
  return roleHierarchy[user.role] >= roleHierarchy[item.requiredRole]
}

const filteredAdminItems = adminItems.filter(canAccess)
```

### Loading States in Page Components
```typescript
// Source: AdminUsers.tsx pattern, verified lines 166-177
export default function AdminAnalyticsDashboard() {
  const { data, isLoading } = useDashboardOverview()

  if (isLoading) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            <div className="h-8 w-48 bg-muted rounded animate-pulse" />
            <div className="h-64 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  return (
    <Section>
      <Container>
        {/* Render data */}
      </Container>
    </Section>
  )
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| React Router v5 with Switch | React Router v6 with Routes | v6.0.0 (Nov 2021) | `element={}` replaces `component=`, no `exact` prop, nested routes use `<Outlet />` |
| React Query v3 | TanStack Query v5 | v5.0.0 (Oct 2023) | Package renamed to @tanstack/react-query, stricter TypeScript, improved DevTools |
| Class components with lifecycle | Function components with hooks | React 16.8+ (Feb 2019) | useQuery, useEffect replace componentDidMount patterns |
| Redux for all state | TanStack Query for server state, Context/useState for client state | Industry shift ~2020 | Server state (API data) separated from client state (UI toggles) |

**Deprecated/outdated:**
- `<Switch>` component: Replaced with `<Routes>` in React Router v6
- `component=` prop: Use `element={}` instead
- `exact` prop: Routes are exact by default in v6
- useHistory hook: Use useNavigate instead
- React Query v3 import paths: Use @tanstack/react-query

## Open Questions

1. **Should analytics routes use nested routing under /admin?**
   - What we know: Current admin routes are flat (/admin, /admin/imports). No Outlet pattern used.
   - What's unclear: Whether analytics should follow flat pattern (/admin/analytics/dashboard) or nested (/admin/analytics with Outlet).
   - Recommendation: Use flat pattern to match existing admin routes. Simplifies routing, no need for Outlet component.

2. **Should all 5 analytics pages share layout/wrapper component?**
   - What we know: AdminUsers.tsx repeats AdminSubNav and Section/Container structure.
   - What's unclear: Whether to extract shared layout for analytics pages.
   - Recommendation: Start with repetition (match AdminUsers pattern), extract if more than 3 pages share identical structure.

3. **Should query key factory be introduced for admin analytics?**
   - What we know: Existing useInsights.ts uses inline query keys. TkDodo recommends factories for complex apps.
   - What's unclear: Threshold for "complex enough" to justify factory pattern.
   - Recommendation: Use inline keys for Phase 15 (5 endpoints). Consider factory if Phase 16+ adds 10+ more admin endpoints.

## Sources

### Primary (HIGH confidence)
- React Router v6 official docs (reactrouter.com/start/framework/routing) - Route organization, protected routes, nested routing
- TanStack Query v5 official docs (tanstack.com/query/latest) - Query keys, caching, hooks API
- Existing codebase patterns:
  - frontend/package.json - Verified versions: react-router-dom ^6.30.3, @tanstack/react-query ^5.90.17
  - frontend/src/App.tsx - Route structure and ProtectedRoute usage
  - frontend/src/components/auth/ProtectedRoute.tsx - Role hierarchy implementation
  - frontend/src/api/insights.ts - API client pattern with typed responses
  - frontend/src/hooks/useInsights.ts - React Query hook pattern with STALE_TIME
  - frontend/src/pages/admin/AdminUsers.tsx - Admin sub-navigation pattern
  - frontend/src/components/layout/Sidebar.tsx - Collapsible navigation with role filtering
  - apps/insights/views.py - Backend parameter validation and endpoint structure
  - apps/insights/urls.py - Admin analytics URL patterns

### Secondary (MEDIUM confidence)
- [The Guide to Nested Routes with React Router](https://ui.dev/react-router-nested-routes) - Nested route concepts
- [How to Use React Query (TanStack Query) for Server State Management](https://oneuptime.com/blog/post/2026-01-15-react-query-tanstack-server-state/view) - 2026 best practices
- [React Data Fetching Best Practices with TanStack Query](https://rtcamp.com/handbook/react-best-practices/data-loading/) - Data loading patterns
- [Effective React Query Keys | TkDodo's blog](https://tkdodo.eu/blog/effective-react-query-keys) - Query key structure patterns
- [Complete guide to authentication with React Router v6](https://blog.logrocket.com/complete-guide-authentication-with-react-router-v6/) - Protected route patterns

### Tertiary (LOW confidence - for awareness)
- [Creating Protected Routes With React Router V6](https://medium.com/@dennisivy/creating-protected-routes-with-react-router-v6-2c4bbaf7bc1c) - Single author tutorial
- [Avoiding Common Mistakes with TanStack Query Part 1](https://www.buncolak.com/posts/avoiding-common-mistakes-with-tanstack-query-part-1/) - Community blog post
- [React Router Common mistakes and how to avoid them](https://medium.com/@rowsana/react-router-common-mistakes-and-how-to-avoid-them-bc110a6dedfe) - Community blog post

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified in package.json and existing codebase
- Architecture: HIGH - Patterns extracted from existing working code (App.tsx, Sidebar.tsx, AdminUsers.tsx)
- Pitfalls: HIGH - Derived from official docs and verified in codebase (get_safe_int_param, role hierarchy)
- Code examples: HIGH - All examples from verified codebase or official documentation

**Research date:** 2026-02-13
**Valid until:** 2026-03-15 (30 days for stable ecosystem; React Router v6 and TanStack Query v5 are mature)
