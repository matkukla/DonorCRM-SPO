---
created: 2026-02-19T22:46:15.737Z
title: Make dashboard tiles editable with drag and drop
area: ui
files:
  - frontend/src/pages/Dashboard.tsx
---

## Problem

The dashboard currently has a fixed tile layout. Users should be able to rearrange tiles via drag and drop and potentially edit which tiles are visible, allowing each user to customize their dashboard view to surface the metrics most relevant to them.

## Solution

Implement drag-and-drop reordering for dashboard tiles using a library like `@dnd-kit/core` or `react-beautiful-dnd`. Persist tile order/visibility per user (localStorage or backend user preferences). Consider a grid layout system that supports responsive drag-and-drop repositioning.
