---
phase: 50
slug: goal-page-frontend-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 50 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-django |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest apps/users/tests/test_views_goals.py -x --no-cov` |
| **Full suite command** | `pytest --cov=apps --cov-report=term-missing` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/users/tests/test_views_goals.py apps/users/tests/test_goal_services.py -x --no-cov`
- **After every plan wave:** Run `pytest --cov=apps --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 50-01-01 | 01 | 1 | GOAL-06 | integration | `pytest apps/users/tests/test_views_goals.py::test_patch_saves_calls_completed -x --no-cov` | ❌ Wave 0 | ⬜ pending |
| 50-01-02 | 01 | 1 | GOAL-06 | integration | `pytest apps/users/tests/test_views_goals.py::test_patch_saves_meetings_held -x --no-cov` | ❌ Wave 0 | ⬜ pending |
| 50-01-03 | 01 | 1 | GOAL-06 | integration | `pytest apps/users/tests/test_views_goals.py::test_get_returns_calls_meetings_fields -x --no-cov` | ❌ Wave 0 | ⬜ pending |
| 50-01-04 | 01 | 1 | GOAL-10 | integration | `pytest apps/users/tests/test_views_goals.py::test_supervisor_can_get_goal_readonly -x --no-cov` | ❌ Wave 0 | ⬜ pending |
| 50-02-01 | 02 | 2 | GOAL-01 | manual | Navigate to /goal — sidebar link visible, page loads | n/a | ⬜ pending |
| 50-02-02 | 02 | 2 | GOAL-01 | manual | Goal route protected — unauthenticated redirect to login | n/a | ⬜ pending |
| 50-03-01 | 03 | 3 | GOAL-06 | integration | `pytest apps/users/tests/test_views_goals.py -x --no-cov` | ✅ | ⬜ pending |
| 50-03-02 | 03 | 3 | GOAL-07 | manual | Monthly Support bar red below 75%, green 75–99%, amber at 100% | n/a | ⬜ pending |
| 50-03-03 | 03 | 3 | GOAL-08 | manual | Milestone message updates at 0/25/50/75/100% thresholds | n/a | ⬜ pending |
| 50-03-04 | 03 | 3 | GOAL-09 | manual | Empty state shows when no goal set or no journals selected | n/a | ⬜ pending |
| 50-04-01 | 04 | 4 | GOAL-05 | unit | `pytest apps/users/tests/test_goal_services.py -x --no-cov` | ✅ | ⬜ pending |
| 50-04-02 | 04 | 4 | GOAL-05 | manual | Pacing tiles show "—" when no goal set | n/a | ⬜ pending |
| 50-05-01 | 05 | 5 | GOAL-10 | integration | `pytest apps/users/tests/test_views_goals.py::test_supervisor_can_get_goal_readonly -x --no-cov` | ❌ Wave 0 | ⬜ pending |
| 50-05-02 | 05 | 5 | GOAL-10 | manual | Supervisor/admin: all inputs disabled, Save hidden, read-only banner visible | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/users/tests/test_views_goals.py` — extend with: `test_patch_saves_calls_completed`, `test_patch_saves_meetings_held`, `test_supervisor_can_get_goal_readonly`, `test_get_returns_calls_meetings_fields`
- [ ] Backend migration `0010_user_calls_meetings.py` — prerequisite before any test runs against new User fields

*Existing test infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Goal nav link visible in sidebar below Dashboard | GOAL-01 | No frontend test infra | Log in as missionary, verify "Goal" appears between Dashboard and Contacts in sidebar |
| Monthly Support bar color changes by threshold | GOAL-07 | Visual/CSS — no frontend test infra | Set goal to $1000, add journal with varying support amounts; verify red/green/amber |
| Milestone messages update at thresholds | GOAL-08 | Visual text content — no frontend test infra | Set goal, add support at 0/25/50/75/100% levels; read message below bar |
| Empty state when no goal set | GOAL-09 | Frontend render state — no backend test | Clear goal amount, verify prompt text appears |
| Empty state when no journals selected | GOAL-09 | Frontend render state — no backend test | Deselect all journals, verify prompt text appears |
| Pacing tiles show "—" when no goal | GOAL-05 | Frontend render state | Clear goal amount, verify all pacing tiles show "—" |
| Supervisor sees read-only page | GOAL-10 | Role-based UI — no frontend test infra | Log in as supervisor, navigate to /goal, verify inputs disabled, Save hidden |
| Admin sees read-only page | GOAL-10 | Role-based UI — no frontend test infra | Log in as admin, navigate to /goal, verify inputs disabled, Save hidden |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
