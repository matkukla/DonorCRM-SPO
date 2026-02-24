# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.
**Current focus:** Phase 36 - Full Stack Audit (v2.0)

## Current Position

Milestone: v2.0 -- Import Revamp, Prayer Intentions & Dashboard Polish
Phase: 36 of 37 (Full Stack Audit)
Plan: 6 of 6 in current phase
Status: In Progress
Last activity: 2026-02-24 -- Completed 36-05 (UI/UX Dark Mode & Accessibility Audit)

Progress: [███████████████████████████░░░░░] 83% (5/6 plans in phase 36)

## Performance Metrics

**Velocity:**
- Total plans completed: 99 (24 v1.0 + 15 v1.1 + 18 v1.2 + 20 v1.3 + 22 v2.0)
- Average duration: ~3.9 minutes
- Total execution time: ~5.1 hours

**By Milestone:**

| Milestone | Plans | Total | Avg/Plan |
|-----------|-------|-------|----------|
| v1.0 (Phases 1-6) | 24 | 1.4 hours | 2.8 min |
| v1.1 (Phases 7-12) | 15 | 76m 43s | 5.1 min |
| v1.2 (Phases 13-19) | 18 | 108m 48s | 6.0 min |
| v1.3 (Phases 20-26) | 20 | ~75 min | ~3.8 min |
| Phase 27 P01 | 2min | 2 tasks | 5 files |
| Phase 27 P02 | 3min | 2 tasks | 14 files |
| Phase 28 P01 | 3min | 2 tasks | 8 files |
| Phase 28 P02 | 3min | 2 tasks | 4 files |
| Phase 29 P01 | 4min | 2 tasks | 7 files |
| Phase 29 P02 | 3min | 2 tasks | 4 files |
| Phase 30 P01 | 2min | 2 tasks | 4 files |
| Phase 30 P02 | 13min | 4 tasks | 16 files |
| Phase 30 P03 | 7min | 2 tasks | 51 files |
| Phase 31 P01 | 4min | 2 tasks | 9 files |
| Phase 31 P02 | 5min | 2 tasks | 5 files |
| Phase 31 P03 | 4min | 2 tasks | 7 files |
| Phase 32 P01 | 2min | 2 tasks | 4 files |
| Phase 32 P02 | 3min | 2 tasks | 10 files |
| Phase 32 P03 | 4min | 2 tasks | 14 files |
| Phase 33 P01 | 3min | 2 tasks | 14 files |
| Phase 33 P02 | 2min | 2 tasks | 4 files |
| Phase 33 P03 | 2min | 2 tasks | 4 files |
| Phase 34 P01 | 2min | 2 tasks | 4 files |
| Phase 36 P01 | 5min | 2 tasks | 5 files |
| Phase 36 P02 | 8min | 2 tasks | 7 files |
| Phase 36 P03 | 7min | 2 tasks | 4 files |
| Phase 36 P04 | 6min | 2 tasks | 15 files |
| Phase 36 P05 | 9min | 2 tasks | 32 files |

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

v2.0 key decision: REPLACE Donation/Pledge with Gift/RecurringGift (full data migration + 77+ file updates). This is NOT the dual-model additive approach from research -- it is a complete replacement requiring MIG-01 through MIG-05.
- [Phase 27]: Solicitor FK uses PROTECT delete to preserve credit history
- [Phase 27]: Money fields use PositiveBigIntegerField (cents) with Decimal amount_dollars property
- [Phase 27]: RecurringGift uses RE-compatible statuses (Active/Held/Completed/Cancelled/Terminated) and extended frequencies
- [Phase 27]: ImportBatch coexists with ImportRun (no replacement); SHA256 dedup per import_type
- [Phase 27]: PrayerIntention.contact is required (not nullable) per user decision
- [Phase 27]: Contact.external_constituent_id uses conditional UniqueConstraint (non-empty only)
- [Phase 28]: Solicitor.user changed from OneToOneField to ForeignKey (many-to-one)
- [Phase 28]: RE CSV header matching uses alias mapping dict for flexible column name support
- [Phase 28]: Ambiguous user name matches excluded from solicitor auto-linking
- [Phase 28]: Three-tier contact matching: constituent_id (global) > email (owner-scoped) > phone (owner-scoped)
- [Phase 28]: Merge-only contact updates: fill blank fields, never overwrite existing non-blank values
- [Phase 28]: Minimum data for new Contacts: require (first_name + last_name) or organization_name
- [Phase 29]: PrayerIntention.gift FK migrated to PrayerIntention.gifts M2M for multi-gift prayer dedup
- [Phase 29]: Gift amount from dedicated column (first row), NOT summed from credits
- [Phase 29]: Missing contacts skip entire gift group; unknown solicitors skip credit only
- [Phase 29]: Prayer dedup by (contact.id, normalized_text_lowercase) with 20-entry conservative stoplist
- [Phase 29]: Empty frequency defaults to Monthly; empty status defaults to Active; unknown values skip group
- [Phase 29]: RecurringGift import does NOT create prayer intentions (prayer text only on one-time gifts)
- [Phase 30]: Reuse DONATION_RECEIVED event type for Gift signals to avoid orphaning existing events
- [Phase 30]: Gift signal unconditionally sets needs_thank_you=True on create (no thanked field check)
- [Phase 30]: Old SPO import functions removed (returning 410 Gone) rather than ported to Gift model since RE import pipeline supersedes them
- [Phase 30]: Late pledge features return empty data gracefully rather than raising errors since RecurringGift has no is_late field
- [Phase 30]: Old property names (has_active_pledge, monthly_pledge_amount) kept as aliases during transition for backward compatibility
- [Phase 30]: EventType names (DONATION_RECEIVED, PLEDGE_CREATED) preserved as historical labels to avoid orphaning existing Event records
- [Phase 30]: Legacy import test files replaced with 410 Gone verification tests to maintain endpoint behavior coverage
- [Phase 31]: GiftDetailView returns GiftDetailSerializer for GET and GiftSerializer for PUT/PATCH
- [Phase 31]: Export CSV filenames keep legacy names: donations_{date}.csv and pledges_{date}.csv
- [Phase 31]: DonationDetailPanel uses named export plus default export wrapper for /donations/:id backward compatibility
- [Phase 31]: api/donations.ts and hooks/useDonations.ts kept as re-export compatibility shims
- [Phase 31]: api/pledges.ts and hooks/usePledges.ts kept as re-export compatibility layers
- [Phase 31]: NeedsAttention late pledges placeholder always shown (not conditional on count)
- [Phase 32]: No serializer class for ImportBatchListView -- hand-built dict for simplicity (only 12 fields)
- [Phase 32]: Import page sections stacked vertically with separators, not nested tabs
- [Phase 32]: Generic import section visible to all users (Coming soon placeholder)
- [Phase 33]: Today's Focus uses SHA256 hash of date+user.pk for deterministic daily rotation offset
- [Phase 33]: Mark Prayed optimistic update patches all cached prayer queries via setQueriesData
- [Phase 33]: Plain HTML table with amber styling for chapel aesthetic instead of DataTable component
- [Phase 33]: Contact picker uses inline search dropdown with useSearchContacts hook
- [Phase 33]: Answered note dialog with optional textarea before status change to answered
- [Phase 33]: Focus Mode uses useCallback for stable keyboard event listener dependencies
- [Phase 33]: Contact Prayer tab filters client-side since per-contact list is small
- [Phase 34]: PointerSensor only (no TouchSensor) -- desktop-only drag per user decision
- [Phase 34]: 8px activation constraint to prevent accidental drags near handle
- [Phase 34]: Main content flattened from left/right column divs to single grid for free reorder
- [Phase 36]: SQL CASE/WHEN frequency multipliers for RecurringGift aggregation (matches monthly_equivalent property)
- [Phase 36]: Contact.needs_thank_you and PrayerIntention.status indexes already present (no migration)
- [Phase 36]: 12 pages lazy-loaded via React.lazy with Suspense inside AppLayout
- [Phase 36]: Vite manualChunks splits recharts and dnd-kit into dedicated vendor chunks
- [Phase 36]: Shared get_safe_int_param/get_safe_year_param in apps/core/utils.py for all query param parsing
- [Phase 36]: Write routes guarded with requiredRole="staff" to exclude read_only users
- [Phase 36]: Import parser fields sanitized via _sanitize_field (null bytes stripped, 10k char truncation)
- [Phase 36]: All API error responses use {'detail'} format (DRF convention), not {'error'}
- [Phase 36]: Frontend re-export shims (api/donations.ts, api/pledges.ts, hooks/useDonations.ts, hooks/usePledges.ts) deleted -- zero imports found
- [Phase 36]: ActivityHeatmap uses light/dark color constant maps with useTheme hook (hex required by @uiw/react-heat-map)
- [Phase 36]: TableHead scope="col" added as default in shared shadcn component for global table accessibility

### Roadmap Evolution

- Phase 37 added: Security check

### Pending Todos

8 pending todo(s). See `.planning/todos/pending/`.

### Blockers/Concerns

- RE CSV real-world encoding behavior should be validated with production-exported files during Phase 28
- Solicitor name format ("Last, First" vs "First Last") is installation-specific -- confirm before Phase 28 ships
- Prayer intention deduplication boundary -- RESOLVED in Phase 29: dedup by (contact, normalized text) with M2M gift linking

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 5 | Remove analytics tab from left sidebar | 2026-02-16 | db2b504 | [5-remove-analytics-tab-from-left-sidebar-a](./quick/5-remove-analytics-tab-from-left-sidebar-a/) |
| 6 | Move Journals to sidebar & add action dialogs | 2026-02-16 | 34097d1 | [6-move-journal-tab-to-own-sidebar-tab-add-](./quick/6-move-journal-tab-to-own-sidebar-tab-add-/) |
| 7 | Implement light and dark mode toggle | 2026-02-16 | ccb4c67 | [7-implement-light-and-dark-mode-toggle](./quick/7-implement-light-and-dark-mode-toggle/) |

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 36-05-PLAN.md
Resume file: .planning/phases/36-full-stack-audit/36-05-SUMMARY.md
Resume: Continue with 36-06-PLAN.md

---

*Last updated: 2026-02-24 (Phase 36 Plan 05 complete)*
