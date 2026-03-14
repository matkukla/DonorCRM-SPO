# Phase 50: Goal Page — Frontend UI - Research

**Researched:** 2026-03-13
**Domain:** React + shadcn/ui, React Query, Tailwind CSS, custom progress bar with milestone markers
**Confidence:** HIGH

## Summary

Phase 50 builds the Goal page entirely in the frontend. Phase 49 already delivered the backend (GoalView at `GET/PATCH /api/v1/goals/me/`, `GoalJournalSelection` model, `get_goal_progress()` service). This phase adds two small backend fields (`calls_completed`, `meetings_held`) to the User model and GoalView, then implements the full frontend: routing, nav, API client, hooks, three-card layout, custom progress bar component with tick marks, pacing stat tiles, motivational messages, and role-based read-only enforcement.

All patterns in this phase are already established in the codebase. The page follows the same lazy-load + ProtectedRoute structure as Dashboard/JournalDetail. The hooks follow the `useMPD.ts` pattern. The API client follows the `mpd.ts` pattern. The pacing tiles reference the Dashboard MPD Financial Overview grid (`sm:grid-cols-2 md:grid-cols-4`). The role-gating reads from `useAuth().user?.role` exactly like the existing admin/supervisor checks throughout the codebase.

The only genuinely new pattern is `GoalProgressBar`: a custom div-based bar (not the Radix UI `progress.tsx` component) with absolute-positioned tick marks at 25/50/75/100% and dynamic fill color based on Monthly Support percentage thresholds.

**Primary recommendation:** Build incrementally — backend fields first, then API layer, then hooks, then page shell + routing + nav, then GoalProgressBar component, then wire everything together with empty-state and read-only logic last.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Page layout**
- Single column, vertically stacked sections
- Three Cards: Goal Settings → Progress → Pacing Targets
- Sidebar nav: "Goal" link added between Dashboard and Contacts in `navItems`
- Goal page route: `/goal` (lazy-loaded, follows pattern of Dashboard/JournalDetail)

**Goal & journal editing UX**
- Goal Settings card: always-editable input fields (goal amount in dollars, goal_weeks)
- Journal selection: checkbox list of user's journals inside the Goal Settings card
- Single "Save" button at bottom of Goal Settings card — saves goal amount, goal_weeks, and journal selections together in one PATCH `/api/goals/me/`
- Read-only mode for supervisor/admin: all inputs and checkboxes disabled, Save button hidden; read-only label or indicator shown

**Calls/meetings input & storage**
- User manually enters calls completed and meetings held (no automatic task integration)
- Inputs live inside the Progress card, one per row next to the relevant progress bar (label | bar | [input])
- Values persisted to server — requires adding `calls_completed` (PositiveIntegerField, default=0) and `meetings_held` (PositiveIntegerField, default=0) to the backend User model or goals API response
- Saved via the same PATCH `/api/goals/me/` — calls and meetings inputs get their own Save button in the Progress card (or share a single save if UX feels cleaner — Claude's discretion)
- Read-only mode: inputs disabled for supervisor/admin

**Progress bars visual design**
- Custom `GoalProgressBar` component (not extending the generic Progress component)
- Milestone tick marks at 25%, 50%, 75%, 100% — absolute-positioned thin lines over the bar
- Monthly Support bar color:
  - Red (`destructive` / red-500) below 75%
  - Green (green-500 or success color) at 75–99%
  - Honey gold (amber-400 or yellow-500) at 100%+
- Calls and Meetings bars: default primary color (no dynamic color)
- Milestone messages: static text line directly below the Monthly Support bar, updates based on progress threshold (0%, 25%, 50%, 75%, 100%)
- Empty state: all three bars rendered at 0% in muted/disabled state with inline prompt text
  - No goal set: "Set a goal amount above to see your support progress"
  - Goal set but no journals selected: "Select journals above to see your support progress"
  - Calls/meetings: show 0% with dashes or "—" if no values entered yet

### Claude's Discretion
- Whether calls/meetings share the Goal Settings Save button or have their own Save in the Progress card
- Exact Tailwind classes for the honey gold color (amber-400 vs yellow-500 vs custom)
- Tick mark visual style (thin vertical line, dot, or small triangle)
- Whether to show a percentage label at the right of each bar
- Skeleton loading state for the page while API data loads

### Deferred Ideas (OUT OF SCOPE)
- Goal history / trend chart — Phase backlog (GOAL-EX-01, noted in Phase 49)
- Per-journal goal breakdown — Phase backlog (GOAL-EX-02, noted in Phase 49)
- Auto-pulling calls/meetings from Tasks data — deferred, user preferred manual entry for now
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GOAL-01 | Missionary can navigate to a dedicated Goal page from the sidebar (below Dashboard) | Add `{ label: "Goal", href: "/goal", icon: <Target .../> }` between Dashboard and Contacts in `navItems`; add lazy route in App.tsx |
| GOAL-05 | Goal page displays pacing targets: estimated calls and meetings needed based on goal amount (25 calls and 10 meetings per $1,000) | Pacing computed from `monthly_support_goal_cents`; tile grid pattern from Dashboard MPD Financial Overview (`sm:grid-cols-2 md:grid-cols-4`); greyed out when no goal set |
| GOAL-06 | Goal page displays three progress bars: Monthly Support ($), Calls Completed, and Meetings Held — each with 25/50/75/100% milestone markers | Custom `GoalProgressBar` component using `relative` container + absolute tick marks; `effective_monthly_support` from API; `calls_completed` and `meetings_held` from new backend fields |
| GOAL-07 | Monthly Support progress bar changes color by threshold (red <75%, green 75-99%, honey gold 100%) | Dynamic Tailwind color class or inline style on GoalProgressBar fill div based on computed percentage |
| GOAL-08 | Goal page shows motivational milestone messages at 0%, 25%, 50%, 75%, 100% progress thresholds | Static message map keyed by threshold bucket; text line below Monthly Support bar |
| GOAL-09 | Goal page shows empty-state messages when no goal is set or no journals are selected | Two empty-state conditions: `monthly_support_goal_cents === 0` and `selected_journal_ids.length === 0` |
| GOAL-10 | Supervisor and admin see Goal page in read-only mode (cannot edit goal or journal selections) | `const isReadOnly = user?.role === "supervisor" || user?.role === "admin"`; all inputs `disabled`, Save button hidden, read-only badge shown |
</phase_requirements>

---

## Standard Stack

### Core (already installed, verified from codebase)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.x | Component framework | Project standard |
| @tanstack/react-query | 5.x | Server state management | Project standard — QueryProvider wraps app |
| axios | 1.x | HTTP client | `apiClient` in `frontend/src/api/client.ts` |
| react-router-dom | 6.x | Client routing, lazy loading | All pages use lazy + ProtectedPage |
| tailwindcss | 3.x | Utility CSS | All styling uses Tailwind |
| lucide-react | Latest | Icons | Sidebar already imports `Target` from Settings.tsx context; used project-wide |
| shadcn/ui (Card, Input, Checkbox, Button, Label) | via components/ui/ | UI primitives | Already installed and used across project |

### No New Dependencies
Phase 50 introduces zero new npm packages. All required primitives exist.

### Backend fields (new, part of this phase)
- `calls_completed`: PositiveIntegerField(default=0) on User model
- `meetings_held`: PositiveIntegerField(default=0) on User model
- Both exposed via existing `GET/PATCH /api/v1/goals/me/` endpoint

---

## Architecture Patterns

### Recommended File Structure
```
apps/users/
├── migrations/0010_user_calls_meetings.py  # new
├── models.py                                # add calls_completed, meetings_held
├── views_goals.py                           # add calls/meetings to PATCH handler
└── goal_services.py                         # add calls/meetings to returned dict

frontend/src/
├── api/
│   └── goals.ts                             # new: GoalData type, getGoal(), updateGoal()
├── hooks/
│   └── useGoal.ts                           # new: useGoalData(), useUpdateGoal()
├── pages/
│   └── goal/
│       └── GoalPage.tsx                     # new: main page (lazy-loaded)
└── components/
    └── goal/
        └── GoalProgressBar.tsx              # new: custom progress bar component
```

### Pattern 1: Lazy-Loaded Page Route (HIGH confidence — direct observation)
**What:** Pages with complex sub-components are lazy-loaded in App.tsx.
**When to use:** All new pages follow this pattern.
```typescript
// frontend/src/App.tsx — add alongside existing lazy imports
const GoalPage = React.lazy(() => import("@/pages/goal/GoalPage"))

// Inside <Routes>:
<Route path="/goal" element={<ProtectedPage><GoalPage /></ProtectedPage>} />
```

### Pattern 2: Sidebar navItems Entry (HIGH confidence — direct observation)
**What:** `navItems` array in `Sidebar.tsx` drives top-nav. Items render via `NavLink`. Insert "Goal" at index 1 (after Dashboard, before Contacts).
```typescript
// frontend/src/components/layout/Sidebar.tsx
// Add to import list:
import { Target } from "lucide-react"

// Add to navItems array at index 1:
{ label: "Goal", href: "/goal", icon: <Target className="h-5 w-5" /> },
```
No `requiredRole` or `visibleRoles` needed — Goal page is visible to all authenticated users (read-only for supervisor/admin enforced on the page itself, not nav).

### Pattern 3: API Client Module (HIGH confidence — direct observation of mpd.ts)
```typescript
// frontend/src/api/goals.ts
import { apiClient } from "./client"

export interface GoalData {
  monthly_support_goal_cents: number
  goal_weeks: number
  selected_journal_ids: string[]
  effective_monthly_support: number   // dollars, from backend calc
  recurring_monthly: number           // dollars
  one_time_monthly: number            // dollars
  calls_completed: number             // new field (Phase 50 backend)
  meetings_held: number               // new field (Phase 50 backend)
}

export interface GoalUpdatePayload {
  monthly_support_goal_cents?: number
  goal_weeks?: number
  journal_ids?: string[]
  calls_completed?: number
  meetings_held?: number
}

export async function getGoal(): Promise<GoalData> {
  const response = await apiClient.get("/goals/me/")
  return response.data
}

export async function updateGoal(payload: GoalUpdatePayload): Promise<GoalData> {
  const response = await apiClient.patch("/goals/me/", payload)
  return response.data
}
```

### Pattern 4: React Query Hooks (HIGH confidence — direct observation of useMPD.ts)
```typescript
// frontend/src/hooks/useGoal.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { getGoal, updateGoal } from "@/api/goals"
import type { GoalUpdatePayload } from "@/api/goals"

export function useGoalData() {
  return useQuery({
    queryKey: ["goal"],
    queryFn: getGoal,
  })
}

export function useUpdateGoal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: GoalUpdatePayload) => updateGoal(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["goal"] })
    },
  })
}
```

### Pattern 5: Custom GoalProgressBar Component (HIGH confidence — CONTEXT.md specification)
**What:** A div-based progress bar with absolute-positioned milestone tick marks. Does NOT use Radix UI `ProgressPrimitive` because: (a) Radix applies `overflow-hidden` which clips absolutely-positioned children, (b) tick marks need to protrude slightly above/below the bar track.
**Structure:**
```typescript
// frontend/src/components/goal/GoalProgressBar.tsx
interface GoalProgressBarProps {
  value: number        // percentage 0-100 (clamped to 0-200 for display, bar clips at 100%)
  colorVariant?: "support" | "default"   // "support" = dynamic color; "default" = primary
  disabled?: boolean   // muted/greyed state for empty-state
  className?: string
}

// Implementation sketch:
// Outer: relative w-full h-3 bg-secondary rounded-full
// Fill: absolute h-full rounded-full transition-all (width: `${Math.min(pct, 100)}%`)
// Tick marks: four absolute divs at left-[25%], left-[50%], left-[75%], left-[100%]
//   height slightly taller than bar (h-4, -top-0.5) to protrude
//   width: 1px, bg: background/80 or white/50
```

**Dynamic color logic for Monthly Support bar:**
```typescript
function getSupportBarColor(pct: number): string {
  if (pct >= 100) return "bg-amber-400"          // honey gold
  if (pct >= 75)  return "bg-green-500"           // green
  return "bg-destructive"                          // red (< 75%)
}
```

### Pattern 6: Pacing Tile Calculations (HIGH confidence — from REQUIREMENTS.md and CONTEXT.md)
```typescript
// Constants (confirmed from REQUIREMENTS.md):
const CALLS_PER_1000 = 25
const MEETINGS_PER_1000 = 10

// Derived from goal amount:
const goalDollars = goalData.monthly_support_goal_cents / 100
const partnersNeeded = Math.ceil(goalDollars / (/* avg gift size — use goal_weeks? */ 1))
// Note: "Partners Needed" calculation needs clarification (see Open Questions)
const callsNeeded = Math.ceil((goalDollars / 1000) * CALLS_PER_1000)
const meetingsNeeded = Math.ceil((goalDollars / 1000) * MEETINGS_PER_1000)
const apptPerWeek = goalData.goal_weeks > 0
  ? (meetingsNeeded / goalData.goal_weeks).toFixed(1)
  : "—"
```

### Pattern 7: Role-Based Read-Only Enforcement (HIGH confidence — direct observation)
```typescript
// Matches existing pattern in Dashboard.tsx and other pages
const { user } = useAuth()
const isReadOnly = user?.role === "supervisor" || user?.role === "admin"

// Usage: <Input disabled={isReadOnly} ... />
// Usage: <Checkbox disabled={isReadOnly} ... />
// Usage: {!isReadOnly && <Button type="submit">Save</Button>}
// Badge: {isReadOnly && <span className="text-xs text-muted-foreground">Read-only</span>}
```

### Pattern 8: Save Feedback (HIGH confidence — direct observation of Settings.tsx)
```typescript
// Follow Settings.tsx profileSuccess pattern:
const [saveSuccess, setSaveSuccess] = useState(false)
// After mutation onSuccess:
setSaveSuccess(true)
setTimeout(() => setSaveSuccess(false), 3000)
// Render:
{saveSuccess && (
  <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
    <CheckCircle className="h-4 w-4" />
    Saved successfully
  </div>
)}
```

### Pattern 9: Backend Field Addition (HIGH confidence — follows Phase 49 migration pattern)
```python
# apps/users/models.py — add two fields to User:
calls_completed = models.PositiveIntegerField(
    'calls completed',
    default=0,
)
meetings_held = models.PositiveIntegerField(
    'meetings held',
    default=0,
)

# apps/users/views_goals.py — add to PATCH handler (follows existing pattern):
if 'calls_completed' in data:
    try:
        value = int(data['calls_completed'])
    except (TypeError, ValueError):
        return Response({'error': 'calls_completed must be a non-negative integer'}, status=400)
    if value < 0:
        return Response({'error': 'calls_completed must be a non-negative integer'}, status=400)
    user.calls_completed = value
    update_fields.append('calls_completed')
# Same pattern for meetings_held

# apps/users/goal_services.py — add to returned dict:
'calls_completed': user.calls_completed,
'meetings_held': user.meetings_held,
```

### Anti-Patterns to Avoid
- **Using Radix `<Progress>` for GoalProgressBar:** `overflow-hidden` on the root clips tick marks. Build `GoalProgressBar` from scratch with divs.
- **Tick marks as border-left on fill div:** Fill width changes; tick positions would shift. Use absolute positioning on the container relative to track width instead.
- **Computing pacing tiles from `effective_monthly_support`:** Pacing is based on `monthly_support_goal_cents` (the target), not current support level.
- **Storing cents in dollar input:** User sees and types dollars; multiply by 100 before PATCHing. When reading from API, divide by 100 for display.
- **`undefined` in query key:** Follow existing pattern — use clean primitive values in queryKey `["goal"]`, not objects with undefined fields.
- **Missing loading skeleton:** Without skeleton/loading state, inputs flash empty then populate on API response, causing layout shift (ui-ux-pro-max `content-jumping` rule).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Checkbox UI | Custom input[type=checkbox] | `Checkbox` from `@/components/ui/checkbox.tsx` | Already installed, matches design system |
| Card layout | Custom div-based card | `Card/CardHeader/CardContent` from `@/components/ui/card.tsx` | Already installed, used everywhere |
| Text inputs | Custom input | `Input` from `@/components/ui/input.tsx` | Already installed |
| API calls | Raw fetch | `apiClient` from `@/api/client.ts` | Auth token injection, refresh logic, error handling |
| Server state | useState + useEffect | `useQuery` / `useMutation` from react-query | Caching, deduplication, stale handling |
| Success/error toasts | Custom state message | `toast()` from sonner (already in project) | Consistent UX, already wired at app root |
| Currency formatting | Custom formatter | `Intl.NumberFormat` (already used in Dashboard.tsx) | Handles locale, rounding |

---

## Common Pitfalls

### Pitfall 1: Cents/Dollars Conversion
**What goes wrong:** Goal amount stored as cents on backend (e.g., `350000` = $3,500). Display raw value and user sees "$350000".
**Why it happens:** API returns `monthly_support_goal_cents` as integer cents.
**How to avoid:** On read: `const dollarValue = (goalData.monthly_support_goal_cents / 100).toString()`. On write: `Math.round(parseFloat(inputValue) * 100)`.
**Warning signs:** Goal amount input shows value 100x too large.

### Pitfall 2: Progress Bar Overflow at 100%+
**What goes wrong:** If `effective_monthly_support > monthly_support_goal`, percentage > 100%, fill div expands past container.
**Why it happens:** No clamp on the percentage.
**How to avoid:** `const fillPct = Math.min((effective / goal) * 100, 100)`. Show percentage value as `Math.round((effective / goal) * 100)` for label (can exceed 100%).

### Pitfall 3: Division by Zero in Progress Calculation
**What goes wrong:** If `monthly_support_goal_cents === 0`, dividing `effective_monthly_support` by goal gives `Infinity` or `NaN`.
**Why it happens:** User hasn't set a goal yet.
**How to avoid:** Gate the progress calculation: `const pct = goalCents > 0 ? (effective / (goalCents / 100)) * 100 : 0`. This also triggers the empty-state rendering.

### Pitfall 4: Journal Checkbox State Sync
**What goes wrong:** `selected_journal_ids` from API contains string UUIDs. Journal list from `useJournals()` returns objects with `id` field (also string UUID). Checking `selectedIds.includes(journal.id)` fails if type or format differs.
**Why it happens:** Backend returns UUIDs as strings; frontend journal IDs are also strings. Should be fine, but requires attention.
**How to avoid:** Always coerce to `String()` on both sides before comparing. Maintain a `Set<string>` for O(1) lookup during render.

### Pitfall 5: Stale API Cache After PATCH
**What goes wrong:** User saves goal settings, data appears to revert momentarily.
**Why it happens:** `queryClient.invalidateQueries({ queryKey: ["goal"] })` triggers refetch, but there's a brief window where old data shows.
**How to avoid:** The invalidation pattern is correct and consistent with other hooks. Alternatively use mutation `onSuccess` to directly set query data from the mutation response (already returned by PATCH). This avoids an extra round-trip.

### Pitfall 6: Goal_weeks Input Not Validated as Integer
**What goes wrong:** User enters `"26.5"` weeks — `parseInt("26.5") === 26` so it passes, but the display is misleading.
**Why it happens:** HTML `<Input type="number">` allows decimals by default.
**How to avoid:** Add `step="1"` and `min="1"` attributes to goal_weeks input. Validate `Number.isInteger(Number(value))` before submitting.

### Pitfall 7: Milestone Tick Marks Off-Center at Boundaries
**What goes wrong:** Tick at 100% (`left-[100%]`) renders partially outside the container if not adjusted.
**Why it happens:** `left: 100%` positions the left edge of the tick at the right edge of the container.
**How to avoid:** Use `left-[100%] -translate-x-1/2` on tick marks, or use `left-[24%]`, `left-[49%]`, `left-[74%]`, `left-[99%]` with half-width offset. Alternatively: `left-[25%] -translate-x-px` pattern.

### Pitfall 8: Journal List Pagination
**What goes wrong:** User with many journals only sees first 10 (DRF default page size) in the checkbox list.
**Why it happens:** `getJournals()` returns a paginated response.
**How to avoid:** Fetch with `page_size=100` param (or use `is_archived=false` to reduce set). Pattern: `useJournals({ page_size: "100" })`. Check `data.results` not `data` for the array.

---

## Code Examples

### Milestone Message Map
```typescript
// Source: CONTEXT.md specification
const MILESTONE_MESSAGES: Record<number, string> = {
  0:   "Every journey starts with a first step — you've got this!",
  25:  "You're a quarter of the way there. Keep making those calls!",
  50:  "Halfway home! Your faithfulness is making a real difference.",
  75:  "Almost there — the finish line is in sight. Keep pressing in!",
  100: "Goal reached! Thank you for your faithful support-raising.",
}

function getMilestoneMessage(pct: number): string {
  if (pct >= 100) return MILESTONE_MESSAGES[100]
  if (pct >= 75)  return MILESTONE_MESSAGES[75]
  if (pct >= 50)  return MILESTONE_MESSAGES[50]
  if (pct >= 25)  return MILESTONE_MESSAGES[25]
  return MILESTONE_MESSAGES[0]
}
```

### Pacing Tiles Grid (MPD Financial Overview pattern from Dashboard.tsx)
```typescript
// Pattern source: Dashboard.tsx lines 175-183 and MPDStatsInline component
<div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
  {/* Partners Needed, Calls Needed, Appointments Needed, Appointments/Week */}
</div>
```

### Greyed Pacing Tiles (when no goal set)
```typescript
// Source: CONTEXT.md specification
const pacingDisabled = goalData.monthly_support_goal_cents === 0

<CardContent className={cn(pacingDisabled && "opacity-40 pointer-events-none")}>
  ...
</CardContent>
// Or show "—" as the value when disabled
```

### Read-Only Banner Pattern
```typescript
// Source: Settings.tsx observation + CONTEXT.md specification
{isReadOnly && (
  <div className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
    <ShieldCheck className="h-4 w-4" />
    You are viewing this page in read-only mode
  </div>
)}
```

### Dollar Input ↔ Cents Conversion
```typescript
// Source: verified pattern from existing monthly_support_goal_cents usage
// Reading from API:
const [goalDollars, setGoalDollars] = useState(
  String(goalData.monthly_support_goal_cents / 100)
)
// Writing to API:
const centsValue = Math.round(parseFloat(goalDollars) * 100)
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Radix Progress for all bars | Custom div bar for GoalProgressBar | Radix clips children via overflow-hidden; tick marks need to pierce the clip |
| Global staleTime only | queryKey-specific staleTime optional | Goal data changes infrequently; default 5-min staleTime is acceptable |

---

## Open Questions

1. **Partners Needed tile calculation**
   - What we know: CONTEXT.md says "Partners Needed" tile exists; REQUIREMENTS.md says pacing is "25 calls and 10 meetings per $1,000"
   - What's unclear: The formula for "Partners Needed" is not specified (number of new donors needed to reach goal?)
   - Recommendation: Compute as `Math.ceil(goalDollars / 100)` (assuming average $100/month partner) or show "—" with a note "based on avg gift". Confirm with user during review, or use a reasonable default (e.g., divide goal by $75 typical monthly gift). The planner should mark this as requiring a design decision.

2. **calls_completed / meetings_held: User model vs. separate table**
   - What we know: CONTEXT.md says "add to backend User model or goals API response"
   - What's clear: User model fields are simplest — same migration pattern as `goal_weeks`. No history needed.
   - Recommendation: Add to User model directly. Phase 50 migration adds two PositiveIntegerField columns.

3. **Progress card Save button placement**
   - What we know: Claude has discretion whether calls/meetings share the Goal Settings Save or have their own Save in Progress card
   - Recommendation: Give the Progress card its own "Save Progress" button. This keeps the two save surfaces independent and avoids accidentally resetting journal selections when saving calls/meetings.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-django |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest apps/users/tests/test_views_goals.py -x --no-cov` |
| Full suite command | `pytest --cov=apps --cov-report=term-missing` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GOAL-01 | Goal route renders and nav link present | smoke (manual) | n/a — frontend route | Wave 0 (no frontend test framework) |
| GOAL-05 | Pacing tile values computed correctly from goal | unit | `pytest apps/users/tests/test_goal_services.py -x --no-cov` | Extend existing ✅ |
| GOAL-06 | PATCH saves calls_completed and meetings_held | integration | `pytest apps/users/tests/test_views_goals.py -x --no-cov` | Extend existing ✅ |
| GOAL-07 | Progress bar color class varies with pct | unit (manual UI) | n/a — visual, no frontend test infra | Wave 0 gap |
| GOAL-08 | Milestone message returns correct text per pct | unit | n/a — pure function, can be tested manually | n/a |
| GOAL-09 | Empty state renders when goal=0 or journals=[] | integration | `pytest apps/users/tests/test_views_goals.py -x --no-cov` | Extend existing ✅ |
| GOAL-10 | GET /api/v1/goals/me/ returns 200 for supervisor | integration | `pytest apps/users/tests/test_views_goals.py::test_supervisor_read_only -x --no-cov` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/users/tests/test_views_goals.py apps/users/tests/test_goal_services.py -x --no-cov`
- **Per wave merge:** `pytest --cov=apps --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/users/tests/test_views_goals.py` — extend with: `test_patch_saves_calls_completed`, `test_patch_saves_meetings_held`, `test_supervisor_can_get_goal_readonly`, `test_get_returns_calls_meetings_fields`
- [ ] Backend migration `0010_user_calls_meetings.py` — prerequisite before any test runs against new fields

*(No frontend test infrastructure exists in this project — frontend behaviors are validated manually per UI/UX guidelines)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase reading: `apps/users/views_goals.py`, `goal_services.py`, `models.py` — Phase 49 backend verified complete
- Direct codebase reading: `frontend/src/App.tsx` — lazy route pattern confirmed
- Direct codebase reading: `frontend/src/components/layout/Sidebar.tsx` — navItems pattern confirmed
- Direct codebase reading: `frontend/src/hooks/useMPD.ts` — React Query hook pattern confirmed
- Direct codebase reading: `frontend/src/api/mpd.ts` — API client module pattern confirmed
- Direct codebase reading: `frontend/src/pages/settings/Settings.tsx` — save feedback pattern, CheckCircle, read-only pattern
- Direct codebase reading: `frontend/src/pages/Dashboard.tsx` — MPD tile grid, stat tile rendering pattern
- Direct codebase reading: `frontend/src/components/ui/progress.tsx` — confirms Radix UI overflow-hidden (reason to build custom)
- Direct codebase reading: `frontend/src/hooks/useJournals.ts` — paginated journal fetch pattern
- `.planning/phases/50-goal-page-frontend-ui/50-CONTEXT.md` — all user decisions verified

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — pacing constants (25 calls / 10 meetings per $1,000) confirmed
- `.claude/skills/ui-ux-pro-max/SKILL.md` — accessibility rules applied (contrast, focus states, content-jumping)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in codebase, no new dependencies needed
- Architecture: HIGH — all patterns directly observed in existing code
- Backend changes: HIGH — straightforward PositiveIntegerField additions following Phase 49 pattern
- Pitfalls: HIGH — sourced from direct code analysis (Radix overflow-hidden, cents/dollars, pagination)
- Pacing formulas: MEDIUM — REQUIREMENTS.md confirms calls/meetings ratios; "Partners Needed" formula unspecified

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable stack, 30-day validity)
