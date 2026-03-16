# Deferred Items — Phase 51

## Pre-existing Test Failures (Out of Scope)

These 15 tests were already failing before Phase 51 changes. They are NOT
introduced by this phase and are out of scope per deviation rules.

### Contacts
- `apps/contacts/tests/test_integration.py::TestPermissionBoundaries::test_admin_sees_all_contacts`
  — Test assumes old admin all-access behavior; unrelated to Phase 51 (pre-existing)

### Gifts
- `apps/gifts/tests/test_views.py::TestGiftPermissionScoping::test_admin_can_access_any_gift_detail`
- `apps/gifts/tests/test_views.py::TestGiftPermissionScoping::test_admin_can_see_all_gifts`
- `apps/gifts/tests/test_views.py::TestRecurringGiftPermissionScoping::test_admin_can_access_any_recurring_gift_detail`
- `apps/gifts/tests/test_views.py::TestRecurringGiftPermissionScoping::test_admin_can_see_all_recurring_gifts`

### Imports / CSV
- `apps/imports/tests/test_services.py::TestGiftExport::test_export_gifts_csv`

### Insights — ActivityHeatmap (endpoint not yet implemented)
- `apps/insights/tests/test_date_filtering.py::TestActivityHeatmap::test_admin_can_access`
- `apps/insights/tests/test_date_filtering.py::TestActivityHeatmap::test_aggregates_multiple_activity_types`
- `apps/insights/tests/test_date_filtering.py::TestActivityHeatmap::test_date_range_filters_activities`
- `apps/insights/tests/test_date_filtering.py::TestActivityHeatmap::test_invalid_date_returns_400`
- `apps/insights/tests/test_date_filtering.py::TestActivityHeatmap::test_returns_365_days_by_default`
- `apps/insights/tests/test_date_filtering.py::TestActivityHeatmap::test_returns_correct_structure`
- `apps/insights/tests/test_date_filtering.py::TestActivityHeatmap::test_staff_cannot_access`
  — All 7 fail with 404 because `/api/v1/insights/admin/activity-heatmap/` is not registered in URLs yet

### Insights — TeamTrends
- `apps/insights/tests/test_team_trends.py::TestTeamTrendsView::test_counts_decisions_by_week`
- `apps/insights/tests/test_team_trends.py::TestTeamTrendsView::test_counts_donations_by_week`

**Confirmed pre-existing:** All 15 were failing before Phase 51 commit `f287e7f`.
Phase 51 reduced failures from 16 to 15 (fixed 1 via Plan 02 test update).
