# Phase 53: View As — Frontend - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Frontend implementation of View As mode: a new ViewAsContext that holds the selected missionary and propagates the X-View-As-User-Id header on every API request via the Axios interceptor, a persistent amber banner in the app layout with an Exit button, a missionary selector on the Dashboard that uses GET /api/users/viewable/, mutation blocking (hide create/edit/delete actions), admin-section hiding in the sidebar, React Query cache invalidation on user change, and sessionStorage persistence across navigation.

</domain>

<decisions>
## Implementation Decisions

### Context architecture
- New `ViewAsContext` — separate from `AuthProvider`, does not extend it
- Provider placement: inside `AuthProvider`, wrapping `QueryProvider` children (needs auth to read user role; needs queryClient to clear cache)
- Reads `sessionStorage` on mount to restore any in-progress View As session across browser refresh
- State shape: `{ viewAsUserId: string | null, viewAsUserName: string | null, setViewAsUser(id, name): void, exitViewAs(): void }`
- On `setViewAsUser()` or `exitViewAs()`: call `queryClient.clear()` (nuclear cache wipe, not invalidation) to prevent stale data from the previous user
- Session cleared only by clicking Exit or logging out — sessionStorage entry removed in both `exitViewAs()` and AuthProvider's `logout()`

### API header injection
- Axios request interceptor in `frontend/src/api/client.ts` reads `viewAsUserId` from sessionStorage directly (not from React context — interceptor lives outside the component tree)
- Adds `X-View-As-User-Id: <uuid>` header to every outbound request when a value is present
- All 40+ existing hooks pick this up automatically with zero per-hook changes

### Banner design & placement
- Rendered in `AppLayout` (top of main content area, above page content)
- Only shown when `viewAsUserId !== null`
- Visual style: amber/warning — `bg-amber-50 border-amber-200 text-amber-800` in light mode; `dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300`
- Icon: `AlertTriangle` or `Eye` from lucide-react (Claude's discretion on exact icon)
- Content: "Viewing [Full Name] · Read Only" with `[Exit]` button on the right
- Exit button: calls `exitViewAs()` → clears state + sessionStorage + React Query cache → stays on current route (no redirect)

### Selector placement & trigger
- Dashboard only — the existing Popover/Command missionary picker on the Dashboard is promoted from local state to calling `setViewAsUser()` on ViewAsContext
- Data source: `GET /api/users/viewable/` via new `useViewableUsers()` hook — replaces the current use of `useUsers()` (all users) and `user.supervised_users` (supervisor branch)
- Response shape from backend: `[{ id: string, full_name: string }]`
- "My Dashboard" option in the picker calls `exitViewAs()` (same effect as the banner Exit button)
- Selector only shown when `user?.role === "admin" || user?.role === "supervisor"` (unchanged from current condition)

### Mutation blocking (frontend)
- `useViewAs()` hook exposes `isViewingAs: boolean` derived from `viewAsUserId !== null`
- Create/edit/delete buttons and action menus: hidden (not disabled) when `isViewingAs` is true
- Applies to: Contact create/edit/delete, Donation/Gift create/edit/delete, Pledge/RecurringGift create/edit/delete, Task create/edit/delete, Journal create/edit/delete, Group create/edit/delete, Prayer intention actions
- Backend enforces 403 regardless — frontend hiding is a UX convenience, not the security layer

### Admin-section hiding in sidebar
- While `isViewingAs` is true, hide from Sidebar:
  - Import/Export nav item
  - Admin nav item (and all admin sub-routes)
  - Insights → Transactions item (`requiredRole: "admin"`)
- My Team nav item (visible to supervisor/coach) remains visible — supervisor can still see team structure
- Implementation: Sidebar reads `isViewingAs` from `useViewAs()` and applies additional filter on top of existing role checks

### Claude's Discretion
- Exact lucide-react icon for the banner (AlertTriangle vs Eye vs Info)
- Whether `useViewableUsers()` lives in `hooks/useUsers.ts` (extending it) or a new `hooks/useViewAs.ts`
- Whether the `ViewAsContext` file lives in `providers/` (alongside AuthProvider) or `contexts/`
- sessionStorage key name (e.g., `donorcrm_view_as_user_id`, `donorcrm_view_as_user_name`)

</decisions>

<specifics>
## Specific Ideas

- The Axios interceptor reads sessionStorage directly (not React context) because the interceptor is set up at module load time outside the React component tree. sessionStorage is the shared source of truth between the React context and the interceptor.
- Dashboard selector promoted: `setSelectedUserId(u.id)` → `setViewAsUser(u.id, u.full_name)`. "My Dashboard" option → `exitViewAs()`. The Popover/Command UI stays exactly as-is.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/api/client.ts` request interceptor (line ~44): Already injects `Authorization: Bearer` header — add `X-View-As-User-Id` in the same interceptor when sessionStorage value is present
- `frontend/src/providers/AuthProvider.tsx`: Pattern for new `ViewAsProvider` — same createContext/useContext/Provider structure; logout() here should also clear View As sessionStorage key
- `frontend/src/pages/Dashboard.tsx` lines 58–70: Existing `selectedUserId` state + `missionaryOptions` logic + Popover/Command selector — promote to ViewAsContext calls; replace `useUsers()` with `useViewableUsers()`
- `frontend/src/pages/Dashboard.tsx` lines 323–327: Existing read-only banner (muted style) — this gets replaced by the app-level banner in AppLayout; Dashboard-local banner removed
- `frontend/src/components/layout/Sidebar.tsx` `navItems` and `bottomNavItems` arrays: Add `isViewingAs` filter; `Import/Export` is in `bottomNavItems`, `Admin` is in `bottomNavItems` with `requiredRole: "admin"`
- `frontend/src/components/layout/AppLayout.tsx` or equivalent: Render `<ViewAsBanner />` component at top of main content column

### Established Patterns
- `useAuth()` from `AuthProvider`: Pattern for `useViewAs()` — identical structure, just reads different context
- `queryClient.clear()` already called in AuthProvider's `logout()` — same call in `exitViewAs()` and `setViewAsUser()`
- Read-only guard pattern (Phase 50): `const isReadOnly = user?.role === "supervisor" || user?.role === "admin"` → replace/extend with `const isReadOnly = isViewingAs` for View As mode
- Dark mode: all new UI needs `dark:` variants (established constraint across all phases)

### Integration Points
- `frontend/src/api/client.ts`: Add sessionStorage read + header injection in request interceptor
- `frontend/src/providers/ViewAsProvider.tsx` (new): ViewAsContext, ViewAsProvider, useViewAs()
- `frontend/src/App.tsx`: Wrap app with `<ViewAsProvider>` inside `<AuthProvider>` but outside `<QueryProvider>` children (or adjust nesting as needed)
- `frontend/src/api/users.ts`: Add `ViewableUser` type `{ id: string; full_name: string }` and `getViewableUsers()` function calling `/users/viewable/`
- `frontend/src/hooks/useUsers.ts` or new `useViewAs.ts`: Add `useViewableUsers()` hook
- `frontend/src/pages/Dashboard.tsx`: Replace local `selectedUserId` state with `useViewAs()`; replace `useUsers()` with `useViewableUsers()`; remove Dashboard-local read-only banner
- `frontend/src/components/layout/Sidebar.tsx`: Import `useViewAs()`, hide Import/Export + Admin + Transactions when `isViewingAs`
- `frontend/src/components/layout/AppLayout.tsx` (or layout wrapper): Render `<ViewAsBanner />` conditionally
- `frontend/src/components/layout/ViewAsBanner.tsx` (new): Amber banner with missionary name + Exit button

</code_context>

<deferred>
## Deferred Ideas

- Coach View As support (view their coached missionaries) — deferred to v2.4+ per VIEWAS-EX-01 in REQUIREMENTS.md
- Audit log of View As sessions — deferred to v2.4+ per VIEWAS-EX-02 in REQUIREMENTS.md
- Header-bar missionary picker (always-accessible selector) — user chose Dashboard-only entry point for now

</deferred>

---

*Phase: 53-view-as-frontend*
*Context gathered: 2026-03-16*
