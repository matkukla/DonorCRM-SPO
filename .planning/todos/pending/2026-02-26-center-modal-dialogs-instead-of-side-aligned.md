---
created: 2026-02-26T13:52:20.378Z
title: Center modal dialogs instead of side-aligned
area: ui
files:
  - frontend/src/components/ui/dialog.tsx
  - frontend/src/components/ui/sheet.tsx
---

## Problem

Modal dialogs for editing (e.g., contact edit, gift edit, task edit) appear off to the side instead of centered on screen. User wants all edit modals/dialogs centered for better UX.

This may involve Sheet components (which slide in from the side by design) being used where centered Dialog components would be more appropriate, or Dialog positioning CSS needing adjustment.

## Solution

- Audit which edit flows use Sheet (side panel) vs Dialog (centered modal)
- Convert side-panel Sheets to centered Dialogs where the user wants centered behavior
- Or adjust Dialog component positioning if it's a CSS issue
- Check shadcn/ui Dialog component default positioning (`items-center justify-center` on overlay)
