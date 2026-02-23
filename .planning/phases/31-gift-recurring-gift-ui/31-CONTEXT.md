# Phase 31: Gift & Recurring Gift UI - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning (revised)

<domain>
## Phase Boundary

Wire the frontend to query the new Gift/RecurringGift backend endpoints while keeping all user-facing terminology as "Donations" and "Pledges". Update list pages, filters, detail views, contact tabs, CSV exports, and dashboard cards/charts to use the new API. Add a donation detail slide-in panel with solicitor credit breakdown (new UI). No renaming of visible text, URLs, or labels.

</domain>

<decisions>
## Implementation Decisions

### Naming & terminology — NO RENAME
- All user-facing text stays as "Donations" and "Pledges" (sidebar, page titles, breadcrumbs, buttons, empty states)
- Frontend URL paths stay as /donations and /pledges (no rename)
- CSV export filenames and column headers stay as-is (donations.csv, "Date", etc.)
- Contact detail page: keep existing "Donations" and "Pledges" tabs (or single "Donations" tab with two sections — one-time and recurring)
- Dashboard card labels stay: "Recent Donations", "Total Donated", "Pledged Monthly Support", etc.
- The only change is that the frontend fetches from the Gift/RecurringGift API endpoints (backend already has backward-compatible URL aliases /donations/ and /pledges/ pointing to gifts app)

### Solicitor credit display
- Credits shown on donation detail view only (not in list page columns)
- Simple table layout: Solicitor Name | Amount | Percentage
- Donation detail opens as a slide-in panel (matching existing User Drilldown pattern)
- Hide credits section entirely when a donation has no solicitor credits (migrated donations won't have them)

### List page columns
- Donations list: Donor Name | Amount | Date | Fund | Description
- Pledges list: Donor Name | Amount | Frequency | Status | Start Date | Fund
- Same filter set as old pages, same labels
- No fund filter added (keep existing filter set)
- Clicking a donation row opens the slide-in detail panel; donor name is a link to contact page

### Dashboard card updates
- No label changes — keep all existing card titles and text
- Late Pledges section kept as placeholder with "Late detection coming soon" text
- Support progress card title stays as "Pledged Monthly Support"

### Claude's Discretion
- Exact slide-in panel layout and styling (should match existing drilldown patterns)
- Loading states and error handling for donation detail fetch
- Pledges filter set (status, frequency filters — follow existing patterns)
- Empty state messages on list pages
- Whether to use a single "Donations" contact tab with two sections or keep two separate tabs

</decisions>

<specifics>
## Specific Ideas

- Slide-in panel should match the existing User Drilldown sidebar pattern already in the codebase
- "Late detection coming soon" placeholder signals future functionality without committing to a timeline
- The key change is plumbing — frontend talks to Gift/RecurringGift API but presents everything with Donation/Pledge labels

</specifics>

<deferred>
## Deferred Ideas

- Late recurring gift detection (requires fulfillment tracking or date-based heuristic) — future phase
- Fund filter on Donations list page — potential future enhancement
- Actual rename of UI terminology from Donations/Pledges to Gifts/Recurring Gifts — future decision

</deferred>

---

*Phase: 31-gift-recurring-gift-ui*
*Context gathered: 2026-02-23 (revised)*
