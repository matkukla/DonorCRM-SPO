---
phase: 48
slug: mpd-dashboard-enhancements
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 48 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest apps/imports/tests/test_mpd_views.py -x --no-cov` |
| **Full suite command** | `pytest apps/imports/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/imports/tests/test_mpd_views.py -x --no-cov`
- **After every plan wave:** Run `pytest apps/imports/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 48-01-01 | 01 | 0 | MPD-01, MPD-02 | unit | `pytest apps/imports/tests/test_mpd_views.py -x --no-cov` | ❌ W0 | ⬜ pending |
| 48-02-01 | 02 | 1 | MPD-01 | unit | `pytest apps/imports/tests/test_mpd_views.py::test_mpd_my_data_includes_monthly_average -x --no-cov` | ❌ W0 | ⬜ pending |
| 48-02-02 | 02 | 1 | MPD-01 | unit | `pytest apps/imports/tests/test_mpd_views.py::test_mpd_my_data_monthly_average_null -x --no-cov` | ❌ W0 | ⬜ pending |
| 48-03-01 | 03 | 1 | MPD-02 | unit | `pytest apps/imports/tests/test_mpd_views.py::test_mpd_overview_includes_monthly_average -x --no-cov` | ❌ W0 | ⬜ pending |
| 48-03-02 | 03 | 1 | MPD-02 | unit | `pytest apps/imports/tests/test_mpd_views.py::test_mpd_overview_admin_only -x --no-cov` | ❌ W0 | ⬜ pending |
| 48-04-01 | 04 | 2 | MPD-01 | manual | Browser: Dashboard shows 4-col grid, Monthly Average tile first | N/A | ⬜ pending |
| 48-04-02 | 04 | 2 | MPD-02 | manual | Browser: Admin sees MPD Overview section below personal tiles | N/A | ⬜ pending |
| 48-04-03 | 04 | 2 | MPD-02 | manual | Browser: Non-admin does not see MPD Overview section | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/imports/tests/test_mpd_views.py` — stubs for MPD-01 and MPD-02 backend view assertions
- [ ] No factory needed — use `Model.objects.create()` directly (pattern from `apps/imports/tests/test_views.py`)

*Note: Frontend (React/Vite) has no test runner configured — frontend changes verified manually via browser.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Monthly Average tile renders first in 4-column grid | MPD-01 | No frontend test runner | Load Dashboard as non-admin with MPD data; verify 4 tiles in order: Monthly Average, MPD Cap, Roll Forward Balance, Months Remaining |
| Admin MPD Overview section renders below personal tiles | MPD-02 | No frontend test runner | Login as admin; verify MPD Overview section appears below personal MPD block |
| Non-admin does not see MPD Overview section | MPD-02 | No frontend test runner | Login as non-admin; verify no MPD Overview section present |
| Admin sees section even when viewing another user | MPD-02 | No frontend test runner | Login as admin, use View As; verify MPD Overview section still visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
