# Quick Task 001: Fix Log Event 400 Error — Summary

## Status: COMPLETE

## Changes Made

### Backend: `apps/journals/serializers.py`
- `JournalStageEventSerializer` now accepts optional `contact_id` write-only field
- `journal_contact` made optional (requires either `journal_contact` or `contact_id`)
- `create()` auto-resolves `contact_id` to a `JournalContact` via `get_or_create`
- If user has no active journals, auto-creates "My Journal" with minimal goal_amount
- Eliminates the 400 "No active journals found" error entirely

### Backend: `apps/dashboard/services.py`
- Removed `in_journal` field and JournalContact batch lookup from `get_late_donations()`
- Simplified response — no longer checks journal membership per contact

### Frontend: `frontend/src/api/journals.ts`
- `StageEventCreate.journal_contact` made optional
- Added optional `contact_id` field

### Frontend: `frontend/src/api/dashboard.ts`
- Removed `in_journal: boolean` from `LateDonation` interface

### Frontend: `frontend/src/pages/journals/components/LogEventDialog.tsx`
- Removed "This contact is not enrolled in any journals" dead-end message
- `handleSubmit` sends `contact_id` when no `journal_contact` exists
- Submit button enabled when `contactId` is available (not just `journalContactId`)

### Frontend: `frontend/src/components/dashboard/LateDonations.tsx`
- Log button always shown (removed `donation.in_journal` condition)

### Frontend: `frontend/src/hooks/useJournals.ts`
- `useCreateStageEvent` onSuccess properly handles both `journal_contact` and `contact_id` paths
- Targeted invalidation for `contact_id` path: journal-events + journals queries
- Broader predicate invalidation as fallback for `journal_contact` path
- Added dashboard query invalidation

## Test Results
- 73 backend tests pass (journals + dashboard)
- TypeScript compiles clean (`npx tsc --noEmit`)

## Commit
`6df8e7f` — made journal more like donorelf
