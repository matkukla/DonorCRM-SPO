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
- **Stage ordering**: Keep Decision column between Close and Thank (not at the end)
- **Decision functionality**: Add Decision column functionality after Next Steps
- **Remove duplicate**: Remove the duplicate Decision section at the end
- **Remove Pipeline Breakdown**: Remove the Pipeline Breakdown section from Reports

## Solution

Create/replace `JournalReport.tsx` per the detailed spec in `prompts/journal_report.md`. Includes loading skeleton, error state, responsive design, chart tooltips, and singular/plural alert text handling. Also reorder stages so Decision sits between Close and Thank, remove duplicate Decision section, and remove Pipeline Breakdown from the report.
