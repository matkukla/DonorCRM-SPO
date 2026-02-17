# Requirements: DonorCRM v1.3

**Defined:** 2026-02-16
**Core Value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.

## v1.3 Requirements

Requirements for v1.3 — Smartsheet Import, Filters & Polish. Each maps to roadmap phases.

### Smartsheet Import

- [ ] **IMP-01**: User can upload an Excel (.xlsx) or CSV file for import
- [ ] **IMP-02**: System detects file format automatically from content (magic bytes)
- [ ] **IMP-03**: User can select import type (Contacts, Donations, Pledges) for Smartsheet files
- [ ] **IMP-04**: User can map source columns to CRM fields via dropdown selects
- [ ] **IMP-05**: System auto-detects column mappings via fuzzy matching and pre-fills dropdowns
- [ ] **IMP-06**: User sees confidence indicators (green/yellow/red) for auto-detected mappings
- [ ] **IMP-07**: User can preview first 10 rows of mapped data before importing
- [ ] **IMP-08**: System validates all rows and reports errors with downloadable error CSV
- [ ] **IMP-09**: System sanitizes formula injection characters (=, +, -, @) on import
- [ ] **IMP-10**: User can save and reuse column mapping templates for repeated imports

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

### Smartsheet Import

- **IMP-F01**: User can import from multi-sheet Excel files with tab selection
- **IMP-F02**: User can drag-and-drop columns for mapping
- **IMP-F03**: System shows real-time import progress bar for large files (>5000 rows)
- **IMP-F04**: User can undo/rollback a completed import

### List Page Filters

- **FLT-F01**: User can build advanced filter queries with AND/OR logic
- **FLT-F02**: User can save filter combinations to database (cross-device)
- **FLT-F03**: User can multi-select values in dropdown filters

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-sheet Excel import | Most Smartsheet exports are single-sheet; tab selection UI adds complexity |
| Drag-and-drop column mapping | HIGH cost, accessibility nightmare; dropdown mapping covers 100% of use cases |
| Import undo/rollback | Validate-first workflow prevents mistakes; undo semantics unclear after edits |
| Formula evaluation on import | Security risk; openpyxl data_only=True reads computed values safely |
| Real-time import progress | Imports <2s for typical missionary data (500-2000 rows) |
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
| — | — | — |

**Coverage:**
- v1.3 requirements: 35 total
- Mapped to phases: 0
- Unmapped: 35 ⚠️

---
*Requirements defined: 2026-02-16*
*Last updated: 2026-02-16 after initial definition*
