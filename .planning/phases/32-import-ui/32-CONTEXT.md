# Phase 32: Import UI - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Unified Import/Export page accessible from the main sidebar where users can upload RE CSVs (4 types), Smartsheet MPD files, view import history, and see a generic CSV import stub (backend wired in Phase 35). Old admin import functionality is removed.

</domain>

<decisions>
## Implementation Decisions

### Page layout & navigation
- Replace the existing sidebar "Import/Export" link to point to the new page; remove the admin imports sub-page entirely
- Page has three grouped tab sections:
  1. **RE Imports** — 4 tabs: Constituent, Solicitor, Gift, Recurring Gift
  2. **Smartsheet** — MPD import (existing functionality moved here)
  3. **Generic** — Contact and Donation tabs showing "Coming soon" placeholder (backend in Phase 35)
- Import history section below the tab groups listing past ImportBatch records with status icons and summary counts

### Upload experience
- **Preview first** workflow: drag-and-drop (or click) to select file → show filename and size → user clicks "Import" button to start processing
- CSV header reference (required and optional columns) is **always visible** below the upload area on each tab
- Visual step numbering on RE import tabs (e.g., "Step 1 of 4", "Step 2 of 4") to guide recommended import order — all tabs remain accessible regardless
- After import completes, result banners show success/error/already-processed counts with expandable error details showing row numbers

### Claude's Discretion
- Whether import results display inline on the tab or in a modal dialog
- Loading/progress indicator style during import processing
- Exact layout of the import history section (table vs cards, columns shown)
- How the Smartsheet section is visually distinguished from RE imports
- Error detail expansion pattern (accordion, collapsible section, etc.)

</decisions>

<specifics>
## Specific Ideas

- 5 import types total: 4 RE CSVs (Constituent, Solicitor, Gift, Recurring Gift) + 1 Smartsheet MPD
- Backend APIs already exist for all 5 import types at `/imports/re/*` and `/imports/mpd/`
- ImportBatch model tracks all imports with SHA256 deduplication, row counts, and error details
- Current admin Import Center has SPO legacy imports (Funds, Entities, Transactions, Pledges) — these are being removed along with the admin imports page
- Exports (contacts CSV, donations CSV) currently exist as download buttons — need to be preserved somewhere on the new page

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 32-import-ui*
*Context gathered: 2026-02-23*
