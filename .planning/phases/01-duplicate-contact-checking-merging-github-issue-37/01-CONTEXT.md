# Phase 1: Duplicate Contact Checking + Merging (GitHub issue #37) - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement duplicate contact detection and merging so missionaries can keep their contact lists clean. Covers: creation-time duplicate warning, dedicated batch scan page, side-by-side review UI with confidence scoring, field-by-field merge with FK reassignment, dismissal tracking, and merge audit trail.

</domain>

<decisions>
## Implementation Decisions

### Duplicate Detection Strategy
- Detect duplicates both on contact creation (pre-save check) and via a dedicated scan page (/contacts/duplicates)
- Use PostgreSQL pg_trgm trigram similarity for fuzzy name matching — no external Python dependencies needed
- Similarity threshold of 0.4 for name matching (catches "John/Jon", "Smith/Smyth" without excessive false positives)
- Detection scoped to owner's contacts only — consistent with existing data isolation model

### Review & Dismissal UX
- Dedicated "/contacts/duplicates" page accessible from contact list, plus warning banner on create
- Side-by-side card comparison view — each field row shows both values, user picks which to keep
- 3-tier confidence scoring: High (exact email or phone match), Medium (name similarity >= 0.6), Low (name similarity >= 0.4)
- DismissedDuplicate model (contact_a, contact_b, dismissed_by, dismissed_at) for persistent dismissal tracking

### Merge Behavior
- Left/right "Keep this one" selection on comparison view — user picks survivor contact
- Field-by-field radio buttons for conflicting values — pre-selected to survivor's value, user can override per field
- Soft delete merged-away contact with merge audit log — mark as merged (not hard delete), store metadata for undo potential
- Automatic FK reassignment in single atomic transaction — all Gift, RecurringGift, Task, JournalContact FKs updated to survivor

### Creation-Time Warning Flow
- Duplicate check fires on form submission (before save) — API returns potential matches, frontend shows warning dialog
- Modal dialog listing top 3 matches with name, email, phone, confidence badge — "Possible duplicates found" with View/Merge/Create Anyway buttons
- Check triggers on first_name + last_name + email + phone — any non-empty field checked; email/phone exact match, name fuzzy
- User can bypass with "Create Anyway" — no forced merge at creation time

### Claude's Discretion
- Database migration strategy and model field choices
- API endpoint naming and URL structure
- Component composition and file organization
- pg_trgm extension installation approach

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Contact model (apps/contacts/models.py): first_name, last_name, email, phone, phone_secondary, organization_name fields — all relevant for matching
- ContactListSerializer / ContactDetailSerializer (apps/contacts/serializers.py) — can extend for duplicate pair responses
- useContacts hooks (frontend/src/hooks/useContacts.ts) — useCreateContact, useSearchContacts patterns to follow
- FilterBar component and useFilterParams hook — reusable for duplicate list filtering
- Side-by-side comparison patterns exist in import preview UI

### Established Patterns
- Owner-scoped querysets via get_visible_user_ids() for data isolation
- UUID primary keys on all models
- Django REST Framework serializers with separate List/Detail/Create variants
- React Query mutations with cache invalidation (invalidateQueries pattern)
- nuqs URL state management for filter persistence
- Radix UI + Tailwind CSS for all UI components
- TanStack Table for sortable data tables

### Integration Points
- apps/contacts/urls.py — new endpoints for duplicate check, scan, merge
- apps/contacts/views.py — new views for duplicate detection and merge operations
- frontend/src/pages/contacts/ — new DuplicateReview page, merge dialog
- frontend/src/pages/contacts/ContactForm.tsx — creation-time check integration
- Sidebar navigation — add "Duplicates" link under Contacts section
- Related models: Gift.donor_contact, RecurringGift.donor_contact, Task.contact, JournalContact.contact — all need FK reassignment during merge

</code_context>

<specifics>
## Specific Ideas

- GitHub issue #37 acceptance criteria are the source of truth for feature scope
- Existing unique constraint `unique_contact_email_per_owner` means email duplicates are already prevented — detection should focus on fuzzy name + phone matches
- external_id and external_constituent_id fields need merge handling (keep survivor's values, warn if both have different external IDs)
- Contact.groups (M2M) should be union-merged during contact merge
- Denormalized stats (total_given, gift_count, first/last_gift_date, last_gift_amount) need recalculation after merge

</specifics>

<deferred>
## Deferred Ideas

- Auto-merge suggestions (automatic merging without user confirmation) — too risky for initial implementation
- Cross-owner duplicate detection — would require visibility model changes
- Configurable per-user similarity thresholds — can add later if needed
- Undo merge feature — soft delete enables this but UI can come in a future phase

</deferred>
