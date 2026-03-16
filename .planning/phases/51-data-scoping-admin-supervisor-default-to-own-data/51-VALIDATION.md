---
phase: 51
slug: data-scoping-admin-supervisor-default-to-own-data
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 51 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest apps/core/tests/test_permissions.py -x` |
| **Full suite command** | `pytest --cov=apps --cov-fail-under=80` |
| **Estimated runtime** | ~10 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/core/tests/test_permissions.py -x`
- **After every plan wave:** Run `pytest --cov=apps --cov-fail-under=80`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 51-01-01 | 01 | 0 | SCOPE-01 | unit | `pytest apps/core/tests/test_permissions.py -x` | ❌ W0 | ⬜ pending |
| 51-01-02 | 01 | 1 | SCOPE-01 | unit | `pytest apps/core/tests/test_permissions.py::test_admin_sees_only_own_data -x` | ❌ W0 | ⬜ pending |
| 51-01-03 | 01 | 1 | SCOPE-01 | unit | `pytest apps/core/tests/test_permissions.py::test_supervisor_sees_only_own_data -x` | ❌ W0 | ⬜ pending |
| 51-01-04 | 01 | 1 | SCOPE-01 | unit | `pytest apps/core/tests/test_permissions.py::test_finance_sees_all -x` | ❌ W0 | ⬜ pending |
| 51-01-05 | 01 | 1 | SCOPE-01 | unit | `pytest apps/core/tests/test_permissions.py -x` | ❌ W0 | ⬜ pending |
| 51-01-06 | 01 | 1 | SCOPE-02 | unit | `pytest apps/users/tests/test_m2m_assignments.py::TestM2MModelBehaviors::test_get_visible_user_ids_returns_missionary_for_both_supervisors -x` | ✅ (needs update) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/core/tests/test_permissions.py` — stubs/tests for SCOPE-01 (all six roles: admin, supervisor, finance, read_only, coach, missionary)

*Note: `apps/users/tests/test_m2m_assignments.py` exists but contains a test asserting old supervisor behavior — needs updating in Wave 1, not a new file gap.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin login sees only own contacts list | SCOPE-01 | E2E browser check | Log in as admin user, navigate to Contacts — verify only own contacts appear, not all users' |
| Supervisor login sees only own contacts | SCOPE-01 | E2E browser check | Log in as supervisor, navigate to Contacts — verify only own contacts appear |
| Admin with `?owner=<other-id>` query param cannot see other's data | SCOPE-01 | Integration behavior | Hit contacts API with admin token and `?owner=<other-user-id>` — verify empty/own results |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
