---
created: 2026-02-26T13:57:18.871Z
title: Rebuild journal report component
area: ui
files:
  - frontend/src/components/journal/JournalReport.tsx
  - prompts/journal_report.md
---

## Problem

The journal report component needs to be rebuilt with a specific layout and design. Full spec is in `prompts/journal_report.md`.

Key sections:
1. **Key Metrics** — 4 cards (Total Contacts, With Decisions, Confirmed $, Pending Decisions) in responsive 2-col/4-col grid
2. **Progress Toward Goal** — green progress bar with confirmed amount, legend, and goal labels
3. **Charts** — Contacts by Stage (bar chart with stage colors) + Decision Status (donut chart with status colors)
4. **Alerts** — Conditional stalled contacts (orange) and open next steps (blue) alerts

Uses `journalsApi.getReport(journalId)` API endpoint with React Query. Recharts for charts. Specific hex colors for stages and decision statuses defined in the spec.

Additional requirements from updated prompt:
- **Remove Decision column after Next Steps** — delete the duplicate Decision section at the end entirely
- **Decision column between Close and Thank** — should allow adding a decision (not just a checkbox)
- **Remove Pipeline Breakdown** — remove Pipeline Breakdown section from Reports
- **Checkbox behavior** — when a checkbox is clicked, the box should be checked directly instead of requiring a logged event

## Solution

Create/replace `JournalReport.tsx` per the detailed spec in `prompts/journal_report.md`. Includes loading skeleton, error state, responsive design, chart tooltips, and singular/plural alert text handling. Also: remove duplicate Decision column after Next Steps, make the Decision column between Close/Thank support adding decisions, remove Pipeline Breakdown, and make checkboxes toggle directly on click.
