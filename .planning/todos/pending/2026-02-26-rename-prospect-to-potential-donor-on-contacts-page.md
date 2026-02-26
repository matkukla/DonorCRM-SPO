---
created: 2026-02-26T14:02:08.441Z
title: Rename Prospect to Potential Donor on contacts page
area: ui
files:
  - frontend/src/pages/contacts/ContactList.tsx
---

## Problem

The contacts page status column shows "Prospect" but the user wants it renamed to "Potential Donor" to better reflect the domain language used by missionaries.

This is a display-only label change in the `statusLabels` map in ContactList.tsx (line ~32: `prospect: "Prospect"` → `prospect: "Potential Donor"`). The backend `status` field value stays `prospect` — only the frontend display label changes.

Also check filter dropdowns and any other places "Prospect" appears as a user-facing label.

## Solution

- Change `statusLabels.prospect` from `"Prospect"` to `"Potential Donor"` in ContactList.tsx
- Search for other occurrences of the "Prospect" display label across frontend components
- Backend model field value (`prospect`) stays unchanged
