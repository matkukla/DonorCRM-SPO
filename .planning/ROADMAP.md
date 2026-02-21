# Roadmap: DonorCRM

## Milestones

- ✅ **v1.0 Journal Feature** -- Phases 1-6 (shipped 2026-01-29)
- ✅ **v1.1 CSV Import** -- Phases 7-12 (shipped 2026-02-04)
- ✅ **v1.2 Admin Analytics Dashboard** -- Phases 13-19 (shipped 2026-02-16)
- ✅ **v1.3 Smartsheet Import, Filters & Polish** -- Phases 20-26 (shipped 2026-02-19)
- **v2.0 Import Revamp, Prayer Intentions & Dashboard Polish** -- Phases 27-35 (in progress)

## Phases

<details>
<summary>v1.0 Journal Feature (Phases 1-6) -- SHIPPED 2026-01-29</summary>

See milestones/v1.0-ROADMAP.md for complete phase details.

**Key Features:**
- Journal CRUD with owner-scoped visibility
- 6-stage pipeline with decision tracking
- Interactive grid UI with analytics charts
- Contact detail integration and task system

**Scope:** 19 requirements, 6 phases, 24 plans

</details>

<details>
<summary>v1.1 CSV Import (Phases 7-12) -- SHIPPED 2026-02-04</summary>

See milestones/v1.1-ROADMAP.md for complete phase details.

**Key Features:**
- Import Center UI for 4 CSV types
- Fund model, external IDs, import audit trail

**Scope:** 19 requirements, 6 phases, 15 plans

</details>

<details>
<summary>v1.2 Admin Analytics Dashboard (Phases 13-19) -- SHIPPED 2026-02-16</summary>

See milestones/v1.2-ROADMAP.md for complete phase details.

**Key Features:**
- Dashboard Overview with summary cards, trend charts, conversion funnel
- Stalled Contacts monitoring, User Detail pages
- Interactive drill-down, heatmap, time period comparison

**Scope:** 26 requirements, 7 phases, 18 plans

</details>

<details>
<summary>v1.3 Smartsheet Import, Filters & Polish (Phases 20-26) -- SHIPPED 2026-02-19</summary>

See milestones/v1.3-ROADMAP.md for complete phase details.

**Key Features:**
- Security fixes (permission bypass, N+1 queries, file size limits, route guards)
- Dark mode color audit, Error Boundary, CSV sanitization
- Reusable filter system with URL persistence, presets, badges, filtered CSV export
- Per-page filters on all 5 list pages with admin owner dropdowns
- Smartsheet MPD import (file upload, format detection, name matching, financial snapshots)
- MPD data on admin dashboard and missionary personal views

**Scope:** 35 requirements, 7 phases, 20 plans, 37 tasks

</details>

### v2.0 Import Revamp, Prayer Intentions & Dashboard Polish (In Progress)

**Milestone Goal:** Replace the existing Donation/Pledge system with Gift/RecurringGift models, build a Raiser's Edge CSV import pipeline, add prayer intentions tracking, and make dashboard tiles draggable.

- [x] **Phase 27: Foundation Models** - Create Gift, RecurringGift, Solicitor, GiftCredit, ImportBatch, and PrayerIntention models with migrations (completed 2026-02-20)
- [x] **Phase 28: RE Import Pipeline (Constituents & Solicitors)** - Build shared RE utilities and Constituent/Solicitor importers with encoding detection and SHA256 dedup (completed 2026-02-21)
- [x] **Phase 29: RE Import Pipeline (Gifts & Recurring Gifts)** - Build Gift/Recurring Gift importers with multi-row grouping and prayer auto-creation (completed 2026-02-21)
- [ ] **Phase 30: Data Migration & Backend Cutover** - Migrate Donation to Gift, Pledge to RecurringGift, update all backend services to use new models
- [ ] **Phase 31: Gift & Recurring Gift UI** - Rename Donations to Gifts and Pledges to Recurring Gifts across all frontend pages, filters, and exports
- [ ] **Phase 32: Import UI** - Build Import/Export page with RE import tabs, generic CSV import, drag-and-drop upload, and import history
- [ ] **Phase 33: Prayer Intentions** - Build Prayer Intentions page, CRUD API, contact detail tab, and status tracking
- [ ] **Phase 34: Dashboard Polish** - Draggable dashboard tiles and dashboard queries updated to Gift/RecurringGift
- [ ] **Phase 35: Generic CSV Import** - Generic CSV import for contacts and donations with matching and dedup
- [ ] **Phase 36: Full-Stack Audit** - Comprehensive security, performance, code quality, UI/UX, and API audit across all v2.0 code paths

## Phase Details

### Phase 27: Foundation Models
**Goal**: All new data models exist in the database so that import pipeline, migration, and UI phases have tables to write to
**Depends on**: Nothing (first phase of v2.0)
**Requirements**: MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05, MODEL-06, MODEL-07, MODEL-08
**Success Criteria** (what must be TRUE):
  1. Gift model exists with external_gift_id, donor_contact FK, fund FK, amount_cents, gift_date, description, and timestamps
  2. GiftCredit and RecurringGiftCredit junction models exist linking gifts to solicitors with per-credit amount_cents
  3. RecurringGift model exists with installment fields (frequency, start_date, end_date), status tracking, and external_gift_id
  4. Solicitor model exists with normalized_name field, optional OneToOneField to User, and external_solicitor_id
  5. ImportBatch model exists with SHA256 hash field (unique on import_type + sha256), status, summary JSON, and row counts
  6. PrayerIntention model exists with contact FK, title, description, status (active/answered/archived), and optional gift FK
  7. Contact model has new fields: external_constituent_id, organization_name, and address fields
**Plans**: 2 plans
Plans:
- [x] 27-01-PLAN.md — Create gifts app with Solicitor, Gift, GiftCredit, RecurringGift, RecurringGiftCredit models and admin
- [ ] 27-02-PLAN.md — Create prayers app, ImportBatch model, Contact field updates, and run all migrations

### Phase 28: RE Import Pipeline (Constituents & Solicitors)
**Goal**: Admins can import RE Constituent and Solicitor CSV files with correct encoding handling, SHA256 dedup, and row-level error reporting
**Depends on**: Phase 27
**Requirements**: IMP-01, IMP-02, IMP-05, IMP-06, IMP-07
**Success Criteria** (what must be TRUE):
  1. Uploading an RE Constituent CSV creates or updates Contact records matched by external_constituent_id, with email/phone fallback and merge-only updates (never overwrites existing data with blanks)
  2. Uploading an RE Solicitor CSV creates Solicitor records with normalized names and auto-links to User accounts when an exact name match exists
  3. Re-uploading the same file returns the cached ImportBatch result without reprocessing (SHA256 dedup works)
  4. Errors on individual rows do not stop processing -- the final result shows all errors with row numbers
  5. Files with Windows-1252 encoding (smart quotes, accented names) are handled transparently via cascading decode
**Plans**: 2 plans
Plans:
- [ ] 28-01-PLAN.md — Solicitor FK fix, shared RE utilities (encoding, dedup, errors), and Solicitor import pipeline
- [ ] 28-02-PLAN.md — Constituent import pipeline with match hierarchy, merge-only updates, and management command

### Phase 29: RE Import Pipeline (Gifts & Recurring Gifts)
**Goal**: Admins can import RE Gift and Recurring Gift CSV files with correct multi-row grouping, credit splitting, and prayer intention auto-creation
**Depends on**: Phase 28
**Requirements**: IMP-03, IMP-04, IMP-10
**Success Criteria** (what must be TRUE):
  1. Uploading an RE Gift CSV groups rows by Gift ID before creating records -- one Gift record with multiple GiftCredit records per solicitor, not duplicate gifts
  2. Uploading an RE Recurring Gift CSV creates RecurringGift records with installment fields and status tracking, using the same grouping pattern
  3. Gift descriptions that contain prayer-relevant text automatically create PrayerIntention records linked to the donor contact
  4. All gift/recurring gift imports respect the same SHA256 dedup, row-level error collection, and encoding detection from Phase 28
**Plans**: 2 plans
Plans:
- [ ] 29-01-PLAN.md — PrayerIntention M2M migration, RE Gift import service with multi-row grouping, prayer auto-creation, CLI + API
- [ ] 29-02-PLAN.md — RE Recurring Gift import service with frequency/status mapping, CLI + API

### Phase 30: Data Migration & Backend Cutover
**Goal**: All existing Donation and Pledge data is migrated to Gift and RecurringGift models, and all backend services query exclusively from the new models
**Depends on**: Phase 27
**Requirements**: MIG-01, MIG-02, MIG-03, MIG-04, MIG-05
**Success Criteria** (what must be TRUE):
  1. Every existing Donation record has a corresponding Gift record with correct field mapping and preserved UUIDs
  2. Every existing Pledge record has a corresponding RecurringGift record with correct field mapping
  3. Contact stats (total_given, last_gift_date, last_gift_amount, gift_count) are calculated from the Gift model and match previous values
  4. Dashboard services, insights services, and analytics endpoints all query Gift/RecurringGift instead of Donation/Pledge
  5. Old Donation and Pledge models are removed from the codebase after migration verification
**Plans**: TBD

### Phase 31: Gift & Recurring Gift UI
**Goal**: Users see "Gifts" and "Recurring Gifts" everywhere that previously said "Donations" and "Pledges", with all list pages, filters, detail views, and exports working against the new models
**Depends on**: Phase 30
**Requirements**: UI-GIFT-01, UI-GIFT-02, UI-GIFT-03, UI-GIFT-04, UI-GIFT-05, UI-GIFT-06, UI-GIFT-07, DASH-02
**Success Criteria** (what must be TRUE):
  1. Sidebar, page titles, breadcrumbs, and all visible text say "Gifts" instead of "Donations" and "Recurring Gifts" instead of "Pledges"
  2. Gifts list page works with all existing filters (date range, amount, contact, owner) querying the Gift model
  3. Recurring Gifts list page works with all existing filters querying the RecurringGift model
  4. Gift detail view shows solicitor credit breakdown (which missionaries are credited and for how much)
  5. Contact detail page has a Gifts tab showing all gifts linked to that contact
  6. CSV exports produce Gift and RecurringGift data (not old Donation/Pledge data)
  7. Dashboard summary cards and charts display data from Gift/RecurringGift models
**Plans**: TBD

### Phase 32: Import UI
**Goal**: Users can access a unified Import/Export page from the main sidebar to upload RE CSVs, view import history, and run generic imports
**Depends on**: Phase 29
**Requirements**: UI-IMP-01, UI-IMP-02, UI-IMP-03, UI-IMP-04, UI-IMP-05, UI-IMP-06, UI-IMP-07, UI-IMP-08
**Success Criteria** (what must be TRUE):
  1. Import/Export page is accessible from the main sidebar (not buried in admin settings)
  2. RE Import section has 4 tabs (Constituent, Solicitor, Gift, Recurring Gift) with drag-and-drop file upload per tab
  3. After import, user sees success/error/already-processed banners with expandable error details showing row numbers
  4. Each import tab shows a reference of required and optional CSV headers
  5. Import history section lists past ImportBatch records with status icons and summary counts
  6. Generic CSV import section exists for contacts and donations (backend wired in Phase 35)
  7. Old import functionality is removed from the admin analytics page
**Plans**: TBD

### Phase 33: Prayer Intentions
**Goal**: Users can track prayer intentions for their contacts, with a dedicated page and contact-level visibility
**Depends on**: Phase 27, Phase 29 (for auto-creation from imports)
**Requirements**: PRAY-01, PRAY-02, PRAY-03, PRAY-04, PRAY-05
**Success Criteria** (what must be TRUE):
  1. Prayer Intentions page is accessible from the main sidebar and shows all of the user's prayer intentions
  2. User can create, edit, and delete prayer intentions manually with title, description, and contact association
  3. Prayer intentions have status tracking: active intentions are visually distinct from answered and archived ones
  4. Contact detail page has a Prayer tab showing all intentions for that contact
  5. Prayer intentions auto-created from RE gift imports appear linked to the correct donor contact
**Plans**: TBD

### Phase 34: Dashboard Polish
**Goal**: Dashboard tiles can be rearranged by dragging, providing a customizable view of missionary data
**Depends on**: Phase 31 (dashboard must already query new models)
**Requirements**: DASH-01
**Success Criteria** (what must be TRUE):
  1. User can drag and drop dashboard tiles to rearrange their layout
  2. Tile order persists for the duration of the browser session but resets on page refresh
  3. Drag interaction provides visual feedback (ghost overlay, drop indicators)
**Plans**: TBD

### Phase 35: Generic CSV Import
**Goal**: Users can import contacts and donations via generic CSV files (not just RE format) with matching and dedup
**Depends on**: Phase 32 (Import UI must exist)
**Requirements**: IMP-08, IMP-09
**Success Criteria** (what must be TRUE):
  1. User can upload a generic CSV of contacts with configurable matching (by name, email, or external ID) and dedup options
  2. User can upload a generic CSV of donations that links to existing contacts and triggers stat recalculation
  3. Both generic import types use the same row-level error reporting and result display as RE imports
**Plans**: TBD

### Phase 36: Full-Stack Audit
**Goal**: All v2.0 code paths are audited for security vulnerabilities, performance bottlenecks, code quality issues, UI/UX gaps, and API inconsistencies
**Depends on**: Phase 35 (all features must be implemented before audit)
**Requirements**: AUDIT-01
**Success Criteria** (what must be TRUE):
  1. Security audit completed: OWASP top 10 reviewed, all permission scoping verified on new endpoints, input validation checked on all import parsers
  2. Performance audit completed: no N+1 queries in new code paths, missing indexes identified and added, frontend bundle impact assessed
  3. Code quality audit completed: dead code removed, inconsistent patterns unified, type safety gaps closed
  4. UI/UX audit completed: dark mode coverage verified on all new pages, accessibility checked (WCAG 4.5:1 contrast), responsive behavior verified
  5. API consistency audit completed: error response formats consistent, endpoint naming follows conventions, serializer field naming aligned
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 27 -> 28 -> 29 -> 30 -> 31 -> 32 -> 33 -> 34 -> 35 -> 36
Note: Phase 30 depends on Phase 27 only (not 28/29), so it could run after 27. However, running it after 29 allows import-created data to be tested alongside migrated data. Phase 33 can begin after Phase 29 completes.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6 | v1.0 | 24/24 | Complete | 2026-01-29 |
| 7-12 | v1.1 | 15/15 | Complete | 2026-02-04 |
| 13-19 | v1.2 | 18/18 | Complete | 2026-02-16 |
| 20-26 | v1.3 | 20/20 | Complete | 2026-02-19 |
| 27. Foundation Models | 2/2 | Complete    | 2026-02-20 | - |
| 28. RE Import (Const & Sol) | 2/2 | Complete    | 2026-02-21 | - |
| 29. RE Import (Gifts) | 2/2 | Complete    | 2026-02-21 | - |
| 30. Data Migration & Cutover | v2.0 | 0/? | Not started | - |
| 31. Gift & Recurring Gift UI | v2.0 | 0/? | Not started | - |
| 32. Import UI | v2.0 | 0/? | Not started | - |
| 33. Prayer Intentions | v2.0 | 0/? | Not started | - |
| 34. Dashboard Polish | v2.0 | 0/? | Not started | - |
| 35. Generic CSV Import | v2.0 | 0/? | Not started | - |
| 36. Full-Stack Audit | v2.0 | 0/? | Not started | - |

**Total:** 4 milestones shipped (77 plans), 1 milestone in progress (v2.0: 10 phases, 46 requirements)

---

*Last updated: 2026-02-20 (Phase 29 planned: 2 plans)*
