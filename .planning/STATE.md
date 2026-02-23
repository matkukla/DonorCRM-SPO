# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.
**Current focus:** Phase 30 - Data Migration Backend Cutover (v2.0)

## Current Position

Milestone: v2.0 -- Import Revamp, Prayer Intentions & Dashboard Polish
Phase: 30 of 36 (Data Migration Backend Cutover)
Plan: 3 of 3 in current phase
Status: Phase Complete
Last activity: 2026-02-23 -- Completed 30-03 (Old App Cleanup)

Progress: [████████████████████████████████] 100% (3/3 plans in phase 30)

## Performance Metrics

**Velocity:**
- Total plans completed: 86 (24 v1.0 + 15 v1.1 + 18 v1.2 + 20 v1.3 + 9 v2.0)
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

Last session: 2026-02-23
Stopped at: Phase 31 context gathered
Resume file: .planning/phases/31-gift-recurring-gift-ui/31-CONTEXT.md
Resume: Plan Phase 31 (/gsd:plan-phase 31)

---

*Last updated: 2026-02-23 (Phase 31 context gathered)*
