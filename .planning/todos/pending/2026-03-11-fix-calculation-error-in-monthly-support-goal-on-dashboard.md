---
created: 2026-03-11T13:40:20.773Z
title: Fix calculation error in "Monthly Support Goal" on dashboard
area: ui
files: []
---

## Problem

The "Monthly Support Goal" tile on the Dashboard is displaying an incorrect value. The calculation logic is producing wrong results, likely due to incorrect aggregation of donation data, wrong field references, or faulty formula logic.

## Solution

Identify the data source and calculation formula behind the Monthly Support Goal tile. Trace through the backend API response and frontend rendering to find where the value goes wrong. Fix the calculation to accurately reflect the missionary's monthly support goal.
