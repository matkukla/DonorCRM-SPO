---
created: 2026-02-16T20:14:29.506Z
title: Add thorough filters for contacts page
area: ui
files:
  - frontend/src/pages/contacts/
---

## Problem

The contacts page currently lacks comprehensive filtering capabilities. Users (missionaries) need to quickly find and segment their contacts based on various criteria to manage donor relationships efficiently.

## Solution

Add filter controls to the contacts page that allow filtering by:
- Contact status/stage in pipeline
- Giving history (amount ranges, frequency)
- Last contact date / stalled contacts
- Tags/groups
- Pledge status (active, lapsed, none)
- Custom date ranges

TBD: Exact filter UI pattern (sidebar filters, dropdown filter bar, or modal). Should follow existing UI patterns in the codebase.
