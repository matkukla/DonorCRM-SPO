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

The system needs a "Mission Supervisor" role for leadership who oversee missionaries. Current roles are: STAFF, ADMIN, FINANCE, READ_ONLY (defined in `UserRole` TextChoices at `models.py:13-20`). A supervisor role would allow cross-missionary visibility and team management capabilities.

## Solution

- Add `SUPERVISOR = 'supervisor', 'Mission Supervisor'` to `UserRole` TextChoices
- Create migration for the new choice
- Add `is_supervisor` property on the User model
- Define supervisor-specific permissions (e.g., view all missionaries' contacts/journals, analytics access)
- Update serializers, admin, and frontend role selectors
- TBD: exact permission scope needs user specification
