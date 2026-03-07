---
phase: quick-12
plan: 01
subsystem: imports
tags: [bug-fix, owner-reassignment, re-import, tdd]
dependency_graph:
  requires: []
  provides: [correct-owner-after-re-gift-import]
  affects: [apps/imports/re_services.py, apps/imports/tests/test_re_services.py]
tech_stack:
  added: []
  patterns: [Solicitor.objects.filter(user=contact.owner).exists() for missionary check]
key_files:
  modified:
    - apps/imports/re_services.py
    - apps/imports/tests/test_re_services.py
decisions:
  - Guard replaced from owner_id equality check to Solicitor FK existence check — more semantically correct and cross-admin safe
metrics:
  duration: ~2 min
  completed: 2026-03-07
---

# Phase quick-12 Plan 01: Fix Contact Owner Reassignment in import_re_gifts Summary

**One-liner:** Replaced owner equality guard with Solicitor FK existence check so RE gift imports always reassign contacts to their missionary regardless of which admin ran the constituent import.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Add failing TDD tests for owner reassignment | 502cccb | apps/imports/tests/test_re_services.py |
| GREEN | Fix owner reassignment guard in re_services.py | 58d4b5b | apps/imports/re_services.py, apps/imports/tests/test_re_services.py |

## What Was Done

### Root Cause

In `apps/imports/re_services.py`, `import_re_gifts` had this guard before reassigning a contact's owner to the matched solicitor's user:

```python
if contact.owner_id == owner.pk:
```

The `owner` parameter is the user who ran the gifts import CLI command (`--owner adminB`). On the Render production database, constituents were imported with `--owner adminA` so `contact.owner_id == adminA.pk`. When gifts were imported with `--owner adminB`, `adminA.pk != adminB.pk`, so the guard failed silently and contacts remained owned by adminA instead of being reassigned to the missionary.

### Fix

Replaced the guard with a semantic check:

```python
contact_owner_is_missionary = Solicitor.objects.filter(user=contact.owner).exists()
if not contact_owner_is_missionary:
```

This correctly skips reassignment only when the contact is already owned by a missionary (someone with a `Solicitor` record), which is the intended behavior. If the current owner is any non-missionary user (admin or otherwise), reassignment proceeds regardless of which admin ran the import.

Also renamed the loop variable from `row` to `credit_row` to avoid shadowing the outer `row` variable.

## Deviations from Plan

### Auto-fixed Issues

**[Rule 1 - Bug] Displaced test method from TestImportRERecurringGiftsPrayers into new class**
- **Found during:** RED phase commit
- **Issue:** The `test_prayer_dedup_across_recurring_gifts` method was the final method of the original `TestImportRERecurringGiftsPrayers` class but got accidentally captured inside the new `TestImportREGiftsOwnerReassignment` class when my edit insertion point matched just before the end of the file. The method used fixtures (`admin_user`, `staff_user`, `setup_contact`) that only exist in `TestImportRERecurringGiftsPrayers`, causing collection errors.
- **Fix:** Moved `test_prayer_dedup_across_recurring_gifts` back into `TestImportRERecurringGiftsPrayers` where it belongs
- **Files modified:** apps/imports/tests/test_re_services.py
- **Commit:** 58d4b5b

## Verification

```
31 passed, 57 warnings in 0.89s
```

All 31 existing + 3 new tests pass.

## Self-Check: PASSED

- apps/imports/re_services.py: modified — guard replaced
- apps/imports/tests/test_re_services.py: modified — 3 new test methods added to TestImportREGiftsOwnerReassignment
- Commit 502cccb: RED phase tests
- Commit 58d4b5b: GREEN phase fix + test file correction
