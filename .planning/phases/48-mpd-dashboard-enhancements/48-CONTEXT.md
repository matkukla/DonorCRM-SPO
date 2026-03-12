# Phase 48: MPD Dashboard Enhancements - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich the dashboard MPD section with two additions: (1) a Monthly Average tile added to the existing MPD Financial Overview visible to all users who have MPD snapshot data, and (2) an Admin MPD Overview section visible only to admin role showing org-wide per-missionary MPD health. No new models, no new pages — dashboard additions only.

</domain>

<decisions>
## Implementation Decisions

### Monthly Average tile

- 4-column grid on the personal MPD Financial Overview section (`md:grid-cols-4`)
- Monthly Average is the **first** tile, before MPD Cap, Roll Forward Balance, and Months Remaining
- Final order: Monthly Average | MPD Cap | Roll Forward Balance | Months Remaining
- Add `monthly_average` to the existing `/api/v1/imports/mpd/me/` response — no new endpoint
- Update `MPDStatsInline` component (or rename/extend) to render 4 cards as Fragment children

### Admin MPD Overview section

- Reuse and extend `MPDOverviewTable` — add a Monthly Average column
- Column order in table: Missionary | Monthly Average | MPD Cap | Roll Forward Balance | Months Remaining
- Add `monthly_average` to the existing `/api/v1/imports/mpd/overview/` response — no new endpoint
- Section appears **below** the missionary's own MPD tiles on the dashboard
- Visible only when `user?.role === "admin"` (follow existing admin check pattern)
- Admin sees both sections when they have their own MPD data; admin section always renders for admin regardless of personal MPD data

### Data currency

- No timestamp shown on tiles or section headers — silent is fine, users understand MPD is monthly
- No-data behavior unchanged: MPD section hidden when `has_data` is false (no empty state added)

### Claude's Discretion

- Exact Tailwind grid class for 4-col responsiveness (e.g., `sm:grid-cols-2 md:grid-cols-4`)
- Whether `MPDStatsInline` is renamed or the 4th card is added inline
- Skeleton loading state for the admin table section

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `MPDStatsInline` (`frontend/src/components/mpd/MPDStatsInline.tsx`): Renders 3 Card fragments in a parent-provided grid. Extend to 4 cards — Monthly Average first.
- `MPDOverviewTable` (`frontend/src/components/mpd/MPDOverviewTable.tsx`): TanStack Table with sortable columns. Add `monthly_average` column using same pattern as other DecimalField columns.
- `useMPDMyData` / `useMPDOverview` hooks (`frontend/src/hooks/useMPD.ts`): Already set up — just update response types.
- `formatMPDCurrency` (`frontend/src/api/mpd.ts`): Existing currency formatter — use for the new Monthly Average tile and column.

### Established Patterns

- MPD tile cards use `CardHeader` + `CardContent` with `text-2xl font-bold` value display
- `MPDOverviewView` uses a Subquery pattern to fetch the latest snapshot per user — extend the `missionaries` dict with `monthly_average`
- `MPDMyDataView` returns a simple dict from a single `.first()` query — just add the new field
- Admin role check: `user?.role === "admin"` (frontend), `IsAdmin` permission class (backend)
- Dashboard MPD section is wrapped in `{!isViewingOther && (...)}` — admin overview should follow same guard

### Integration Points

- Backend: `MPDMyDataView.get()` return dict — add `monthly_average` field
- Backend: `MPDOverviewView.get()` per-missionary dict — add `monthly_average` field
- Frontend: `MPDMyDataResponse` interface in `frontend/src/api/mpd.ts` — add `monthly_average?: string | null`
- Frontend: `MPDMissionaryOverview` interface in `frontend/src/api/mpd.ts` — add `monthly_average?: string | null`
- Frontend: `Dashboard.tsx` MPD section (~line 293) — change grid to 4-col, render Monthly Average first, add admin section below

</code_context>

<specifics>
## Specific Ideas

No specific references beyond the requirements — standard MPD tile pattern.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 48-mpd-dashboard-enhancements*
*Context gathered: 2026-03-12*
