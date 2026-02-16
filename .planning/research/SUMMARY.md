# Research Summary: Smartsheet Import, Filters & Polish (v1.3)

**Project:** DonorCRM v1.3 - Smartsheet Import, List Page Filters, Quality Audit
**Researched:** 2026-02-16
**Overall confidence:** HIGH

## Executive Summary

This milestone adds three capabilities to the existing DonorCRM: (1) Smartsheet file import with user-defined column mapping for Excel/CSV files, (2) comprehensive filtering on all list pages (contacts, journals, donations/transactions), and (3) a systematic quality audit covering dark mode consistency, security posture, and code quality.

The stack additions are minimal: one new backend dependency (openpyxl for Excel parsing), one backend upgrade (django-filter 23.x to 24.3 for custom FilterSet classes), and one dev tool swap (ruff replacing black+isort+flake8). Zero new frontend dependencies -- the column mapping UI uses existing Radix Select dropdowns rather than drag-and-drop, and the filter UI uses existing Radix + TanStack Table components. This restraint is deliberate: the existing stack already has everything needed for dropdowns, date pickers, popovers, and table filtering.

The critical finding from stack research is that django-filter 25.2 (the latest version) is INCOMPATIBLE with Django 4.2 -- it requires Django 5.2+. The project must use django-filter 24.3, the last version supporting Django 4.2. This would have caused a blocking dependency error if not caught during research. The existing codebase already uses `DjangoFilterBackend` with basic `filterset_fields` in 6 viewsets, so the upgrade path is adding custom `FilterSet` classes for date ranges, amount ranges, and text lookups -- not introducing a new pattern.

The Smartsheet import architecture extends the existing 4-type CSV import pipeline (Funds, Entities, Transactions, Pledges) rather than creating parallel infrastructure. The key insight is that column mapping happens in the frontend (Radix Select dropdowns), the mapped data is sent to the backend, and the backend transforms it into the same dict format that existing `parse_*_csv()` validators expect. This reuses 100% of existing validation, import, and audit trail logic.

## Key Findings

**Stack:** 1 new backend dep (openpyxl 3.1.5), 1 upgrade (django-filter to 24.3 NOT 25.2), 1 dev tool swap (ruff replaces black+isort+flake8). Zero new frontend deps.

**Architecture:** Smartsheet import extends existing CSV pipeline via column mapping transformation layer. Filters upgrade existing viewsets from simple `filterset_fields` to custom `FilterSet` classes. Quality audit is process, not architecture.

**Critical pitfall:** django-filter 25.2 breaks Django 4.2. Also: breaking existing CSV imports via premature refactoring, CSV formula injection on Smartsheet uploads, and N+1 queries when adding filter backends to views.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Excel/CSV Backend Parsing** - Add openpyxl, build file type detection, header extraction, and column mapping application logic
   - Addresses: Smartsheet .xlsx support, column header extraction for mapping UI
   - Avoids: Breaking existing CSV pipeline (copy-paste first, refactor later)
   - Pitfall prevention: Formula injection checks, file size limits, read_only mode

2. **Column Mapping Frontend** - Multi-step import wizard with Radix Select dropdowns for source-to-target field mapping
   - Addresses: User-defined column mapping, auto-detect common headers, preview before import
   - Avoids: Drag-drop accessibility failures (dropdown-only approach)
   - Depends on: Phase 1 header extraction API

3. **Backend Filtering** - Upgrade django-filter to 24.3, add custom FilterSet classes for contacts, journals, donations
   - Addresses: Date range, amount range, status, and text search filters
   - Avoids: Permission bypass via exposed owner field in FilterSets, N+1 query degradation
   - Pitfall prevention: Query profiling, queryset scoping before filter application

4. **Frontend Filtering UI** - Reusable FilterBar component using existing Radix Popover/Select/DatePicker
   - Addresses: Comprehensive filters on all list pages with URL param persistence
   - Avoids: Filter state desync between URL and UI (URL as single source of truth)
   - Depends on: Phase 3 backend filter endpoints

5. **Quality Audit** - Dark mode color inventory, ruff migration, security review, WCAG contrast checks
   - Addresses: 35+ hardcoded light-mode colors, black/isort/flake8 to ruff migration, permission audit
   - Avoids: Breaking formatting during ruff migration (run format, commit, then enable lint rules)
   - Depends on: Phases 1-4 complete (audit all new code too)

**Phase ordering rationale:**
- Backend parsing (Phase 1) before mapping UI (Phase 2) because the UI needs header extraction API
- Backend filtering (Phase 3) before frontend filtering (Phase 4) because frontend calls backend filter endpoints
- Quality audit (Phase 5) last because it audits ALL new code from Phases 1-4
- Import before filters because imports are higher user value (unblocks data onboarding)
- Filters before audit because filters are user-facing features

**Research flags for phases:**
- Phase 1: Standard openpyxl patterns, LOW research risk. Watch for Excel date serial number handling.
- Phase 2: Standard React form patterns, LOW research risk. Auto-detect fuzzy matching algorithm may need tuning.
- Phase 3: django-filter 24.3 version constraint is CRITICAL. Verify compatibility during implementation. Custom FilterSet class patterns well-documented.
- Phase 4: URL param state management is a known pitfall. Use existing useSearchParams pattern from DonationList.tsx.
- Phase 5: Dark mode color replacement is mechanical work. Ruff migration needs careful sequencing (format first, then lint).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified with PyPI/npm. Critical django-filter incompatibility caught. openpyxl and ruff versions confirmed current. |
| Features | HIGH | Feature landscape well-mapped. Table stakes vs differentiators clear. Anti-features identified (no drag-drop, no multi-sheet, no query builder). |
| Architecture | HIGH | Extends existing patterns (import pipeline, DjangoFilterBackend, URL params). No new paradigms. All integration points documented. |
| Pitfalls | HIGH | 11 pitfalls catalogued with phase mappings. Critical ones: django-filter version, CSV formula injection, breaking existing imports, N+1 queries. |

## Gaps to Address

- **Excel date serial numbers:** openpyxl returns dates as datetime objects, not strings. The existing `_parse_date()` function expects strings. Need conversion layer.
- **Multi-sheet Excel files:** Current architecture ignores all sheets except active. Should document this limitation for users.
- **Filter performance at scale:** Need to profile with production-like data (5000+ contacts) during Phase 3, not just in Phase 5 audit.
- **ruff 2026 style guide:** The 0.15.1 release includes new formatting rules. Running `ruff format` may change many files -- should be a single commit before any lint rule changes.

## Files Created/Updated

| File | Purpose |
|------|---------|
| `.planning/research/SUMMARY.md` | This file -- executive summary with roadmap implications |
| `.planning/research/STACK.md` | Technology recommendations (UPDATED: corrected django-filter version, removed dnd-kit) |
| `.planning/research/FEATURES.md` | Feature landscape (existing, comprehensive) |
| `.planning/research/SMARTSHEET_ARCHITECTURE.md` | Architecture patterns for import + filtering (existing, comprehensive) |
| `.planning/research/PITFALLS_V1.3_SMARTSHEET_FILTERS.md` | Domain pitfalls with phase mappings (existing, comprehensive) |

---
*Research Summary for: DonorCRM v1.3 -- Smartsheet Import, Filters & Polish*
*Researched: 2026-02-16*
*Confidence: HIGH -- All findings verified with official sources. Critical version incompatibility caught.*
