---
created: 2026-03-12T14:35:04.802Z
title: Implement supervisor and admin missionary impersonation view with read-only access
area: auth
files:
  - frontend/src/components/layout/Sidebar.tsx
  - frontend/src/pages/dashboard/Dashboard.tsx
  - apps/users/models.py
  - apps/users/views.py
---

## Problem

When a supervisor or admin selects a missionary to view, the experience should feel as if they have actually logged into that missionary's account — seeing their dashboard, contacts, journals, and data exactly as the missionary sees it. Currently there is no such impersonation/view-as UX.

Related todo: `2026-02-26-create-mission-supervisor-role.md` (covers role creation and scoping).

## Solution

Implement a **"View As" mode** for supervisors and admins:

1. **Missionary selector** — a dropdown or modal (in sidebar or top nav) that lets supervisors/admins pick a missionary from their assigned list (admins see all, supervisors see only their assigned missionaries).

2. **View-as banner** — when viewing as a missionary, show a persistent read-only banner at the top of the screen (e.g., "Viewing as John Smith — Read Only") with an "Exit" button to return to the supervisor's own view.

3. **Data scoping** — all API calls while in view-as mode should be scoped to the selected missionary's data. Options:
   - Pass `?as_user=<missionary_id>` query param and have backend validate the requestor has permission
   - Or fetch data from the missionary's perspective by filtering on their user ID

4. **Read-only enforcement** — all create/edit/delete actions should be disabled or hidden while in view-as mode. The UI should visually indicate read-only state (e.g., disabled buttons, greyed-out inputs, "View only" tooltips).

5. **Navigation** — sidebar and tabs should reflect the missionary's navigation (same as their own view), not the supervisor's admin controls.

**UX goal:** It should feel seamless, like you are inside the missionary's account but with a clear indicator that it's a supervised read-only view.
