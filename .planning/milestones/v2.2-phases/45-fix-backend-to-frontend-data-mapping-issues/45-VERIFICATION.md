---
phase: 45-fix-backend-to-frontend-data-mapping-issues
verified: 2026-03-07T00:00:00Z
status: human_needed
score: 13/13 automated must-haves verified
re_verification: false
human_verification:
  - test: "Navigate to /contacts/new, leave First Name and Last Name blank, enter 'Test Org Ltd' in Organization Name, click Create Contact"
    expected: "Contact is created successfully without validation error. Contact appears in list with 'Test Org Ltd' in Name column."
    why_human: "Form validation behavior and React rendering cannot be verified by grep or tsc alone — already confirmed once during Plan 04 but no automated regression guard exists"
  - test: "Navigate to contact list, search for a partial org name (e.g. first 4 characters of an org contact's organization_name)"
    expected: "Org contact appears in search results"
    why_human: "Search UX behavior requires running UI; backend search is verified by pytest but frontend wiring of the search box to the correct endpoint is UI-level"
  - test: "Open an org contact detail page, click Edit, change Organization Name, save"
    expected: "Organization Name field is pre-populated; saved value persists after returning to detail page; no server-side validation error"
    why_human: "Edit roundtrip (pre-population + PATCH round-trip) requires running UI; already verified in Plan 04 manual check but warrants regression check after migration 0008"
---

# Phase 45: Fix Backend-to-Frontend Data Mapping Issues — Verification Report

**Phase Goal:** Fix all backend-to-frontend data mapping issues for organization contacts — organization_name must flow correctly through model, serializers, search, CSV export, TypeScript interfaces, React form, and detail view.
**Verified:** 2026-03-07
**Status:** human_needed (all automated checks pass; 3 UI behaviors require human regression check)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Contact.full_name returns organization_name when first_name and last_name are both blank | VERIFIED | `apps/contacts/models.py` line 154-155: `name = f'..'.strip(); return name or self.organization_name` |
| 2 | Contact.first_name and last_name allow blank values at model level | VERIFIED | `models.py` line 64-65: both fields have `blank=True`; migration `0008_allow_blank_first_last_name` exists |
| 3 | ContactListSerializer includes organization_name | VERIFIED | `serializers.py` line 21: `'organization_name'` present in fields list |
| 4 | ContactDetailSerializer includes organization_name and it is writable | VERIFIED | `serializers.py` line 52: `'organization_name'` in fields; NOT in read_only_fields; has `required=False, allow_blank=True` on first_name/last_name |
| 5 | ContactCreateSerializer accepts blank first_name/last_name with non-blank organization_name | VERIFIED | `serializers.py` lines 92-93: explicit `required=False, allow_blank=True` declarations; `organization_name` in Meta.fields (line 103) |
| 6 | Contact list search (search_fields) finds org contacts by organization_name | VERIFIED | `views.py` line 56: `search_fields = ['first_name', 'last_name', 'email', 'organization_name']` |
| 7 | Contact search endpoint Q filter finds org contacts by organization_name | VERIFIED | `views.py` line 266: `Q(organization_name__icontains=query)` present in filter chain |
| 8 | CSV export Name column uses contact.full_name (not f-string) | VERIFIED | `export_views.py` line 70: `sanitize_csv_value(contact.full_name)` |
| 9 | ContactListItem TypeScript interface includes organization_name?: string | VERIFIED | `frontend/src/api/contacts.ts` line 10: `organization_name?: string` present |
| 10 | ContactCreate TypeScript interface includes organization_name?: string | VERIFIED | `frontend/src/api/contacts.ts` line 44: `organization_name?: string` present |
| 11 | ContactForm shows Organization Name input field with relaxed validation | VERIFIED | `ContactForm.tsx`: state init (line 39), useEffect pre-population (line 59), org-aware validate (lines 89-91), JSX input (lines 165-169) |
| 12 | ContactDetail shows organization_name in Contact Information card | VERIFIED | `ContactDetail.tsx` lines 284-287: conditional render with Building2 icon; Building2 imported at line 28 |
| 13 | All 7 TDD tests pass green | VERIFIED | `pytest apps/contacts/tests/test_org_contact_mapping.py -q --no-cov` output: **7 passed** |

**Score:** 13/13 automated must-haves verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/contacts/models.py` | full_name property with organization_name fallback; blank=True on first_name/last_name | VERIFIED | Lines 151-155 (full_name); lines 64-65 (blank=True) |
| `apps/contacts/serializers.py` | organization_name in all 3 serializers; allow_blank on first/last in Create and Detail | VERIFIED | ContactListSerializer (line 21), ContactDetailSerializer (line 52), ContactCreateSerializer (line 103); explicit CharField declarations lines 92-93 and 33-34 |
| `apps/contacts/views.py` | organization_name in search_fields and Q filter | VERIFIED | Line 56 (search_fields); line 266 (Q filter) |
| `apps/contacts/export_views.py` | CSV uses contact.full_name not f-string | VERIFIED | Line 70: `sanitize_csv_value(contact.full_name)` |
| `apps/contacts/tests/test_org_contact_mapping.py` | 7 tests covering all org-contact behaviors | VERIFIED | 7 test functions present; all pass |
| `apps/contacts/tests/factories.py` | OrgContactFactory with blank names and non-blank organization_name | VERIFIED | Lines 43-47: OrgContactFactory subclasses ContactFactory with `first_name = ''`, `last_name = ''`, `organization_name = factory.LazyFunction(lambda: fake.company())` |
| `apps/contacts/migrations/0008_allow_blank_first_last_name.py` | Migration for blank=True on first_name/last_name | VERIFIED | File exists; generated 2026-03-08; alters both fields |
| `frontend/src/api/contacts.ts` | organization_name on ContactListItem and ContactCreate | VERIFIED | Line 10 (ContactListItem); line 44 (ContactCreate); ContactDetail inherits via extends |
| `frontend/src/pages/contacts/ContactForm.tsx` | Organization Name input + relaxed validation + useEffect pre-population | VERIFIED | 5 occurrences of organization_name confirmed |
| `frontend/src/pages/contacts/ContactDetail.tsx` | organization_name display in Contact Information card with Building2 icon | VERIFIED | Lines 28, 284-287 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `models.py` full_name | `export_views.py` | `contact.full_name` property call | WIRED | export_views.py line 70 uses `contact.full_name` directly |
| `models.py` full_name | `serializers.py` | `full_name = serializers.CharField(read_only=True)` | WIRED | serializers.py line 15 and 32 |
| `api/contacts.ts` ContactListItem | `ContactForm.tsx` | ContactCreate interface typed as formData | WIRED | ContactForm.tsx uses `useState<ContactCreate>({organization_name: ""})` |
| `api/contacts.ts` ContactListItem | `ContactDetail.tsx` | `contact.organization_name` access | WIRED | ContactDetail.tsx lines 284-287 render `contact.organization_name` |
| `views.py` search_fields | DRF SearchFilter | DRF auto-applies search_fields | WIRED | `organization_name` added to search_fields list at line 56 |
| `views.py` Q filter | ContactSearchView | Q chain in get_queryset | WIRED | `Q(organization_name__icontains=query)` at line 266 |

---

## Requirements Coverage

The requirement IDs ORG-01 through ORG-05 referenced across all 4 plans DO NOT appear in `.planning/REQUIREMENTS.md`. They are not listed in the requirements table, not defined under any section heading, and not mapped in the Traceability section.

**Status: ORPHANED REQUIREMENT IDs**

| Requirement | Defined In | In REQUIREMENTS.md | Status |
|-------------|-----------|-------------------|--------|
| ORG-01 | Plans 01-04 | No | ORPHANED — ID used but never defined in REQUIREMENTS.md |
| ORG-02 | Plans 01-04 | No | ORPHANED |
| ORG-03 | Plans 01-04 | No | ORPHANED |
| ORG-04 | Plans 01-04 | No | ORPHANED |
| ORG-05 | Plans 01-04 | No | ORPHANED |

**Assessment:** The underlying functionality these IDs represent is fully implemented and verified (see Observable Truths above). The gap is documentation-only: REQUIREMENTS.md was not updated to define the ORG-xx requirement set or add them to the Traceability table. This is a documentation debt, not a functional gap. No code changes are needed.

**Recommendation:** Add ORG-01 through ORG-05 definitions to REQUIREMENTS.md and map them to Phase 45 in the Traceability table.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned all modified files for TODO/FIXME, placeholder returns (`return null`, `return []`), empty handlers, and console.log-only implementations. None found in phase scope.

---

## Human Verification Required

### 1. Create org contact via UI form

**Test:** Navigate to `/contacts/new`. Leave First Name and Last Name blank. Enter an organization name (e.g., "Acme Foundation"). Click Create Contact.
**Expected:** Contact is created successfully. No validation error blocks submission. Contact appears in the contact list with the organization name in the Name column.
**Why human:** React form validation and submission behavior requires running UI. The backend `ContactCreateSerializer` is verified by pytest, but the frontend `validate()` function and `createContact()` API call path can only be exercised in the browser.

### 2. Search for org contact by organization name

**Test:** With an org contact in the system, use the search box on the contacts list page to search for the first few characters of its organization name.
**Expected:** The org contact appears in search results.
**Why human:** The backend search endpoints are pytest-verified. The frontend wiring of the search box to `/contacts/search/` or `/contacts/?search=` requires running UI to confirm no regression.

### 3. Edit org contact roundtrip

**Test:** Open an org contact's detail page. Click Edit. Verify the Organization Name field is pre-populated. Change the value, save. Return to the detail page.
**Expected:** Organization Name field was pre-filled on load. Saved value is persisted. No server-side error (which would indicate the migration or serializer allow_blank fix regressed).
**Why human:** The pre-population logic (`useEffect` in ContactForm) and the PATCH request path (ContactDetailSerializer with `allow_blank=True`) require the running stack to exercise together. This was verified manually during Plan 04 but has no automated regression test.

---

## Gaps Summary

No functional gaps found. All 13 automated must-haves are verified against the actual codebase. The 7 TDD tests pass. All artifacts exist, are substantive, and are correctly wired.

The only gap is documentation: ORG-01 through ORG-05 requirement IDs are used in plans and summaries but are never defined in REQUIREMENTS.md. This does not block Phase 46 from proceeding.

Three items require human regression verification because they involve React form interaction and roundtrip UI behavior that cannot be exercised by pytest or tsc.

---

*Verified: 2026-03-07*
*Verifier: Claude (gsd-verifier)*
