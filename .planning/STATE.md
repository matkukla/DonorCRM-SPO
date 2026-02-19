# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-16)

**Core value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.
**Current focus:** Phase 25 in progress (v1.3)

## Current Position

Milestone: v1.3 — Smartsheet Import, Filters & Polish
Phase: 25 of 25 (Smartsheet Import Frontend)
Plan: 4 of 4 complete
Status: Phase Complete
Last activity: 2026-02-19 — Phase 25 Plan 04 complete (MPD inline stats on UserDetail and Dashboard)

Progress: [################################] 94% (77/82 total plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 75 (24 v1.0 + 15 v1.1 + 18 v1.2 + 18 v1.3)
- Average duration: 4.2 minutes
- Total execution time: ~4.2 hours

**By Milestone:**

| Milestone | Plans | Total | Avg/Plan |
|-----------|-------|-------|----------|
| v1.0 (Phases 1-6) | 24 | 1.4 hours | 2.8 min |
| v1.1 (Phases 7-12) | 15 | 76m 43s | 5.1 min |
| v1.2 (Phases 13-19) | 18 | 108m 48s | 6.0 min |

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

- **20-01:** No data migration needed for monthly_equivalent (computed @property, not stored field)
- **20-01:** Admin users bypass owner filter in stage event creation (consistent with ContactThankView pattern)
- **20-02:** Skipped SPOImportTile.tsx size check (no file handler; ImportDialog handles file selection)
- **20-02:** Used useRef guard pattern for toast to prevent duplicate notifications on ProtectedRoute redirect
- **20-03:** Skipped visual indicators for unseen events (is_new has no current UI distinction; decoupling marking from GET is the core fix)
- **20-03:** Used getattr fallback pattern so serializer works with and without prefetch
- **21-01:** Used dark:bg-*-950/50 opacity pattern for dark backgrounds (matches NeedsAttention.tsx reference)
- **21-01:** Replaced generic grays (text-gray-400, border-gray-300) with semantic tokens (text-muted-foreground, border-border)
- **21-02:** Used OWASP single-quote prefix for CSV sanitization (spreadsheet-native text-mode indicator)
- **21-02:** Kept event creation, thank-you marking, and pledge fulfillment as create-only in signal
- **21-03:** ErrorBoundary placed inside ThemeProvider but outside AuthProvider/BrowserRouter (dark mode works in fallback, auth/routing errors caught)
- **21-03:** Used instanceof check for unknown error type in FallbackProps (react-error-boundary v6 TypeScript strict mode)
- **22-01:** Used individual DateFilter fields instead of DateFromToRangeFilter (avoids 24.3 suffix breaking change)
- **22-01:** Owner field excluded from all FilterSets (admin-only owner filtering stays in get_queryset for security)
- **22-01:** Echo pseudo-buffer defined locally in each export_views.py (matching insights pattern)
- **22-02:** Used nuqs useQueryStates with shallow:false to trigger React Query re-renders on filter change
- **22-02:** Generic useFilterParams<T> hook instead of per-page hooks for maximum reuse
- **22-02:** Presets explicitly null other filter fields to prevent filter stacking between presets
- **22-02:** Button variant="secondary" for Presets/Export (not "outline" which is the red CTA style)
- **22-03:** Used Record<string, any> for FilterParsers type (SingleParserBuilder incompatible with ReturnType<>)
- **22-03:** Kept local searchInput state with useEffect sync for controlled search input in ContactList
- **22-03:** Removed Transactions separate Filters Card wrapper in favor of FilterBar-managed layout
- **23-01:** JournalExportCSVView replicates DonationExportCSVView pattern (Echo class, StreamingHttpResponse, 10k limit)
- **23-01:** FundListView uses pagination_class=None for dropdown consumption
- **23-01:** is_archived logic preserved in JournalListCreateView and replicated in JournalExportCSVView
- **23-02:** Used useUsers hook for admin owner dropdown (avoids new API endpoint)
- **23-02:** Presets explicitly null all new filter fields to prevent filter stacking between presets
- **23-03:** page_size=50 for journal list (card grid layout, fewer journals than donations/pledges)
- **23-03:** Kept JournalFilters interface for backward compatibility but getJournals now uses Record<string, string>
- **24-01:** DecimalField max_digits=12 for financial fields (accommodates values like $71,352.72 and roll forward balances)
- **24-01:** months_remaining_rf as CharField (can be numeric or "infinite")
- **24-01:** pct_standard_to_max as IntegerField storing raw percentage (104 for "104%")
- **24-02:** No file extension check on MPD upload -- format auto-detected from PK magic bytes (XLSX) or fallback (CSV)
- **24-02:** Duplicate user names treated as ambiguous and added to unmatched list (not matched to either)
- **24-02:** Formula injection strips =, +, @, tab, CR but NOT - (negative currency is legitimate)
- **25-01:** N+1 acceptable for MPDOverviewView (<50 missionaries, simplicity over optimization)
- **25-01:** Decimal values serialized as str() for JSON compatibility (consistent with DRF default)
- **25-02:** Native file input instead of react-papaparse for MPD upload (backend handles all parsing)
- **25-02:** MPD section placed below SPO grid, not in IMPORT_CONFIGS array (separate import system)

### Pending Todos

5 pending todo(s). See `.planning/todos/pending/`.

### Blockers/Concerns

**Ordering constraints (from research):**
- QAL-01, QAL-02 (security) MUST precede filter work (Phase 20 before 22-23)
- QAL-05 (N+1 fix) MUST precede journal filters (Phase 20 before 23)
- QAL-06 (file size limits) MUST precede Smartsheet import (Phase 20 before 24-25)
- django-filter must be pinned to 24.3 (NOT 25.2) -- 25.2 requires Django 5.2+

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 5 | Remove analytics tab from left sidebar | 2026-02-16 | db2b504 | [5-remove-analytics-tab-from-left-sidebar-a](./quick/5-remove-analytics-tab-from-left-sidebar-a/) |
| 6 | Move Journals to sidebar & add action dialogs | 2026-02-16 | 34097d1 | [6-move-journal-tab-to-own-sidebar-tab-add-](./quick/6-move-journal-tab-to-own-sidebar-tab-add-/) |
| 7 | Implement light and dark mode toggle | 2026-02-16 | ccb4c67 | [7-implement-light-and-dark-mode-toggle](./quick/7-implement-light-and-dark-mode-toggle/) |

## Session Continuity

Last session: 2026-02-19
Stopped at: Completed 25-03-PLAN.md
Resume: Phase 25 Plan 04 (Smartsheet Import Frontend)

---

*Last updated: 2026-02-19 (Phase 25 Plan 03 complete — MPD overview dashboard table)*
