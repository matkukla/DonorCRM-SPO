# Phase 27: Foundation Models - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Create all new data models (Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Solicitor, ImportBatch, PrayerIntention) and update the Contact model with new fields. Models and migrations only — no API endpoints, no import logic, no UI.

</domain>

<decisions>
## Implementation Decisions

### ImportBatch vs ImportRun
- ImportBatch should track ALL import types (RE, generic CSV, Smartsheet) — it is the universal import tracking model
- Whether to replace ImportRun or coexist: Claude's discretion based on codebase analysis
- Error storage pattern (separate table vs JSON field): Claude's discretion based on query patterns and data volume
- Summary storage (JSON field vs integer columns): Claude's discretion based on codebase patterns

### Relationship Constraints
- PrayerIntention requires a Contact FK — every prayer intention must be tied to a donor contact (not nullable)
- Gift requires a Contact FK (donor_contact) — every gift must link to a Contact; imports must match or create the contact first
- Whether GiftCredits are required on a Gift: Claude's discretion based on how RE data works
- Solicitor delete behavior on GiftCredits: Claude's discretion — pick the safest approach

### Field Behavior
- RecurringGift status values: Claude's discretion based on RE export data and existing Pledge statuses
- RecurringGift frequency format: Claude's discretion based on what RE exports provide
- Contact address field granularity: Claude's discretion based on RE constituent export format
- PrayerIntention status timestamps (answered_at, archived_at): Claude's discretion based on display usefulness

### Claude's Discretion
Claude has broad flexibility on this phase since it is pure infrastructure. The user locked two key constraints:
1. PrayerIntention.contact is required (not nullable)
2. Gift.donor_contact is required (not nullable)

All other field design, constraint, and structural decisions are delegated to Claude based on codebase patterns, RE export data format, and downstream phase needs.

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing codebase patterns (TimeStampedModel, UUID PKs, cents for money).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 27-foundation-models*
*Context gathered: 2026-02-20*
