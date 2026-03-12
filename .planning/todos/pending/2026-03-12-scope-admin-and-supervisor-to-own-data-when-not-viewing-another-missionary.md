---
created: 2026-03-12T14:40:13.207Z
title: Scope admin and supervisor to own data when not viewing another missionary
area: auth
files:
  - apps/contacts/views.py
  - apps/donations/views.py
  - apps/journals/views.py
  - apps/tasks/views.py
  - apps/users/models.py
---

## Problem

Admins and supervisors are missionary staff too — they have their own contacts, journals, donations, and tasks. Currently the admin role likely bypasses all `owner` filters in querysets (since admins need to see all data for oversight). But when an admin or supervisor is just doing their own missionary work (not overseeing others), they should only see and edit their own data — not everyone else's.

The desired behavior:
- **Default mode** (no "view-as" selected): admin and supervisor see ONLY their own data, same as a regular staff/missionary account
- **View-as mode** (selected a missionary to oversee): admin/supervisor see that missionary's data read-only (covered by related todo: `2026-03-12-implement-supervisor-and-admin-missionary-impersonation-view-with-read-only-access.md`)
- Admins retain access to the admin panel (user management, org settings) but their missionary data views are scoped to themselves by default

## Solution

Audit all backend queryset `get_queryset()` methods across apps (contacts, donations, journals, pledges, tasks, insights). Currently they likely branch on `user.role == 'admin'` to skip owner filtering. Change the logic so:

1. In default mode, ALL roles (including admin and supervisor) filter by `owner=request.user`
2. Only when a "view-as" session is active (e.g., a `?as_user=<id>` param or a session variable) do admin/supervisor get elevated access to another user's data

This pairs directly with the "view-as" impersonation todo. The two should be implemented together as they affect the same permission layer.

Also check frontend: if any components show org-wide data to admins by default (e.g., a global contact list), those need to be scoped to `owner=self` in default mode.
