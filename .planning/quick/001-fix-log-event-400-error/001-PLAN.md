# Quick Task 001: Fix Log Event 400 Error

## Goal
Fix the 400 "No active journals found. Create a journal first." error when logging events for contacts via the `contact_id` path. In DonorElf-style UX, every contact should be loggable without manual journal setup.

## Tasks

### Task 1: Auto-create default journal on stage event creation
**File:** `apps/journals/serializers.py`
- In `JournalStageEventSerializer.create()`, when `contact_id` is provided and user has no active journals, auto-create a "My Journal" instead of raising a 400 error
- Use `Decimal('0.01')` for goal_amount (minimum allowed by validator)

### Task 2: Fix cache invalidation for contact_id path
**File:** `frontend/src/hooks/useJournals.ts`
- In `useCreateStageEvent()` onSuccess handler, properly handle both `journal_contact` and `contact_id` paths
- Invalidate `["contacts", contact_id, "journal-events"]` and `["contacts", contact_id, "journals"]` when `contact_id` is set
- Invalidate `["dashboard"]` for journal activity widget refresh

### Task 3: Remove in_journal guard from Late Donations
**Files:** `apps/dashboard/services.py`, `frontend/src/api/dashboard.ts`, `frontend/src/components/dashboard/LateDonations.tsx`
- Remove `in_journal` field from backend response (no longer needed since all contacts can now log)
- Remove `in_journal` from `LateDonation` TypeScript interface
- Always show Log button (remove `donation.in_journal` condition)

## Acceptance Test
Clicking "Log" on any contact opens the Log Event dialog and allows submitting an event, regardless of whether the contact was previously enrolled in a journal or the user had any journals at all. No 400 error occurs.
