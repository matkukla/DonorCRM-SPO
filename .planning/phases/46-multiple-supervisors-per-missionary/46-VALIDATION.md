---
phase: 46
slug: multiple-supervisors-per-missionary
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-django (current version) |
| **Config file** | `pytest.ini` / `setup.cfg` (project root) |
| **Quick run command** | `pytest apps/users/tests/ -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~15 seconds (quick) / ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/users/tests/ -x -q`
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 46-W0-01 | W0 | 0 | M2M model behaviors | unit | `pytest apps/users/tests/test_m2m_assignments.py -x -q` | ❌ W0 | ⬜ pending |
| 46-W0-02 | W0 | 0 | Factory helpers | unit | `pytest apps/users/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 46-01-01 | 01 | 1 | Migration: FK→M2M data preserved | migration | `pytest --migrations apps/users/tests/test_m2m_assignments.py -x -q` | ❌ W0 | ⬜ pending |
| 46-01-02 | 01 | 1 | M2M field: symmetrical=False | unit | `pytest apps/users/tests/test_m2m_assignments.py::test_m2m_not_symmetrical -x -q` | ❌ W0 | ⬜ pending |
| 46-02-01 | 02 | 2 | AssignmentsView GET returns arrays | integration | `pytest apps/users/tests/test_m2m_assignments.py::test_assignments_get_returns_arrays -x -q` | ❌ W0 | ⬜ pending |
| 46-02-02 | 02 | 2 | AssignmentsView PATCH set (replace) | integration | `pytest apps/users/tests/test_m2m_assignments.py::test_assignments_patch_set -x -q` | ❌ W0 | ⬜ pending |
| 46-02-03 | 02 | 2 | AssignmentsView PATCH additive=True appends | integration | `pytest apps/users/tests/test_m2m_assignments.py::test_assignments_patch_additive -x -q` | ❌ W0 | ⬜ pending |
| 46-02-04 | 02 | 2 | Role change → auto-unassign M2M | unit | `pytest apps/users/tests/test_m2m_assignments.py::test_role_change_clears_m2m -x -q` | ❌ W0 | ⬜ pending |
| 46-02-05 | 02 | 2 | get_visible_user_ids() union across supervisors | unit | `pytest apps/users/tests/test_m2m_assignments.py::test_scoping_union -x -q` | ❌ W0 | ⬜ pending |
| 46-02-06 | 02 | 2 | UserSerializer exposes supervisor_ids[] | integration | `pytest apps/users/tests/test_m2m_assignments.py::test_user_serializer_supervisor_ids -x -q` | ❌ W0 | ⬜ pending |
| 46-03-01 | 03 | 3 | Frontend multi-select (manual) | manual | — | — | ⬜ pending |
| 46-03-02 | 03 | 3 | Supervisor view toggle renders (manual) | manual | — | — | ⬜ pending |
| 46-04-01 | 04 | 4 | User detail shows assigned missionaries (manual) | manual | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/users/tests/test_m2m_assignments.py` — new test file for all M2M behavioral stubs
- [ ] `apps/users/tests/factories.py` — add `SupervisorUserFactory` and `CoachUserFactory` if missing
- [ ] Test stubs covering: multi-supervisor assignment, additive bulk PATCH, role-change auto-clear, scoping union, serializer arrays, migration data preservation

*Existing infrastructure (pytest-django, factory-boy) covers all phase requirements — no new test packages needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-select chip UI in AdminAssignments table cell | Locked: chip/tag style | React UI behavior, no Playwright | Open Admin > Assignments, click supervisor cell, search and select 2+ supervisors, verify chips appear |
| Supervisor view toggle switches table layout | Locked: missionary/supervisor views | React UI state | Click toggle, verify rows become supervisors with missionary chips |
| Soft limit warning at 5+ supervisors | Locked: warn, don't enforce | UI-only feedback | Assign 5+ supervisors to one missionary, verify warning displays |
| User detail read-only missionary list | Locked: supervisor detail page | React UI | Open Admin > Users > [supervisor], verify assigned missionaries listed |
| Bulk additive applies without removing existing | Locked: bulk is additive | E2E workflow | Assign sup1 to missionary A, then bulk-apply sup2 to same missionary, verify both assigned |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
