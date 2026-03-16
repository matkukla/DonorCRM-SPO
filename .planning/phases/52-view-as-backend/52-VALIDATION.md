---
phase: 52
slug: view-as-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 52 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest apps/core/tests/test_middleware.py apps/users/tests/test_views_viewable.py apps/core/tests/test_permissions.py -x` |
| **Full suite command** | `pytest --cov=apps --cov-fail-under=80` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/core/tests/test_middleware.py apps/users/tests/test_views_viewable.py apps/core/tests/test_permissions.py -x`
- **After every plan wave:** Run `pytest --cov=apps --cov-fail-under=80`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 52-01-01 | 01 | 0 | VIEWAS-07, VIEWAS-08, VIEWAS-12 | unit/integration | `pytest apps/core/tests/test_middleware.py apps/users/tests/test_views_viewable.py apps/core/tests/test_permissions.py -x` | ❌ W0 | ⬜ pending |
| 52-02-01 | 02 | 1 | VIEWAS-07, VIEWAS-08 | integration | `pytest apps/core/tests/test_middleware.py -x` | ❌ W0 | ⬜ pending |
| 52-02-02 | 02 | 1 | VIEWAS-08 | unit | `pytest apps/core/tests/test_permissions.py::test_view_as_overrides_scoping -x` | ❌ W0 | ⬜ pending |
| 52-03-01 | 03 | 1 | VIEWAS-08 | integration | `pytest apps/core/tests/test_permissions.py -x` | ❌ W0 | ⬜ pending |
| 52-04-01 | 04 | 1 | VIEWAS-12 | integration | `pytest apps/users/tests/test_views_viewable.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/core/tests/test_middleware.py` — stubs for VIEWAS-07, VIEWAS-08 middleware behavior (mutation blocking, role validation, target validation)
- [ ] `apps/users/tests/test_views_viewable.py` — stubs for VIEWAS-12 (admin sees all, supervisor sees assigned, missionary gets 403)
- [ ] `apps/core/tests/test_permissions.py` — append `test_view_as_overrides_scoping` stub (file already exists)

*Existing infrastructure covers pytest + pytest-django; no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | All phase behaviors have automated verification | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
