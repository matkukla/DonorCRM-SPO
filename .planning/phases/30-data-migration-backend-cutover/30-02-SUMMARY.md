---
phase: 30-data-migration-backend-cutover
plan: 02
subsystem: api
tags: [django, gifts, recurring-gifts, service-cutover, dashboard, insights, serializers, filters]

# Dependency graph
requires:
  - phase: 30-data-migration-backend-cutover
    plan: 01
    provides: Gift/RecurringGift models with data migration and signal handlers
  - phase: 27-new-models-prayer-intentions
    provides: Gift, RecurringGift, Solicitor models
provides:
  - All backend services (contacts, dashboard, insights, users, imports) querying Gift/RecurringGift exclusively
  - Gift/RecurringGift CRUD API endpoints (serializers, views, filters, urls) ready for URL registration
  - Contact.update_giving_stats() using Gift with cents-to-Decimal conversion
  - Late pledge features gracefully returning empty data
affects: [30-03, frontend-api-consumers, dashboard-ui, insights-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: [cents-to-dollars conversion via amount_cents/100 in service aggregations, owner scoping via donor_contact__owner]

key-files:
  created:
    - apps/gifts/serializers.py
    - apps/gifts/views.py
    - apps/gifts/filters.py
    - apps/gifts/urls.py
  modified:
    - apps/contacts/models.py
    - apps/contacts/views.py
    - apps/contacts/urls.py
    - apps/dashboard/services.py
    - apps/dashboard/views.py
    - apps/insights/services.py
    - apps/users/views.py
    - apps/users/serializers.py
    - apps/imports/services.py
    - apps/imports/views.py
    - apps/imports/tasks.py
    - apps/core/management/commands/generate_sample_data.py

key-decisions:
  - "Old SPO import functions removed (returning 410 Gone) rather than ported to Gift model since RE import pipeline supersedes them"
  - "Late pledge features return empty data gracefully rather than raising errors since RecurringGift has no is_late field"
  - "Old property names (has_active_pledge, monthly_pledge_amount) kept as aliases during transition for backward compatibility"

patterns-established:
  - "All service aggregations use amount_cents with /100 conversion for dollar display"
  - "All contact FK paths use donor_contact__owner (not contact__owner) for Gift/RecurringGift models"
  - "Gift API endpoints use GiftFilterSet with individual DateFilter fields (not DateFromToRangeFilter)"

requirements-completed: [MIG-03, MIG-05]

# Metrics
duration: 13min
completed: 2026-02-20
---

# Phase 30 Plan 02: Backend Service Cutover Summary

**All backend services switched from Donation/Pledge to Gift/RecurringGift with cents-to-dollars conversion, Gift CRUD API endpoints created, and legacy import functions removed**

## Performance

- **Duration:** 13 min 6s
- **Started:** 2026-02-21T03:46:35Z
- **Completed:** 2026-02-21T03:59:41Z
- **Tasks:** 4
- **Files modified:** 16

## Accomplishments
- Contact model properties and update_giving_stats() query Gift/RecurringGift with correct cents conversion
- All 20+ dashboard and insights service functions rewritten to use Gift/RecurringGift exclusively
- Gift/RecurringGift CRUD API endpoints with serializers, filters, views, and URL patterns ready for Plan 30-03
- Users, imports, and generate_sample_data all migrated to new models
- Zero imports of apps.donations or apps.pledges outside their own app directories

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Contact model and contact views to use Gift/RecurringGift** - `ad6516b` (feat)
2. **Task 2a: Rewrite dashboard and insights services** - `e0ca343` (feat)
3. **Task 2b: Rewrite imports, users, and generate_sample_data** - `7d3e989` (feat)
4. **Task 3: Create Gift/RecurringGift API endpoints** - `157a76d` (feat)

## Files Created/Modified
- `apps/gifts/serializers.py` - GiftSerializer, GiftCreateSerializer, RecurringGiftSerializer, RecurringGiftCreateSerializer
- `apps/gifts/views.py` - CRUD views with owner scoping for Gift and RecurringGift
- `apps/gifts/filters.py` - GiftFilterSet and RecurringGiftFilterSet with date/amount/contact filters
- `apps/gifts/urls.py` - URL patterns for Gift and RecurringGift endpoints
- `apps/contacts/models.py` - update_giving_stats uses Gift with cents conversion; new recurring gift properties
- `apps/contacts/views.py` - ContactGiftsView and ContactRecurringGiftsView replace old views
- `apps/contacts/urls.py` - Updated imports to use renamed view classes
- `apps/dashboard/services.py` - All functions rewritten for Gift/RecurringGift
- `apps/dashboard/views.py` - GiftSerializer replaces DonationSerializer; PledgeSerializer removed
- `apps/insights/services.py` - All 13+ functions updated for Gift/RecurringGift
- `apps/users/views.py` - CurrentUserView queries RecurringGift for active pledge count
- `apps/users/serializers.py` - get_active_pledge_count queries RecurringGift
- `apps/imports/services.py` - Old SPO functions removed; export_gifts_csv replaces export_donations_csv
- `apps/imports/views.py` - Legacy endpoints return 410 Gone; DonationExportView uses Gift
- `apps/imports/tasks.py` - import_donations_async removed
- `apps/core/management/commands/generate_sample_data.py` - Creates Gift/RecurringGift objects

## Decisions Made
- Removed old SPO import functions entirely (parse_donations_csv, import_donations, etc.) since the RE import pipeline from Phases 28-29 fully supersedes them. Legacy endpoints return HTTP 410 Gone.
- Late pledge features (get_late_donations, late_pledges in needs_attention) return empty data structures to preserve API response shape for frontend compatibility.
- Kept old property names (has_active_pledge, monthly_pledge_amount) as aliases pointing to new implementations for backward compatibility during the transition period.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All backend services exclusively use Gift/RecurringGift models
- Gift/RecurringGift CRUD API endpoints exist and are ready for Plan 30-03 to register in api_urls.py
- Plan 30-03 can safely remove old donations/ and pledges/ app URL includes
- Zero remaining imports of old models outside their own app directories

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 30-data-migration-backend-cutover*
*Completed: 2026-02-20*
