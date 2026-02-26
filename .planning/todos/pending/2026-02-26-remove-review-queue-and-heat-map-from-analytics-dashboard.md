---
created: 2026-02-26T14:39:36.556Z
title: Remove Review Queue and heat map from analytics dashboard
area: ui
files:
  - frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx
  - frontend/src/pages/admin/analytics/components/ActivityHeatmap.tsx
  - frontend/src/pages/insights/ReviewQueue.tsx
  - frontend/src/components/layout/Sidebar.tsx
  - frontend/src/App.tsx
---

## Problem

The analytics dashboard has two features to remove:
1. **Review Queue** — `ReviewQueue.tsx` component in insights, referenced in Sidebar, App routes, and insights API/hooks
2. **Activity Heat Map** — `ActivityHeatmap.tsx` component used in AdminAnalyticsDashboard

## Solution

- Remove the ActivityHeatmap component from AdminAnalyticsDashboard and delete `ActivityHeatmap.tsx`
- Remove ReviewQueue page/component, its route in App.tsx, its sidebar link, and clean up related API/hook references (`useInsights.ts`, `insights.ts`, `insights/index.ts`)
