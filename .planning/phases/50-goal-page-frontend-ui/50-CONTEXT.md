# Phase 50: Goal Page — Frontend UI - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

New Goal page for missionaries to track fundraising progress: goal amount + journal selection (settings), three progress bars with milestone markers and color coding (Monthly Support, Calls, Meetings), pacing target stat tiles, motivational milestone messages, and read-only enforcement for supervisors and admins. Sidebar nav link added. No new backend models beyond what Phase 49 delivered — this phase adds `calls_completed` and `meetings_held` fields to the existing goals API.

</domain>

<decisions>
## Implementation Decisions

### Page layout
- Single column, vertically stacked sections
- Three Cards: Goal Settings → Progress → Pacing Targets
- Sidebar nav: "Goal" link added between Dashboard and Contacts in `navItems`
- Goal page route: `/goal` (lazy-loaded, follows pattern of Dashboard/JournalDetail)

### Goal & journal editing UX
- Goal Settings card: always-editable input fields (goal amount in dollars, goal_weeks)
- Journal selection: checkbox list of user's journals inside the Goal Settings card
- Single "Save" button at bottom of Goal Settings card — saves goal amount, goal_weeks, and journal selections together in one PATCH `/api/goals/me/`
- Read-only mode for supervisor/admin: all inputs and checkboxes disabled, Save button hidden; read-only label or indicator shown

### Calls/meetings input & storage
- User manually enters calls completed and meetings held (no automatic task integration)
- Inputs live inside the Progress card, one per row next to the relevant progress bar (label | bar | [input])
- Values persisted to server — requires adding `calls_completed` (PositiveIntegerField, default=0) and `meetings_held` (PositiveIntegerField, default=0) to the backend User model or goals API response
- Saved via the same PATCH `/api/goals/me/` — calls and meetings inputs get their own Save button in the Progress card (or share a single save if UX feels cleaner — Claude's discretion)
- Read-only mode: inputs disabled for supervisor/admin

### Progress bars visual design
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

</decisions>

<specifics>
## Specific Ideas

- The pacing targets section displays 4 stat tiles (2×2 or 1×4 grid): Partners Needed, Calls Needed, Appointments Needed, Appointments/Week — matching the MPD tile pattern (CardHeader + CardContent with text-2xl font-bold value)
- Pacing tiles should be greyed out / show "—" when no goal is set (can't compute targets without a goal)
- Milestone messages are motivational — Claude writes the copy for each threshold (0%, 25%, 50%, 75%, 100%)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/ui/progress.tsx`: Radix UI progress bar — do NOT modify. Build `GoalProgressBar` as a new component in `frontend/src/components/goal/` or `frontend/src/pages/goal/`
- `frontend/src/components/ui/card.tsx`: Card/CardHeader/CardContent — use for all three sections (Goal Settings, Progress, Pacing Targets)
- `frontend/src/components/ui/checkbox.tsx`: Use for journal selection list
- `frontend/src/components/ui/input.tsx`: Use for goal amount, goal_weeks, calls_completed, meetings_held inputs
- `frontend/src/components/layout/Sidebar.tsx`: `navItems` array — add `{ label: "Goal", href: "/goal", icon: <Target ... /> }` between Dashboard and Contacts (Target icon already imported in Settings.tsx)
- `frontend/src/pages/Dashboard.tsx` MPD tiles: Reference pattern for pacing stat tiles (text-2xl font-bold, CardHeader + CardContent)

### Established Patterns
- Lazy-loaded pages: `const GoalPage = React.lazy(() => import("@/pages/goal/GoalPage"))` in App.tsx — matches Dashboard, JournalDetail, etc.
- API hooks: create `useGoal` hook in `frontend/src/hooks/useGoal.ts` using React Query, following `useMPD.ts` pattern
- API client: create `frontend/src/api/goals.ts` with types and fetch functions for `GET/PATCH /api/goals/me/`
- Read-only enforcement: check `user?.role === "supervisor" || user?.role === "admin"` — same pattern as MPD admin check
- Money display: goal amount stored in cents on backend, display in dollars — follow existing `monthly_support_goal_cents` pattern
- Save feedback: show success state after save (follow Settings.tsx `profileSuccess` pattern with CheckCircle icon)

### Integration Points
- `frontend/src/components/layout/Sidebar.tsx`: Add Goal nav item to `navItems` array
- `frontend/src/App.tsx`: Add `/goal` route (lazy-loaded) and import GoalPage
- `frontend/src/api/goals.ts` (new): Types for GoalData response, updateGoal function calling `/api/goals/me/`
- `frontend/src/hooks/useGoal.ts` (new): `useGoalData()` and `useUpdateGoal()` React Query hooks
- `frontend/src/pages/goal/GoalPage.tsx` (new): Main page component
- `frontend/src/components/goal/GoalProgressBar.tsx` (new): Custom progress bar with tick marks and dynamic color
- Backend: `calls_completed` and `meetings_held` fields needed on goals API — Phase 50 adds these (small backend touch, part of this phase)

</code_context>

<deferred>
## Deferred Ideas

- Goal history / trend chart — Phase backlog (GOAL-EX-01, noted in Phase 49)
- Per-journal goal breakdown — Phase backlog (GOAL-EX-02, noted in Phase 49)
- Auto-pulling calls/meetings from Tasks data — deferred, user preferred manual entry for now

</deferred>

---

*Phase: 50-goal-page-frontend-ui*
*Context gathered: 2026-03-13*
