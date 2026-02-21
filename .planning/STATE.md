# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.
**Current focus:** Phase 29 - RE Import Pipeline (Gifts & Recurring Gifts) (v2.0)

## Current Position

Milestone: v2.0 -- Import Revamp, Prayer Intentions & Dashboard Polish
Phase: 29 of 36 (RE Import Pipeline - Gifts & Recurring Gifts)
Plan: 1 of 2 in current phase
Status: In Progress
Last activity: 2026-02-20 -- Completed 29-01 (RE Gift Import)

Progress: [████████████████                ] 50% (1/2 plans in phase 29)

## Performance Metrics

**Velocity:**
- Total plans completed: 82 (24 v1.0 + 15 v1.1 + 18 v1.2 + 20 v1.3 + 5 v2.0)
- Average duration: ~3.8 minutes
- Total execution time: ~4.9 hours

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

Last session: 2026-02-20
Stopped at: Completed 29-01-PLAN.md (RE Gift Import)
Resume: Continue to 29-02 (RE Recurring Gift Import).

---

*Last updated: 2026-02-20 (29-01 complete)*
