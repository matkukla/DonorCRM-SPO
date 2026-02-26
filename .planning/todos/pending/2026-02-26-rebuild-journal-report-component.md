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

## Solution

Create/replace `JournalReport.tsx` per the detailed spec in `prompts/journal_report.md`. Includes loading skeleton, error state, responsive design, chart tooltips, and singular/plural alert text handling.
