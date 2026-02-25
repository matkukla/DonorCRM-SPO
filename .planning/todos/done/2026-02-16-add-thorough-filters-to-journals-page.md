---
created: 2026-02-16T20:16:15.623Z
title: Add thorough filters to Journals page
area: ui
files:
  - frontend/src/pages/journals/
---

## Problem

The Journals page currently lacks filtering capabilities. Users need to quickly find specific journals based on various criteria, especially as the number of journals grows over time.

## Solution

Add filter controls to the Journals page that allow filtering by:
- Journal status (active, completed, archived)
- Date range (created date, deadline)
- Goal progress (on track, behind, exceeded)
- Number of contacts
- Search by journal name

TBD: Exact filter UI pattern — should match whatever pattern is used for contacts page filters for consistency.
