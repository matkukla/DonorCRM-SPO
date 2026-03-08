---
phase: 45-fix-backend-to-frontend-data-mapping-issues
plan: "03"
subsystem: frontend
tags: [contacts, organization_name, typescript, react]
dependency_graph:
  requires: [45-02]
  provides: [organization_name UI end-to-end]
  affects: [frontend/src/api/contacts.ts, frontend/src/pages/contacts/ContactForm.tsx, frontend/src/pages/contacts/ContactDetail.tsx]
tech_stack:
  added: []
  patterns: [conditional-render pattern for Contact Information card fields, org-name-aware validation (hasPersonName || hasOrgName)]
key_files:
  created: []
  modified:
    - frontend/src/api/contacts.ts
    - frontend/src/pages/contacts/ContactForm.tsx
    - frontend/src/pages/contacts/ContactDetail.tsx
decisions:
  - organization_name added to ContactListItem (not ContactDetail directly) so ContactDetail inherits via extends — single source of truth
  - First/last name required validation replaced with combined check: require at least one of first_name, last_name, or organization_name
  - Organization Name input placed as full-width row above First/Last Name grid in Basic Information card
  - Building2 lucide icon used for organization display in Contact Information card
metrics:
  duration: "~2 minutes"
  completed: "2026-03-07"
  tasks: 2
  files: 3
---

# Phase 45 Plan 03: Wire organization_name through React frontend Summary

Organization_name TypeScript interfaces, ContactForm input field with relaxed validation, and ContactDetail display row wired end-to-end.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add organization_name to TS interfaces and ContactForm | 2c299e6 | contacts.ts, ContactForm.tsx |
| 2 | Show organization_name in ContactDetail view | 6553164 | ContactDetail.tsx |

## What Was Built

### Task 1: TypeScript Interfaces + ContactForm (2c299e6)

**contacts.ts changes:**
- Added `organization_name?: string` to `ContactListItem` interface after `full_name`
- Added `organization_name?: string` to `ContactCreate` interface after `last_name`
- `ContactDetail` inherits `organization_name` automatically via `extends ContactListItem` — no duplication needed

**ContactForm.tsx changes:**
- Added `organization_name: ""` to initial `useState<ContactCreate>` object
- Added `organization_name: existingContact.organization_name || ""` in `useEffect` pre-population block (edit mode)
- Replaced individual `first_name required` + `last_name required` checks with combined org-aware validation: `if (!hasPersonName && !hasOrgName) { newErrors.first_name = "First name or organization name is required" }`
- Added Organization Name `<Input>` as a full-width labeled row above the First/Last Name two-column grid, with placeholder "Leave blank for individual contacts"

### Task 2: ContactDetail Display (6553164)

**ContactDetail.tsx changes:**
- Added `Building2` to the lucide-react import
- Added conditional `{contact.organization_name && (<div>...Building2 icon + organization_name text...</div>)}` block before the email block in the Contact Information card — follows the exact same pattern as email, phone, and address fields

## Verification

- `npx tsc --noEmit`: Zero errors in all modified files
- Backend tests: Pre-existing failures (7 tests) unrelated to this plan's changes — confirmed by stash test showing same failures before our changes

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] frontend/src/api/contacts.ts modified (organization_name in ContactListItem and ContactCreate)
- [x] frontend/src/pages/contacts/ContactForm.tsx modified (state, useEffect, validate, JSX)
- [x] frontend/src/pages/contacts/ContactDetail.tsx modified (Building2 import + conditional render)
- [x] Commit 2c299e6 exists: feat(45-03): add organization_name to TS interfaces and ContactForm
- [x] Commit 6553164 exists: feat(45-03): show organization_name in ContactDetail Contact Information card
