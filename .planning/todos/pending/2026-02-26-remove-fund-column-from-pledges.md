---
created: 2026-02-26T14:10:00.000Z
title: Remove Fund column from Pledges
area: ui
files:
  - frontend/src/pages/pledges/PledgeList.tsx
---

## Problem

The Pledges (Recurring Gifts) list page has a "Fund" column (`fund_name` accessor, line ~121 in PledgeList.tsx) that the user wants removed.

## Solution

- Remove the Fund column definition object from the columns array in PledgeList.tsx (lines ~120-124)
- Check if `fund_name` is referenced in filters or sorting and clean up if needed
