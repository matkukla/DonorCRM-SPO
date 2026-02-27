# Project Research Summary

**Project:** DonorCRM v2.2 — UI Polish, Journal Report Rebuild & Mission Supervisor Role
**Domain:** Missionary donor CRM — role expansion, reporting rebuild, prayer workflow, UI refinement
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

DonorCRM v2.2 is a focused internal improvement milestone on a mature Django + React codebase. The defining characteristic of this milestone is that every feature is an enhancement to existing infrastructure — no new dependencies, no new architectural patterns, no greenfield components. The five feature areas (Mission Supervisor role, journal report rebuild, Begin Prayer expansion, dashboard modifications, and UI polish) all operate within the established stack of Django 4.2 / DRF, React 19 / TypeScript, Recharts 3.6, Radix UI, TanStack Query, and nuqs URL state. The recommended approach is to ship low-risk UI polish first, then self-contained feature rebuilds, and tackle the Mission Supervisor role last given its cross-cutting scope.

The key risk in this milestone is the Mission Supervisor role. Adding a new authorization tier — "sees assigned missionaries' data, not all data" — to a codebase built on a simple binary owner/admin model requires systematic changes across 40+ `get_queryset` methods and 11 admin analytics endpoints. The proven mitigation is to build a centralized `owner_scoped_filter()` Q helper in `apps/core/querysets.py` before touching any view, then mechanically refactor all views to use it. This makes supervisor scoping consistent by construction rather than relying on manually updating each view. The M2M relationship on User (`supervised_users = ManyToManyField('self', symmetrical=False)`) is the correct data model — it avoids cascade deletion issues that a FK approach would introduce and supports future multi-supervisor scenarios at zero additional cost.

All other features are lower-risk frontend component work against existing APIs. The journal report rebuild is the second-largest feature: a new aggregated backend endpoint (`GET /api/journals/analytics/report/?journal_id=X`) replacing four separate calls, and a new `JournalReport.tsx` component replacing four chart components. Begin Prayer is purely frontend — a new entry point that launches the existing `PrayerFocusMode`. Dashboard and UI polish changes are surgical frontend edits with zero backend impact.

## Key Findings

### Recommended Stack

Zero new dependencies are needed for all v2.2 features. Every capability required — bar charts, donut charts, progress bars, role-based routing, URL state management, drag-and-drop tiles — already exists in the installed packages. The installed stack is fully sufficient: Recharts 3.6.0 (BarChart, LineChart, PieChart/donut via `innerRadius`), `@radix-ui/react-progress` 1.1.8, `@radix-ui/react-select` 2.2.6, `nuqs` 2.8.8 for URL state, `lucide-react` for icons, and `@dnd-kit/core` + `@dnd-kit/sortable` for tile dragging.

**Core technologies (all pre-installed, zero new packages):**
- Django 4.2 + DRF: M2M relationship for supervisor assignments, queryset scoping via Q helpers, permission classes, migrations
- React 19 + TypeScript: All frontend feature components; no new patterns beyond what is already in use
- Recharts 3.6.0: Bar, line, and donut (PieChart with `innerRadius`) charts — all three types verified in active production files
- `@radix-ui/react-progress` 1.1.8: Goal progress bar in journal report — component exists at `components/ui/progress.tsx`
- nuqs 2.8.8: URL state for missionary dashboard selector (`?viewing_user=<uuid>`) — follows existing filter bar convention across all pages
- TanStack Query 5.90: Data fetching and cache invalidation for all new hooks; existing patterns reused
- `@dnd-kit/sortable` 10.0.0: Dashboard tile reordering already works; cross-section drag requires merging SortableContexts

See `STACK.md` for feature-by-feature technology analysis with exact file and line references for every component.

### Expected Features

**Must have (table stakes — UI polish, P1):**
- Dashboard text cleanup: remove "2026 calendar year" from GivingSummaryCard, "Updated today" from MonthlyGiftsCard, "Recent Journal Activity" tile entirely
- Rename "Prospect" to "Potential Donor" across ContactList, ContactForm, ContactDetail
- Remove Fund and Description columns from gifts page; add Type column
- Remove Fund column from pledges page
- Remove Review Queue and heatmap from analytics dashboard
- Audit and fix non-centered dialogs (audit Sheet vs Dialog usage before touching base component)
- Dashboard gap/spacing reduction (reduce `gap-6` to `gap-4`, `space-y-8` to `space-y-6`)

**Must have (differentiators, P1):**
- Mission Supervisor role: scoped read access to assigned missionaries' data across all endpoints and admin analytics
- Journal report rebuild: 4 metric cards, goal progress bar, stage bar chart, decision donut chart, checkbox direct-check behavior
- Dashboard bar/line chart toggle on MonthlyGiftsCard

**Should have (P2 — include if schedule permits):**
- Begin Prayer dedicated session entry point on prayer page and enhanced completion flow
- Dashboard cross-section tile dragging (flatten to single SortableContext)

**Defer (v2.3+):**
- Supervisor self-assignment capability — breaks admin control of org structure
- Persistent dashboard tile order — requires user preferences model and migration; explicitly out of scope in PROJECT.md
- Real-time prayer session sync — no WebSocket infrastructure; prayer is personal
- Dynamic column visibility toggle — UI complexity without validated user need

See `FEATURES.md` for complete dependency graph, impact matrix by file, and full anti-features analysis.

### Architecture Approach

The central architectural decision for v2.2 is the centralized `owner_scoped_filter()` Q helper in `apps/core/querysets.py`. This is the correct pattern because the current codebase has four distinct role-check patterns across 40+ `get_queryset` methods. Creating a single helper that returns a Q object (empty for admin/finance/read_only, owner-in-supervised-set for supervisor, owner-equals-user for staff) and refactoring all views to use it ensures the supervisor role gets consistent scoping without missed views. The journal report rebuild follows the same consolidation principle: replace four API calls and four chart components with one aggregated endpoint and one component.

**Major components:**
1. `apps/core/querysets.py` (new file) — `owner_scoped_filter(user, owner_field='owner')` Q helper; used by all 40+ owner-scoped views across contacts, journals, gifts, tasks, prayers, and insights apps
2. `User.supervised_users` M2M — self-referential `ManyToManyField('self', symmetrical=False)` mapping supervisors to assigned missionaries; creates `users_user_supervised_users` junction table automatically
3. New `report` action on `JournalAnalyticsViewSet` — single aggregated endpoint `GET /api/journals/analytics/report/?journal_id=X` replacing four separate analytics calls
4. `frontend/src/pages/journals/components/JournalReport.tsx` (new) — metrics, progress bar, Recharts bar and donut charts, conditional alert sections
5. `frontend/src/components/dashboard/MissionarySelector.tsx` (new) — Radix Select dropdown for supervisor/admin to view a missionary's dashboard; uses nuqs `?viewing_user=<uuid>`
6. `apps/dashboard/views.py` (modified) — `_get_viewable_user()` helper validates supervisor access to target user; passes target user to existing `get_dashboard_summary(user)` service (no service layer changes needed)

See `ARCHITECTURE.md` for complete view inventory (40+ methods with exact file:line references), component boundary definitions, anti-patterns, and build order rationale within each phase.

### Critical Pitfalls

1. **Supervisor queryset scoping is inconsistent across 40+ views with 4 distinct patterns** — The codebase uses `== 'admin'`, `in ['admin', 'finance', 'read_only']`, `!= 'admin'`, and separate `_scope_*` helper functions. Adding `supervisor` without a centralized Q helper will leak all data or lock supervisors out entirely across different endpoints. Prevention: build `owner_scoped_filter()` first, then refactor all views before adding any supervisor-specific logic.

2. **Self-referential FK on User creates cascade deletion traps** — A supervisor FK (PROTECT) blocks deactivating supervisors; (SET_NULL) silently orphans missionaries with no supervisor scope. Prevention: use M2M (`ManyToManyField('self', symmetrical=False)`) — deactivation leaves M2M rows harmless and querysets naturally return an empty supervised set.

3. **Frontend ProtectedRoute numeric hierarchy cannot express supervisor's mixed access model** — Supervisor needs admin-level page access (analytics dashboard) but not full admin access (user management). The current numeric hierarchy (admin:4, finance:3, staff:2, read_only:1) cannot encode this split. Prevention: replace with explicit per-route allowed-role arrays or capability maps; update `User` type in both `auth.ts` and `users.ts` (they are separate files with separate type definitions).

4. **Journal report requires a backend endpoint that does not currently exist** — The spec references `journalsApi.getReport(journalId)` but the backend only has separate analytics endpoints (decision-trends, stage-activity, pipeline-breakdown, next-steps-queue), not a per-journal aggregated report. Prevention: build the `JournalAnalyticsViewSet.report()` endpoint before or alongside the frontend component — never build frontend first against a missing API.

5. **Checkbox "direct check" conflicts with event-sourced stage tracking** — Stage is determined by `JournalStageEvent` history (see `get_current_stage` in `contacts/serializers.py`), not a boolean field. "Checking" a stage must create a stage event silently. Prevention: optimistically check the UI, POST to existing `JournalStageEventListCreateView` in the background, revert on mutation failure with a toast error.

See `PITFALLS.md` for 14 pitfalls total with phase-specific warnings, exact code locations, and prevention strategies verified against the actual codebase.

## Implications for Roadmap

Based on combined research, the phase structure is driven by three principles: (1) zero-dependency changes first, (2) self-contained features second, and (3) cross-cutting model changes last. Phases 1-3 can be executed in parallel or any order. Phase 4 must be last because the Q helper refactor in Phase 4 touches view files that Phase 2 also modifies — serializing Phase 4 avoids merge conflicts.

### Phase 1: UI Polish and Dashboard Modifications

**Rationale:** Zero backend changes, zero risk, immediate user-visible improvements. All items are independent of each other and of all other phases. Parallelizable within the phase.
**Delivers:** Cleaner dashboard text, corrected "Potential Donor" label, simplified gifts and pledges list pages, analytics UI trimmed of Review Queue and heatmap, fixed dialog centering, tighter dashboard gaps, bar/line chart toggle on MonthlyGiftsCard
**Addresses:** All "table stakes" table stakes features plus the chart toggle differentiator (LOW implementation cost, MEDIUM+ user value across all items)
**Avoids:** Pitfall 7 (remove column and its filter together, not column alone), Pitfall 10 (audit which flows use Sheet vs Dialog before touching base component — Sheet slides from side by design, Dialog centers), Pitfall 14 (remove analytics UI working backwards: sidebar link -> route -> component -> hook -> API client)
**Research flag:** Standard patterns — skip `/gsd:research-phase`

### Phase 2: Journal Report Rebuild

**Rationale:** Self-contained new endpoint plus new component pair. No interaction with other v2.2 features. Build backend endpoint first within this phase — front-ending a missing API produces confusing empty/error state during development.
**Delivers:** Rebuilt Reports tab with 4 metric cards, goal progress bar, stage bar chart (6 stages with specific hex colors), decision donut chart, conditional stalled/next-steps alert sections; checkbox direct-check behavior (auto-creates stage event without dialog); removal of old Pipeline Breakdown chart and ReportCharts.tsx components
**Addresses:** "Journal report rebuild" and "stage checkbox direct-check" features (both P1, both on the journal detail page — coupling them in one phase avoids duplicate journal page testing rounds)
**Avoids:** Pitfall 8 (build backend endpoint first), Pitfall 9 (checkboxes create stage events silently via optimistic updates, not a separate boolean field), Pitfall 12 (verify no other consumers of old chart components before deleting them — grep for all imports)
**Research flag:** Standard patterns — skip `/gsd:research-phase`; all chart types already in active use in the codebase with verified Recharts 3.6.0 APIs

### Phase 3: Begin Prayer

**Rationale:** Pure frontend, smallest scope of all feature phases, uses existing backend endpoints entirely. No risk of interfering with other work.
**Delivers:** Prominent "Begin Prayer" button on prayer page, wired to fetch today's focus intentions and open existing PrayerFocusMode; any UX enhancements to the focus session flow; enhanced completion summary
**Addresses:** "Begin Prayer" P2 differentiator feature
**Avoids:** Pitfall 11 (extend existing PrayerFocusMode — do not create a parallel fullscreen overlay with competing `window.keydown` handlers for Arrow, Space, Enter, P, Escape)
**Research flag:** Standard patterns — skip `/gsd:research-phase`; existing `PrayerFocusMode.tsx` is 243 lines of complete implementation

### Phase 4: Mission Supervisor Role

**Rationale:** Largest scope, most files modified, requires a Django migration, and the Q helper refactor touches view files that Phase 2 also modifies. Must execute last. The Q helper and view refactor are the load-bearing foundation — execute them first within this phase before any permission or frontend work.
**Delivers:** Supervisor role with scoped visibility across all data endpoints; supervisor assignment management API and admin UI; missionary dashboard selector for supervisor and admin users; supervisor access to admin analytics scoped to their assigned missionaries; frontend role hierarchy, sidebar navigation, and route guard updates
**Addresses:** "Mission Supervisor role" high-value P1 differentiator
**Build order within phase:** (1) User model + migration (SUPERVISOR choice + supervised_users M2M), (2) `owner_scoped_filter()` Q helper in `apps/core/querysets.py`, (3) refactor ALL 40+ views to use the helper, (4) `IsAdminOrSupervisor` permission class, (5) supervisor assignment management endpoint, (6) dashboard `user_id` param + `_get_viewable_user()`, (7) insights service scoping for supervisors, (8) frontend: User types in both `auth.ts` and `users.ts`, (9) frontend: role hierarchy replacement in `ProtectedRoute.tsx` and `Sidebar.tsx`, (10) frontend: `AdminUsers.tsx` role selector + assignment UI, (11) frontend: `MissionarySelector.tsx` component, (12) frontend: Dashboard wiring with nuqs `?viewing_user` param
**Avoids:** Pitfall 1 (centralized Q helper before touching any view), Pitfall 2 (M2M not FK), Pitfall 3 (permission classes control access level; querysets control data scope — two separate concerns), Pitfall 4 (capability-based route guards, not numeric hierarchy), Pitfall 5 (`_get_viewable_user()` validates supervisor access before returning target user data)
**Research flag:** Recommend `/gsd:research-phase` — the view inventory (40+ methods across 8 apps with 4 distinct patterns), insights service function scoping, and frontend role hierarchy replacement are complex enough to warrant a phase-level planning research pass before implementation begins

### Phase Ordering Rationale

- Phases 1-3 have zero inter-phase dependencies and can run in any order or in parallel across developers
- Phase 4 modifies `apps/journals/views.py` (adding a `report` action), which Phase 2 also modifies — doing Phase 4 last eliminates merge conflicts
- Within Phase 4, the Q helper and view refactor (steps 2-3) must precede all permission changes and all frontend work; the refactor is safe because it produces identical behavior for existing roles while adding the supervisor branch
- The supervisor M2M migration (step 1 of Phase 4) is non-destructive: it adds a new choice string to an existing CharField (`max_length=20`, 'supervisor' is 10 chars) and creates one new junction table — no data transformation needed

### Research Flags

Phases likely needing `/gsd:research-phase` during planning:
- **Phase 4 (Mission Supervisor):** 40+ views across 8 apps with 4 distinct scoping patterns; insights service functions require parameter-threading for supervisor filtering; frontend role hierarchy replacement needs careful audit of all `ProtectedRoute` `requiredRole` props in `App.tsx` and all `canAccess` / `roleHierarchy` usages in `Sidebar.tsx`

Phases with standard patterns (skip research-phase):
- **Phase 1 (UI Polish):** All changes are CSS values, label strings, and column array edits — no research needed
- **Phase 2 (Journal Report):** Chart types already in active use; API aggregation follows existing analytics viewset pattern; checkbox behavior change follows existing mutation/optimistic update pattern
- **Phase 3 (Begin Prayer):** Single component extension using existing backend — no research needed

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified every feature against actual installed package versions and existing code files with line references; confirmed zero new dependencies |
| Features | HIGH | Features sourced directly from user spec files in `prompts/`; codebase impact verified by reading source files with exact file:line locations |
| Architecture | HIGH | All patterns verified against actual view files; 40+ `get_queryset` methods inventoried and categorized; component boundaries confirmed by reading source |
| Pitfalls | HIGH | 14 pitfalls identified from direct codebase analysis of the actual four distinct role-check patterns, the event-sourced stage tracking model, and the DndContext structure — not speculative |

**Overall confidence: HIGH**

The high confidence across all areas reflects that this is a research milestone on an existing mature codebase, not a greenfield project. Research was conducted by reading actual source files rather than relying on external documentation.

### Gaps to Address

- **Dashboard "draggable anywhere" scope:** PITFALLS.md flags that true cross-section drag is significantly more complex than within-section reordering. The current three-SortableContext structure would require either flattening to a single array (losing distinct section grids) or adding cross-container drag logic with `useDroppable`. Clarify with the user during Phase 1 planning whether "drag anywhere" means cross-section or within-section before implementing.

- **Begin Prayer persistence decision:** FEATURES.md notes the decision between client-side-only prayer sessions vs. a `PrayerSession` model for server-side persistence. If the user wants sessions logged (e.g., "you prayed for 12 intentions on 2026-02-26"), a model + migration is needed. If a client-side completion summary is sufficient, no backend change is required. Clarify during Phase 3 planning.

- **Insights service scoping for supervisors:** The analytics service functions (`_scope_gifts`, `_scope_tasks` etc. in `apps/insights/services.py`) have their own role-check logic separate from the view-level Q helper pattern. The exact refactor approach — either extend helpers to accept a `user_ids` parameter, or thread the Q helper through — needs to be confirmed during Phase 4 planning.

- **Gift "Type" column source field:** PITFALLS.md flags that adding a `payment_type` field requires a migration with a careful default value (`blank=True, default=''`). Confirm whether this field already exists on the Gift model from RE import data (the RE import pipeline brings in a "Gift Type" column) or needs to be added fresh — check `apps/gifts/models.py` and the RE import serializer before Phase 1 implementation begins.

## Sources

### Primary (HIGH confidence — direct codebase analysis)
- `apps/users/models.py` — UserRole TextChoices, User model structure
- `apps/core/permissions.py` — 6 permission classes
- `apps/contacts/views.py`, `apps/journals/views.py`, `apps/gifts/views.py`, `apps/tasks/views.py`, `apps/prayers/views.py`, `apps/insights/views.py` — 40+ `get_queryset` methods, 4 distinct role-check patterns inventoried
- `apps/dashboard/views.py`, `apps/dashboard/services.py` — DashboardView, `get_dashboard_summary` with user parameter
- `apps/contacts/serializers.py` — event-sourced stage tracking via JournalStageEvent (`get_current_stage`)
- `frontend/src/components/auth/ProtectedRoute.tsx` — numeric role hierarchy (admin:4, finance:3, staff:2, read_only:1)
- `frontend/src/api/auth.ts`, `frontend/src/api/users.ts` — User type definitions with hardcoded role union
- `frontend/src/pages/Dashboard.tsx` — 3 SortableContext zones, handleDragEnd, tile render logic
- `frontend/src/pages/prayer/PrayerFocusMode.tsx` — 243 lines, keyboard handlers, fullscreen overlay
- `frontend/src/components/dashboard/GivingSummaryCard.tsx` — donut chart pattern (lines 80-94)
- `frontend/src/components/dashboard/MonthlyGiftsCard.tsx` — bar chart pattern (lines 60-99)
- `frontend/src/components/ui/progress.tsx` — Radix Progress component
- `frontend/src/components/ui/dialog.tsx` — Dialog centering via `translate-x[-50%] translate-y[-50%]`
- `frontend/package.json` — Exact installed package versions confirmed
- `requirements/base.txt` — Python package versions confirmed

### Primary (HIGH confidence — user spec documents)
- `prompts/mission_supervisor.md` — Mission Supervisor role requirements and access model
- `prompts/journal_report.md` — Detailed journal report component spec with API response shape
- `prompts/dashboard_modification.md` — Dashboard change list
- `prompts/prayer_intentions.md` — Begin Prayer feature requirements

### Primary (HIGH confidence — planning documents)
- `.planning/PROJECT.md` — Constraints, current state, out-of-scope items (persistent tile order explicitly excluded)
- `.planning/EDGE_CASE_AUDIT.md` — Known journal system edge cases
- `.planning/todos/pending/` — 9 pending todo files with feature specs

---
*Research completed: 2026-02-26*
*Ready for roadmap: yes*
