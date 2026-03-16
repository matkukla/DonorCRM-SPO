# Phase 53: View As — Frontend - Research

**Researched:** 2026-03-16
**Domain:** React Context, Axios interceptors, React Query cache management, sessionStorage, shadcn/ui components
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Context architecture**
- New `ViewAsContext` — separate from `AuthProvider`, does not extend it
- Provider placement: inside `AuthProvider`, wrapping `QueryProvider` children (needs auth to read user role; needs queryClient to clear cache)
- Reads `sessionStorage` on mount to restore any in-progress View As session across browser refresh
- State shape: `{ viewAsUserId: string | null, viewAsUserName: string | null, setViewAsUser(id, name): void, exitViewAs(): void }`
- On `setViewAsUser()` or `exitViewAs()`: call `queryClient.clear()` (nuclear cache wipe, not invalidation) to prevent stale data from the previous user
- Session cleared only by clicking Exit or logging out — sessionStorage entry removed in both `exitViewAs()` and AuthProvider's `logout()`

**API header injection**
- Axios request interceptor in `frontend/src/api/client.ts` reads `viewAsUserId` from sessionStorage directly (not from React context — interceptor lives outside the component tree)
- Adds `X-View-As-User-Id: <uuid>` header to every outbound request when a value is present
- All 40+ existing hooks pick this up automatically with zero per-hook changes

**Banner design & placement**
- Rendered in `AppLayout` (top of main content area, above page content)
- Only shown when `viewAsUserId !== null`
- Visual style: amber/warning — `bg-amber-50 border-amber-200 text-amber-800` in light mode; `dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300`
- Icon: `AlertTriangle` or `Eye` from lucide-react (Claude's discretion on exact icon)
- Content: "Viewing [Full Name] · Read Only" with `[Exit]` button on the right
- Exit button: calls `exitViewAs()` → clears state + sessionStorage + React Query cache → stays on current route (no redirect)

**Selector placement & trigger**
- Dashboard only — the existing Popover/Command missionary picker on the Dashboard is promoted from local state to calling `setViewAsUser()` on ViewAsContext
- Data source: `GET /api/users/viewable/` via new `useViewableUsers()` hook — replaces the current use of `useUsers()` (all users) and `user.supervised_users` (supervisor branch)
- Response shape from backend: `[{ id: string, full_name: string }]`
- "My Dashboard" option in the picker calls `exitViewAs()` (same effect as the banner Exit button)
- Selector only shown when `user?.role === "admin" || user?.role === "supervisor"` (unchanged from current condition)

**Mutation blocking (frontend)**
- `useViewAs()` hook exposes `isViewingAs: boolean` derived from `viewAsUserId !== null`
- Create/edit/delete buttons and action menus: hidden (not disabled) when `isViewingAs` is true
- Applies to: Contact create/edit/delete, Donation/Gift create/edit/delete, Pledge/RecurringGift create/edit/delete, Task create/edit/delete, Journal create/edit/delete, Group create/edit/delete, Prayer intention actions
- Backend enforces 403 regardless — frontend hiding is a UX convenience, not the security layer

**Admin-section hiding in sidebar**
- While `isViewingAs` is true, hide from Sidebar:
  - Import/Export nav item
  - Admin nav item (and all admin sub-routes)
  - Insights → Transactions item (`requiredRole: "admin"`)
- My Team nav item (visible to supervisor/coach) remains visible
- Implementation: Sidebar reads `isViewingAs` from `useViewAs()` and applies additional filter on top of existing role checks

### Claude's Discretion
- Exact lucide-react icon for the banner (AlertTriangle vs Eye vs Info)
- Whether `useViewableUsers()` lives in `hooks/useUsers.ts` (extending it) or a new `hooks/useViewAs.ts`
- Whether the `ViewAsContext` file lives in `providers/` (alongside AuthProvider) or `contexts/`
- sessionStorage key name (e.g., `donorcrm_view_as_user_id`, `donorcrm_view_as_user_name`)

### Deferred Ideas (OUT OF SCOPE)
- Coach View As support (view their coached missionaries) — deferred to v2.4+ per VIEWAS-EX-01
- Audit log of View As sessions — deferred to v2.4+ per VIEWAS-EX-02
- Header-bar missionary picker (always-accessible selector) — user chose Dashboard-only entry point
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIEWAS-01 | Admin can select any missionary from a dropdown to view as | `useViewableUsers()` hook fetching `GET /api/users/viewable/`; backend returns all active missionaries for admin |
| VIEWAS-02 | Supervisor can select any of their assigned missionaries from a dropdown to view as | Same `useViewableUsers()` hook; backend filters to `supervised_users` for supervisor role |
| VIEWAS-03 | Persistent banner appears showing missionary's name and read-only indicator | `ViewAsBanner` component in `AppLayout`; amber color scheme confirmed from CONTEXT |
| VIEWAS-04 | Banner includes an "Exit" button that returns user to their own view | `exitViewAs()` method on `ViewAsContext`; no redirect needed |
| VIEWAS-05 | All data shown belongs to selected missionary | Axios interceptor injects `X-View-As-User-Id` header on every request; backend scopes via Phase 52 middleware |
| VIEWAS-06 | All create/edit/delete actions are disabled or hidden in View As mode | `isViewingAs` from `useViewAs()` used to hide buttons across 7+ pages |
| VIEWAS-09 | Admin-only navigation sections hidden while in View As mode | Sidebar reads `isViewingAs` and additionally filters Import/Export, Admin, Transactions |
| VIEWAS-10 | View As selection persists across page navigation until explicitly exited | sessionStorage as source of truth; ViewAsProvider restores on mount |
| VIEWAS-11 | All React Query caches invalidated when View As user changes | `queryClient.clear()` called in both `setViewAsUser()` and `exitViewAs()` |
</phase_requirements>

## Summary

Phase 53 is a pure frontend phase that wires up the View As capability on top of Phase 52's backend. The core machinery is a new `ViewAsProvider` (React Context) that holds the selected user ID and name, syncs with sessionStorage for persistence, and drives all UI state changes. The Axios request interceptor — already established for JWT injection — is extended with a second conditional header injection that reads sessionStorage directly. This avoids any circular dependency between the interceptor (module scope) and React Context (render scope).

The Dashboard's existing Popover/Command missionary picker is promoted from local `useState` to calling `setViewAsUser()`/`exitViewAs()` on the context. The banner is a new `ViewAsBanner` component slotted into `AppLayout` above the `<main>` content. Mutation blocking and sidebar hiding both flow from a single `isViewingAs` boolean from `useViewAs()`, a pattern already established in this codebase for role-based visibility.

No new libraries are needed. No new routes are needed. The heaviest work is the breadth audit: ensuring every create/edit/delete trigger across contacts, donations, pledges, tasks, journals, groups, and prayer pages is hidden when `isViewingAs` is true.

**Primary recommendation:** Build in waves — (1) ViewAsProvider + sessionStorage + interceptor, (2) banner + App.tsx wiring, (3) Dashboard selector promotion + useViewableUsers, (4) sidebar hiding, (5) mutation blocking breadth pass across all 7 page areas.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.0 | Context/Provider pattern | Already in project |
| @tanstack/react-query | 5.90.17 | `queryClient.clear()` for cache wipe | Already in project |
| axios | 1.13.2 | Interceptor extension | Already in project; interceptor pattern established |
| lucide-react | 0.562.0 | Icons for banner (AlertTriangle/Eye) | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui Button | local | Exit button in banner | Already used everywhere |
| sessionStorage (browser API) | native | Cross-page persistence | Already used by project for tokens (localStorage); sessionStorage preferred here because View As should not survive a browser close |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sessionStorage direct read in interceptor | React Context in interceptor | Context is React-only; interceptor is module-level. sessionStorage is the only safe shared medium |
| `queryClient.clear()` | `queryClient.invalidateQueries()` | invalidateQueries refetches in background, can return stale data briefly. `clear()` is nuclear — forces fresh fetch after user change. Decision is locked |
| Separate `ViewAsContext` | Extending `AuthProvider` | Separation of concerns; AuthProvider is stable and tested. Locked decision |

**Installation:** No new packages required.

## Architecture Patterns

### File Layout
```
frontend/src/
├── providers/
│   ├── AuthProvider.tsx        # Existing — add logout() sessionStorage clear
│   ├── ViewAsProvider.tsx      # NEW — ViewAsContext, ViewAsProvider, useViewAs()
│   └── QueryProvider.tsx       # Existing — queryClient exported for ViewAsProvider
├── api/
│   ├── client.ts               # Existing — add sessionStorage read + X-View-As-User-Id header
│   └── users.ts                # Existing — add ViewableUser type + getViewableUsers()
├── hooks/
│   └── useUsers.ts             # Existing — add useViewableUsers() hook (or new useViewAs.ts)
├── components/
│   └── layout/
│       ├── AppLayout.tsx       # Existing — render <ViewAsBanner /> above <main>
│       ├── Sidebar.tsx         # Existing — add isViewingAs filter
│       └── ViewAsBanner.tsx    # NEW — amber banner component
└── pages/
    └── Dashboard.tsx           # Existing — major refactor: promote picker to ViewAsContext
```

### Pattern 1: ViewAsProvider
**What:** A React Context provider that wraps the authenticated portion of the app, managing View As state and syncing to sessionStorage.
**When to use:** Wrap inside `<AuthProvider>` but outside `<QueryProvider>`. AuthProvider must be ancestor (to read user role in components). QueryProvider must be descendant so `queryClient.clear()` can be called (queryClient is imported directly from QueryProvider.tsx, not from context, so this constraint is actually about ensuring QueryProvider has mounted before any query is made after a setViewAsUser call).

```typescript
// Source: AuthProvider.tsx pattern (project-established)
const VIEW_AS_USER_ID_KEY = "donorcrm_view_as_user_id"
const VIEW_AS_USER_NAME_KEY = "donorcrm_view_as_user_name"

interface ViewAsContextType {
  viewAsUserId: string | null
  viewAsUserName: string | null
  setViewAsUser: (id: string, name: string) => void
  exitViewAs: () => void
  isViewingAs: boolean
}

export function ViewAsProvider({ children }: { children: ReactNode }) {
  const [viewAsUserId, setViewAsUserId] = useState<string | null>(
    () => sessionStorage.getItem(VIEW_AS_USER_ID_KEY)
  )
  const [viewAsUserName, setViewAsUserName] = useState<string | null>(
    () => sessionStorage.getItem(VIEW_AS_USER_NAME_KEY)
  )

  const setViewAsUser = useCallback((id: string, name: string) => {
    sessionStorage.setItem(VIEW_AS_USER_ID_KEY, id)
    sessionStorage.setItem(VIEW_AS_USER_NAME_KEY, name)
    setViewAsUserId(id)
    setViewAsUserName(name)
    queryClient.clear()
  }, [])

  const exitViewAs = useCallback(() => {
    sessionStorage.removeItem(VIEW_AS_USER_ID_KEY)
    sessionStorage.removeItem(VIEW_AS_USER_NAME_KEY)
    setViewAsUserId(null)
    setViewAsUserName(null)
    queryClient.clear()
  }, [])

  // ...
}
```

### Pattern 2: Axios Interceptor Extension
**What:** Add a second header in the existing request interceptor in `client.ts`. The interceptor reads sessionStorage directly — no React import needed.
**When to use:** Always. The interceptor fires for every outbound request.

```typescript
// Source: client.ts line 41-52 (project code — extending existing pattern)
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // NEW: inject View As header from sessionStorage
    const viewAsUserId = sessionStorage.getItem("donorcrm_view_as_user_id")
    if (viewAsUserId) {
      config.headers["X-View-As-User-Id"] = viewAsUserId
    }
    return config
  },
  (error) => Promise.reject(error)
)
```

### Pattern 3: App.tsx Provider Nesting
**What:** `ViewAsProvider` wraps `BrowserRouter` and its descendants (including Sidebar, all pages) but is itself inside `AuthProvider` (needs auth), and `QueryProvider` is its ancestor (queryClient imported by module reference, not context).
**When to use:** The current nesting is:

```
ThemeProvider
  ErrorBoundary
    QueryProvider       ← queryClient is a module-level export
      AuthProvider      ← user.role needed by ViewAsProvider consumers
        [ViewAsProvider NEW]
          BrowserRouter
            NuqsAdapter
              Routes...
```

This placement is correct: ViewAsProvider uses `queryClient` via direct import (no React dependency), and `useViewAs()` is available to all routed pages.

### Pattern 4: Mutation Hiding via isViewingAs
**What:** All create/edit/delete UI elements check `isViewingAs` from `useViewAs()` and render `null` or are omitted from JSX when true.
**When to use:** Any component that has a create, edit, delete, or other write action.

```typescript
// Pattern used across pages (extends existing isReadOnly pattern)
const { isViewingAs } = useViewAs()

// Hide create button
{!isViewingAs && (
  <Button onClick={() => navigate("/contacts/new")}>
    Add Contact
  </Button>
)}

// Hide edit/delete in row actions
{!isViewingAs && canEdit && (
  <DropdownMenuItem onClick={...}>Edit</DropdownMenuItem>
)}
```

### Pattern 5: Dashboard Selector Promotion
**What:** Dashboard's existing `selectedUserId` local state and the Popover/Command picker are replaced with `ViewAsContext` calls. The picker UI is unchanged; only the state management moves to context.
**When to use:** This is the primary entry point for entering View As mode.

```typescript
// BEFORE (Dashboard.tsx lines 58-68)
const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
const { data: allUsers } = useUsers()
const missionaryOptions = user?.role === "admin"
  ? (allUsers?.filter((u) => u.id !== user.id && u.is_active) || [])
  : (user?.supervised_users || [])

// AFTER
const { viewAsUserId, viewAsUserName, setViewAsUser, exitViewAs, isViewingAs } = useViewAs()
const { data: viewableUsers } = useViewableUsers()
// missionaryOptions = viewableUsers (response already filtered to correct set per role)

// onSelect in CommandItem:
onSelect={() => { setViewAsUser(u.id, u.full_name); setViewingPickerOpen(false) }}
// "My Dashboard" onSelect:
onSelect={() => { exitViewAs(); setViewingPickerOpen(false) }}
```

### Anti-Patterns to Avoid
- **Reading viewAsUserId from React context in the Axios interceptor:** The interceptor is set up at module load time — outside the React tree. sessionStorage is the only safe shared medium.
- **Using `queryClient.invalidateQueries()` instead of `queryClient.clear()`:** Invalidation refetches in background and can serve stale data to the new View As user briefly. `clear()` is the correct nuclear approach here (locked decision).
- **Disabling mutation buttons instead of hiding them:** Disabled buttons are confusing when there is no visible explanation. The decision is to hide entirely.
- **Adding isViewingAs check to the Axios interceptor for mutation blocking:** The backend (Phase 52) already returns 403. The frontend blocking is UX only — hiding buttons is sufficient.
- **Forgetting the GoalPage TODO:** `GoalPage.tsx` line 72 has `const isReadOnly = false // TODO(phase-52): re-enable when View As context exists`. This needs to be updated to `const isReadOnly = isViewingAs`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-page state persistence | Custom event system / URL params | sessionStorage (native) | URL params expose internal user IDs; events don't survive page reload |
| Cache invalidation on user switch | Per-query invalidation loop | `queryClient.clear()` | 40+ queries — looping over all would be error-prone and incomplete |
| Middleware-style header injection | Per-hook header parameter | Axios request interceptor | Interceptor fires on all requests; per-hook approach misses new hooks |

**Key insight:** The two hard problems (header injection breadth + cache coherence) both have single-point solutions already available in the project architecture. No new library or custom infrastructure is needed.

## Common Pitfalls

### Pitfall 1: queryClient imported before QueryProvider mounts
**What goes wrong:** If ViewAsProvider calls `queryClient.clear()` during mount (e.g., in useEffect), and QueryProvider hasn't mounted yet, the clear runs against a stale reference.
**Why it happens:** `queryClient` is a module-level singleton exported from `QueryProvider.tsx`. It exists as soon as the module loads, so there is no actual risk — the import is always valid.
**How to avoid:** The import is safe because it's a module-level singleton, not a React context value. No issue exists.
**Warning signs:** None — this is a false pitfall. The architecture is sound.

### Pitfall 2: sessionStorage key mismatch between interceptor and ViewAsProvider
**What goes wrong:** The interceptor reads `sessionStorage.getItem("donorcrm_view_as_user_id")` but the provider uses a different key constant, or the key is defined separately in two files.
**Why it happens:** Interceptor lives in `client.ts`; provider lives in `ViewAsProvider.tsx`. Both need the same key.
**How to avoid:** Define a single exported constant in one place (e.g., in `ViewAsProvider.tsx` or a shared constants file) and import it into `client.ts`. Alternatively, repeat the string literal in both places with a code comment.
**Warning signs:** View As header not sent despite session being active, or header sent after exit.

### Pitfall 3: Dashboard isViewingOther logic becomes inconsistent with ViewAsContext
**What goes wrong:** Dashboard currently derives `isViewingOther = selectedUserId !== null && selectedUserId !== user?.id`. After promotion to ViewAsContext, this derivation changes — `viewAsUserId` from context is always the "other" user (never the logged-in user's own ID).
**Why it happens:** The old logic handled a case where `selectedUserId` could equal `user.id` (i.e., "select yourself"). ViewAsContext never allows self-selection (backend and UI both prevent it).
**How to avoid:** Replace all uses of local `isViewingOther` with `isViewingAs` from `useViewAs()`. Remove the `selectedUserId !== user?.id` guard — it's no longer needed.
**Warning signs:** Dashboard shows "viewing other" banner when looking at own dashboard, or vice versa.

### Pitfall 4: Dashboard's read-only banner not removed
**What goes wrong:** After promoting the selector to ViewAsContext, the Dashboard-local read-only banner (lines 323-327 in Dashboard.tsx) still renders alongside the new app-level ViewAsBanner, showing duplicate banners.
**Why it happens:** The old Dashboard had its own inline banner. The new architecture uses AppLayout-level banner.
**How to avoid:** Explicitly remove the Dashboard-local banner (the `{isViewingOther && selectedUserName && <div>...Viewing {selectedUserName}'s dashboard (read-only)</div>}` block).
**Warning signs:** Two banners visible when in View As mode.

### Pitfall 5: Sidebar canAccess function vs isViewingAs layering
**What goes wrong:** The current `canAccess()` function in Sidebar checks role hierarchy. Adding `isViewingAs` as an additional filter must not conflict with the existing role checks — an admin in View As mode should still see `My Team` (for supervisor) but not `Import/Export` or `Admin`.
**Why it happens:** The items to hide are selectively a subset of what the role would normally show. A blanket `isViewingAs → hide everything admin-only` would break supervisor's own legitimate items.
**How to avoid:** Apply the View As filter as a second-pass after `canAccess()`, specifically targeting the three item labels/hrefs: `Import/Export`, `Admin`, and the Transactions insights item. Do not change `canAccess()` itself — add a separate `isHiddenInViewAs(item)` predicate.
**Warning signs:** Supervisor loses My Team link in View As mode, or admin keeps Import/Export link in View As mode.

### Pitfall 6: GoalPage isReadOnly hardcoded to false
**What goes wrong:** `GoalPage.tsx` line 72 has `const isReadOnly = false // TODO(phase-52): re-enable when View As context exists`. If this isn't updated in Phase 53, goal editing will be enabled in View As mode.
**Why it happens:** Intentional placeholder left during Phase 50 implementation.
**How to avoid:** Update GoalPage to `const { isViewingAs } = useViewAs()` and `const isReadOnly = isViewingAs`.
**Warning signs:** Goal settings editable when in View As mode.

### Pitfall 7: AuthProvider logout does not clear View As sessionStorage
**What goes wrong:** If a user is in View As mode and their JWT expires (or they navigate to `/login`), the next login as a different user inherits the previous View As session from sessionStorage.
**Why it happens:** `AuthProvider.logout()` currently clears JWT tokens (via `clearTokens()`) but knows nothing about View As keys.
**How to avoid:** In `AuthProvider.tsx`'s `logout()` callback, add `sessionStorage.removeItem(VIEW_AS_USER_ID_KEY)` and `sessionStorage.removeItem(VIEW_AS_USER_NAME_KEY)`. Import or inline the key constants.
**Warning signs:** A fresh login session immediately shows the View As banner.

## Code Examples

### ViewableUser API Client

```typescript
// frontend/src/api/users.ts — additions
export interface ViewableUser {
  id: string
  full_name: string
}

export async function getViewableUsers(): Promise<ViewableUser[]> {
  const response = await apiClient.get("/users/viewable/")
  return response.data
}
```

### useViewableUsers Hook

```typescript
// frontend/src/hooks/useUsers.ts (or useViewAs.ts) — additions
export function useViewableUsers() {
  return useQuery({
    queryKey: ["viewable-users"],
    queryFn: () => getViewableUsers(),
  })
}
```

Note: This query is only called on Dashboard when the user is admin/supervisor. No `enabled` guard is strictly needed since non-admin/supervisor users never reach the Dashboard picker, but adding `enabled: user?.role === "admin" || user?.role === "supervisor"` is clean.

### ViewAsBanner Component

```typescript
// frontend/src/components/layout/ViewAsBanner.tsx (new)
import { Eye, X } from "lucide-react"  // or AlertTriangle
import { Button } from "@/components/ui/button"
import { useViewAs } from "@/providers/ViewAsProvider"

export function ViewAsBanner() {
  const { isViewingAs, viewAsUserName, exitViewAs } = useViewAs()

  if (!isViewingAs) return null

  return (
    <div className="flex items-center justify-between gap-3 px-4 py-2 bg-amber-50 border-b border-amber-200 text-amber-800 text-sm dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300">
      <div className="flex items-center gap-2">
        <Eye className="h-4 w-4 shrink-0" />
        <span>Viewing <strong>{viewAsUserName}</strong> · Read Only</span>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={exitViewAs}
        className="text-amber-800 hover:text-amber-900 hover:bg-amber-100 dark:text-amber-300 dark:hover:text-amber-200 dark:hover:bg-amber-900/30 h-7 px-2"
      >
        <X className="h-3.5 w-3.5 mr-1" />
        Exit
      </Button>
    </div>
  )
}
```

### AppLayout Integration

```typescript
// frontend/src/components/layout/AppLayout.tsx — modified main content area
import { ViewAsBanner } from "./ViewAsBanner"

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <div className="hidden lg:flex lg:w-64 lg:flex-col">
        <Sidebar />
      </div>
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <ViewAsBanner />  {/* NEW — above main content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
```

### Sidebar View As Filter

```typescript
// frontend/src/components/layout/Sidebar.tsx — additions
import { useViewAs } from "@/providers/ViewAsProvider"

// In component:
const { isViewingAs } = useViewAs()

// Items to hide in View As mode (in addition to existing canAccess filter)
const viewAsHiddenHrefs = new Set(["/import-export", "/admin"])
// Transactions is filtered via insightsItems filter:
const filteredInsightsItems = insightsItems
  .filter(canAccess)
  .filter((item) => !isViewingAs || item.href !== "/insights/transactions")

// Bottom nav filtered:
const filteredBottomNavItems = bottomNavItems
  .filter(canAccess)
  .filter((item) => !isViewingAs || !viewAsHiddenHrefs.has(item.href))
```

### Mutation Blocking — ContactList Example

```typescript
// Pattern for all list pages with create buttons
const { isViewingAs } = useViewAs()

// In JSX:
{!isViewingAs && (
  <Button onClick={() => navigate("/contacts/new")}>
    <Plus className="h-4 w-4 mr-2" />
    Add Contact
  </Button>
)}
```

## Breadth Audit: Mutation Blocking Locations

Based on codebase inspection, the following locations require `isViewingAs` hiding:

| Page/Component | Mutation Type | Current Guard | Action Needed |
|----------------|--------------|---------------|---------------|
| `ContactList.tsx` | Create Contact | `canEdit` role check | Add `!isViewingAs &&` wrapper around Add Contact button |
| `ContactList.tsx` | Edit/Delete Contact | `canEdit` role check | Add `isViewingAs` to `canEdit` logic |
| `ContactDetail.tsx` | Edit/Delete Contact, Add Donation, Create Pledge, Add Task, Log Event | `isReadOnly` role check | Extend `isReadOnly` to also be true when `isViewingAs` |
| `DonationList.tsx` | Record Donation | None currently | Add `!isViewingAs` guard |
| `DonationDetail.tsx` | Edit/Delete Gift | `isReadOnly` role check | Extend `isReadOnly` to include `isViewingAs` |
| `PledgeList.tsx` | Create Pledge | None currently | Add `!isViewingAs` guard |
| `TaskList.tsx` | Create Task | None currently | Add `!isViewingAs` guard |
| `JournalList.tsx` | Create Journal (CreateJournalDialog trigger) | None currently | Add `!isViewingAs` guard |
| `JournalDetail.tsx` | Journal edit actions | Need to inspect | Add `!isViewingAs` guards |
| `GroupList.tsx` | Create Group, Delete Group | None currently | Add `!isViewingAs` guards |
| `PrayerList.tsx` | Add Prayer intention | None currently | Add `!isViewingAs` guard |
| `GoalPage.tsx` | Edit goal/journals | `isReadOnly = false` (TODO) | Change to `const isReadOnly = isViewingAs` |

**Observation:** Several pages (`DonationList`, `PledgeList`, `TaskList`, `JournalList`, `GroupList`, `PrayerList`) have NO existing read-only guards because they previously relied on route-level role guards (`requiredRole="missionary"`) to block supervisors/admins from creating. Under View As, an admin or supervisor is the authenticated user — they pass the `requiredRole="missionary"` route check. The frontend mutation blocking must therefore be applied at the button level.

**ContactDetail and DonationDetail** already have an `isReadOnly` pattern (checking supervisor/coach viewing a missionary's record). The clean approach is to expand `isReadOnly` to also be true when `isViewingAs` is true, making it a single boolean that governs all `!isReadOnly` render guards.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pass `user_id` query param for every request | X-View-As-User-Id header via interceptor | Phase 52 backend, Phase 53 frontend | Zero per-hook changes required |
| Dashboard local state for missionary selector | ViewAsContext shared state | Phase 53 | Picker promotion is the entry point for global View As |
| Role-based read-only (supervisor/coach check) | isViewingAs from ViewAsContext | Phase 53 | Unifies all read-only cases into one boolean |

**Deprecated/outdated:**
- `Dashboard.tsx` `selectedUserId` local state: replaced by `viewAsUserId` from `useViewAs()`
- `Dashboard.tsx` `isViewingOther` derived state: replaced by `isViewingAs` from `useViewAs()`
- `Dashboard.tsx` `useUsers()` call for admin missionary list: replaced by `useViewableUsers()`
- `Dashboard.tsx` `user.supervised_users` for supervisor list: replaced by `useViewableUsers()`
- `Dashboard.tsx` local read-only banner (lines 323-327): replaced by app-level `ViewAsBanner` in AppLayout

## Open Questions

1. **Should `useViewableUsers()` be in `hooks/useUsers.ts` or a new `hooks/useViewAs.ts`?**
   - What we know: Both locations are valid patterns in the codebase
   - What's unclear: Whether future View As hooks (none currently planned) would warrant a dedicated file
   - Recommendation: Add to `hooks/useUsers.ts` — it's a user-fetching hook. Only create `hooks/useViewAs.ts` if there are multiple View As hooks.

2. **Does the `markEventsSeen` call in Dashboard need protection?**
   - What we know: Dashboard.tsx line 93-99 calls `markEventsSeen()` only when `!isViewingOther`. After migration, this should use `!isViewingAs`.
   - What's unclear: Whether `markEventsSeen` is already gated by the middleware (it's a POST/write endpoint)
   - Recommendation: Backend will 403 it via ViewAsMiddleware, so frontend guard is UX only. Change `!isViewingOther` to `!isViewingAs`.

3. **Dashboard MPD data path for viewed missionary**
   - What we know: Dashboard currently derives `viewedMissionaryMpdData` from `mpdOverviewData.missionaries` for the admin case. This logic reads the selected user's MPD data from the admin overview.
   - What's unclear: Whether this path continues to work correctly in View As mode, or whether the backend MPD endpoint also respects the `X-View-As-User-Id` header.
   - Recommendation: The backend MPD endpoints were updated in Phase 52 to scope by `X-View-As-User-Id`. The existing `viewedMissionaryMpdData` fallback can be removed; `mpdData` will automatically scope to the viewed missionary. Verify during implementation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None — no frontend test framework configured in package.json |
| Config file | None — no vitest.config.ts, jest.config.ts, or similar detected |
| Quick run command | N/A — no automated frontend tests |
| Full suite command | `cd frontend && npm run build` (TypeScript compile as proxy for correctness) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIEWAS-01 | Admin sees dropdown of all missionaries | manual-only | — | N/A |
| VIEWAS-02 | Supervisor sees only assigned missionaries | manual-only | — | N/A |
| VIEWAS-03 | Banner appears with missionary name | manual-only | — | N/A |
| VIEWAS-04 | Exit button clears banner and state | manual-only | — | N/A |
| VIEWAS-05 | Data shown is from selected missionary | manual-only | — | N/A |
| VIEWAS-06 | Create/edit/delete buttons hidden | manual-only | — | N/A |
| VIEWAS-09 | Admin nav items hidden | manual-only | — | N/A |
| VIEWAS-10 | Session persists across navigation | manual-only | — | N/A |
| VIEWAS-11 | React Query cache cleared on user change | manual-only | — | N/A |
| — | TypeScript compile | smoke | `cd /home/matkukla/projects/DonorCRM/frontend && npm run build` | ✅ (build script) |

### Sampling Rate
- **Per task commit:** `cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit` (type-check only, faster than full build)
- **Per wave merge:** `cd /home/matkukla/projects/DonorCRM/frontend && npm run build`
- **Phase gate:** Full build green + manual browser verification before `/gsd:verify-work`

### Wave 0 Gaps
- None — no test files to create. This project has no frontend test infrastructure. Manual verification is the sole mechanism for VIEWAS requirements.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `frontend/src/api/client.ts`, `frontend/src/providers/AuthProvider.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/layout/AppLayout.tsx`, `frontend/src/App.tsx`, `frontend/src/api/users.ts`, `frontend/src/hooks/useUsers.ts`
- Backend source — `apps/users/views.py` ViewableUsersView confirmed response shape `[{ id, full_name }]`
- Backend source — `apps/users/serializers.py` ViewableUserSerializer confirmed fields: `id`, `full_name`
- `.planning/phases/53-view-as-frontend/53-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- `frontend/src/pages/contacts/ContactDetail.tsx`, `frontend/src/pages/donations/DonationDetail.tsx` — existing `isReadOnly` pattern confirmed by code inspection
- `frontend/src/providers/QueryProvider.tsx` — `queryClient` is module-level singleton, importable outside React tree

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, verified by package.json
- Architecture: HIGH — patterns derived directly from existing codebase code inspection
- Pitfalls: HIGH — all pitfalls derived from actual code in the repo (TODOs, existing guards, naming)
- Breadth audit: HIGH — all pages inspected directly; mutation locations confirmed

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable codebase; no external dependencies changing)
