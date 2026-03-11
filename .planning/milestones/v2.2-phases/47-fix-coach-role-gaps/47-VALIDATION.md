---
phase: 47
slug: fix-coach-role-gaps
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 47 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-django |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest apps/contacts/tests/ apps/users/tests/ apps/imports/tests/ apps/insights/tests/ -x -q` |
| **Full suite command** | `python -m pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest apps/contacts/tests/ apps/users/tests/ apps/imports/tests/ apps/insights/tests/ -x -q`
- **After every plan wave:** Run `python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 47-01-01 | 01 | 1 | ROLE-01 | unit | `python -m pytest conftest.py apps/imports/tests/test_spo_views.py apps/imports/tests/test_spo_csv_fixture_mapping.py apps/insights/tests/test_user_drilldown.py -x -q` | ✅ (failing) | ⬜ pending |
| 47-02-01 | 02 | 1 | ROLE-03 | integration | `python -m pytest apps/contacts/tests/ -x -q -k coach` | ❌ W0 | ⬜ pending |
| 47-02-02 | 02 | 1 | ROLE-04 | integration | `python -m pytest apps/users/tests/test_views.py -x -q -k coached_user_ids` | ❌ W0 | ⬜ pending |
| 47-02-03 | 02 | 1 | ROLE-05 | integration | `python -m pytest apps/contacts/tests/ -x -q -k coach` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/contacts/tests/test_integration.py` — add `TestCoachContactAccess` class with tests for ROLE-03 and ROLE-05
- [ ] `apps/users/tests/test_views.py` — add `test_admin_can_set_coached_user_ids` for ROLE-04

*Note: The 4 stale-role files (ROLE-01) already exist and are failing — Wave 0 for Plan 01 is fixing those strings, not creating new files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Coach can navigate to `/team/:userId` Contacts tab and see contacts in browser | ROLE-05 | End-to-end UI flow | 1. Log in as coach user 2. Navigate to an assigned missionary's team page 3. Click Contacts tab 4. Verify contacts load without 403 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
