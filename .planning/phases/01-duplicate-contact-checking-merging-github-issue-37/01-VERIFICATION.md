---
phase: 01-duplicate-contact-checking-merging-github-issue-37
verified: 2026-03-27T17:30:00Z
status: human_needed
score: 22/22 automated must-haves verified
re_verification: false
human_verification:
  - test: "Navigate to /contacts/duplicates — verify sidebar shows Duplicates link with GitMerge icon"
    expected: "Duplicates nav item appears in sidebar after Contacts, with GitMerge icon"
    why_human: "Visual rendering of sidebar icon cannot be verified programmatically"
  - test: "Click Scan for Duplicates — verify toast shows pair count or 'No new duplicates found'"
    expected: "Toast appears: 'Found N potential duplicate pairs.' or 'No new duplicates found.'"
    why_human: "Requires running frontend against live PostgreSQL to test pg_trgm scan"
  - test: "Open /contacts/duplicates/:pairId for a real pair — verify side-by-side comparison renders"
    expected: "Both contact names appear in column headers, fields with different values show radio buttons, identical fields collapse to single display"
    why_human: "Requires real contacts with overlapping fields; MergeFieldRow rendering behavior needs visual inspection"
  - test: "Select survivor on merge view — verify field radios reset to survivor's values"
    expected: "Switching survivor from Left to Right resets all field override selectors to Right's values"
    why_human: "Controlled state reset on survivor change is interactive behavior"
  - test: "Create a contact with name matching an existing — verify 'Possible Duplicates Found' dialog appears"
    expected: "Dialog shows up to 3 matches with name, email, confidence badge, View Contact link"
    why_human: "Requires running full frontend + backend against PostgreSQL for pg_trgm to fire"
  - test: "Click Keep Editing — verify dialog closes and form state is preserved"
    expected: "Dialog disappears, form fields retain previous input values"
    why_human: "Form state preservation after dialog dismissal requires interactive browser test"
  - test: "Execute a merge — verify loser disappears from contact list and survivor shows merged gifts total"
    expected: "Loser contact (is_merged=True) no longer appears in GET /api/v1/contacts/; survivor's total_given includes transferred gifts"
    why_human: "End-to-end merge with real PostgreSQL data + stat recalculation verification"
---

# Phase 01: Duplicate Contact Checking and Merging — Verification Report

**Phase Goal:** Implement duplicate contact detection and merging — creation-time check, batch scan, side-by-side review UI, field-by-field merge with FK reassignment, dismissal tracking, merge audit trail

**Verified:** 2026-03-27T17:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | find_duplicates_for_contact returns scored matches from owner-scoped contacts using name similarity, exact email, and exact phone | VERIFIED | `services.py:28` — function exists with TrigramSimilarity + email/phone exact match, filters `is_merged=False`, 3-tier confidence; 8 tests pass |
| 2  | scan_duplicates_for_owner returns deduplicated pairs excluding dismissed pairs and merged contacts | VERIFIED | `services.py:125` — excludes dismissed pairs via canonical set, filters is_merged=False; test_scan_excludes_dismissed_pairs + test_scan_excludes_merged_contacts pass |
| 3  | merge_contacts atomically reassigns all FK relationships to survivor, union-merges groups, soft-deletes loser, recalculates stats, and creates audit log | VERIFIED | `services.py:231` — @transaction.atomic, select_for_update(), 6 FK updates (Gift, RecurringGift, Task, PrayerIntention, Event, JournalContact), groups.add(), is_merged=True, update_giving_stats(), ContactMergeLog created; 13 tests pass |
| 4  | DismissedDuplicate canonicalizes pair ordering (contact_a_id < contact_b_id) and has unique constraint | VERIFIED | `models.py:263-265` — save() method swaps IDs when contact_a_id > contact_b_id; UniqueConstraint on contact_a/contact_b; test_dismissed_duplicate_canonicalization passes |
| 5  | JournalContact merge handles unique_together conflict by transferring stage events and deleting loser JournalContact | VERIFIED | `services.py:327` — _merge_journal_contacts checks for survivor_jc conflict, transfers JournalStageEvent/Decision/NextStep to survivor_jc, deletes loser_jc; test_merge_journal_contact_with_conflict passes |
| 6  | POST /api/v1/contacts/duplicates/check/ returns potential duplicates for given contact data | VERIFIED | `views.py:417` DuplicateCheckView, `urls.py:32` registered before uuid catch-all; 9 API tests pass |
| 7  | GET /api/v1/contacts/duplicates/scan/ returns all duplicate pairs for the authenticated user | VERIFIED | `views.py:433` DuplicateScanView; `urls.py:33`; 9 API tests pass |
| 8  | POST /api/v1/contacts/duplicates/merge/ merges two contacts and returns the survivor | VERIFIED | `views.py:444` MergeContactsView calls merge_contacts, returns ContactDetailSerializer(survivor); 9 API tests pass |
| 9  | POST /api/v1/contacts/duplicates/dismiss/ marks a pair as not-duplicates | VERIFIED | `views.py:464` DismissDuplicateView creates DismissedDuplicate; `urls.py:35`; 9 API tests pass |
| 10 | Contact list view excludes is_merged=True contacts | VERIFIED | `views.py:77` ContactListCreateView, `views.py:113` ContactDetailView, `views.py:294` ContactSearchView all filter is_merged=False |
| 11 | radio-group and alert-dialog shadcn components are installed and importable | VERIFIED | Files exist: `frontend/src/components/ui/radio-group.tsx` (15 RadioGroup references), `frontend/src/components/ui/alert-dialog.tsx` (53 AlertDialog references); tsc passes |
| 12 | TypeScript types exist for DuplicateMatch, DuplicatePair, MergeRequest, DismissRequest | VERIFIED | `api/contacts.ts:73,88,97,104` — all 4 interfaces defined |
| 13 | API functions exist for checkDuplicates, scanDuplicates, mergeContacts, dismissDuplicate | VERIFIED | `api/contacts.ts:259,270,276,282` — all 4 async functions call correct backend endpoints |
| 14 | React Query hooks exist for useDuplicateScan, useMergeContacts, useDismissDuplicate, useCheckDuplicates | VERIFIED | `useContacts.ts:141,150,158,172` — all 4 hooks defined |
| 15 | Calling useMergeContacts().mutate() invalidates contacts, duplicates, and dashboard query caches | VERIFIED | `useContacts.ts:162-171` — onSuccess invalidates ["contacts"], ["duplicates"], ["dashboard"]; hook tests pass |
| 16 | User can navigate to /contacts/duplicates from sidebar | VERIFIED | `Sidebar.tsx:47` — `{ label: "Duplicates", href: "/contacts/duplicates", icon: <GitMerge> }` after Contacts entry; `App.tsx:120` route registered |
| 17 | Duplicates page shows duplicate pairs with confidence badges, scan button, dismiss, and review | VERIFIED | `DuplicateList.tsx` — 164 lines, imports useDuplicateScan/useDismissDuplicate, renders "Potential Duplicates", "Scan for Duplicates" button, "Not Duplicates" dismiss, empty state "No duplicates found" |
| 18 | User can select survivor and override individual fields on merge view; external_id included | VERIFIED | `DuplicateMergeView.tsx` — 383 lines, survivorSide state, MERGE_FIELDS with external_id/external_constituent_id, MergeFieldRow per field, AlertDialog confirmation |
| 19 | AlertDialog confirmation appears before merge executes | VERIFIED | `DuplicateMergeView.tsx:360` — "Merge these contacts?", "Yes, Merge Contacts", AlertDialogTrigger wraps the CTA |
| 20 | Keep Both Contacts dismisses pair and navigates back | VERIFIED | `DuplicateMergeView.tsx:349` — "Keep Both Contacts" button calls dismissMutation + navigate("/contacts/duplicates") |
| 21 | Creating a contact triggers duplicate check before save; dialog warns about top 3 matches | VERIFIED | `ContactForm.tsx:55,124,134` — useCheckDuplicates, mutateAsync before create, setShowDuplicateDialog(true) on matches; DuplicateWarningDialog shows with matches.slice(0,3) |
| 22 | Duplicate check API failure degrades gracefully; creation proceeds with warning toast | VERIFIED | `ContactForm.tsx:143` — toast.warning("Unable to check for duplicates..."); creation proceeds; 9 vitest behavioral tests pass |

**Score:** 22/22 truths verified (automated)

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `config/settings/base.py` | VERIFIED | Line 29: `'django.contrib.postgres'` in INSTALLED_APPS |
| `apps/contacts/models.py` | VERIFIED | DismissedDuplicate (line 244), ContactMergeLog (line 269), is_merged (line 112), merged_into (line 113) all present; canonical pair ordering in save() |
| `apps/contacts/services.py` | VERIFIED | find_duplicates_for_contact, scan_duplicates_for_owner, merge_contacts, _merge_journal_contacts all defined; @transaction.atomic, select_for_update(), TrigramSimilarity, MERGEABLE_FIELDS with external IDs |
| `apps/contacts/migrations/0009_add_pg_trgm_and_merge_models.py` | VERIFIED | Exists, contains TrigramExtension (2 occurrences), depends on 0008_allow_blank_first_last_name |
| `apps/contacts/serializers.py` | VERIFIED | DuplicateCheckSerializer (145), DuplicateMatchSerializer (153), DuplicatePairSerializer (168), MergeRequestSerializer (177), DismissRequestSerializer (188) all present |
| `apps/contacts/views.py` | VERIFIED | DuplicateCheckView (417), DuplicateScanView (433), MergeContactsView (444), DismissDuplicateView (464); is_merged=False in 3 views |
| `apps/contacts/urls.py` | VERIFIED | 4 duplicate patterns (lines 32-35) registered before `<uuid:pk>/` catch-all (line 36) |
| `apps/contacts/tests/test_merge.py` | VERIFIED | 13 test functions; all pass |
| `apps/contacts/tests/test_duplicate_detection.py` | VERIFIED | 8 test functions; all pass |
| `apps/contacts/tests/test_duplicate_api.py` | VERIFIED | 9 test functions; all pass |
| `frontend/src/components/ui/radio-group.tsx` | VERIFIED | Exists, RadioGroup defined |
| `frontend/src/components/ui/alert-dialog.tsx` | VERIFIED | Exists, AlertDialog family defined |
| `frontend/src/api/contacts.ts` | VERIFIED | All 4 interfaces and 4 API functions present; apiClient.post/get calls to correct endpoints |
| `frontend/src/hooks/useContacts.ts` | VERIFIED | All 4 React Query hooks present; imports from @/api/contacts |
| `frontend/vitest.config.ts` | VERIFIED | Exists, defineConfig with jsdom environment and path aliases |
| `frontend/src/test/setup.ts` | VERIFIED | Exists, imports @testing-library/jest-dom |
| `frontend/src/hooks/__tests__/useContacts.test.ts` | VERIFIED | 4 tests pass (after npm install) |
| `frontend/src/pages/contacts/DuplicateList.tsx` | VERIFIED | 164 lines; imports useDuplicateScan, useDismissDuplicate; all required copy strings present |
| `frontend/src/pages/contacts/components/ConfidenceBadge.tsx` | VERIFIED | Exists; maps high/medium/low to destructive/warning/secondary |
| `frontend/src/pages/contacts/DuplicateMergeView.tsx` | VERIFIED | 383 lines; MERGE_FIELDS with external_id/external_constituent_id; AlertDialog; useMergeContacts; "Merge Contacts", "Records to Migrate", "Field Comparison", "Merge these contacts?", "Yes, Merge Contacts", "Keep Both Contacts", "Contacts merged successfully" all present |
| `frontend/src/pages/contacts/components/MergeFieldRow.tsx` | VERIFIED | Exists; export function MergeFieldRow defined |
| `frontend/src/pages/contacts/components/DuplicateWarningDialog.tsx` | VERIFIED | "Possible Duplicates Found", "We found contacts...", "Keep Editing", "Create Anyway", "View Contact", target="_blank", matches.slice(0, 3), ConfidenceBadge all present |
| `frontend/src/pages/contacts/ContactForm.tsx` | VERIFIED | useCheckDuplicates, DuplicateWarningDialog, checkDuplicatesMutation.mutateAsync, setShowDuplicateDialog, handleCreateAnyway, "Checking...", "Unable to check for duplicates" all present |
| `frontend/src/pages/contacts/__tests__/ContactFormDuplicateCheck.test.tsx` | VERIFIED | 9 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `apps/contacts/services.py` | `apps/contacts/models.py` | `from apps.contacts.models import Contact, ContactMergeLog, DismissedDuplicate` | WIRED | Line 15 |
| `apps/contacts/services.py` | `apps/journals/models.py` | `from apps.journals.models import Decision, JournalContact, JournalStageEvent, NextStep` | WIRED | Line 339 (inside _merge_journal_contacts) |
| `apps/contacts/views.py` | `apps/contacts/services.py` | `from apps.contacts.services import find_duplicates_for_contact, scan_duplicates_for_owner, merge_contacts` | WIRED | Line 25 |
| `apps/contacts/urls.py` | `apps/contacts/views.py` | DuplicateCheckView, DuplicateScanView, MergeContactsView, DismissDuplicateView | WIRED | Lines 32-35 |
| `frontend/src/hooks/useContacts.ts` | `frontend/src/api/contacts.ts` | imports checkDuplicates, scanDuplicates, mergeContacts, dismissDuplicate | WIRED | Lines 15-18 |
| `frontend/src/api/contacts.ts` | `/api/v1/contacts/duplicates/*` | apiClient.post/get calls to correct endpoint paths | WIRED | Lines 259-285 |
| `frontend/src/pages/contacts/DuplicateList.tsx` | `frontend/src/hooks/useContacts.ts` | useDuplicateScan, useDismissDuplicate | WIRED | Lines 3, 16-17 |
| `frontend/src/App.tsx` | `frontend/src/pages/contacts/DuplicateList.tsx` | Import + Route element | WIRED | Line 21, 120 |
| `frontend/src/App.tsx` | `frontend/src/pages/contacts/DuplicateMergeView.tsx` | React.lazy + Route element | WIRED | Line 39, 121 |
| `frontend/src/pages/contacts/DuplicateMergeView.tsx` | `frontend/src/hooks/useContacts.ts` | useContact, useMergeContacts, useDismissDuplicate, useContactDonations, useContactPledges, useContactTasks, useContactJournals | WIRED | Lines 4-11 |
| `frontend/src/pages/contacts/DuplicateMergeView.tsx` | `frontend/src/api/contacts.ts` | type ContactDetail | WIRED | Line 39 |
| `frontend/src/pages/contacts/ContactForm.tsx` | `frontend/src/hooks/useContacts.ts` | useCheckDuplicates | WIRED | Line 3 |
| `frontend/src/pages/contacts/components/DuplicateWarningDialog.tsx` | `frontend/src/pages/contacts/components/ConfidenceBadge.tsx` | ConfidenceBadge import and usage | WIRED | Verified by tsc pass and vitest tests |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `DuplicateMergeView.tsx` | leftContact, rightContact | useContact(leftId), useContact(rightId) | Yes — calls GET /api/v1/contacts/:id/, backed by ContactDetailSerializer reading DB | FLOWING |
| `DuplicateMergeView.tsx` | donationsList, pledgesList, tasksList, journalsList | useContactDonations/Pledges/Tasks/Journals(loserId) | Yes — backed by live API endpoints reading DB | FLOWING |
| `DuplicateList.tsx` | data (DuplicatePair[]) | useDuplicateScan() -> scanDuplicates() -> GET .../duplicates/scan/ | Yes — DuplicateScanView calls scan_duplicates_for_owner which queries Contact model | FLOWING (pg_trgm-dependent; SQLite fallback skips name matching gracefully) |
| `ContactForm.tsx` | duplicateMatches | useCheckDuplicates().mutateAsync -> checkDuplicates() -> POST .../duplicates/check/ | Yes — DuplicateCheckView calls find_duplicates_for_contact | FLOWING (pg_trgm-dependent) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 21 backend tests pass (merge + detection) | `python -m pytest apps/contacts/tests/test_merge.py apps/contacts/tests/test_duplicate_detection.py -x --no-cov -q` | 21 passed | PASS |
| All 9 API integration tests pass | `python -m pytest apps/contacts/tests/test_duplicate_api.py -x --no-cov -q` | 9 passed | PASS |
| All 13 frontend vitest tests pass | `cd frontend && npx vitest run` | 13 passed (2 test files) | PASS |
| TypeScript compiles with 0 errors | `cd frontend && npx tsc --noEmit` | No output (exit 0) | PASS |
| Django system check passes | `python manage.py check` | "0 issues" | PASS |
| URLs: duplicate patterns before uuid catch-all | grep check on urls.py | lines 32-35 before line 36 | PASS |
| Frontend routes: /contacts/duplicates before /contacts/:id | grep check on App.tsx | lines 120-121 before line 122 | PASS |
| vitest installed in node_modules | `ls frontend/node_modules/vitest` | Present after `npm install` | PASS |

Note: vitest and @testing-library packages were listed in package.json but NOT installed in node_modules before npm install was run during this verification. Running `npm install` in the frontend directory resolves the dependency gap. Tests pass after installation.

### Requirements Coverage

There is no REQUIREMENTS.md file in .planning/ for this project. Requirements are defined inline in PLAN frontmatter under the `requirements:` field.

| Requirement | Plan(s) | Description (from PLAN context) | Status | Evidence |
|-------------|---------|--------------------------------|--------|----------|
| DUP-01 | 01-02, 01-03, 01-06 | Creation-time duplicate check fires on contact form submit | SATISFIED | ContactForm.tsx: useCheckDuplicates, DuplicateWarningDialog; test_duplicate_api.py covers API; 9 vitest tests |
| DUP-02 | 01-01, 01-02, 01-03, 01-04 | Batch scan returns duplicate pairs for owner | SATISFIED | scan_duplicates_for_owner in services.py; DuplicateScanView; DuplicateList.tsx; useDuplicateScan hook |
| DUP-03 | 01-01, 01-03, 01-05 | Merge reassigns all FKs atomically (6 FK types) | SATISFIED | merge_contacts @transaction.atomic; 13 merge tests pass |
| DUP-04 | 01-01, 01-02, 01-03, 01-04 | Dismissed pairs excluded from scan; DismissedDuplicate persisted | SATISFIED | scan_duplicates_for_owner excludes dismissed; DismissDuplicateView; test_scan_excludes_dismissed_pairs |
| DUP-05 | 01-01, 01-05 | Merge creates audit log (ContactMergeLog) | SATISFIED | merge_contacts creates ContactMergeLog with survivor, loser_id, loser_name, field_overrides, records_migrated; test_merge_creates_audit_log |
| DUP-06 | 01-01, 01-05 | Soft delete marks loser as merged (is_merged=True + merged_into FK) | SATISFIED | merge_contacts sets loser.is_merged=True, loser.merged_into=survivor; test_merge_soft_deletes_loser |
| DUP-07 | 01-01, 01-05 | JournalContact unique_together conflict handled during merge | SATISFIED | _merge_journal_contacts transfers stage events, deletes loser JC; test_merge_journal_contact_with_conflict |
| DUP-08 | 01-01, 01-05 | Survivor stats recalculated after merge | SATISFIED | merge_contacts calls survivor.update_giving_stats() inside transaction; test_merge_recalculates_stats |

All 8 requirement IDs (DUP-01 through DUP-08) are satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `apps/contacts/services.py` | 113 | `# SQLite or pg_trgm not available -- skip name matching` (graceful degradation comment) | Info | Intentional design: SQLite test environments skip trigram matching, fall back to exact match only. This is correct behavior documented as a pattern in SUMMARY.md. Not a stub. |
| `apps/contacts/tests/test_integration.py` | 189 | `test_admin_sees_all_contacts` fails with 404 | Warning | PRE-EXISTING failure — test_integration.py was NOT modified in this phase. The test assumes admin sees all contacts across owners, but `get_visible_user_ids()` for admin role returns `{user.id}` only (cross-user access is View As only). The `is_merged=False` filter added in Plan 02 is NOT the cause of this 404. The failure predates this phase by multiple milestones. |

No stub anti-patterns found in phase-created files. All artifacts have substantive implementations with real data flowing.

### Human Verification Required

#### 1. Sidebar Visual Rendering

**Test:** Navigate to the DonorCRM app in a browser. Observe the left sidebar.
**Expected:** "Duplicates" nav item appears in the sidebar, positioned after "Contacts", with a GitMerge icon.
**Why human:** Icon rendering and sidebar layout position cannot be verified programmatically.

#### 2. Duplicate Scan with Real PostgreSQL

**Test:** Log in as a missionary user. Navigate to /contacts/duplicates. Click "Scan for Duplicates".
**Expected:** After scan, either a toast appears: "Found N potential duplicate pairs." (if duplicates exist) or "No new duplicates found." (if clean). If duplicates found, the table shows pairs with confidence badges (High=red, Medium=yellow, Low=gray).
**Why human:** pg_trgm is PostgreSQL-only. All scan tests mock the service layer. Real behavior needs a running PostgreSQL instance.

#### 3. Side-by-Side Merge View Rendering

**Test:** Click "Review" on a duplicate pair. Observe the merge view at /contacts/duplicates/:pairId.
**Expected:** Two contact names appear as column headers. Fields with different values show radio buttons (one per cell for left/right selection). Fields with identical values show a single centered value. External ID and Constituent ID rows appear if both contacts have different non-empty values.
**Why human:** MergeFieldRow's identical-value collapse and radio rendering requires visual inspection with real data.

#### 4. Survivor Selection Resets Field Overrides

**Test:** On the merge view, select "Keep Right" as the survivor. Observe all field rows. Then switch to "Keep Left".
**Expected:** On each switch, all per-field radio selections reset to the new survivor's side. The controlled state reset fires correctly.
**Why human:** Interactive state management requires browser testing.

#### 5. Creation-Time Warning Dialog with Real Data

**Test:** Navigate to /contacts/new. Fill in first name and last name matching an existing contact. Click "Create Contact".
**Expected:** "Possible Duplicates Found" dialog appears listing up to 3 matches with name, email, phone, and confidence badge. "View Contact" link opens the matching contact in a new tab.
**Why human:** Requires live PostgreSQL + pg_trgm for the check to find name-similarity matches.

#### 6. Keep Editing Form State Preservation

**Test:** Trigger the duplicate warning dialog. Click "Keep Editing".
**Expected:** Dialog closes. All previously entered form field values (first name, last name, email, phone, notes, etc.) are preserved exactly as entered.
**Why human:** Form state preservation after dialog close requires browser testing.

#### 7. End-to-End Merge Verification

**Test:** Execute a merge on the merge view. Click "Merge Contacts" > "Yes, Merge Contacts".
**Expected:** Toast: "Contacts merged successfully." Navigation returns to /contacts/duplicates. The merged-away contact no longer appears in GET /api/v1/contacts/. The surviving contact's total_given includes all transferred gifts.
**Why human:** End-to-end merge with real data, stat recalculation, and UI redirect requires a full running environment.

### Gaps Summary

No automated gaps found. All 22 must-have truths are verified. The one failing test (`test_admin_sees_all_contacts` in test_integration.py) is a pre-existing failure that predates this phase by multiple milestones — the test relies on admin cross-user contact access which was intentionally scoped to View As only in Phase 52. This is not a regression introduced by this phase.

The only finding requiring attention before production deployment:

**vitest/testing-library not installed in node_modules** — package.json lists `vitest: ^4.1.2` and `@testing-library/*` but they were not present in node_modules when verification began. Running `npm install` in the `frontend/` directory resolves this. If CI/CD runs `npm ci` or `npm install` before running tests, this is not an issue. If not, `npm install` must be run before frontend tests can execute.

---

_Verified: 2026-03-27T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
