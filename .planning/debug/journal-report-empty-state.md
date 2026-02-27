---
status: diagnosed
trigger: "Journal report pages show 'No contacts in this journal' even though contacts exist"
created: 2026-02-27T00:00:00Z
updated: 2026-02-27T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED -- Query param name mismatch between frontend and backend for journal members endpoint causes Grid tab to show contacts from ALL journals while Report tab correctly scopes to the specific journal.
test: Verified by reading both endpoints
expecting: N/A -- root cause confirmed
next_action: Report diagnosis

## Symptoms

expected: Report tab shows metrics, charts, and alerts for journals that have contacts
actual: Some journal report pages show "No contacts in this journal yet." despite contacts appearing in the Grid tab
errors: None (logic/data bug, not an error)
reproduction: User has multiple journals. Journal A has contacts, Journal B has no contacts. Open Journal B, see contacts in Grid tab (leaked from Journal A), switch to Report tab, see "No contacts in this journal yet."
started: Since the journal-report feature was introduced

## Eliminated

- hypothesis: Date filtering removes contacts from the report count
  evidence: Backend line 577-591 shows `members` queryset has NO date filtering; `total_contacts = members.count()` always reflects true membership regardless of date range
  timestamp: 2026-02-27T00:01:00Z

- hypothesis: Data shape mismatch between backend response and frontend expectations
  evidence: Backend returns `metrics.total_contacts` as integer, frontend type `JournalReportData` expects `number`, and the empty-state check `data.metrics.total_contacts === 0` correctly tests the value
  timestamp: 2026-02-27T00:05:00Z

- hypothesis: Wrong journalId passed to the Report component
  evidence: JournalDetail.tsx line 149 passes `id ?? ""` from useParams, same ID used for both Grid and Report tabs
  timestamp: 2026-02-27T00:06:00Z

## Evidence

- timestamp: 2026-02-27T00:01:00Z
  checked: Backend journal_report action (views.py lines 554-648)
  found: `members = JournalContact.objects.filter(journal=journal)` on line 577, `total_contacts = members.count()` on line 591. Date filtering only on events/decisions (lines 583-588). Report correctly scopes to the specific journal.
  implication: Report endpoint is correct.

- timestamp: 2026-02-27T00:02:00Z
  checked: Frontend empty state condition (ReportCharts.tsx line 152)
  found: `if (data && data.metrics.total_contacts === 0)` shows "No contacts in this journal yet."
  implication: Empty state triggers when backend returns 0 contacts for this journal.

- timestamp: 2026-02-27T00:07:00Z
  checked: Frontend getJournalMembers API function (journals.ts line 94)
  found: Sends query param as `journal` -- `params.append('journal', journalId)`
  implication: This is the WRONG param name for the backend.

- timestamp: 2026-02-27T00:08:00Z
  checked: Backend JournalContactListCreateView.get_queryset() (views.py lines 228-231)
  found: Reads query param as `journal_id` -- `self.request.query_params.get('journal_id')`. The `filterset_fields` is only `['contact__status']`, NOT `['journal']`. So the `?journal=<uuid>` param is COMPLETELY IGNORED.
  implication: The journal members list endpoint returns ALL members from ALL non-archived journals for the user, not scoped to any specific journal.

- timestamp: 2026-02-27T00:09:00Z
  checked: Frontend getJournalReport API function (journals.ts line 250)
  found: Correctly sends `params.append('journal_id', journalId)` -- matches what the backend expects.
  implication: The Report endpoint is correctly scoped. The mismatch is only in the members list endpoint.

- timestamp: 2026-02-27T00:10:00Z
  checked: JournalDetail.tsx rendering (lines 101-149)
  found: Grid tab uses `useJournalMembers(id)` which calls the broken members endpoint, Report tab uses `useJournalReport(id)` which calls the correct report endpoint.
  implication: Grid and Report tabs show data from different scopes. Grid shows ALL contacts across journals; Report correctly shows only this journal's contacts.

## Resolution

root_cause: Query parameter name mismatch in the journal members API call. The frontend `getJournalMembers()` (frontend/src/api/journals.ts line 94) sends `?journal=<uuid>` but the backend `JournalContactListCreateView` (apps/journals/views.py line 229) expects `?journal_id=<uuid>`. Because the param is silently ignored, the members list returns ALL contacts from ALL of the user's non-archived journals instead of just the specified journal. The Report tab correctly uses `journal_id` and returns 0 contacts for journals that truly have none. The user perceives a bug because the Grid tab (incorrectly) shows contacts while the Report tab (correctly) shows none.
fix: Change frontend/src/api/journals.ts line 94 from `params.append('journal', journalId)` to `params.append('journal_id', journalId)`
verification:
files_changed: []
