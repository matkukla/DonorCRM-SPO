---
phase: quick-13
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/users/tests/test_models.py
  - apps/users/tests/test_views.py
  - frontend/src/pages/admin/AdminAssignments.tsx
autonomous: true
requirements: []

must_haves:
  truths:
    - "pytest apps/users/tests/test_models.py::TestUserModel::test_role_properties passes"
    - "pytest apps/users/tests/test_views.py::TestUserListView::test_admin_can_create_user passes"
    - "Assignments page shows a sticky/bottom Save button so user never loses access to it when the list is long"
    - "Navigating away from Assignments with unsaved changes shows a browser-level confirmation prompt"
  artifacts:
    - path: "apps/users/tests/test_models.py"
      provides: "Fixed test_role_properties — no is_staff_role reference"
    - path: "apps/users/tests/test_views.py"
      provides: "Fixed test_admin_can_create_user — no 'staff' role string"
    - path: "frontend/src/pages/admin/AdminAssignments.tsx"
      provides: "Sticky save bar + unsaved-changes navigation guard"
  key_links:
    - from: "test_models.py::test_role_properties"
      to: "UserRole enum"
      via: "Role values that exist in Phase 43 (missionary, admin, finance, read_only, supervisor, coach)"
    - from: "AdminAssignments.tsx dirty state"
      to: "useBeforeUnload / React Router blocker"
      via: "dirty.size > 0 check"
---

<objective>
Fix two pre-existing failing tests left over from Phase 43's role rename, and improve the Assignments page UX with a sticky Save button and an unsaved-changes navigation guard.

Purpose: The broken tests produce noise in every test run. The UX improvements reduce the risk of accidentally losing work while managing assignments for a long missionary list.
Output: Two test files corrected, AdminAssignments.tsx updated with sticky save bar and navigation guard.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/46-multiple-supervisors-per-missionary/46-06-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix two pre-existing failing tests from Phase 43 role rename</name>
  <files>apps/users/tests/test_models.py, apps/users/tests/test_views.py</files>
  <action>
Fix two tests that reference removed/renamed identifiers from Phase 43's role redesign:

**apps/users/tests/test_models.py — test_role_properties (line 42)**
The test uses `is_staff_role` which was removed in Phase 43. The property no longer exists on User.
- The `staff` user in the test is created with `role=UserRole.MISSIONARY` — there is no "staff" concept post-Phase 43.
- Replace the `is_staff_role` assertions with properties that actually exist: `is_missionary` (True for UserRole.MISSIONARY), `is_supervisor`, `is_coach`.
- Remove the variable name `staff` — rename to `missionary` to match intent.
- New test shape:
  ```python
  missionary = UserFactory(role=UserRole.MISSIONARY)
  supervisor = UserFactory(role=UserRole.SUPERVISOR)
  coach = UserFactory(role=UserRole.COACH)
  admin = UserFactory(role=UserRole.ADMIN)
  finance = UserFactory(role=UserRole.FINANCE)
  readonly = UserFactory(role=UserRole.READ_ONLY)

  assert missionary.is_missionary is True
  assert missionary.is_admin is False
  assert supervisor.is_supervisor is True
  assert coach.is_coach is True
  assert admin.is_admin is True
  assert finance.is_finance is True
  assert readonly.is_read_only is True
  ```
- Verify imports: UserRole already imported.

**apps/users/tests/test_views.py — test_admin_can_create_user (line 63)**
The test posts `'role': 'staff'` which is not a valid UserRole value in Phase 43+. Valid roles are: missionary, supervisor, coach, finance, admin, read_only.
- Change `'role': 'staff'` to `'role': 'read_only'` (or any valid role; read_only is the safest as it has no write access to other data).
- No other changes needed to this test.
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM && python -m pytest apps/users/tests/test_models.py::TestUserModel::test_role_properties apps/users/tests/test_views.py::TestUserListView::test_admin_can_create_user -v</automated>
  </verify>
  <done>Both tests pass. No other tests in test_models.py or test_views.py are broken by the change.</done>
</task>

<task type="auto">
  <name>Task 2: Add sticky Save bar and unsaved-changes guard to AdminAssignments</name>
  <files>frontend/src/pages/admin/AdminAssignments.tsx</files>
  <action>
Two UX improvements to AdminAssignments.tsx:

**1. Sticky Save bar**
When a missionary list is long, the toolbar Save button scrolls out of view. Add a sticky bottom bar that appears only when `dirty.size > 0` (missionary view). This mirrors the pattern common in admin forms.

Add after the existing Supervisor View Table block (before the closing `</div></Container></Section>`) a sticky bar:
```tsx
{viewMode === "missionary" && dirty.size > 0 && (
  <div className="sticky bottom-0 z-10 border-t border-border bg-background/95 backdrop-blur-sm py-3 -mx-4 px-4 flex items-center justify-between">
    <span className="text-sm text-muted-foreground">
      {dirty.size} unsaved change{dirty.size !== 1 ? "s" : ""}
    </span>
    <Button
      disabled={updateMutation.isPending}
      onClick={handleSave}
    >
      {updateMutation.isPending ? "Saving..." : "Save Changes"}
    </Button>
  </div>
)}
```

The existing toolbar Save button stays in place (no removal) — the sticky bar is additive.

**2. Unsaved-changes navigation guard**
Use React Router's `useBlocker` hook (available in react-router-dom v6.7+) to block navigation when `dirty.size > 0`.

Add to imports:
```tsx
import { NavLink, useBlocker } from "react-router-dom"
```

Add inside the component (after the state declarations):
```tsx
const blocker = useBlocker(
  ({ currentLocation, nextLocation }) =>
    dirty.size > 0 && currentLocation.pathname !== nextLocation.pathname
)
```

Add a confirmation dialog just before the closing `</Section>` tag (but inside the JSX):
```tsx
{blocker.state === "blocked" && (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
    <div className="bg-background rounded-lg border border-border p-6 shadow-lg max-w-sm w-full mx-4">
      <h2 className="text-lg font-semibold mb-2">Unsaved Changes</h2>
      <p className="text-sm text-muted-foreground mb-4">
        You have {dirty.size} unsaved assignment change{dirty.size !== 1 ? "s" : ""}. Leave anyway?
      </p>
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={() => blocker.reset()}>
          Stay
        </Button>
        <Button variant="destructive" size="sm" onClick={() => blocker.proceed()}>
          Leave
        </Button>
      </div>
    </div>
  </div>
)}
```

Place this block as the last child inside the outer `<Section>` wrapper, after `</Container>`.

Also add a native `beforeunload` guard for browser tab close / refresh (covers cases useBlocker doesn't):
```tsx
useEffect(() => {
  const handler = (e: BeforeUnloadEvent) => {
    if (dirty.size > 0) {
      e.preventDefault()
    }
  }
  window.addEventListener("beforeunload", handler)
  return () => window.removeEventListener("beforeunload", handler)
}, [dirty.size])
```

Add `useEffect` to imports if not already present (it already is — check existing imports). Ensure `useBlocker` is added to the react-router-dom import line.
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>
- Zero TypeScript errors.
- Sticky bar code is present: `sticky bottom-0` in the JSX.
- useBlocker import present.
- Blocker dialog JSX present after the closing Container tag inside Section.
- beforeunload useEffect present.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
  Task 1: Fixed test_role_properties (is_staff_role removed) and test_admin_can_create_user ('staff' → 'read_only'). Both tests now pass.
  Task 2: AdminAssignments now shows a sticky Save bar at the bottom of the page when there are unsaved changes, and blocks navigation away from the page with a confirmation dialog.
  </what-built>
  <how-to-verify>
  1. Run: `cd /home/matkukla/projects/DonorCRM && python -m pytest apps/users/tests/test_models.py apps/users/tests/test_views.py -v` — should see no failures for test_role_properties or test_admin_can_create_user.

  2. In the running frontend app, go to Admin > Assignments.
  3. Make any change to a missionary's supervisor or coach.
  4. Scroll down — the sticky bar "X unsaved changes" + "Save Changes" button should appear at the bottom of the viewport.
  5. Click a sidebar nav link (e.g., Contacts) while changes are unsaved — a "Unsaved Changes" dialog should appear with "Stay" / "Leave" options.
  6. Click "Stay" — you stay on Assignments. Click "Leave" — you navigate away.
  </how-to-verify>
  <resume-signal>Type "approved" or describe any issues</resume-signal>
</task>

</tasks>

<verification>
- `python -m pytest apps/users/tests/test_models.py::TestUserModel::test_role_properties apps/users/tests/test_views.py::TestUserListView::test_admin_can_create_user -v` — both PASS
- `cd frontend && npx tsc --noEmit` — zero errors
- Sticky bar visible at bottom when assignments are dirty
- Navigation guard fires when navigating away with unsaved changes
</verification>

<success_criteria>
Two previously-failing tests pass. The AdminAssignments page no longer loses the Save button when scrolling, and prompts before discarding unsaved work.
</success_criteria>

<output>
After completion, create `.planning/quick/13-check-if-there-is-a-way-to-make-phase-46/13-SUMMARY.md`
</output>
