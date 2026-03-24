---
phase: 56
slug: task-broadcasting-broadcast-tasks-to-targeted-user-groups-with-completion-tracking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-django |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `pytest apps/tasks/tests/ -x -q` |
| **Full suite command** | `pytest apps/tasks/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/tasks/tests/ -x -q`
- **After every plan wave:** Run `pytest apps/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 56-01-01 | 01 | 0 | BC-01,BC-02,BC-03 | unit stubs | `pytest apps/tasks/tests/test_broadcast_services.py -x` | ❌ W0 | ⬜ pending |
| 56-01-02 | 01 | 0 | BC-05,BC-06,BC-07 | unit stubs | `pytest apps/tasks/tests/test_broadcast_views.py -x` | ❌ W0 | ⬜ pending |
| 56-02-01 | 02 | 1 | BC-03 | unit | `pytest apps/tasks/tests/test_broadcast_services.py::TestCreateBroadcast -x` | ❌ W0 | ⬜ pending |
| 56-02-02 | 02 | 1 | BC-09,BC-10 | unit | `pytest apps/tasks/tests/test_broadcast_services.py::TestCascadeEdit -x` | ❌ W0 | ⬜ pending |
| 56-03-01 | 03 | 1 | BC-01,BC-02 | integration | `pytest apps/tasks/tests/test_broadcast_views.py::TestBroadcastCreate -x` | ❌ W0 | ⬜ pending |
| 56-03-02 | 03 | 1 | BC-06,BC-07 | integration | `pytest apps/tasks/tests/test_broadcast_views.py::TestBroadcastList -x` | ❌ W0 | ⬜ pending |
| 56-04-01 | 04 | 2 | BC-04 | integration | `pytest apps/dashboard/tests/test_services.py -x -k needs_attention` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/tasks/tests/test_broadcast_services.py` — stubs for BC-03, BC-09, BC-10
- [ ] `apps/tasks/tests/test_broadcast_views.py` — stubs for BC-01, BC-02, BC-05, BC-06, BC-07
- [ ] `apps/tasks/tests/test_broadcast_serializers.py` — stubs for BC-05
- [ ] `apps/tasks/tests/factories.py` — add BroadcastTaskFactory

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Megaphone badge visible on broadcast tasks in task list | UI-01 | Visual/CSS rendering | Open Tasks page as missionary, verify broadcast tasks show megaphone icon |
| "Assigned by [Name]" subtitle appears | UI-02 | Visual rendering | Check task list row for broadcast task shows sender name |
| Broadcast creation dialog with target selector | UI-03 | Interactive form | As admin, click "Broadcast Task", verify target options and form fields |
| Confirmation dialog shows recipient count | UI-04 | Interactive dialog | Submit broadcast form, verify "This will create a task for X users" appears |
| Admin tracking page at /admin/broadcasts | UI-05 | Page layout/navigation | As admin, navigate to Admin > Broadcasts, verify list with progress bars |
| Supervisor tracking section on Team page | UI-06 | Page layout | As supervisor, open Team page, verify "Broadcast Tasks" section visible |
| Broadcast detail DataTable with per-user status | UI-07 | Interactive table | Click a broadcast, verify sortable/filterable user completion table |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
