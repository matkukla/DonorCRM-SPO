# Requirements: DonorCRM v1.3

**Defined:** 2026-02-16
**Core Value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.

## v1.3 Requirements

Requirements for v1.3 — Smartsheet Import, Filters & Polish. Each maps to roadmap phases.

### Smartsheet MPD Report Import

- [ ] **IMP-01**: Admin can upload an Excel (.xlsx) or CSV Smartsheet MPD report file
- [ ] **IMP-02**: System detects file format automatically from content (magic bytes)
- [ ] **IMP-03**: System matches each row to an existing DonorCRM user by First Name + Last Name
- [ ] **IMP-04**: Unmatched rows are reported to admin (not silently dropped)
- [ ] **IMP-05**: System sanitizes formula injection characters (=, +, -, @) in cell values before storage
- [ ] **IMP-06**: Admin has a dedicated upload page for the monthly Smartsheet report
- [ ] **IMP-07**: Admin sees import results: matched/unmatched missionaries, snapshot counts
- [ ] **IMP-08**: Admin dashboard shows latest MPD data per missionary (MPD Cap, Rollover Balance, financial stats)
- [ ] **IMP-09**: Each missionary sees their own MPD data in their personal view
- [ ] **IMP-10**: Monthly snapshots accumulate historically for trend analysis

### List Page Filters

- [ ] **FLT-01**: User can filter by date range (start/end) on donation, journal, pledge, and transaction pages
- [ ] **FLT-02**: User can filter by amount range (min/max) on donation and pledge pages
- [ ] **FLT-03**: User can filter contacts by group membership
- [ ] **FLT-04**: Admin can filter contacts and donations by owner (missionary)
- [ ] **FLT-05**: User can filter donations by payment method and fund
- [ ] **FLT-06**: User can filter pledges by frequency and search by donor name
- [ ] **FLT-07**: User can search and filter journals by name, date range, and archived status
- [ ] **FLT-08**: Filter state persists in URL params on all pages (fix Transactions page bug)
- [ ] **FLT-09**: User can clear all active filters with one click
- [ ] **FLT-10**: User can apply filter presets ("Needs Thank You", "This Month", "Late Pledges", "Stalled")
- [ ] **FLT-11**: User sees active filter summary badges showing applied filters
- [ ] **FLT-12**: User can export filtered results to CSV
- [ ] **FLT-13**: All filtering is server-side with proper query optimization

### Quality Audit

- [ ] **QAL-01**: Fix ListAPIView permission bypass — scope get_queryset() by owner for non-admin users
- [ ] **QAL-02**: Fix cross-user contact access in stage event creation (owner check)
- [ ] **QAL-03**: Fix 59 hardcoded dark mode colors across 13 files with semantic Tailwind classes
- [ ] **QAL-04**: Verify WCAG 4.5:1 contrast compliance in dark mode across all pages
- [ ] **QAL-05**: Fix N+1 queries in journal grid (351 queries → <10 with prefetch_related)
- [ ] **QAL-06**: Add file size limits to upload endpoints (DATA_UPLOAD_MAX_MEMORY_SIZE)
- [ ] **QAL-07**: Fix float arithmetic in pledge monthly_equivalent (use Decimal)
- [ ] **QAL-08**: Add frontend route guards for role-based access
- [ ] **QAL-09**: Fix dashboard GET side effect (events marked seen before user reads them)
- [ ] **QAL-10**: Add React Error Boundary at app root with fallback UI
- [ ] **QAL-11**: Fix donation edit not refreshing contact stats
- [ ] **QAL-12**: Add CSV export formula sanitization (prefix =, +, -, @ characters)

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Smartsheet MPD Report Import

- **IMP-F01**: Admin can delete/undo a specific MPD upload and its snapshots
- **IMP-F02**: MPD data comparison between two time periods
- **IMP-F03**: Automated Smartsheet import via API integration (no manual upload)
- **IMP-F04**: MPD goal tracking alerts when missionaries fall below MPD Standard

### List Page Filters

- **FLT-F01**: User can build advanced filter queries with AND/OR logic
- **FLT-F02**: User can save filter combinations to database (cross-device)
- **FLT-F03**: User can multi-select values in dropdown filters

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Import undo/rollback | Snapshots are immutable records; admin can re-upload corrected files |
| Automated Smartsheet API | Manual monthly upload is sufficient; API adds auth complexity |
| Real-time import progress | Imports <1s for typical missionary data (10-50 rows) |
| Advanced filter query builder | Overwhelming for 90% of users; stacked AND covers 95% of use cases |
| Saved filters (backend) | URL params already bookmarkable and shareable; no new model needed |
| Multi-select filter dropdowns | Complicates serialization and query logic; marginal value |
| Automated visual regression testing | Overkill for 13 files; manual dark mode checklist sufficient |
| Full OWASP penetration test | Targeted audit of known issues more cost-effective |
| APM monitoring infrastructure | Django Debug Toolbar in dev sufficient; known N+1 patterns |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| IMP-01 | Phase 24 | Pending |
| IMP-02 | Phase 24 | Pending |
| IMP-03 | Phase 24 | Pending |
| IMP-04 | Phase 24 | Pending |
| IMP-05 | Phase 24 | Pending |
| IMP-06 | Phase 25 | Pending |
| IMP-07 | Phase 25 | Pending |
| IMP-08 | Phase 25 | Pending |
| IMP-09 | Phase 25 | Pending |
| IMP-10 | Phase 24 | Pending |
| FLT-01 | Phase 23 | Pending |
| FLT-02 | Phase 23 | Pending |
| FLT-03 | Phase 23 | Pending |
| FLT-04 | Phase 23 | Pending |
| FLT-05 | Phase 23 | Pending |
| FLT-06 | Phase 23 | Pending |
| FLT-07 | Phase 23 | Pending |
| FLT-08 | Phase 22 | Pending |
| FLT-09 | Phase 22 | Pending |
| FLT-10 | Phase 22 | Pending |
| FLT-11 | Phase 22 | Pending |
| FLT-12 | Phase 22 | Pending |
| FLT-13 | Phase 22 | Pending |
| QAL-01 | Phase 20 | Pending |
| QAL-02 | Phase 20 | Pending |
| QAL-03 | Phase 21 | Pending |
| QAL-04 | Phase 21 | Pending |
| QAL-05 | Phase 20 | Pending |
| QAL-06 | Phase 20 | Pending |
| QAL-07 | Phase 20 | Pending |
| QAL-08 | Phase 20 | Pending |
| QAL-09 | Phase 20 | Pending |
| QAL-10 | Phase 21 | Pending |
| QAL-11 | Phase 21 | Pending |
| QAL-12 | Phase 21 | Pending |

**Coverage:**
- v1.3 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-02-16*
*Last updated: 2026-02-16 after roadmap creation*
