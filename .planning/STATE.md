---
gsd_state_version: 1.0
milestone: v2.3
milestone_name: Goal Tracking & View As
status: executing
stopped_at: Completed 53-03-PLAN.md
last_updated: "2026-03-17T07:27:08.157Z"
last_activity: 2026-03-18 - Completed quick task 260318-gc8: check test_data mapping
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 22
  completed_plans: 20
  percent: 8
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.
**Current focus:** Phase 48 — MPD Dashboard Enhancements (ready to plan)

## Current Position

Phase: 48 of 53 (MPD Dashboard Enhancements)
Plan: 02 of 2 (next to execute)
Status: Executing — Plan 01 complete, Plan 02 pending
Last activity: 2026-03-18 - Completed quick task 260318-gc8: check test_data mapping

Progress: [█░░░░░░░░░] 8% — 0/6 phases, 1/2 plans (phase 48)

## Performance Metrics

**Velocity:**
- Total plans completed: 141 (across v1.0–v2.2)
- Total phases: 47 complete
- Total milestones: 7 shipped

**v2.3 Phases:**

| Phase | Goal | Requirements |
|-------|------|-------------|
| 48 | MPD dashboard: Monthly Average tile + Admin MPD Overview | MPD-01, MPD-02 |
| 49 | Goal backend: fiscal year utility, data model, API | FISC-01, FISC-02, GOAL-02, GOAL-03, GOAL-04, GOAL-11 |
| 50 | Goal frontend: UI, progress bars, pacing, read-only | GOAL-01, GOAL-05, GOAL-06, GOAL-07, GOAL-08, GOAL-09, GOAL-10 |
| 51 | Data scoping: admin/supervisor default to own data | SCOPE-01, SCOPE-02 |
| 52 | View As backend: middleware, permissions, mutation blocking | VIEWAS-07, VIEWAS-08, VIEWAS-12 |
| 53 | View As frontend: context, banner, selector, cache | VIEWAS-01 through VIEWAS-06, VIEWAS-09, VIEWAS-10, VIEWAS-11 |
| Phase 48 P02 | 8 | 2 tasks | 4 files |
| Phase 48-mpd-dashboard-enhancements P02 | 30 | 3 tasks | 4 files |
| Phase 49 P01 | 4min | 3 tasks | 4 files |
| Phase 49 P02 | 4 | 2 tasks | 3 files |
| Phase 49 P03 | 25min | 2 tasks | 10 files |
| Phase 49 P04 | 6m | 2 tasks | 5 files |
| Phase 50 P01 | 1min | 1 tasks | 2 files |
| Phase 50 P02 | 2 | 1 tasks | 1 files |
| Phase 50 P03 | 1min | 2 tasks | 2 files |
| Phase 50 P04 | 6min | 3 tasks | 3 files |
| Phase 51 P01 | 17min | 1 tasks | 1 files |
| Phase 51 P02 | 6min | 2 tasks | 2 files |
| Phase 51 P03 | 2min | 2 tasks | 2 files |
| Phase 52-view-as-backend P01 | 2min | 2 tasks | 3 files |
| Phase 52 P04 | 15min | 2 tasks | 4 files |
| Phase 52-view-as-backend P03 | 17min | 2 tasks | 15 files |
| Phase 52-view-as-backend P02 | 18min | 1 tasks | 3 files |
| Phase 53 P01 | 3min | 2 tasks | 6 files |
| Phase 53-view-as-frontend P02 | 8min | 2 tasks | 3 files |
| Phase 53 P03 | 10min | 2 tasks | 14 files |

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

Recent decisions relevant to v2.3 (Phase 48):
- [48-01]: monthly_average positioned after user_name and before current_mpd_cap in MPDOverviewView — matches intended table column order

Recent decisions relevant to v2.3:
- [quick-15]: get_support_progress() scoped to donor_contact__owner=user for all roles — Monthly Support Goal is personal
- [Phase 47]: get_visible_user_ids() returns None sentinel for all-access roles — this sentinel will need to change under SCOPE-01 (admins default to own data)
- [Phase 46]: supervised_users field name kept in CurrentUserSerializer — frontend uses it for supervisor and coach
- [Phase 48]: Admin MPD Overview table placed outside the \!isViewingOther guard so admins see all-missionaries overview regardless of which user's dashboard they view
- [Phase 48-mpd-dashboard-enhancements]: Admin MPD Overview table requires both role=admin AND \!isViewingOther — hidden when admin browses a missionary's dashboard via View As
- [Phase 49-01]: Deferred imports in test stubs (inline inside test body) so all 17 items collect before implementation modules exist
- [Phase 49-01]: months_remaining returns 10 for Aug 15 (counts months AFTER current month through June); minimum guard returns 1 even on June 30
- [Phase 49-01]: UserFactory monthly_support_goal_cents uses random_int (integer cents 100000-1000000); goal_weeks defaults to 52
- [Phase 49]: FREQUENCY_MULTIPLIERS and _monthly_equivalent_aggregate extracted to apps/core/gift_utils.py so goal_services.py can import them without circular dashboard app dependency
- [Phase 49]: Case, When, RecurringGiftFrequency removed from dashboard/services.py imports after confirming no remaining usages after extraction
- [Phase 49-03]: Two-migration strategy: schema-only 0007 (RenameField + AddField + CreateModel) then data-conversion 0008 (RunPython + AlterField) avoids PostgreSQL type-cast error on direct decimal-to-integer ALTER
- [Phase 49-03]: API response dict keys kept as 'monthly_goal' in dashboard/services.py for backwards API compat — only model field access updated to monthly_support_goal_cents
- [Phase 49-04]: GoalView does not use a DRF serializer — reads request.data directly and returns get_goal_progress() dict, following existing CurrentUserView pattern
- [Phase 49-04]: selected_journal_ids returned as list of strings (str(jid)) for consistent JSON serialization across UUID fields
- [Phase 50-01]: JournalStageEvent FK chain is journal_contact__journal -> Journal, so counts use journal_contact__journal_id__in (not journal_id__in)
- [Phase 50-01]: Early-return path (no journals) explicitly returns calls_count=0 and meetings_count=0 to maintain consistent response shape
- [Phase 50-02]: Tick marks placed on wrapper div (not track or fill) to avoid clipping — allows fixed positions at 25/50/75/100% regardless of fill width
- [Phase 50-02]: disabled=true applies opacity-40 at wrapper level + bg-muted fill; 100% tick uses -translate-x-full to keep right edge inside container
- [Phase 50]: 50-03: GoalUpdatePayload excludes calls_count/meetings_count (server-computed, not writable via PATCH)
- [Phase 50]: 50-03: useUpdateGoal uses setQueryData(['goal'], data) not invalidateQueries to avoid stale-cache round-trip flash
- [Phase 50]: 50-03: PATCH write key is journal_ids (not selected_journal_ids) matching backend contract
- [Phase 50-04]: GoalPage built as single file with inline PacingTile — pacing values computed at component top-level shared by Progress bars and Pacing Targets card
- [Phase 50-04]: calls_count and meetings_count shown as read-only labels only — no input fields rendered on Progress card (server-computed from journal events)
- [Phase 51-01]: Supervisor test assigns a missionary (missionary.supervisors.add(sup)) to trigger RED state — supervisor with no supervised users already returns {sup.id} matching target assertion, so the test would have passed incorrectly without the assignment
- [Phase 51]: Admin and supervisor branches removed from get_visible_user_ids(); fallthrough return {user.id} handles all non-coach non-finance roles uniformly
- [Phase 51]: 15 pre-existing test failures confirmed not caused by Phase 51 changes; documented in deferred-items.md, out of scope
- [Phase 51-03]: Role guard in _resolve_target_user() placed BEFORE get_visible_user_ids() call — admin/supervisor bypass visibility check entirely for dashboard dropdown, not just after checking it
- [Phase 51-03]: Dashboard dropdown selection (explicit ?user_id=) and default data scoping are independent access patterns — _resolve_target_user() handles selection, get_visible_user_ids() handles list scoping
- [Phase 52-01]: test_get_allowed_in_view_as asserts status_code != 403 (not == 200) — middleware should not block; underlying view may return any code
- [Phase 52-01]: test_view_as_overrides_scoping uses .build() for both users — get_visible_user_ids is synchronous and doesn't query user objects directly, no DB needed
- [Phase 52]: viewable/ URL registered before <uuid:pk>/ to prevent literal path being caught by UUID converter
- [Phase 52]: Test URL in scaffold corrected from /api/users/viewable/ to /api/v1/users/viewable/ (all API endpoints use /api/v1/ prefix)
- [Phase 52-03]: dashboard/services.py not updated — target user already resolved via _resolve_target_user(request) in view layer
- [Phase 52-03]: insights _scope_* helpers and parent service functions gain request=None for view-context callers to thread request through
- [Phase 52-02]: _resolve_viewer() checks _force_auth_user (DRF test hook) before session auth and JWT Bearer — required for force_authenticate() to work in middleware
- [Phase 52-02]: DRF Response used for 403s in ViewAsMiddleware (not JsonResponse) — response.data['detail'] accessible to DRF test client assertions
- [Phase 52-02]: Mutation guard placed after _validate_and_attach — invalid target gets 'Invalid View As target' regardless of HTTP method; valid target + POST gets 'Mutations are not allowed'
- [Phase 53-01]: X-View-As-User-Id injected via string literal in client.ts interceptor (not import) to avoid circular dependency with ViewAsProvider.tsx
- [Phase 53-01]: VIEW_AS_USER_ID_KEY and VIEW_AS_USER_NAME_KEY exported from ViewAsProvider.tsx as constants for import by future plan components
- [Phase 53-01]: isViewingAs is derived as viewAsUserId !== null in context value object, not separate useState — avoids state sync bugs
- [Phase 53-02]: isViewingOther alias removed — all guards use isViewingAs directly from context (cleaner, one canonical name)
- [Phase 53-02]: effectiveMpdData = mpdData directly — X-View-As-User-Id header scopes MPD server-side, no client-side missionary lookup needed
- [Phase 53]: [53-03]: StageCell and EventTimelineDrawer use useViewAs() directly inside the component rather than via props — avoids prop drilling through JournalGrid intermediary
- [Phase 53]: [53-03]: ContactDetail/DonationDetail isReadOnly extended as isViewingAs || existingCondition — existing !isReadOnly guards cover all mutations automatically

### Pending Todos

21 pending todo(s). See `.planning/todos/pending/`.

### Blockers/Concerns

- SCOPE-01 changes existing admin/supervisor behavior (currently all-access by default). The get_visible_user_ids() None sentinel will need an update — admins will return their own user ID instead of None, unlocking all-access only in View As. Plan carefully to avoid breaking admin analytics dashboard.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260318-gc8 | check all the files in the test_data folder and make sure all the data in them will get mapped to the application correctly | 2026-03-18 | 53a8b34 | [260318-gc8-check-all-the-files-in-the-test-data-fol](./quick/260318-gc8-check-all-the-files-in-the-test-data-fol/) |

## Session Continuity

Last session: 2026-03-17T07:27:08.138Z
Stopped at: Completed 53-03-PLAN.md
Resume: Plan Phase 49 with `/gsd:plan-phase 49`
