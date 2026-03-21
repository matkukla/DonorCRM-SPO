---
phase: 55
slug: add-scheduled-pipeline-stage-to-journal-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + Django TestCase (backend); no frontend tests |
| **Config file** | `pytest.ini` at project root |
| **Quick run command** | `python manage.py test apps.journals --verbosity=1` |
| **Full suite command** | `python manage.py test --verbosity=1` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python manage.py test apps.journals --verbosity=1`
- **After every plan wave:** Run `python manage.py test --verbosity=1`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 55-01-01 | 01 | 1 | D-02 | unit | `python manage.py test apps.journals.tests -k scheduled` | ❌ W0 | ⬜ pending |
| 55-01-02 | 01 | 1 | D-03 | unit | `python manage.py test apps.journals.tests -k scheduled_event` | ❌ W0 | ⬜ pending |
| 55-01-03 | 01 | 1 | D-13 | unit | `python manage.py test apps.journals.tests -k metadata` | ❌ W0 | ⬜ pending |
| 55-01-04 | 01 | 1 | D-15 | unit | `python manage.py test apps.journals.tests -k validation` | ❌ W0 | ⬜ pending |
| 55-01-05 | 01 | 1 | D-17 | unit | `python manage.py test apps.journals.tests -k goal_exclusion` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/journals/tests/test_scheduled_stage.py` — covers D-02, D-03, D-13, D-15
- [ ] Assertion in goal service tests verifying `meeting_scheduled` exclusion (D-17)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Calendar icon displays correctly (filled/faded) | D-04, D-05 | Visual rendering | Open journal grid, verify empty scheduled cell shows faded CalendarDays icon, checked cell shows filled CalendarDays icon with date label |
| Date picker opens on empty cell click | D-10 | UI interaction | Click empty scheduled cell, verify LogEventDialog opens with date picker |
| Date label shows "Mar 25" format | D-04 | Visual format | Create scheduled event with date, verify cell shows short month + day |
| Analytics charts include scheduled stage | D-18 | Visual chart rendering | Open report page, verify scheduled appears in pipeline breakdown and stage activity charts |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
