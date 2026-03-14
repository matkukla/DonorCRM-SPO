# Deferred Items — Phase 50

## Pre-existing Build Errors (out of scope for 50-04)

Discovered during `npm run build` (tsc -b). These errors existed before any 50-04 changes and are unrelated to GoalPage.tsx.

1. `src/pages/admin/analytics/UserDetail.tsx(208,18)`: TS2741 — Property 'monthlyAverage' is missing in MPDStatsInlineProps (from phase 48 work)
2. `src/pages/contacts/ContactList.tsx(60,9)`: TS6133 — 'isAdmin' declared but never read
3. `src/pages/donations/DonationList.tsx(42,9)`: TS6133 — 'isAdmin' declared but never read
4. `src/pages/journals/components/StageCell.tsx(75,6)`: TS6133 — 'contactId' declared but never read
5. `src/pages/journals/components/StageCell.tsx(75,56)`: TS6133 — 'onCellClick' declared but never read

Note: `npx tsc --noEmit` passes clean. Only `tsc -b` (project references mode used by vite build) surfaces these.
