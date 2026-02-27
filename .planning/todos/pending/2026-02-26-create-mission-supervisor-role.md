---
created: 2026-02-26T16:07:39.748Z
title: Create Mission Supervisor role
area: auth
files:
  - apps/users/models.py:13-20
  - apps/users/serializers.py
  - apps/users/admin.py
  - frontend/src/components/layout/Sidebar.tsx
---

## Problem

The system needs a "Mission Supervisor" role for leadership who oversee a subset of missionaries. Current roles are: STAFF, ADMIN, FINANCE, READ_ONLY (defined in `UserRole` TextChoices at `models.py:13-20`).

Per spec (`prompts/mission_supervisor.md`):
- Mission Supervisor has **same access as Admin** but can **only see missionaries assigned to them**
- Admins can see **all** staff members
- Both Supervisors and Admins should be able to **select a missionary and view their dashboard**

## Solution

- Add `SUPERVISOR = 'supervisor', 'Mission Supervisor'` to `UserRole` TextChoices + migration
- Add `is_supervisor` property on User model
- Add supervisor-missionary relationship (e.g., `supervisor` FK on User, or M2M `supervised_users`)
- Scope supervisor queries to only return their assigned missionaries' data (contacts, journals, donations, etc.)
- Add missionary selector UI for supervisors/admins to view a missionary's dashboard as them
- Admins retain full visibility across all staff; supervisors see only their assigned subset
- Update serializers, admin, permissions, and frontend role selectors
