# Phase 4: Grid UI Core - User Acceptance Testing

**Phase Goal:** User sees a functional grid with contacts as rows, stages as columns, and can open event timeline drawer.

**Started:** 2026-01-25
**Status:** Complete

## Test Cases

### T1: Grid Layout with Contacts and Stages
**What to verify:** Navigate to a journal detail page and verify the grid displays correctly with contacts as rows and pipeline stages as columns.

**Steps:**
1. Navigate to http://localhost:5173/journals/{journal-id} (use a journal with contacts)
2. Verify grid displays with column headers: Contact, Contact, Meet, Close, Decision, Thank, Next Steps
3. Verify each row shows a contact name in the first column
4. Verify contact email appears below the name

**Result:** [x] Pass  [ ] Fail  [ ] Blocked

---

### T2: Sticky Headers and First Column
**What to verify:** Scroll the grid vertically and horizontally to confirm headers and contact names stay visible.

**Steps:**
1. On the journal grid page, scroll down (if there are enough contacts)
2. Verify the header row (stage names) stays fixed at the top
3. Scroll right horizontally
4. Verify the Contact name column stays fixed on the left
5. Verify the corner cell (intersection) stays visible in both scroll directions

**Result:** [x] Pass  [ ] Fail  [ ] Blocked

---

### T3: Stage Cell Checkmarks
**What to verify:** Stage cells display checkmarks when there are logged events for that stage.

**Steps:**
1. Look at a contact row that has events logged
2. Verify stages with events show a checkmark icon
3. Verify stages without events show an empty/inactive cell

**Result:** [x] Pass  [ ] Fail  [ ] Blocked

---

### T4: Freshness Color Coding
**What to verify:** Checkmark colors indicate how recent the last event was.

**Steps:**
1. Find stage cells with events of varying ages
2. Verify color coding:
   - Green: Event within last 7 days
   - Yellow: Event within last 30 days
   - Orange: Event within last 90 days
   - Red: Event older than 90 days

**Result:** [x] Pass  [ ] Fail  [ ] Blocked

---

### T5: Tooltip on Hover
**What to verify:** Hovering over a stage cell shows a tooltip with event summary.

**Steps:**
1. Hover over a stage cell that has events
2. Wait briefly for tooltip to appear (300ms delay)
3. Verify tooltip shows:
   - Event type (e.g., "Call Logged")
   - Relative time (e.g., "3 days ago")
   - Notes preview (if any)
   - Total event count for that stage

**Result:** [x] Pass  [ ] Fail  [ ] Blocked

---

### T6: Click Opens Timeline Drawer
**What to verify:** Clicking a stage cell opens a drawer from the right showing the event timeline.

**Steps:**
1. Click on a stage cell (with or without events)
2. Verify a drawer slides in from the right side
3. Verify drawer header shows contact name and stage name
4. Verify drawer can be closed (X button or click outside)

**Result:** [x] Pass  [ ] Fail  [ ] Blocked

---

### T7: Timeline Shows Chronological Events
**What to verify:** The timeline drawer displays events in chronological order with visual timeline.

**Steps:**
1. Click on a stage cell with multiple events
2. Verify events are listed chronologically (most recent first or last)
3. Verify each event shows:
   - Event type badge
   - Relative time (e.g., "3 days ago")
   - Event notes/details
4. Verify timeline visual (vertical line connecting events)

**Result:** [x] Pass  [ ] Fail  [ ] Blocked

---

### T8: Load More Pagination
**What to verify:** Timeline drawer loads 5 events initially with "Load More" option.

**Steps:**
1. Click on a stage cell with more than 5 events
2. Verify only 5 events show initially
3. Verify "Load More" button appears at bottom
4. Click "Load More"
5. Verify additional events load below

**Result:** [x] Pass  [ ] Fail  [ ] Blocked

---

### T9: Horizontal Scroll
**What to verify:** Grid supports horizontal scrolling to see all 6 stage columns.

**Steps:**
1. Resize browser window to be narrower than the grid
2. Verify horizontal scrollbar appears
3. Scroll right to see all stage columns
4. Verify all 6 stages are visible when scrolled

**Result:** [x] Pass  [ ] Fail  [ ] Blocked

---

## Summary

| Test | Description | Result |
|------|-------------|--------|
| T1 | Grid Layout with Contacts and Stages | Pass |
| T2 | Sticky Headers and First Column | Pass |
| T3 | Stage Cell Checkmarks | Pass |
| T4 | Freshness Color Coding | Pass |
| T5 | Tooltip on Hover | Pass |
| T6 | Click Opens Timeline Drawer | Pass |
| T7 | Timeline Shows Chronological Events | Pass |
| T8 | Load More Pagination | Pass |
| T9 | Horizontal Scroll | Pass |

**Overall Result:** [x] All Passed  [ ] Issues Found

---

*UAT Session Started: 2026-01-25*
*UAT Session Completed: 2026-01-25*
*Tests: 9 passed, 0 failed, 0 blocked*
