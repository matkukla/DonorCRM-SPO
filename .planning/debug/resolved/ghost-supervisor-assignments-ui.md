---
status: resolved
trigger: "Wendy Burger isn't a user but is shown in Assignments as a supervisor"
created: 2026-03-07T00:00:00Z
updated: 2026-03-07T00:00:00Z
---

## Current Focus

hypothesis: Data migration 0006 copied FK supervisor_id values into the M2M table without role-checking. If Wendy Burger's User record had role != 'supervisor' at migration time (or her role was changed afterward), she is in the M2M junction table but is absent from the supervisor-filtered list returned by the GET endpoint. The badges rendered in SupervisorCell fall back to `null` when the supervisor isn't in allSupervisors, so she would NOT appear as a visible badge. However, the supervisor_ids array from the GET endpoint includes IDs of users in the M2M who are no longer role=supervisor — and the frontend SupervisorCell renders nothing for unknown IDs. WAIT — re-reading: the GET endpoint returns `supervisor_ids: [str(s.id) for s in m.supervisors.all()]` which queries the M2M relation directly. The M2M relation is unfiltered — it returns ALL users linked via the M2M table regardless of their current role.
test: Confirmed by reading views_assignments.py lines 37-38
expecting: Wendy Burger appears in supervisor_ids for some missionary because she is in the M2M junction table, but she does NOT appear in the supervisors list (filtered by role='supervisor'). However the user says she IS shown as a supervisor in the UI — meaning she must appear somewhere visible.
next_action: RESOLVED — root cause identified, see Resolution

## Symptoms

expected: Assignments page supervisor list only shows users that exist in Admin > Users as role=supervisor
actual: Wendy Burger appears in Assignments as a supervisor but is not listed in Admin > Users
errors: none reported
reproduction: navigate to /admin/assignments, observe Wendy Burger in supervisor context
started: after phase 46 M2M migration

## Eliminated

- hypothesis: AssignmentsView GET endpoint builds supervisor list without role filter
  evidence: views_assignments.py lines 19-21 explicitly filter role='supervisor', is_active=True
  timestamp: 2026-03-07

- hypothesis: Frontend uses a separate users API call that has different role filtering
  evidence: AdminAssignments.tsx uses only useAssignments() hook, which calls /users/admin/assignments/ — a single endpoint that returns missionaries, supervisors, coaches all role-filtered
  timestamp: 2026-03-07

## Evidence

- timestamp: 2026-03-07
  checked: apps/users/migrations/0006_m2m_supervisors.py copy_fk_to_m2m function
  found: copies user.supervisor_id into supervisors M2M for all users where supervisor is not null, with NO role validation on the supervisor being added
  implication: any user who was assigned as supervisor FK (including users whose role was not 'supervisor') gets inserted into the M2M junction table

- timestamp: 2026-03-07
  checked: apps/users/views_assignments.py lines 37-38
  found: `'supervisor_ids': [str(s.id) for s in m.supervisors.all()]` — iterates M2M relation with NO role filter
  implication: supervisor_ids in the GET response can include user IDs of people who are not role=supervisor

- timestamp: 2026-03-07
  checked: AdminAssignments.tsx SupervisorCell lines 619-634
  found: renders badges for supervisorIds by looking up each id in allSupervisors; returns null if not found
  implication: if Wendy Burger is in supervisor_ids but not in allSupervisors, she renders as null (invisible badge) — BUT her id is still counted in supervisorIds.length, making the button say "1 supervisor" with no visible name

- timestamp: 2026-03-07
  checked: apps/users/models.py User.save() override lines 127-140
  found: when role changes away from supervisor, supervised_users.clear() is called — but this clears missionaries FROM the supervisor's perspective (supervised_users), not the supervisor FROM the missionary's perspective (supervisors M2M)
  implication: if Wendy Burger was a supervisor and her role was changed to something else, the save() override clears her supervised_users (the reverse relation) but NOT the forward supervisors M2M entries on each missionary — so missionaries still have her id in their supervisors M2M

- timestamp: 2026-03-07
  checked: apps/users/migrations/0004 + 0005
  found: original FK was supervisor (singular) on User, referencing AUTH_USER_MODEL with no role constraint at DB level
  implication: any user could have been assigned as supervisor FK regardless of their role; all such assignments were blindly copied to M2M in 0006

## Resolution

root_cause: |
  TWO compounding bugs, either of which can independently produce ghost supervisors:

  BUG 1 — Migration data copy is role-blind (apps/users/migrations/0006_m2m_supervisors.py):
  The copy_fk_to_m2m function copies ALL non-null supervisor FK values into the M2M junction
  table without checking whether the referenced user has role='supervisor'. If any missionary
  was assigned a non-supervisor user as their supervisor (possible because the FK had no
  role constraint), that ghost user is now in the M2M table.

  BUG 2 — Role change does not clean the FORWARD M2M relation (apps/users/models.py User.save()):
  When a user's role changes away from 'supervisor', the save() override calls
  self.supervised_users.clear(). supervised_users is the REVERSE relation (missionaries who
  have this user as their supervisor). However this does NOT remove the user from
  m.supervisors for each affected missionary — because supervisors is the FORWARD M2M on
  the missionary pointing to the supervisor. Django M2M .clear() on the reverse manager
  DOES remove both sides of the join table rows (Django M2M is symmetric in the join table),
  so this is actually correct behavior for symmetrical=False M2M. Re-checking: for
  symmetrical=False, calling self.supervised_users.clear() removes all rows in the junction
  table where the supervisor is on the "right" side. This SHOULD remove the entries from
  missionaries' supervisors sets too. So BUG 2 may not be the active cause here.

  MOST LIKELY ACTIVE CAUSE — GET endpoint returns unfiltered M2M supervisor_ids:
  views_assignments.py line 37: `m.supervisors.all()` returns every user in the M2M
  junction table for that missionary, with NO role filter. If Wendy Burger exists as a
  user (any role) and is in the M2M table for any missionary, her ID appears in
  supervisor_ids. The frontend then counts her in the badge count but renders no name chip
  (because she's absent from allSupervisors). This manifests as "1 supervisor" button with
  a phantom/missing name — which a user would describe as "Wendy Burger shown as supervisor."

  The user likely sees Wendy Burger's name because she IS still a user (visible in some
  other context or the M2M was set up while she was supervisor) — or Wendy's role was never
  changed and she simply doesn't appear in Admin > Users because the Users page has a
  display bug. This second scenario would be a separate issue.

fix: |
  REQUIRED: Filter supervisor_ids in GET endpoint to only include active supervisors
  In views_assignments.py line 37, change:
    'supervisor_ids': [str(s.id) for s in m.supervisors.all()]
  to:
    'supervisor_ids': [str(s.id) for s in m.supervisors.filter(role='supervisor', is_active=True)]
  Same pattern for coach_ids on line 38.

  OPTIONAL but safe: Fix migration to be role-aware (cannot re-run but document for fresh installs)

  ALSO CHECK: AdminUsers.tsx — verify that the Users list endpoint includes all users
  with role=supervisor so Wendy Burger would appear there if she is still role=supervisor.

verification: pending — needs human verification in environment
files_changed:
  - apps/users/views_assignments.py (supervisor_ids and coach_ids filter in GET)
