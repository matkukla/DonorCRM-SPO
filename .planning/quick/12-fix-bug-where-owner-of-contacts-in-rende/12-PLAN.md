---
phase: quick-12
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/imports/re_services.py
  - apps/imports/tests/test_re_services.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "After import_re_gifts runs, contacts are owned by the matching missionary (solicitor's user), not the admin who ran the import"
    - "The owner reassignment fires regardless of who imported the constituents"
    - "Contacts already owned by a missionary are not re-reassigned to a different missionary"
  artifacts:
    - path: "apps/imports/re_services.py"
      provides: "Fixed owner reassignment logic in import_re_gifts"
      contains: "contact.owner = sol.user"
    - path: "apps/imports/tests/test_re_services.py"
      provides: "Regression test covering the reassignment scenario"
      exports: ["test_import_gifts_reassigns_contact_owner_to_solicitor"]
  key_links:
    - from: "import_re_gifts"
      to: "contact.owner"
      via: "solicitor_lookup -> sol.user"
      pattern: "contact\\.owner = sol\\.user"
---

<objective>
Fix the owner reassignment guard in `import_re_gifts` that prevents contacts from being correctly assigned to their missionary when constituents and gifts were imported by different admin users.

Purpose: In the Render production database, RE constituent files were imported with `--owner adminA`, but RE gift files were imported with `--owner adminB`. The guard `if contact.owner_id == owner.pk` fails in this cross-admin scenario, so contacts remain owned by the wrong user instead of being reassigned to the missionary whose solicitor credit appears in the gifts CSV.

Output: Contacts are reliably reassigned to the first matched solicitor's user (the missionary) after running `import_re_gifts`, regardless of which admin ran the constituent import.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Key facts about the bug:
- `import_re_gifts` in `apps/imports/re_services.py` has a contact owner reassignment block at ~line 1364
- The guard `if contact.owner_id == owner.pk:` only fires when the contact's current owner matches the `--owner` flag passed to the gifts import command
- In production, constituents were imported with `--owner adminA` and gifts with `--owner adminB` — so `contact.owner_id != owner.pk` and reassignment never fires
- Contacts end up owned by `adminA` instead of the missionary
- The `owner` parameter in `import_re_gifts` is passed as the same user for both `uploaded_by` and `owner` in the management command (line 61-62 of import_re_gifts.py)
- The reassignment iterates `for row in rows` where `rows` is the gift credit rows for that gift group (from `for gift_id, rows in groups.items()`) — this is correct
- `import_re_recurring_gifts` does NOT have this reassignment logic — no change needed there
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix owner reassignment guard in import_re_gifts</name>
  <files>apps/imports/re_services.py, apps/imports/tests/test_re_services.py</files>
  <behavior>
    - Test: contact imported with owner=admin1, gifts imported with owner=admin2, solicitor linked to missionary user — contact.owner should be reassigned to missionary
    - Test: contact already owned by a missionary (has Solicitor record) — should NOT be reassigned
    - Test: no solicitor match in gift rows — contact owner unchanged
  </behavior>
  <action>
In `apps/imports/re_services.py`, find the owner reassignment block (~line 1364-1375):

```python
# Reassign contact owner to first resolved solicitor's user
# (only if contact is still owned by the importer)
if contact.owner_id == owner.pk:
    for row in rows:
        sol_name = row.get('solicitor_name', '')
        if not sol_name:
            continue
        sol = solicitor_lookup.get(normalize_solicitor_name(sol_name))
        if sol and sol.user_id:
            contact.owner = sol.user
            contact.save(update_fields=['owner'])
            break
```

Replace the guard `if contact.owner_id == owner.pk:` with a guard that checks whether the contact's current owner already has a Solicitor record (meaning they're already a missionary who owns this contact intentionally). The new logic:

```python
# Reassign contact owner to first resolved solicitor's user.
# Only skip if the contact is already owned by a linked missionary
# (i.e. the owner has a Solicitor record). This handles the case where
# constituents and gifts are imported by different admin users.
contact_owner_is_missionary = Solicitor.objects.filter(user=contact.owner).exists()
if not contact_owner_is_missionary:
    for credit_row in rows:
        sol_name = credit_row.get('solicitor_name', '')
        if not sol_name:
            continue
        sol = solicitor_lookup.get(normalize_solicitor_name(sol_name))
        if sol and sol.user_id:
            contact.owner = sol.user
            contact.save(update_fields=['owner'])
            break
```

Note: rename the loop variable from `row` to `credit_row` to avoid shadowing the outer `row` variable (defensive clarity).

In `apps/imports/tests/test_re_services.py`, add a new test class `TestImportREGiftsOwnerReassignment` with:
1. `test_reassigns_owner_when_imported_by_different_admin`: create contact with owner=admin1, create solicitor linked to a missionary user, run import_re_gifts with uploaded_by=admin1, owner=admin2 — assert contact.owner == missionary
2. `test_does_not_reassign_if_already_owned_by_missionary`: create a Solicitor for staff_user (missionary), create contact with owner=staff_user, run gifts import — assert contact.owner still == staff_user
3. `test_no_reassign_if_no_solicitor_match`: run gifts import with no solicitor in CSV — contact.owner unchanged
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM && python -m pytest apps/imports/tests/test_re_services.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>
    - All existing re_services tests pass
    - New owner reassignment tests pass
    - Contact owner is reassigned to missionary when contact was imported by a different admin
    - Contact owner is preserved when already owned by a missionary (has Solicitor record)
  </done>
</task>

</tasks>

<verification>
Run the full imports test suite to confirm no regressions:
`cd /home/matkukla/projects/DonorCRM && python -m pytest apps/imports/tests/ -x -q`
</verification>

<success_criteria>
- `import_re_gifts` reassigns contact owner to the first matched solicitor's user regardless of which admin ran `import_re_constituents`
- Contacts already owned by a missionary (user with Solicitor record) are not re-reassigned
- All imports tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/12-fix-bug-where-owner-of-contacts-in-rende/12-SUMMARY.md`
</output>
