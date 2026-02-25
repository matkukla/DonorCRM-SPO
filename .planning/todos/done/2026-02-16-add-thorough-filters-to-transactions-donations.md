---
created: 2026-02-16T20:30:08.612Z
title: Add thorough filters to transactions/donations
area: ui
files:
  - frontend/src/pages/donations/
---

## Problem

The transactions/donations page currently lacks comprehensive filtering capabilities. Users need to quickly find and analyze specific donations based on various criteria to manage donor relationships and track giving patterns.

## Solution

Add filter controls to the transactions/donations page that allow filtering by:
- Date range (donation date)
- Amount range (min/max)
- Donor/contact
- Fund/campaign
- Payment method
- Recurring vs one-time

TBD: Exact filter UI pattern — should match whatever pattern is used for contacts and journals page filters for consistency across the app.
