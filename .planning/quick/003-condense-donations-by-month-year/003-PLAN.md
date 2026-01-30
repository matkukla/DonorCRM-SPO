---
id: quick-003
type: quick
title: Condense Donations by Month/Year
status: planned
files_modified:
  - frontend/src/pages/insights/DonationsByMonthYear.tsx
  - frontend/src/pages/insights/index.ts
  - frontend/src/components/layout/Sidebar.tsx
  - frontend/src/App.tsx
---

<objective>
Consolidate "Donations by Month" and "Donations by Year" into a single "Donations by Month/Year" page.

Purpose: Simplify insights navigation by combining two similar views into one unified page with a year selector that shows 12-month breakdown for the selected year.

Output: Single page at `/insights/donations-by-month-year` with year selector, bar chart, and table showing all 12 months (including zeros).
</objective>

<context>
Existing pages to consolidate:
- `frontend/src/pages/insights/DonationsByMonth.tsx` - Has year selector, 12-month display, chart + table
- `frontend/src/pages/insights/DonationsByYear.tsx` - Shows 5-year summary without selector

The DonationsByMonth page already has the exact functionality needed:
- Year selector dropdown (current year - 4 years)
- 12-month breakdown with zeros for empty months
- Bar chart with totals
- Table with month details
- Uses `useDonationsByMonth(year)` hook

Backend already filters to only actual donations (no status field - all Donation records are received/posted).

Key files:
- `frontend/src/api/insights.ts` - API types and functions (keep existing)
- `frontend/src/hooks/useInsights.ts` - React Query hooks (keep existing)
- `apps/insights/views.py` - Backend views (keep existing)
- `apps/insights/services.py` - Service functions (keep existing)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create consolidated DonationsByMonthYear component</name>
  <files>frontend/src/pages/insights/DonationsByMonthYear.tsx</files>
  <action>
Create new `DonationsByMonthYear.tsx` based on existing `DonationsByMonth.tsx`:
1. Copy DonationsByMonth.tsx as the base (it already has 90% of the functionality)
2. Update page title to "Donations by Month/Year"
3. Update description to "Monthly donation breakdown by year"
4. Keep existing functionality:
   - Year selector (5 years: current year back to current-4)
   - 12-month display with zeros for months with no donations
   - Bar chart showing monthly totals
   - Table with Month, Donations count, Total columns
   - Summary row at bottom
5. Use existing `useDonationsByMonth(selectedYear)` hook (no backend changes needed)

Note: Backend `get_donations_by_month()` in services.py already:
- Filters to user-scoped donations via `_scope_donations()`
- All Donation records are received/posted (no status filtering needed)
- Fills in zeros for months with no donations
  </action>
  <verify>File exists at `frontend/src/pages/insights/DonationsByMonthYear.tsx` with year selector and 12-month display</verify>
  <done>New consolidated component created with year selector, bar chart, and 12-month table</done>
</task>

<task type="auto">
  <name>Task 2: Update routing and navigation</name>
  <files>
    frontend/src/pages/insights/index.ts
    frontend/src/components/layout/Sidebar.tsx
    frontend/src/App.tsx
  </files>
  <action>
1. Update `frontend/src/pages/insights/index.ts`:
   - Remove exports for DonationsByMonth and DonationsByYear
   - Add export for DonationsByMonthYear

2. Update `frontend/src/components/layout/Sidebar.tsx`:
   - In `insightsItems` array, replace:
     - `{ label: "Donations by Month", href: "/insights/donations-by-month", icon: <Calendar ... /> }`
     - `{ label: "Donations by Year", href: "/insights/donations-by-year", icon: <CalendarDays ... /> }`
   - With single entry:
     - `{ label: "Donations by Month/Year", href: "/insights/donations-by-month-year", icon: <Calendar ... /> }`
   - Remove CalendarDays import if no longer used

3. Update `frontend/src/App.tsx`:
   - Update imports to use DonationsByMonthYear instead of DonationsByMonth and DonationsByYear
   - Replace two routes:
     - `/insights/donations-by-month`
     - `/insights/donations-by-year`
   - With single route:
     - `/insights/donations-by-month-year`
  </action>
  <verify>
Run `npm run build` in frontend directory - should compile without errors.
Visit `/insights/donations-by-month-year` in browser - page loads with year selector.
  </verify>
  <done>
- Single route `/insights/donations-by-month-year` active
- Sidebar shows single "Donations by Month/Year" entry
- Old routes removed
  </done>
</task>

<task type="auto">
  <name>Task 3: Clean up old files</name>
  <files>
    frontend/src/pages/insights/DonationsByMonth.tsx
    frontend/src/pages/insights/DonationsByYear.tsx
  </files>
  <action>
Delete the old separate files that are no longer used:
1. Delete `frontend/src/pages/insights/DonationsByMonth.tsx`
2. Delete `frontend/src/pages/insights/DonationsByYear.tsx`

Note: Keep API functions (`getDonationsByMonth`, `getDonationsByYear`) and hooks (`useDonationsByMonth`, `useDonationsByYear`) in case other code uses them. The new page only uses `useDonationsByMonth`.
  </action>
  <verify>
Files deleted. Run `npm run build` in frontend - should still compile without errors.
  </verify>
  <done>Old DonationsByMonth.tsx and DonationsByYear.tsx files removed</done>
</task>

</tasks>

<verification>
1. `cd frontend && npm run build` - No TypeScript errors
2. Start dev server and navigate to `/insights/donations-by-month-year`
3. Verify year selector shows 5 years (current through current-4)
4. Select different years and verify data updates
5. Verify chart displays 12 bars (one per month)
6. Verify table shows all 12 months with zeros for empty months
7. Verify Sidebar shows single "Donations by Month/Year" entry
8. Verify old routes `/insights/donations-by-month` and `/insights/donations-by-year` redirect to 404 or home
</verification>

<success_criteria>
- Single page at `/insights/donations-by-month-year` replaces two separate pages
- Year selector allows switching between years
- All 12 months displayed with zeros for empty months
- Bar chart and table both present
- Sidebar navigation consolidated to single entry
- Build passes with no errors
</success_criteria>
