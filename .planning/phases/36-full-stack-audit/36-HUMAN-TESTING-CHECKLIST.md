# Human Testing Checklist

**Phase 36: Full-Stack Audit**
**Created:** 2026-02-24
**Purpose:** Consolidates all pending manual verification items from v2.0 phases plus new accessibility checks from the audit.

## How to Use

1. Start the development servers:
   - Backend: `python manage.py runserver` (http://localhost:8000)
   - Frontend: `cd frontend && npm run dev` (http://localhost:5173)
2. Log in as a staff user
3. Use Chrome DevTools for dark mode testing (toggle via the theme toggle button in the sidebar)
4. Work through each section, checking items as verified

**Base URL:** http://localhost:5173

---

## Phase 30: Data Migration

- [ ] Verify gift/recurring gift counts match old donation/pledge counts (check total_given and gift_count on a few contacts)

## Phase 31: Gift & Recurring Gift UI

- [ ] Donations list page (`/donations`) loads and displays gift data correctly
- [ ] Gift detail page shows gift information with correct dollar formatting
- [ ] Solicitor credit panel shows on gift detail (when credits exist)
- [ ] Pledge status/frequency filters work with new RecurringGift options (Active, Held, Completed, Cancelled, Terminated)
- [ ] Gift amount filter: filter by $100 min shows correct gifts (fixed in Plan 01 -- dollar-to-cents conversion)

## Phase 32: Import UI

- [ ] Drag-and-drop file upload works in RE import tabs (admin user only)
- [ ] Upload RE Constituent CSV end-to-end (create or update contacts)
- [ ] Import history auto-refreshes after upload completes
- [ ] Import tabs are admin-only (non-admin users see appropriate restriction)
- [ ] Import history shows "Duplicate" status for re-uploaded files (fixed in Plan 01 -- status persisted to DB)

## Phase 33: Prayer Intentions

- [ ] Prayer page (`/prayers`) loads with amber chapel aesthetic
- [ ] Focus mode keyboard navigation (arrow keys to navigate, space to mark prayed)
- [ ] Answered note dialog appears before marking as answered (optional textarea)
- [ ] Contact detail Prayer tab shows intentions for that contact

## Phase 34: Dashboard Polish

- [ ] Drag dashboard tiles to reorder (grab handle visible on hover)
- [ ] Drop indicator appears during drag
- [ ] Tile order resets on page refresh (intentional -- no persistence)
- [ ] Drag works on Needs Attention, What Changed, Quick Actions sections
- [ ] No tile "snapping" issues or visual glitches during drag
- [ ] Keyboard drag: Tab to handle, Enter to pick up, arrows to move, Enter to drop

## Phase 36: Dark Mode (Audit Additions)

- [ ] Prayer focus mode renders correctly in dark mode (text readable, amber accents visible)
- [ ] Import result banners (success/error/duplicate) render correctly in dark mode
- [ ] Admin analytics charts render with visible colors in dark mode
- [ ] Activity heatmap shows GitHub-style green gradient in dark mode (fixed in Plan 05)
- [ ] All data tables have sufficient contrast in dark mode

## Phase 36: Accessibility (Audit Additions)

- [ ] Tab through sidebar items: focus ring visible on each item
- [ ] Tab through data table rows: keyboard navigation functional
- [ ] Tab through action buttons (edit, delete, etc.): focus ring visible
- [ ] Screen reader: icon-only buttons announce their purpose (e.g., "Edit contact", "Delete task")
- [ ] All table headers have appropriate column scope for screen readers (fixed in Plan 05)
- [ ] Filter dropdowns are keyboard-navigable (arrow keys, Enter to select)

## Phase 36: API Consistency (Audit Additions)

- [ ] API error responses show user-friendly messages (not raw error objects)
- [ ] Read-only users cannot navigate to create/edit forms (routes guarded in Plan 02)
- [ ] Read-only users can still view all data (lists, details, exports)

---

## Summary

| Category | Items |
|----------|-------|
| Data Migration | 1 |
| Gift/Recurring Gift UI | 5 |
| Import UI | 5 |
| Prayer Intentions | 4 |
| Dashboard Polish | 6 |
| Dark Mode | 5 |
| Accessibility | 6 |
| API Consistency | 3 |
| **Total** | **35** |

---

*Compiled from: v2.0-MILESTONE-AUDIT.md (19 items) + Phase 36 audit findings (16 items)*
*Phase: 36-full-stack-audit*
*Created: 2026-02-24*
