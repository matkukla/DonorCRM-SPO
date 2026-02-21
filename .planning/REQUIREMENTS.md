# Requirements: DonorCRM

**Defined:** 2026-02-20
**Core Value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.

## v2.0 Requirements

Requirements for v2.0 milestone: Import Revamp, Prayer Intentions & Dashboard Polish.

### Data Models

- [ ] **MODEL-01**: Gift model replaces Donation with externalGiftId, donorContact FK, solicitor credit support, and cents-based amounts
- [ ] **MODEL-02**: GiftCredit junction model links Gift to Solicitor with per-credit amount (many-to-many with amounts)
- [ ] **MODEL-03**: RecurringGift model replaces Pledge with installment fields, status tracking, and externalGiftId
- [ ] **MODEL-04**: RecurringGiftCredit junction model links RecurringGift to Solicitor
- [ ] **MODEL-05**: Solicitor model with normalized name matching and auto-linking to User accounts
- [ ] **MODEL-06**: ImportBatch model with SHA256 file deduplication, status tracking, and summary JSON
- [ ] **MODEL-07**: PrayerIntention model tied to Contact with title, description, status (active/answered/archived), and optional Gift link
- [ ] **MODEL-08**: Contact model updated with externalConstituentId, organizationName, and address fields

### Import Pipeline

- [x] **IMP-01**: RE Constituent import creates/updates Contacts with externalConstituentId matching, email/phone fallback, merge-only updates
- [x] **IMP-02**: RE Solicitor import creates Solicitor records with normalized name dedup and auto-link to User accounts
- [ ] **IMP-03**: RE Gift import with multi-row grouping by Gift ID, GiftCredit creation per solicitor, and Contact linking
- [ ] **IMP-04**: RE Recurring Gift import with same grouping pattern, installment fields, and status tracking
- [x] **IMP-05**: SHA256 idempotency -- re-uploading same file returns cached result without reprocessing
- [x] **IMP-06**: Row-level error collection -- errors don't stop processing, final report shows all errors with row numbers
- [x] **IMP-07**: Windows-1252 encoding detection with cascading fallback (UTF-8-sig, UTF-8, Windows-1252)
- [ ] **IMP-08**: Generic CSV import for contacts with matching and dedup options
- [ ] **IMP-09**: Generic CSV import for donations with contact linking and stat recalculation
- [ ] **IMP-10**: Prayer intention auto-creation from RE gift description field during gift import

### Data Migration

- [ ] **MIG-01**: Migrate existing Donation records to Gift model with field mapping and UUID preservation
- [ ] **MIG-02**: Migrate existing Pledge records to RecurringGift model
- [ ] **MIG-03**: Update Contact stats (totalGiven, lastGiftDate, lastGiftAmount) to query Gift model
- [ ] **MIG-04**: Remove old Donation and Pledge models after migration verification
- [ ] **MIG-05**: Update all backend services (dashboard, insights, analytics) to use Gift/RecurringGift

### Import UI

- [ ] **UI-IMP-01**: Import/Export page accessible from main sidebar (not admin-only)
- [ ] **UI-IMP-02**: RE import section with 4 tabs (Constituent, Solicitor, Gift, Recurring Gift)
- [ ] **UI-IMP-03**: Drag-and-drop file upload with file name/size display and import button
- [ ] **UI-IMP-04**: Import result display with success/error/already-processed banners and expandable error list
- [ ] **UI-IMP-05**: CSV header reference showing required and optional headers per import type
- [ ] **UI-IMP-06**: Import history list with status icons and past ImportBatch records
- [ ] **UI-IMP-07**: Generic CSV import section for contacts and donations
- [ ] **UI-IMP-08**: Remove import functionality from admin analytics page

### Gift/Recurring Gift UI

- [ ] **UI-GIFT-01**: Rename "Donations" to "Gifts" across sidebar, page titles, and components
- [ ] **UI-GIFT-02**: Rename "Pledges" to "Recurring Gifts" across sidebar, page titles, and components
- [ ] **UI-GIFT-03**: Gifts list page with existing filters updated for Gift model fields
- [ ] **UI-GIFT-04**: Recurring Gifts list page with existing filters updated for RecurringGift model fields
- [ ] **UI-GIFT-05**: Gift detail view showing solicitor credit breakdown (which missionaries are credited)
- [ ] **UI-GIFT-06**: Contact detail Gifts tab showing gifts linked to that contact
- [ ] **UI-GIFT-07**: Update CSV exports to use Gift/RecurringGift data

### Prayer Intentions

- [ ] **PRAY-01**: Prayer Intentions page accessible from main sidebar with list of all intentions
- [ ] **PRAY-02**: User can create, edit, and delete prayer intentions manually
- [ ] **PRAY-03**: Prayer intention status tracking (active, answered, archived)
- [ ] **PRAY-04**: Prayer tab on Contact detail page showing intentions for that contact
- [ ] **PRAY-05**: Prayer intentions created automatically from RE gift import descriptions are linked to the donor contact

### Dashboard

- [ ] **DASH-01**: Dashboard tiles can be rearranged via drag-and-drop (session-only, resets on refresh)
- [ ] **DASH-02**: Dashboard summary cards and charts updated to query Gift/RecurringGift instead of Donation/Pledge

### Audit

- [ ] **AUDIT-01**: Full-stack audit covering security (OWASP top 10, auth, permission scoping), performance (N+1 queries, missing indexes, bundle size), code quality (dead code, type safety, inconsistent patterns), UI/UX (accessibility, dark mode, responsive), and API consistency across all v2.0 code paths

## Future Requirements

Deferred to future releases.

### From v2.0 Planned Items
- **JRN-V2-02**: Real-Time Collaboration
- **JRN-V2-03**: Communication Integration
- **JRN-V2-04**: Mobile Native App
- **JRN-V2-05**: Bulk Journal Operations
- **JRN-V2-06**: Custom Stage Definitions
- **JRN-V2-07**: AI Suggestions
- Configurable alert thresholds (per coach)
- Email digest reports for coaches
- Saved column mapping templates for RE imports
- Import undo/rollback

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated Smartsheet API integration | Manual upload sufficient; API adds OAuth complexity |
| Real-time import progress (WebSocket) | Imports complete in <2s for typical data; overkill |
| Drag-drop column mapping UI | Dropdown selects sufficient; drag-drop adds accessibility complexity |
| Multi-sheet Excel import | RE exports are single-sheet; complexity not justified |
| Saved filter views (backend) | URL params already bookmarkable and shareable |
| Advanced filter query builder | Stacked AND covers 95% of use cases |
| Dashboard tile persistence (backend) | Session-only rearrangement sufficient for v2.0 |
| Prayer intention reminders/notifications | No notification infrastructure yet |
| Import CSV for RE types (admin builds mapping) | RE headers are fixed; no mapping needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MODEL-01 | Phase 27 | Pending |
| MODEL-02 | Phase 27 | Pending |
| MODEL-03 | Phase 27 | Pending |
| MODEL-04 | Phase 27 | Pending |
| MODEL-05 | Phase 27 | Pending |
| MODEL-06 | Phase 27 | Pending |
| MODEL-07 | Phase 27 | Pending |
| MODEL-08 | Phase 27 | Pending |
| IMP-01 | Phase 28 | Complete |
| IMP-02 | Phase 28 | Complete |
| IMP-03 | Phase 29 | Pending |
| IMP-04 | Phase 29 | Pending |
| IMP-05 | Phase 28 | Complete |
| IMP-06 | Phase 28 | Complete |
| IMP-07 | Phase 28 | Complete |
| IMP-08 | Phase 35 | Pending |
| IMP-09 | Phase 35 | Pending |
| IMP-10 | Phase 29 | Pending |
| MIG-01 | Phase 30 | Pending |
| MIG-02 | Phase 30 | Pending |
| MIG-03 | Phase 30 | Pending |
| MIG-04 | Phase 30 | Pending |
| MIG-05 | Phase 30 | Pending |
| UI-IMP-01 | Phase 32 | Pending |
| UI-IMP-02 | Phase 32 | Pending |
| UI-IMP-03 | Phase 32 | Pending |
| UI-IMP-04 | Phase 32 | Pending |
| UI-IMP-05 | Phase 32 | Pending |
| UI-IMP-06 | Phase 32 | Pending |
| UI-IMP-07 | Phase 32 | Pending |
| UI-IMP-08 | Phase 32 | Pending |
| UI-GIFT-01 | Phase 31 | Pending |
| UI-GIFT-02 | Phase 31 | Pending |
| UI-GIFT-03 | Phase 31 | Pending |
| UI-GIFT-04 | Phase 31 | Pending |
| UI-GIFT-05 | Phase 31 | Pending |
| UI-GIFT-06 | Phase 31 | Pending |
| UI-GIFT-07 | Phase 31 | Pending |
| PRAY-01 | Phase 33 | Pending |
| PRAY-02 | Phase 33 | Pending |
| PRAY-03 | Phase 33 | Pending |
| PRAY-04 | Phase 33 | Pending |
| PRAY-05 | Phase 33 | Pending |
| DASH-01 | Phase 34 | Pending |
| DASH-02 | Phase 31 | Pending |
| AUDIT-01 | Phase 36 | Pending |

**Coverage:**
- v2.0 requirements: 46 total
- Mapped to phases: 46
- Unmapped: 0

---
*Requirements defined: 2026-02-20*
*Last updated: 2026-02-20 after roadmap creation (all requirements mapped to phases)*
