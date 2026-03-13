---
gsd_state_version: 1.0
milestone: v2.3
milestone_name: Goal Tracking & View As
status: executing
stopped_at: Completed 49-03-PLAN.md
last_updated: "2026-03-13T03:24:55.867Z"
last_activity: 2026-03-12 — Phase 48 Plan 01 complete (monthly_average in MPD views)
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 6
  completed_plans: 5
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
Last activity: 2026-03-12 — Phase 48 Plan 01 complete (monthly_average in MPD views)

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

### Pending Todos

17 pending todo(s). See `.planning/todos/pending/`.

### Blockers/Concerns

- SCOPE-01 changes existing admin/supervisor behavior (currently all-access by default). The get_visible_user_ids() None sentinel will need an update — admins will return their own user ID instead of None, unlocking all-access only in View As. Plan carefully to avoid breaking admin analytics dashboard.

## Session Continuity

Last session: 2026-03-13T03:24:55.861Z
Stopped at: Completed 49-03-PLAN.md
Resume: Plan Phase 49 with `/gsd:plan-phase 49`
