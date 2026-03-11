# Phase 41: Begin Prayer - Research

**Researched:** 2026-02-27
**Domain:** Frontend UI — button replacement, selection dialog, Focus Mode integration
**Confidence:** HIGH

## Summary

Phase 41 replaces the existing small "Enter Focus Mode" button in the Today's Focus section with a prominent "Begin Prayer" button, and adds an intention selection dialog between the button click and Focus Mode launch. This is a pure frontend change — no backend modifications required.

The existing codebase has all necessary infrastructure: the `PrayerFocusMode` component already accepts an `intentions` prop (array of `PrayerIntention`), the `usePrayers` hook supports fetching active intentions via query params, the `useTodaysFocus` hook provides today's curated set for pre-checking, and the project already has Dialog and Checkbox components from shadcn/ui (Radix-based).

**Primary recommendation:** Create a new `BeginPrayerDialog` component that fetches all active intentions, pre-checks today's focus ones, and passes the user's selection to the existing `PrayerFocusMode`. Modify `TodaysFocus` to render the "Begin Prayer" button and wire the dialog. No new API endpoints needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Button lives inside the Today's Focus section, replacing the existing "Enter Focus Mode" button
- Medium accent button — primary amber styling, larger than current button but not full-width
- Label: "Begin Prayer" (exact text)
- Icon: Sparkles (same as current "Enter Focus Mode" for continuity)
- Button is always visible and clickable, even with no active intentions
- When clicked with no intentions: launches Focus Mode which already has an empty state screen ("No Intentions for Today" with Return button)
- When clicked with intentions: opens a selection dialog before entering Focus Mode
- Centered modal/dialog opens when "Begin Prayer" is clicked
- Shows all active prayer intentions with checkboxes (not just today's focus)
- Today's focus intentions are pre-checked by default
- User can check/uncheck individual intentions to customize their prayer session
- "Start Prayer" button at bottom launches Focus Mode with selected intentions
- Dialog should show intention title and contact name for each item
- "Enter Focus Mode" button is completely removed/replaced by "Begin Prayer"
- Single entry point — cleaner UI

### Claude's Discretion
- Whether to include a "Select All" / "Deselect All" toggle in the selection dialog (decide based on typical intention count and UX)
- Dialog layout and styling details (fit the warm prayer aesthetic)
- Exact button sizing within the "medium accent" direction
- How to handle the case where user deselects all intentions and clicks "Start Prayer"

### Deferred Ideas (OUT OF SCOPE)
- "Add Prayer Intention isn't working" — reported as a bug, needs investigation outside this phase
- Quick-start option that skips selection (potential future enhancement if selection step feels heavy)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRAY-01 | Prayer Request page has a "Begin Prayer" button that launches expanded Focus Mode | Full implementation path mapped: replace TodaysFocus button, add selection dialog, wire to existing PrayerFocusMode component |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @radix-ui/react-dialog | ^1.1.15 | Selection dialog modal | Already installed; project pattern for all modals |
| @radix-ui/react-checkbox | ^1.3.3 | Intention checkboxes in selection dialog | Already installed; shadcn/ui Checkbox component exists |
| lucide-react | ^0.562.0 | Sparkles icon for button | Already installed; Sparkles already used in TodaysFocus |
| @tanstack/react-query | ^5.90.17 | Data fetching for active intentions | Already installed; usePrayers/useTodaysFocus hooks exist |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | ^2.0.7 | Toast notifications (if needed) | Already installed; use if error states need user notification |

### Alternatives Considered
None. All required components already exist in the project.

**Installation:**
No new packages needed. All dependencies are already installed.

## Architecture Patterns

### Existing File Structure (prayer module)
```
frontend/src/
├── api/prayers.ts               # API client (getPrayers, getTodaysFocus, etc.)
├── hooks/usePrayers.ts          # React Query hooks (usePrayers, useTodaysFocus, etc.)
└── pages/prayer/
    ├── PrayerList.tsx            # Main page component (manages focusModeOpen state)
    ├── PrayerFocusMode.tsx       # Full-screen focus overlay (accepts intentions[] prop)
    ├── PrayerIntentionPanel.tsx   # Create/edit dialog
    └── components/
        ├── TodaysFocus.tsx       # Today's Focus section (has "Enter Focus Mode" button)
        ├── PrayerCard.tsx        # Card component for prayer intention
        └── StatusBadge.tsx       # Status badge component
```

### Pattern 1: Current Focus Mode Launch Flow
**What:** Currently, `PrayerList.tsx` owns the `focusModeOpen` state. `TodaysFocus` calls `onStartFocusMode` which sets `focusModeOpen = true`. `PrayerFocusMode` receives `intentions={todaysFocusData ?? []}`.
**Key insight:** The current flow always passes today's focus data. The new flow needs to pass user-selected intentions instead.

```typescript
// Current flow in PrayerList.tsx (lines 296-300):
<PrayerFocusMode
  open={focusModeOpen}
  onClose={() => setFocusModeOpen(false)}
  intentions={todaysFocusData ?? []}
/>
```

### Pattern 2: Dialog-First Modal Pattern (project standard)
**What:** All overlays use centered Dialog with `max-h-[80vh]` and `overflow-y-auto`.
**Source:** STATE.md accumulated decisions (v2.2 pattern)
**Example:**
```typescript
// From PrayerIntentionPanel.tsx (existing pattern):
<Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
  <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
    <DialogHeader>
      <DialogTitle className="font-serif text-amber-900 dark:text-amber-100">
        ...
      </DialogTitle>
      <DialogDescription>...</DialogDescription>
    </DialogHeader>
    {/* content */}
    <DialogFooter>...</DialogFooter>
  </DialogContent>
</Dialog>
```

### Pattern 3: Amber Prayer Aesthetic
**What:** The prayer module uses a consistent warm amber color palette.
**Colors used throughout prayer pages:**
- Background: `bg-amber-50/30 dark:bg-amber-950/10`
- Section background: `bg-amber-50/30 dark:bg-amber-950/20`
- Borders: `border-amber-100 dark:border-amber-900/50`
- Headers: `font-serif text-amber-900 dark:text-amber-100`
- Body text: `text-amber-700 dark:text-amber-300`
- Muted text: `text-amber-700/70 dark:text-amber-400/60`
- Primary action button: `bg-amber-600 hover:bg-amber-700 text-white dark:bg-amber-700 dark:hover:bg-amber-600`

### Pattern 4: New Component — BeginPrayerDialog
**What:** A new component that owns the selection dialog state and intention filtering logic.
**Recommended structure:**

```typescript
// frontend/src/pages/prayer/components/BeginPrayerDialog.tsx
interface BeginPrayerDialogProps {
  open: boolean
  onClose: () => void
  onStartPrayer: (intentions: PrayerIntention[]) => void
}
```

**State management:**
1. Fetch all active intentions via `usePrayers({ status: 'active', page_size: '200' })`
2. Fetch today's focus via `useTodaysFocus()` (for pre-checking)
3. Maintain `selectedIds: Set<string>` state, initialized from today's focus IDs
4. On "Start Prayer" click: filter active intentions to selected IDs, call `onStartPrayer(filtered)`

### Anti-Patterns to Avoid
- **Creating a new API endpoint:** The existing `GET /prayers/?status=active&page_size=200` is sufficient. Do not create a new backend endpoint for this.
- **Modifying PrayerFocusMode:** The `PrayerFocusMode` component already accepts an `intentions` array and handles empty state. Do not modify it.
- **Nesting Dialog inside Dialog:** The BeginPrayerDialog must be a sibling of PrayerFocusMode in the DOM tree, not nested inside TodaysFocus. This avoids Radix portal issues (project has had this problem before — see EventTimelineDrawer decision in STATE.md).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Selection dialog | Custom overlay/portal | shadcn Dialog component | Handles focus trapping, escape, overlay click, portals |
| Checkboxes | Custom checkbox inputs | shadcn Checkbox (Radix) | Accessible, keyboard navigable, proper ARIA states |
| Scrollable list | Custom scroll | CSS `max-h-[50vh] overflow-y-auto` | Native scrolling is sufficient for lists under 100 items |

**Key insight:** Every UI primitive needed already exists in the project. This phase is pure composition, not component creation.

## Common Pitfalls

### Pitfall 1: Stale Today's Focus Data for Pre-checking
**What goes wrong:** The `useTodaysFocus()` data may be stale (5-min `staleTime` from global config) when the dialog opens, causing mismatched pre-checks.
**Why it happens:** React Query global staleTime is 5 minutes.
**How to avoid:** Either accept the staleness (it's fine — the pre-check is just a convenience default) or call `queryClient.invalidateQueries({ queryKey: ["prayers", "focus"] })` when opening the dialog.
**Warning signs:** Pre-checked items don't match what's shown in Today's Focus section.

### Pitfall 2: Paginated Active Intentions
**What goes wrong:** The `usePrayers({ status: 'active' })` hook uses paginated API (PAGE_SIZE=25). Users with many intentions might not see all of them in the selection dialog.
**Why it happens:** The `PrayerIntentionListCreateView` uses default pagination.
**How to avoid:** Pass `page_size: '200'` in params to effectively get all active intentions (missionaries are unlikely to have 200+ active intentions). Alternatively, the existing list endpoint could be extended to support `page_size=0` for no pagination, but `200` is simpler and safe.
**Warning signs:** Dialog shows fewer intentions than expected.

### Pitfall 3: Button Always Visible Means Two Flows
**What goes wrong:** If you make the button conditional on having intentions, it violates the user decision "button is always visible and clickable, even with no active intentions."
**Why it happens:** Current "Enter Focus Mode" button is hidden when no intentions exist (line 23 of TodaysFocus.tsx: `{intentions && intentions.length > 0 && (...)}`).
**How to avoid:** Remove the conditional. Button always renders. When clicked with 0 active intentions, skip dialog and go straight to Focus Mode empty state.
**Warning signs:** Button disappearing when there are no intentions.

### Pitfall 4: Checkbox State Reset on Dialog Reopen
**What goes wrong:** If `selectedIds` is not reset when the dialog opens, previous selections persist.
**Why it happens:** React state persists across dialog open/close if the component stays mounted.
**How to avoid:** Use a `useEffect` that resets `selectedIds` from today's focus data whenever `open` changes to `true`.
**Warning signs:** Opening dialog shows previous session's selections instead of fresh defaults.

## Code Examples

### Example 1: "Begin Prayer" Button (replacing Enter Focus Mode)
```typescript
// In TodaysFocus.tsx — replace the existing conditional button
// Currently (lines 23-33):
//   {intentions && intentions.length > 0 && (
//     <Button variant="secondary" size="sm" ...>
//       <Sparkles className="h-4 w-4" />
//       Enter Focus Mode
//     </Button>
//   )}
//
// Replace with (always visible, amber accent):
<Button
  onClick={onBeginPrayer}
  className="gap-1.5 bg-amber-600 hover:bg-amber-700 text-white dark:bg-amber-700 dark:hover:bg-amber-600"
>
  <Sparkles className="h-4 w-4" />
  Begin Prayer
</Button>
```

### Example 2: Selection Dialog Checkbox Row
```typescript
// Individual intention row with checkbox
<label
  key={intention.id}
  className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-amber-50/50 dark:hover:bg-amber-950/30 cursor-pointer transition-colors"
>
  <Checkbox
    checked={selectedIds.has(intention.id)}
    onCheckedChange={(checked) => {
      setSelectedIds(prev => {
        const next = new Set(prev)
        if (checked) next.add(intention.id)
        else next.delete(intention.id)
        return next
      })
    }}
    className="border-amber-300 dark:border-amber-700 data-[state=checked]:bg-amber-600 data-[state=checked]:border-amber-600"
  />
  <div className="flex-1 min-w-0">
    <p className="font-medium text-amber-900 dark:text-amber-100 truncate">
      {intention.title}
    </p>
    <p className="text-sm text-amber-700/70 dark:text-amber-400/60">
      {intention.contact_name}
    </p>
  </div>
</label>
```

### Example 3: State Initialization from Today's Focus
```typescript
// Reset selected IDs when dialog opens
useEffect(() => {
  if (open && todaysFocusData) {
    setSelectedIds(new Set(todaysFocusData.map(i => i.id)))
  }
}, [open, todaysFocusData])
```

### Example 4: Modified PrayerList Integration
```typescript
// In PrayerList.tsx — new state and flow
const [beginPrayerDialogOpen, setBeginPrayerDialogOpen] = useState(false)
const [selectedIntentions, setSelectedIntentions] = useState<PrayerIntention[]>([])

const handleBeginPrayer = () => {
  // Check if there are any active intentions
  // If none, skip dialog and go straight to Focus Mode (empty state)
  // If some, open selection dialog
}

const handleStartPrayer = (intentions: PrayerIntention[]) => {
  setSelectedIntentions(intentions)
  setBeginPrayerDialogOpen(false)
  setFocusModeOpen(true)
}

// PrayerFocusMode now receives selectedIntentions instead of todaysFocusData:
<PrayerFocusMode
  open={focusModeOpen}
  onClose={() => setFocusModeOpen(false)}
  intentions={selectedIntentions}
/>
```

## Discretion Recommendations

### Select All / Deselect All Toggle
**Recommendation: Include it.** The Today's Focus algorithm selects up to 5 intentions, but active intentions could number 10-30+. Having a toggle makes it easy to start from scratch or select everything. Place it as a small text button in the dialog header area, not a prominent control.

### Deselect All + Start Prayer
**Recommendation: Disable the "Start Prayer" button when 0 intentions are selected.** This prevents confusion — if the user wants the empty state, they can close the dialog and the "Begin Prayer" button with 0 active intentions already launches Focus Mode directly. A disabled state with helper text like "Select at least one intention" is clear.

### Dialog Styling
**Recommendation:** Follow the warm amber aesthetic. Use `font-serif` for the dialog title, amber borders and backgrounds consistent with the rest of the prayer page. Max width `max-w-md` is sufficient since content is just a checkbox list.

### Button Sizing
**Recommendation:** Use the default Button size (h-10) with custom amber styling. The current "Enter Focus Mode" is `size="sm"` (h-9) and `variant="secondary"`. The new button should be slightly larger at default size with amber background to be more prominent without being oversized.

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/pages/prayer/components/TodaysFocus.tsx` | Replace "Enter Focus Mode" button with "Begin Prayer", make always visible, update callback prop |
| `frontend/src/pages/prayer/PrayerList.tsx` | Add dialog/selection state, wire BeginPrayerDialog, change PrayerFocusMode intentions prop |
| **NEW** `frontend/src/pages/prayer/components/BeginPrayerDialog.tsx` | Selection dialog component with checkboxes |

**Backend:** No changes needed. Existing `GET /prayers/?status=active&page_size=200` serves all active intentions.

## Open Questions

1. **Exact intention count in practice**
   - What we know: Today's focus selects min(5, total). Active intentions could be any number.
   - What's unclear: Typical active intention count for real users.
   - Recommendation: Design for 5-50 intentions (scrollable list in dialog). The `page_size=200` param handles edge cases.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `frontend/src/pages/prayer/` — all 6 files read in full
- Codebase inspection: `apps/prayers/` — models.py, views.py, serializers.py, filters.py, urls.py
- Codebase inspection: `frontend/src/components/ui/dialog.tsx`, `checkbox.tsx`, `button.tsx`
- Codebase inspection: `.planning/STATE.md` — dialog-first modal pattern, project decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and used in project
- Architecture: HIGH - pattern directly follows existing prayer module structure and project Dialog conventions
- Pitfalls: HIGH - identified from codebase inspection (pagination, conditional rendering, state reset)

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (stable — pure frontend composition)
