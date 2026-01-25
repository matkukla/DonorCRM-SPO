# Phase 5: Grid Interactions & Decision UI - UAT Session

**Started:** 2026-01-25
**Test Journal ID:** `151b8e2e-34c2-48a4-82ec-c671292eb519`
**URL:** http://localhost:5173/journals/151b8e2e-34c2-48a4-82ec-c671292eb519

## Test Cases

### T1: Journal Header Shows Stats (JRN-14)
**Steps:**
1. Navigate to journal detail page
2. Observe the header section below the back button

**Expected:**
- Journal name displayed prominently
- Goal amount shown (e.g., "$10,000")
- Deadline shown (if set)
- Progress bar with percentage toward goal
- Total decisions count
- Total pledged amount

**Status:** passed
**Result:** Header displays all stats correctly

---

### T2: Decision Column Display (JRN-13)
**Steps:**
1. Look at the Decision column in the grid
2. Find a row with an existing decision

**Expected:**
- Decision column visible as second-to-last column
- Cells with decisions show amount, cadence badge, and status badge
- Status badge is color-coded (green=active, yellow=pending, gray=paused, red=declined)
- Empty cells show "Add Decision" or similar prompt

**Status:** passed
**Result:** Decision column displays with color-coded status badges

---

### T3: Decision Dialog Opens and Updates (JRN-13)
**Steps:**
1. Click on any decision cell (existing or empty)
2. In the dialog, update the amount, cadence, and/or status
3. Click Save

**Expected:**
- Dialog opens with form fields for amount, cadence (dropdown), status (dropdown)
- On save, dialog closes and grid cell updates immediately
- No full page refresh occurs

**Status:** passed
**Result:** Dialog opens with form fields and saves correctly

---

### T4: Header Updates After Decision Change (Success Criteria #6)
**Steps:**
1. Note the current "Total Pledged" and "Decisions" count in header
2. Edit a decision to change the amount (or add a new decision)
3. Save the decision

**Expected:**
- Header stats update immediately after save
- Total pledged reflects the new amount
- No page refresh needed

**Status:** passed
**Result:** Header stats update immediately after decision changes

---

### T5: Next Steps Column Display (JRN-06)
**Steps:**
1. Look at the Next Steps column (last column in grid)
2. Observe the display for different rows

**Expected:**
- Next Steps column visible as last column
- Shows count (e.g., "0", "1", "2/3" for completed/total)
- Clickable to open popover

**Status:** passed
**Result:** Next Steps column displays with counts

---

### T6: Next Steps Checklist CRUD (JRN-06)
**Steps:**
1. Click on a Next Steps cell to open the popover
2. Add a new step by typing and pressing Enter
3. Check/uncheck a step
4. Delete a step (hover for trash icon)
5. Close and reopen the popover

**Expected:**
- Popover shows checklist UI
- Can add new items via input field
- Can toggle items complete/incomplete
- Can delete items
- Changes persist after closing and reopening

**Status:** passed
**Result:** Checklist supports full CRUD with persistence

---

### T7: Stage Movement Warning - Skip Forward (JRN-05)
**Steps:**
1. Find a contact with events only in "Contact" stage
2. Click on a stage cell several stages ahead (e.g., "Close")
3. Create an event

**Expected:**
- Warning toast appears indicating stages were skipped
- Event is still created (no hard block)
- Warning is informational only

**Status:** passed
**Result:** Warning toast appears when skipping stages

---

### T8: Stage Movement Warning - Revisiting (JRN-05)
**Steps:**
1. Find a contact with events in later stages (e.g., "Meet" or beyond)
2. Click on an earlier stage (e.g., "Contact")
3. Create an event

**Expected:**
- Toast appears indicating "Revisiting" earlier stage
- Event is still created (no hard block)
- Warning is informational only

**Status:** passed
**Result:** Warning toast appears when revisiting earlier stage

---

### T9: Grid Efficiency - No Cascade Re-renders
**Steps:**
1. Open browser DevTools
2. Edit a single decision or toggle a next step
3. Observe if only that cell updates (vs entire grid flashing)

**Expected:**
- Only the modified cell re-renders
- No visible full-grid flash
- UI feels responsive and smooth

**Status:** passed
**Result:** Grid updates efficiently without cascade re-renders

---

## Summary

| Test | Description | Status |
|------|-------------|--------|
| T1 | Header shows stats | passed |
| T2 | Decision column display | passed |
| T3 | Decision dialog opens/updates | passed |
| T4 | Header updates after decision change | passed |
| T5 | Next Steps column display | passed |
| T6 | Next Steps checklist CRUD | passed |
| T7 | Stage skip warning | passed |
| T8 | Stage revisit warning | passed |
| T9 | Grid efficiency | passed |

**Total:** 9/9 passed
