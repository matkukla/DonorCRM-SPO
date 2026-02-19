# Phase 25: Smartsheet MPD Report Frontend - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin can upload a monthly Smartsheet MPD Dashboard Report from the Import Center and see results (matched/unmatched missionaries). MPD financial data is surfaced on the admin analytics dashboard and on individual missionary views (both admin detail pages and missionaries' own personal views). Historical snapshots accumulate but trend display is deferred.

</domain>

<decisions>
## Implementation Decisions

### Upload & Results
- Upload lives in the **Import Center** as a new tab/tile alongside existing CSV import types
- After upload, results display in a **modal/dialog** (not inline or navigation)
- Results modal shows **unmatched names with their financial row data** so admin can see what was skipped
- Upload history display is at Claude's discretion (see below)

### Dashboard MPD Data
- MPD data appears as a **new "MPD Overview" section below existing dashboard content** (not integrated into team table)
- Key fields per missionary: **MPD Cap, Roll Forward Balance, Months Remaining** (not full snapshot)
- Layout: **sortable summary table** with one row per missionary and MPD columns
- No "last uploaded" freshness date indicator needed

### Missionary Detail Pages (Admin View)
- MPD data is **inline with existing stats** on the admin per-missionary detail page (not a separate tab/section)
- Shows same fields: MPD Cap, Roll Forward Balance, Months Remaining

### Missionary Personal View
- Missionaries see their **own MPD data on their home/overview page**
- Same detail level as admin sees (MPD Cap, Roll Forward Balance, Months Remaining)
- **Latest snapshot only** — no trend charts or historical comparison

### Claude's Discretion
- Whether to show upload history list in Import Center (past uploads with date/filename/counts)
- Exact placement and styling of MPD fields on missionary detail and personal views
- Loading states and empty states when no MPD data exists yet
- Error handling UX for failed uploads

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing Import Center patterns for the upload tile, and existing dashboard/detail page patterns for data display.

</specifics>

<deferred>
## Deferred Ideas

- Historical trend display (MPD Cap over time charts, sparklines) — requirement IMP-10 mentions trend enablement but user wants latest-only for now. Data accumulates; visualization can be added later.

</deferred>

---

*Phase: 25-smartsheet-import-frontend*
*Context gathered: 2026-02-19*
