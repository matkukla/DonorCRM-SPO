---
phase: 01-duplicate-contact-checking-merging-github-issue-37
plan: 02
subsystem: api
tags: [drf, rest_api, duplicate_detection, contact_merge, serializers, api_views]

# Dependency graph
requires:
  - phase: 01-01
    provides: services.py (find_duplicates_for_contact, scan_duplicates_for_owner, merge_contacts), DismissedDuplicate model, Contact.is_merged/merged_into fields
provides:
  - DuplicateCheckView (POST /api/v1/contacts/duplicates/check/) for pre-creation duplicate checking
  - DuplicateScanView (GET /api/v1/contacts/duplicates/scan/) for batch duplicate scanning
  - MergeContactsView (POST /api/v1/contacts/duplicates/merge/) for contact merging
  - DismissDuplicateView (POST /api/v1/contacts/duplicates/dismiss/) for pair dismissal
  - is_merged=False filtering on ContactListCreateView, ContactDetailView, ContactSearchView
  - Serializers for all duplicate API input/output
affects: [01-03, 01-04, 01-05, 01-06]

# Tech tracking
tech-stack:
  added: []
  patterns: [APIView-based endpoints for non-CRUD operations, mock service layer at view level for SQLite-safe API tests]

key-files:
  created:
    - apps/contacts/tests/test_duplicate_api.py
  modified:
    - apps/contacts/serializers.py
    - apps/contacts/views.py
    - apps/contacts/urls.py

key-decisions:
  - "DuplicateMatchSerializer uses source='contact.field' pattern to flatten nested contact data into top-level response fields"
  - "API tests mock service functions at view level (patch apps.contacts.views.*) to avoid pg_trgm SQLite incompatibility while testing full HTTP cycle"
  - "Duplicate URL patterns placed before <uuid:pk>/ catch-all to prevent UUID converter from capturing literal path segments"
  - "MergeRequestSerializer field_overrides uses CharField child (not ChoiceField) to allow flexible values"

patterns-established:
  - "Mock service layer at view import path for API tests requiring PostgreSQL-only features"
  - "Register literal URL paths before UUID catch-all patterns in Django URL configuration"

requirements-completed: [DUP-01, DUP-02, DUP-03, DUP-04]

# Metrics
duration: 4min
completed: 2026-03-27
---

# Phase 01 Plan 02: REST API Endpoints for Duplicate Detection, Scanning, Merging, and Dismissing Summary

**4 DRF APIView endpoints for duplicate check/scan/merge/dismiss with serializers, merged-contact list filtering, and 9 passing API integration tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T21:50:48Z
- **Completed:** 2026-03-27T21:54:48Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- 4 new API endpoints: duplicate check (POST), duplicate scan (GET), contact merge (POST), pair dismiss (POST)
- 5 serializers for API input validation and output formatting: DuplicateCheckSerializer, DuplicateMatchSerializer, DuplicatePairSerializer, MergeRequestSerializer, DismissRequestSerializer
- Contact list, detail, and search views now exclude is_merged=True contacts
- 9 API integration tests with mocked service layer for SQLite compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Add duplicate serializers, API views, URL patterns, and filter merged contacts from list** - `c9fb2f8` (feat)
2. **Task 2: API integration tests for duplicate endpoints** - `d1f89cd` (test)

## Files Created/Modified
- `apps/contacts/serializers.py` - Added 5 serializers for duplicate API input/output
- `apps/contacts/views.py` - Added 4 APIView classes, added is_merged=False filtering to list/detail/search views
- `apps/contacts/urls.py` - Added 4 duplicate URL patterns before UUID catch-all
- `apps/contacts/tests/test_duplicate_api.py` - 9 API integration tests covering all endpoints

## Decisions Made
- DuplicateMatchSerializer uses `source='contact.field'` pattern to flatten nested contact data into top-level JSON response fields
- API tests mock service functions at view level to avoid pg_trgm SQLite incompatibility while still testing full HTTP request/response cycle
- MergeRequestSerializer field_overrides uses CharField child (more flexible than ChoiceField) to support future override value types
- Duplicate URL patterns registered before `<uuid:pk>/` to prevent Django's UUID converter from capturing literal path segments like "duplicates"

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 4 duplicate API endpoints are live and tested
- Frontend can now consume these endpoints to build the duplicate review UI (Plans 03-06)
- Contact list API already excludes merged contacts, so existing frontend contact list will automatically hide merged-away contacts

## Self-Check: PASSED

All created/modified files verified present. Both commit hashes verified in git log.

---
*Phase: 01-duplicate-contact-checking-merging-github-issue-37*
*Completed: 2026-03-27*
