---
phase: 45-fix-backend-to-frontend-data-mapping-issues
plan: "02"
subsystem: api
tags: [django, rest-framework, contacts, organization, serializer, search, csv-export]

# Dependency graph
requires:
  - phase: 45-01
    provides: OrgContactFactory and 7 failing RED tests for org-contact behaviors
provides:
  - Contact.full_name falls back to organization_name when first/last names blank
  - organization_name in ContactListSerializer, ContactDetailSerializer, ContactCreateSerializer
  - ContactCreateSerializer allows blank first_name/last_name when organization_name present
  - ContactListCreateView.search_fields includes organization_name
  - ContactSearchView Q filter includes organization_name__icontains
  - CSV export Name column uses contact.full_name (covers org contacts)
affects: [45-03, frontend-contact-list, frontend-contact-detail, csv-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "full_name property returns name or self.organization_name (org-contact fallback)"
    - "Explicit allow_blank=True on serializer fields for org-only contacts"

key-files:
  created: []
  modified:
    - apps/contacts/models.py
    - apps/contacts/serializers.py
    - apps/contacts/views.py
    - apps/contacts/export_views.py
    - apps/contacts/tests/test_org_contact_mapping.py

key-decisions:
  - "organization_name NOT added to read_only_fields in ContactDetailSerializer — must remain writable so users can edit it"
  - "ContactCreateSerializer uses explicit CharField declarations for first_name/last_name (allow_blank=True) rather than relying on model defaults"
  - "CSV export uses contact.full_name property instead of f-string — single source of truth for display name logic"

patterns-established:
  - "Org-contact display name: full_name property with 'name or self.organization_name' pattern"

requirements-completed: [ORG-01, ORG-02, ORG-03, ORG-04, ORG-05]

# Metrics
duration: 3min
completed: 2026-03-07
---

# Phase 45 Plan 02: Fix Backend-to-Frontend Data Mapping Summary

**Django Contact model full_name fallback + organization_name in all serializers, search, and CSV export — all 7 RED TDD tests turn GREEN**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-07T19:10:27Z
- **Completed:** 2026-03-07T19:13:34Z
- **Tasks:** 2
- **Files modified:** 5 (4 source + 1 test file URL fix)

## Accomplishments
- Contact.full_name now returns organization_name when first_name and last_name are both blank
- All 3 serializers (List, Detail, Create) expose organization_name; Create serializer allows blank first/last
- /contacts/ list search and /contacts/search/ Q filter both find org contacts by organization_name
- CSV export Name column shows organization_name for org contacts instead of blank

## Task Commits

1. **Task 1: Fix Contact.full_name and all 3 serializers** - `1388522` (feat)
2. **Task 2: Fix search paths and CSV export** - `f9fb6ef` (feat, includes Rule 1 URL auto-fix)

## Files Created/Modified
- `apps/contacts/models.py` - full_name property: `name = f'..'.strip(); return name or self.organization_name`
- `apps/contacts/serializers.py` - organization_name added to ContactListSerializer, ContactDetailSerializer, ContactCreateSerializer; explicit allow_blank on first_name/last_name in Create serializer
- `apps/contacts/views.py` - search_fields + Q filter include organization_name
- `apps/contacts/export_views.py` - CSV Name column uses contact.full_name instead of f-string
- `apps/contacts/tests/test_org_contact_mapping.py` - URL paths corrected (auto-fix, see deviations)

## Decisions Made
- organization_name NOT added to ContactDetailSerializer.read_only_fields — must remain writable so users can edit it via PATCH
- ContactCreateSerializer gets explicit first_name/last_name CharField declarations with allow_blank=True so validators don't reject org-only contacts
- CSV export delegates to full_name property for single source of truth on display names

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed wrong URL paths in test file created by Plan 01**
- **Found during:** Task 2 verification
- **Issue:** test_org_contact_mapping.py used `/contacts/`, `/contacts/search/`, `/contacts/export/` — all returning 404. Actual API is under `/api/v1/` prefix per config/urls.py. Export URL is `/api/v1/contacts/export/csv/` not `/contacts/export/`.
- **Fix:** Updated 4 URL strings in test file to correct `/api/v1/contacts/...` paths
- **Files modified:** apps/contacts/tests/test_org_contact_mapping.py
- **Verification:** All 7 tests PASS after URL correction
- **Committed in:** f9fb6ef (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test URLs)
**Impact on plan:** Auto-fix essential for test correctness — wrong URLs meant 4 tests could never pass. No scope creep.

## Issues Encountered
- Pre-existing failures in apps/contacts/tests/test_integration.py (7 tests) confirmed to be unrelated to this plan — identical failures on clean codebase before any changes. Logged as out-of-scope.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 7 org-contact backend behaviors verified GREEN
- API now correctly exposes organization_name for org contacts in list, detail, create, search, and CSV
- Frontend can display organization_name in contact lists; Phase 45-03 can address frontend rendering

---
*Phase: 45-fix-backend-to-frontend-data-mapping-issues*
*Completed: 2026-03-07*
