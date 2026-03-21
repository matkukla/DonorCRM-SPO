---
created: 2026-03-21T09:04:37.271Z
title: Add MPD Resources sidebar section with Links and Pacing Calculator pages
area: ui
priority: P1
source: "GitHub Issue #22 — Simple Fix #1 - MPD Resources Tab"
backlog_ref: "Row 26"
files:
  - frontend/src/components/layout/Sidebar.tsx
  - frontend/src/pages/goal/GoalPage.tsx
  - frontend/src/components/goal/
  - frontend/src/App.tsx
  - frontend/src/providers/ViewAsProvider.tsx
---

## Problem

Missionaries need a dedicated section for MPD planning tools and reference material, separate from Goal tracking. The pacing calculator currently lives on the Goal page but doesn't belong there — the Goal page should stay focused on progress and journal selection. There's also no place for external resource links like spo.org/mpd.

## Solution

Frontend-only change. No backend modifications needed.

**Sidebar — new collapsible section:**
- Add "MPD Resources" collapsible section below Insights, identical pattern (same expand/collapse, localStorage persistence, chevron behavior)
- Two sub-items: "Links" (/mpd-resources/links) and "Pacing Calculator" (/mpd-resources/pacing)
- Collapsed by default, visible to all roles
- Icons: BookOpen (parent), ExternalLink (Links), Calculator (Pacing)

**Links page** (`frontend/src/pages/mpd-resources/LinksPage.tsx`):
- Static page with clickable resource links (starts with "SPO MPD Handbook" → spo.org/mpd, opens new tab)
- Designed as an extensible list (cards/rows), not inline anchors

**Pacing Calculator page** (`frontend/src/pages/mpd-resources/PacingCalculatorPage.tsx`):
- Relocate existing pacing section from Goal page
- Must fetch its own data independently (no longer receives props from GoalPage)
- Preserve exact same calculations, display, and behavior
- View As: editable inputs disabled when viewing as another user

**Goal page cleanup:**
- Remove pacing section entirely
- Clean up imports/state used exclusively by pacing
- Adjust layout spacing so remaining content looks intentional

**Routes:** Two new lazy-loaded routes wrapped in ProtectedRoute (all roles)

Full spec in GitHub Issue #22.
