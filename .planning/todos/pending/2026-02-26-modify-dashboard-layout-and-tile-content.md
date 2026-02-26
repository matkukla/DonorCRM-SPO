---
created: 2026-02-26T13:46:18.214Z
title: Modify dashboard layout and tile content
area: ui
files:
  - frontend/src/pages/Dashboard.tsx
  - prompts/dashboard_modification.md
---

## Problem

Dashboard has visual clutter and layout gaps that need cleanup per user specs in `prompts/dashboard_modification.md`:

1. Remove "2026 calendar year" text from Giving and Expecting tiles
2. Remove "Updated today" from Monthly Gifts tile
3. Delete "Recent Journal Activity" tile entirely
4. Make tiles draggable anywhere (currently drag may be constrained)
5. Resize dashboard components to eliminate large gaps between boxes
6. Create an option to toggle between bar chart and line graph in Donations

## Solution

- Items 1-3: Find and remove specific text/components in Dashboard.tsx or tile sub-components
- Item 4: Review dnd-kit PointerSensor config; may need to adjust grid constraints or sortable strategy
- Item 5: Adjust Tailwind grid gap/sizing classes to close spacing between tiles
- Item 6: Add a toggle button (bar/line) to the Donations chart tile, switch Recharts component type
