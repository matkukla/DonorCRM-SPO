---
phase: 01
slug: duplicate-contact-checking-merging-github-issue-37
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) / vitest (frontend) |
| **Config file** | config/settings/test.py (backend), frontend/vitest.config.ts (frontend) |
| **Quick run command** | `python manage.py test apps.contacts.tests --settings=config.settings.test` |
| **Full suite command** | `python manage.py test --settings=config.settings.test && cd frontend && npx vitest run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python manage.py test apps.contacts.tests --settings=config.settings.test`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DUP-DETECT | unit | `python manage.py test apps.contacts.tests.test_duplicate_detection` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | DUP-MERGE | unit | `python manage.py test apps.contacts.tests.test_merge` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | DUP-UI | integration | `cd frontend && npx vitest run src/pages/contacts/__tests__/` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 2 | DUP-CREATE | integration | `python manage.py test apps.contacts.tests.test_duplicate_check_on_create` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/contacts/tests/test_duplicate_detection.py` — stubs for duplicate detection service
- [ ] `apps/contacts/tests/test_merge.py` — stubs for merge service and FK reassignment
- [ ] `apps/contacts/tests/test_duplicate_check_on_create.py` — stubs for creation-time check
- [ ] `frontend/src/pages/contacts/__tests__/` — directory for duplicate UI tests

*Existing test infrastructure covers framework installation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Side-by-side comparison layout renders correctly | DUP-UI | Visual layout verification | Navigate to /contacts/duplicates, click Review on a pair, verify side-by-side card layout |
| Confidence badge colors match UI-SPEC | DUP-UI | CSS visual check | Compare badge colors to UI-SPEC color definitions |
| Creation-time warning modal appears | DUP-CREATE | Full browser interaction flow | Create contact with same name as existing, verify modal with matches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
