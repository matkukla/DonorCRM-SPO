---
created: 2026-03-11T13:41:54.002Z
title: Set start of fiscal year to July 1st and reset after every year
area: general
files: []
---

## Problem

The application currently has no configured fiscal year start date. Financial calculations, reporting periods, and annual aggregations (e.g., YTD giving, annual goals) need to be anchored to the organization's fiscal year, which starts July 1st and resets annually on that date.

## Solution

Add a fiscal year start configuration (July 1st) that is used across donation summaries, dashboard tiles, and reporting. Date range calculations for "this fiscal year" should dynamically compute the current fiscal year window (July 1 of the current or prior calendar year through June 30 of the next) and reset automatically each year.
