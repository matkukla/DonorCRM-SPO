# Deferred Items — Phase 47

## Pre-existing Test Failures (Out of Scope)

These failures were present before phase 47 began and are NOT caused by any changes in this phase.

### apps/imports/tests/test_services.py::TestGiftExport::test_export_gifts_csv
- Pre-existing failure confirmed by stash comparison
- Related to StreamingHttpResponse CSV export (see MEMORY.md note on silent exceptions)

### apps/insights/tests/test_date_filtering.py::TestActivityHeatmap (4 tests)
- Pre-existing failures confirmed by stash comparison
- Unrelated to coach role permissions

### apps/insights/tests/test_team_trends.py::TestTeamTrendsView::test_counts_donations_by_week
- Pre-existing failure confirmed by stash comparison
- Unrelated to coach role permissions
