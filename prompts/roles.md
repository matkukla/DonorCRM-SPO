You are a senior full-stack engineer. Implement role-based access + supervisor/coach assignment management for our Donor CRM.

IMPORTANT CONSTRAINTS
- Roles: ADMIN, SUPERVISOR, COACH, MISSIONARY
- Rename “staff” to “missionary” in UI + data model naming (where applicable).
- One missionary can have at most ONE supervisor (required rule).
- One missionary can have at most ONE coach (also required rule).
- Supervisors and coaches can VIEW everything for missionaries assigned to them, but can EDIT NOTHING.
- Admin can view/edit everything.
- Missionaries can view/edit only their own data (existing behavior; preserve).
- Add a dedicated Admin screen for managing assignments (under Admin tab).

DELIVERABLES
1) Provide a plan (steps + files touched + migrations)
2) Implement schema + backend endpoints + frontend pages/components
3) Add strict authorization middleware
4) Add tests / verification checklist
Do not do large refactors; integrate smoothly with existing UI patterns.

--------------------------------------------
PART 1 — DATA MODEL
--------------------------------------------

A) Update User model to support:
- role enum: ADMIN | SUPERVISOR | COACH | MISSIONARY
- supervisorId (nullable) -> points to a User with role SUPERVISOR
- coachId (nullable) -> points to a User with role COACH

Use explicit self-relations, and enforce:
- supervisorId can only reference a SUPERVISOR
- coachId can only reference a COACH
- one-to-many: one supervisor has many missionaries; same for coach

If using Prisma, implement something like:

model User {
  id        String   @id @default(cuid())
  role      UserRole @default(MISSIONARY)

  // Missionary -> Supervisor assignment
  supervisorId String?
  supervisor   User? @relation("SupervisorAssignments", fields: [supervisorId], references: [id])
  supervisees  User[] @relation("SupervisorAssignments")

  // Missionary -> Coach assignment
  coachId   String?
  coach     User? @relation("CoachAssignments", fields: [coachId], references: [id])
  coachees  User[] @relation("CoachAssignments")

  // ...
  @@index([role])
  @@index([supervisorId])
  @@index([coachId])
}

enum UserRole {
  ADMIN
  SUPERVISOR
  COACH
  MISSIONARY
}

Migration rules:
- Existing “STAFF” users should become MISSIONARY
- Existing admin retains ADMIN
- supervisorId/coachId default null for all existing users

B) IMPORTANT: Add a helper query to fetch “allowedMissionaryIds”:
- Admin: all users with role MISSIONARY
- Supervisor: all users where supervisorId = currentUser.id
- Coach: all users where coachId = currentUser.id
- Missionary: only self

--------------------------------------------
PART 2 — AUTHORIZATION (STRICT)
--------------------------------------------

Implement an authorization utility used by ALL relevant endpoints:

function canViewUser(viewer, targetUserId) {
  if (viewer.role === 'ADMIN') return true;
  if (viewer.id === targetUserId) return true;

  if (viewer.role === 'SUPERVISOR') return targetUser.supervisorId === viewer.id;
  if (viewer.role === 'COACH') return targetUser.coachId === viewer.id;

  return false;
}

function mustBeAdmin(req, res, next) { ... }
function mustBeAdminOrSupervisorOrCoach(req, res, next) { ... }

Then enforce:
- Supervisors/coaches MUST NOT be able to POST/PATCH/DELETE data for assigned missionaries
- They can only GET/READ for assigned missionaries
- Admin can do all
- Missionaries can do CRUD only for their own records

Implement this with route-level guards:
- For any mutation route, reject roles SUPERVISOR/COACH unless they are modifying only non-sensitive “coach notes” (we are NOT adding notes now, so block all mutations).
- For read routes, apply “allowedMissionaryIds” filter at query layer.

--------------------------------------------
PART 3 — BACKEND ENDPOINTS
--------------------------------------------

A) Admin: Assignments management API

GET /api/admin/assignments
- Returns list of missionaries with:
  { missionaryId, missionaryName, missionaryEmail, supervisorId, supervisorName, coachId, coachName }
- Include also lists of supervisors and coaches for dropdowns:
  supervisors: [{id, name, email}]
  coaches: [{id, name, email}]

PATCH /api/admin/assignments
Body:
{
  assignments: [
    { missionaryId, supervisorId: string | null, coachId: string | null }
  ]
}
Rules:
- Only ADMIN can call
- Validate missionaryId is role MISSIONARY
- Validate supervisorId (if not null) is role SUPERVISOR
- Validate coachId (if not null) is role COACH
- Enforce one-to-one for missionary: just set supervisorId/coachId fields (no join table needed)
- Return summary: { updatedCount, errors: [{missionaryId, error}] }

B) Read filtering for supervisor/coach views:
- Wherever you have endpoints like:
  GET /api/journals
  GET /api/journals/:id
  GET /api/contacts
  GET /api/contacts/:id
  GET /api/admin/journals/... (if exists)
Ensure:
- Admin: unrestricted
- Supervisor/Coach: query is restricted to allowedMissionaryIds
  Example: contacts where ownerUserId IN allowedMissionaryIds
  journals where ownerUserId IN allowedMissionaryIds
- Missionary: ownerUserId = self

Also ensure any GET /api/users or lists don’t leak data.

--------------------------------------------
PART 4 — FRONTEND
--------------------------------------------

A) Rename “Staff” to “Missionary” in UI:
- Admin Create User form: role label should show Missionary
- Any nav labels: Staff -> Missionaries
- Any filters and copy updates accordingly

B) Add Admin screen: “Assignments”
Location:
Admin tab -> dropdown/side menu -> “Assignments”

Route: /admin/assignments

UI requirements:
- Table listing missionaries (search + pagination)
Columns:
  Missionary Name | Email | Supervisor (dropdown) | Coach (dropdown) | Status (saved/dirty) | Actions
- Dropdown options populated from API (supervisors/coaches).
- Allow setting supervisor/coach to “Unassigned”.
- Bulk actions:
  - Select multiple missionaries and set supervisor or coach in bulk
- Save button:
  - Only sends changed rows (diff-based)
  - Shows toast on success and highlights failures per row
- Must match current UI style (Tailwind, existing admin layout components)

C) Supervisor/Coach “view-only mode”
Where they can see assigned missionaries:
- Add a “My Team” page (or reuse existing Users list if present) for SUPERVISOR/COACH only:
  Route: /team
  Shows list of assigned missionaries.
  Clicking missionary opens a read-only view into their:
    - Journals list
    - Journal details
    - Contacts list
Use existing pages but pass a “viewAsUserId” param OR implement “impersonation-lite” in frontend:
  - URL includes ?userId=<missionaryId>
  - Backend enforces view permission; frontend disables edit controls when viewer role is SUPERVISOR/COACH
Disable/hide:
  - all “Add”, “Edit”, “Delete”, “Quick Log”, “Save” buttons
Show a banner:
  “Viewing as Supervisor/Coach — Read-only”

IMPORTANT:
Even if frontend hides buttons, backend must block mutations.

--------------------------------------------
PART 5 — TESTING / VERIFICATION
--------------------------------------------

Add tests (or at least a manual verification checklist) covering:

- Admin:
  - Can assign/unassign supervisors/coaches
  - Can see all journals/contacts for any missionary
  - Can still edit anything

- Supervisor:
  - Can view only missionaries assigned to them
  - Can view those missionaries’ journals/contacts/details
  - Cannot create/edit/delete anything (journals, contacts, events, decisions, next steps)
  - Gets 403 on mutation endpoints

- Coach:
  - Same as supervisor but via coachId assignment

- Missionary:
  - Can only view/edit their own data
  - Cannot access /admin/* routes (403)

Edge cases:
- Missionary has no supervisor/coach: should not appear for supervisors/coaches
- Assignment changes should take effect immediately (invalidate queries on save)
- Prevent assigning a non-supervisor as supervisor or non-coach as coach (backend validation)

--------------------------------------------
IMPLEMENTATION NOTES
--------------------------------------------

- Prefer the simplest approach: store supervisorId/coachId directly on missionary User row.
- Avoid refactors; integrate with existing routes/services/hooks.
- Add indexes for supervisorId/coachId for performance at 200+ users.
- Include clear error messages for failed assignment updates.

Start by producing a step-by-step plan, then implement.
