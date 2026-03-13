---
phase: 49
slug: goal-page-data-model-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest apps/core/tests/ apps/users/tests/ apps/dashboard/tests/ -x --no-cov` |
| **Full suite command** | `pytest --cov=apps --cov-fail-under=80` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/core/tests/ apps/users/tests/ apps/dashboard/tests/ -x --no-cov`
- **After every plan wave:** Run `pytest --cov=apps --cov-fail-under=80`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 0 | FISC-01, FISC-02 | unit | `pytest apps/core/tests/test_fiscal_year.py -x --no-cov` | ❌ W0 | ⬜ pending |
| 49-01-02 | 01 | 0 | GOAL-04 | unit | `pytest apps/users/tests/test_goal_services.py -x --no-cov` | ❌ W0 | ⬜ pending |
| 49-01-03 | 01 | 0 | GOAL-02, GOAL-03 | integration | `pytest apps/users/tests/test_views_goals.py -x --no-cov` | ❌ W0 | ⬜ pending |
| 49-02-01 | 02 | 1 | FISC-01, FISC-02 | unit | `pytest apps/core/tests/test_fiscal_year.py -x --no-cov` | ❌ W0 | ⬜ pending |
| 49-03-01 | 03 | 1 | GOAL-11 | unit | `pytest apps/users/tests/ -x --no-cov` | ✅ (extend) | ⬜ pending |
| 49-04-01 | 04 | 1 | GOAL-02, GOAL-03, GOAL-04 | integration | `pytest apps/users/tests/test_goal_services.py apps/users/tests/test_views_goals.py -x --no-cov` | ❌ W0 | ⬜ pending |
| 49-05-01 | 05 | 2 | GOAL-02, GOAL-03 | integration | `pytest apps/users/tests/test_views_goals.py -x --no-cov` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/core/tests/test_fiscal_year.py` — stubs for FISC-01, FISC-02 (boundary cases: July, June, January)
- [ ] `apps/users/tests/test_goal_services.py` — stubs for GOAL-04 (mock journals, contacts, gifts)
- [ ] `apps/users/tests/test_views_goals.py` — stubs for GOAL-02, GOAL-03 (API integration tests)
- [ ] Update `apps/users/tests/factories.py` — rename `monthly_goal` → `monthly_support_goal_cents`, add `goal_weeks`

*Wave 0 must pass before Wave 1 tasks begin.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Settings page no longer shows Fundraising Goal input (or shows link to Goal page) | GOAL-11 | Frontend UI change, no unit test coverage in Phase 49 | Navigate to /settings, confirm monthly_goal field is absent or replaced |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
