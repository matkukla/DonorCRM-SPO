# Phase 31: Gift & Recurring Gift UI - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Rename "Donations" to "Gifts" and "Pledges" to "Recurring Gifts" across the entire frontend. Update all list pages, filters, detail views, contact tabs, CSV exports, and dashboard cards/charts to query the new Gift/RecurringGift backend endpoints. Add a gift detail slide-in panel with solicitor credit breakdown (new UI). Remove old donation/pledge terminology and URL paths.

</domain>

<decisions>
## Implementation Decisions

### Solicitor credit display
- Credits shown on gift detail view only (not in list page columns)
- Simple table layout: Solicitor Name | Amount | Percentage
- Gift detail opens as a slide-in panel (matching existing User Drilldown pattern)
- Hide credits section entirely when a gift has no solicitor credits (migrated donations won't have them)

### Naming & terminology
- Sidebar items: "Gifts" and "Recurring Gifts"
- Contact detail page: single "Gifts" tab with two sections inside (one-time gifts table + recurring gifts table)
- Frontend URL paths rename: /donations -> /gifts, /pledges -> /recurring-gifts
- CSV export filenames and column headers fully renamed (gifts.csv, "Gift Date", etc.)

### List page columns
- Gifts list: Donor Name | Amount | Gift Date | Fund | Description
- Recurring Gifts list: Donor Name | Amount | Frequency | Status | Start Date | Fund
- Same filter set as old pages, labels renamed ("Gift Date" instead of "Date")
- No fund filter added (keep existing filter set)
- Clicking a gift row opens the slide-in detail panel; donor name is a link to contact page

### Dashboard card updates
- Label rename only — no layout or data changes
- "Recent Donations" -> "Recent Gifts", "Total Donated" -> "Total Given", etc.
- Late Pledges section kept as placeholder with "Late detection coming soon" text
- Support progress card title: "Monthly Support" (not "Pledged Monthly Support" or "Monthly Recurring Gift Support")

### Claude's Discretion
- Exact slide-in panel layout and styling (should match existing drilldown patterns)
- Loading states and error handling for gift detail fetch
- Recurring Gifts filter set (status, frequency filters — follow existing patterns)
- Empty state messages on list pages

</decisions>

<specifics>
## Specific Ideas

- Slide-in panel should match the existing User Drilldown sidebar pattern already in the codebase
- "Late detection coming soon" placeholder signals future functionality without committing to a timeline
- Single "Gifts" tab on contact detail keeps the tab bar clean — use section headers inside to separate one-time vs recurring

</specifics>

<deferred>
## Deferred Ideas

- Late recurring gift detection (requires fulfillment tracking or date-based heuristic) — future phase
- Fund filter on Gifts list page — potential future enhancement

</deferred>

---

*Phase: 31-gift-recurring-gift-ui*
*Context gathered: 2026-02-23*
