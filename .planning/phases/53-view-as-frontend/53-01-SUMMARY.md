---
phase: 53-view-as-frontend
plan: "01"
subsystem: frontend-state
tags: [view-as, react-context, axios-interceptor, session-storage, query-cache]
dependency_graph:
  requires: [Phase 52 View As backend middleware]
  provides: [ViewAsContext, ViewAsProvider, useViewAs, X-View-As-User-Id header, useViewableUsers]
  affects: [frontend/src/providers/*, frontend/src/api/*, frontend/src/hooks/useUsers.ts, frontend/src/App.tsx]
tech_stack:
  added: []
  patterns: [React Context with createContext/useContext, sessionStorage lazy initializer, Axios request interceptor extension, queryClient.clear() on session switch]
key_files:
  created:
    - frontend/src/providers/ViewAsProvider.tsx
  modified:
    - frontend/src/api/client.ts
    - frontend/src/api/users.ts
    - frontend/src/hooks/useUsers.ts
    - frontend/src/providers/AuthProvider.tsx
    - frontend/src/App.tsx
decisions:
  - "X-View-As-User-Id injected via sessionStorage string literal in interceptor (no import) to avoid circular dependency between client.ts and ViewAsProvider.tsx"
  - "VIEW_AS_USER_ID_KEY and VIEW_AS_USER_NAME_KEY exported as constants from ViewAsProvider.tsx so future callers can import rather than duplicate string literals"
  - "isViewingAs is a derived value (viewAsUserId !== null) in the context value object, not a separate useState — avoids state sync issues"
  - "ViewAsProvider nests inside AuthProvider and outside BrowserRouter per plan spec — Toaster moved inside ViewAsProvider to stay in tree"
  - "AuthProvider.logout() uses string literals for sessionStorage keys (matching ViewAsProvider constants) rather than importing to avoid cross-provider dependency"
metrics:
  duration: "3 minutes"
  completed_date: "2026-03-17"
  tasks_completed: 2
  files_changed: 6
requirements_covered: [VIEWAS-05, VIEWAS-10, VIEWAS-11]
---

# Phase 53 Plan 01: View As Infrastructure Summary

**One-liner:** ViewAsContext with sessionStorage persistence, Axios X-View-As-User-Id header injection, and viewable-users API/hook — complete foundation for View As feature.

## What Was Built

The View As state infrastructure layer: a React context provider that persists session state in sessionStorage, an Axios interceptor extension that injects the scoping header on every outbound request, and the API client and React Query hook needed to fetch the list of viewable missionaries.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create ViewAsProvider with sessionStorage sync and queryClient.clear() | e4018cf | frontend/src/providers/ViewAsProvider.tsx |
| 2 | Extend Axios interceptor, API client, useViewableUsers hook, App.tsx, AuthProvider logout | e3d9938 | frontend/src/api/client.ts, users.ts, hooks/useUsers.ts, providers/AuthProvider.tsx, App.tsx |

## Verification Results

- `npx tsc --noEmit` passes with zero errors
- ViewAsProvider.tsx exports: `ViewAsProvider`, `useViewAs`, `VIEW_AS_USER_ID_KEY`, `VIEW_AS_USER_NAME_KEY`
- client.ts interceptor reads `sessionStorage.getItem("donorcrm_view_as_user_id")` and sets `X-View-As-User-Id` header
- users.ts exports `ViewableUser` interface and `getViewableUsers()` calling `/users/viewable/`
- useUsers.ts exports `useViewableUsers()` using queryKey `["viewable-users"]`
- AuthProvider `logout()` removes both View As sessionStorage keys before `queryClient.clear()`
- App.tsx wraps `BrowserRouter` (and `Toaster`) with `ViewAsProvider` inside `AuthProvider`

## Decisions Made

1. **String literal in interceptor** — Used `"donorcrm_view_as_user_id"` directly in `client.ts` rather than importing `VIEW_AS_USER_ID_KEY` from ViewAsProvider.tsx to avoid circular dependency (interceptor lives outside React tree).

2. **Exported key constants** — `VIEW_AS_USER_ID_KEY` and `VIEW_AS_USER_NAME_KEY` exported from ViewAsProvider.tsx so future plan components can import them rather than duplicating strings.

3. **isViewingAs as derived value** — Computed as `viewAsUserId !== null` in the context value object rather than separate `useState` to eliminate state sync bugs.

4. **Toaster moved inside ViewAsProvider** — Per plan spec, Toaster was inside AuthProvider; moved inside ViewAsProvider to keep it in the correct subtree.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- `frontend/src/providers/ViewAsProvider.tsx` — FOUND
- `frontend/src/api/client.ts` (modified) — FOUND
- `frontend/src/api/users.ts` (modified) — FOUND
- `frontend/src/hooks/useUsers.ts` (modified) — FOUND
- `frontend/src/providers/AuthProvider.tsx` (modified) — FOUND
- `frontend/src/App.tsx` (modified) — FOUND
- Commit e4018cf — FOUND
- Commit e3d9938 — FOUND
