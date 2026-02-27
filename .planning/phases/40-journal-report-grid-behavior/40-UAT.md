---
status: complete
phase: 40-journal-report-grid-behavior
source: 40-01-SUMMARY.md, 40-02-SUMMARY.md
started: 2026-02-27T20:00:00Z
updated: 2026-02-27T20:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Report Tab Metric Cards
expected: Open a journal detail page and click the Report tab. You should see 4 metric cards at the top: Total Contacts, With Decisions, Confirmed $, and Pending.
result: pass

### 2. Goal Progress Bar
expected: Below the metric cards, a goal progress bar shows how much of the journal's goal has been reached based on confirmed amounts.
result: pass

### 3. Contacts by Stage Bar Chart
expected: A bar chart titled "Contacts by Stage" shows distribution of contacts across pipeline stages (Contact, Meet, Close, Decision, Thank, Next Steps).
result: pass

### 4. Decision Status Donut Chart
expected: A donut chart titled "Decision Status" shows breakdown of decisions (e.g., confirmed, declined, pending) with color-coded segments.
result: issue
reported: "Some reports have 'No contacts in this journal' even though they are there"
severity: major
note: Pre-existing bug — Grid tab sends ?journal= but backend expects ?journal_id=, causing Grid to leak contacts from all journals. Report tab correctly uses journal_id and accurately shows 0 contacts for empty journals. Root cause is in frontend/src/api/journals.ts line 94 (getJournalMembers param mismatch), not in Phase 40 code.

### 5. Conditional Alert Cards
expected: If any contacts have no activity in 30+ days, a "Stalled Contacts" alert card appears. If there are open next steps, an "Open Next Steps" alert card appears. If neither condition applies, no alert cards are shown.
result: pass

### 6. Date Range Picker
expected: A date range picker is visible on the report tab. Selecting a date range filters the chart data and decision metrics to that period. Total Contacts (snapshot) and Next Steps (current state) remain unaffected by the date filter.
result: pass

### 7. Decision Column Position in Grid
expected: On the journal detail Grid tab, columns appear in this order: Contact > Meet > Close > Decision > Thank > Next Steps. The Decision column sits between Close and Thank.
result: issue
reported: "Next steps is duplicated. Remove the column where it is just the check box and keep the one where you can add a next step"
severity: major
fix: Removed 'next_steps' from STAGES_AFTER_DECISION in JournalGrid.tsx so only the actionable NextStepsCell column remains.

### 8. Instant Stage Toggle (Unchecked)
expected: In the grid, click an unchecked stage checkbox. The checkbox immediately fills/checks without opening any dialog. A brief loading spinner may appear while the event is created.
result: pass

### 9. Checked Stage Unchecks
expected: Click a stage checkbox that is already checked. The checkbox unchecks (deletes the stage events for that stage) with a loading spinner during the operation. No dialog or confirmation.
result: pass

### 10. Independent Stage Toggles
expected: Check a later stage (e.g., "Close") without checking earlier stages (e.g., "Contact", "Meet"). The later stage checks independently -- earlier stages remain unchecked. No warning toasts or sequential enforcement.
result: pass

## Summary

total: 10
passed: 8
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "Decision Status donut chart shows accurate data for the current journal"
  status: failed
  reason: "User reported: Some reports have 'No contacts in this journal' even though they are there"
  severity: major
  test: 4
  root_cause: "frontend/src/api/journals.ts line 94 sends ?journal= but backend expects ?journal_id= — Grid tab leaks contacts from all journals, Report tab correctly scopes and shows 0 for truly empty journals. Pre-existing bug, not introduced by Phase 40."
  artifacts:
    - path: "frontend/src/api/journals.ts"
      issue: "getJournalMembers sends param 'journal' instead of 'journal_id'"
    - path: "apps/journals/views.py"
      issue: "members list action reads 'journal_id' from query_params (line 229)"
  missing:
    - "Change params.append('journal', journalId) to params.append('journal_id', journalId) in getJournalMembers"
  debug_session: ".planning/debug/journal-report-empty-state.md"

- truth: "Grid columns appear without duplication: Contact > Meet > Close > Decision > Thank > Next Steps"
  status: fixed
  reason: "User reported: Next steps is duplicated — checkbox column and actionable NextStepsCell column both present"
  severity: major
  test: 7
  root_cause: "STAGES_AFTER_DECISION included 'next_steps' which rendered a StageCell checkbox, plus separate NextStepsCell column"
  artifacts:
    - path: "frontend/src/pages/journals/components/JournalGrid.tsx"
      issue: "STAGES_AFTER_DECISION contained 'next_steps' creating duplicate column"
  missing: []
  fix_applied: "Removed 'next_steps' from STAGES_AFTER_DECISION array"
