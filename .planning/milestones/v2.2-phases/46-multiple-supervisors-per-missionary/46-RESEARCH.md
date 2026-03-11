# Phase 46: Multiple Supervisors per Missionary - Research

**Researched:** 2026-03-07
**Domain:** Django M2M migration, data scoping, React multi-select UI
**Confidence:** HIGH (all findings verified from source code)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Both supervisor and coach relationships become many-to-many (not just supervisors)
- A single user can hold both supervisor and coach roles for the same missionary (allowed)
- No hard limit on supervisors/coaches per missionary — soft UI guidance only (warn if count >= 5), no enforcement
- When a user's role is changed away from supervisor or coach, their missionary assignments are automatically cleared (auto-unassign on role change)
- Replace the single-select dropdowns with multi-select dropdowns (chip/tag style) for both supervisor and coach columns in AdminAssignments
- Uses the same searchable multi-select pattern already present in the user edit form
- Bulk assignment is additive: bulk action adds selected supervisor(s)/coach(es) to missionaries' existing assignments without replacing them
- Assignments page gains a toggle to switch between two views: Missionary view (default) and Supervisor view (rows are supervisors, showing all missionaries assigned to each)
- Supervisor and coach user detail pages show a read-only list of missionaries currently assigned to them (Admin > Users > [supervisor/coach user])
- All assigned supervisors independently see a missionary's data — additive, no primary/secondary distinction
- Each supervisor's list page and dashboard selector shows their own assigned set
- Supervisors cannot see who else supervises a shared missionary
- Owner column on list pages unchanged
- Auto-migrate: existing FK assignments are copied into new M2M join tables during migration
- After data is copied to M2M, old FK columns (supervisor_id, coach_id) are dropped — clean break
- Join table design is Claude's discretion

### Claude's Discretion
- M2M join table structure (explicit through model with timestamps vs Django auto-generated)
- Backend queryset update for scoping (how to query M2M supervisors instead of ForeignKey)
- Soft limit UX implementation detail (warning threshold and display)
- API serializer structure for M2M supervisor/coach fields

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 46 converts two self-referencing ForeignKeys on the User model (`supervisor` and `coach`) to ManyToManyFields. This is a breaking schema change: `supervisor_id` and `coach_id` columns disappear entirely, replaced by M2M join tables. The impact fans out across one model, four serializers/views in the users app, one centralized `get_visible_user_ids()` function (used by every scoped view), and the AdminAssignments frontend page.

The existing code is well-structured for this change. All data-scoping flows through the single `get_visible_user_ids()` function in `apps/core/permissions.py`. The reverse relations `supervised_users` and `coached_users` are already used as queryset filters — after M2M conversion, the same relation names work identically (Django M2M and FK reverse managers share the same `.filter()` / `.values_list()` API). The only behavioral difference is that a missionary can now be in the `supervised_users` queryset of multiple supervisors simultaneously.

The frontend already has the full Popover + Command multi-select chip pattern in AdminUsers.tsx (for supervisor/coach user edit). AdminAssignments.tsx uses single-select Radix Select dropdowns that need to be replaced with the same Popover+Command pattern. The local state Map needs to change from `{ supervisor_id: string|null, coach_id: string|null }` to `{ supervisor_ids: string[], coach_ids: string[] }`.

**Primary recommendation:** Migrate in four waves: (1) migration file, (2) backend model+serializer+views, (3) frontend API types + AdminAssignments UI, (4) AdminUsers user detail read-only missionary list.

---

## Standard Stack

### Core (all already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django M2M | Django 4.2 | ManyToManyField on User | Built-in, no new dependency |
| django-factory-boy | current | Test factories | Already used in apps/users/tests/factories.py |
| pytest-django | current | Test runner | Already used |
| cmdk (shadcn command) | installed | Searchable multi-select | Already used in AdminUsers.tsx |

No new packages needed. The multi-select UI component (Popover + Command from shadcn/ui) is already installed and used.

---

## Architecture Patterns

### M2M Migration Strategy (Django)

**Pattern: RunPython data copy BEFORE AlterField/RemoveField**

This was established in migration 0005_roles_redesign.py (RunPython before AlterField to avoid constraint violations). The same pattern applies here.

Migration steps in order:
1. `AddField` — add `supervisors = ManyToManyField('self', ...)` and `coaches = ManyToManyField('self', ...)`
2. `RunPython` — copy existing FK data: for each user with `supervisor_id`, add to M2M; same for `coach_id`
3. `RemoveField` — remove old `supervisor` FK field
4. `RemoveField` — remove old `coach` FK field

```python
# Source: existing migration 0005_roles_redesign.py pattern + Django docs

def copy_fk_to_m2m(apps, schema_editor):
    User = apps.get_model('users', 'User')
    # supervisor
    for user in User.objects.filter(supervisor__isnull=False).select_related('supervisor'):
        user.supervisors.add(user.supervisor)
    # coach
    for user in User.objects.filter(coach__isnull=False).select_related('coach'):
        user.coaches.add(user.coach)


def reverse_m2m_to_fk(apps, schema_editor):
    # Not reversible in a meaningful way — reverse migration is no-op
    pass
```

**CRITICAL:** `RunPython` must run AFTER `AddField` (M2M table must exist) but BEFORE `RemoveField` (FK data must still be there).

### M2M Field Definition

Recommendation: Use Django auto-generated M2M (no explicit through model). The user specified "join table design is Claude's discretion." Auto-generated is simpler — no through model overhead since timestamps are not needed for this use case.

```python
# Source: apps/users/models.py analysis

# Replace:
supervisor = models.ForeignKey('self', null=True, blank=True,
    on_delete=models.SET_NULL, related_name='supervised_users')
coach = models.ForeignKey('self', null=True, blank=True,
    on_delete=models.SET_NULL, related_name='coached_users')

# With:
supervisors = ManyToManyField('self', symmetrical=False, blank=True,
    related_name='supervised_users',
    help_text='Supervisors assigned to this missionary')
coaches = ManyToManyField('self', symmetrical=False, blank=True,
    related_name='coached_users',
    help_text='Coaches assigned to this missionary')
```

Key points:
- `symmetrical=False` required for self-referencing M2M (otherwise Django would make it bidirectional)
- Keep `related_name='supervised_users'` and `related_name='coached_users'` — preserves all existing reverse queryset code without changes
- Field names change from `supervisor`/`coach` (FK) to `supervisors`/`coaches` (M2M plural) — touches every place that assigns these fields

### Scoping: get_visible_user_ids() — Minimal Change

The centralized scoping function in `apps/core/permissions.py` already uses the reverse relations:
```python
# Current (FK reverse manager):
ids = set(user.supervised_users.filter(is_active=True).values_list('id', flat=True))

# After M2M:  IDENTICAL — M2M reverse manager has same API
ids = set(user.supervised_users.filter(is_active=True).values_list('id', flat=True))
```

No change needed to `get_visible_user_ids()` — the reverse relation `supervised_users` and `coached_users` work identically after M2M conversion.

### can_view_contact() — Minimal Change

Same situation. `self.supervised_users.filter(...)` and `self.coached_users.filter(...)` in `User.can_view_contact()` work identically after M2M.

### AssignmentsView Backend

Current GET returns scalars:
```python
'supervisor_id': str(m.supervisor_id) if m.supervisor_id else None,
'coach_id': str(m.coach_id) if m.coach_id else None,
```

New GET must return arrays. Use `prefetch_related` not `select_related`:
```python
missionaries = User.objects.filter(
    role='missionary', is_active=True
).prefetch_related('supervisors', 'coaches').order_by('last_name', 'first_name')

# In response:
'supervisor_ids': [str(s.id) for s in m.supervisors.all()],
'coach_ids': [str(c.id) for c in m.coaches.all()],
```

Current PATCH receives `supervisor_id`/`coach_id` scalars, sets `missionary.supervisor = supervisor`, saves with `update_fields=['supervisor', 'coach']`. New PATCH must receive arrays and use M2M set/add operations:

```python
# Additive bulk assignment (per locked decision):
# For individual row edits: set() replaces all (full replace)
# For bulk apply: add() appends without removing existing

# Individual row change:
missionary.supervisors.set(supervisor_objs)
missionary.coaches.set(coach_objs)

# Bulk additive:
missionary.supervisors.add(*supervisor_objs)
missionary.coaches.add(*coach_objs)
```

The PATCH payload needs to differentiate these two modes. Recommendation: add an `additive: bool` flag to each item, or use a separate bulk endpoint. Simplest: the PATCH item carries `supervisor_ids: string[] | null` and `additive: bool`. If `additive=true`, use `.add()`; if `additive=false`, use `.set()`.

### UserAdminUpdateSerializer — Auto-Unassign on Role Change

Current update logic clears by setting FK to None on downstream users:
```python
instance.supervised_users.update(supervisor=None)
User.objects.filter(id__in=supervised_ids, is_active=True).update(supervisor=instance)
```

After M2M, `supervised_users` is a reverse M2M manager — `.update()` does not work on M2M relations. Must use the M2M manager:
```python
# Clear all current assignments from this supervisor:
# Forward approach — remove self from all missionaries' supervisors:
User.objects.filter(supervisors=instance).exclude(
    id__in=User.objects.filter(id__in=supervised_ids)
)
# Simplest: clear the forward M2M on instance
instance.supervised_users.clear()  # reverse M2M — removes self from all
# Then add new:
new_supervised = User.objects.filter(id__in=supervised_ids, is_active=True)
for m in new_supervised:
    m.supervisors.add(instance)
```

Wait — with the new M2M field named `supervisors` on the missionary side, and `supervised_users` as the reverse name on the supervisor side:
- `supervisor_instance.supervised_users.all()` = missionaries this person supervises
- `missionary_instance.supervisors.all()` = supervisors assigned to this missionary

Auto-unassign on role change: when admin changes a user from `supervisor` to another role, their `supervised_users.clear()` (reverse M2M) removes them from all missionaries' supervisors set.

### CurrentUserSerializer

```python
def get_supervised_users(self, obj):
    if obj.role == 'supervisor':
        qs = obj.supervised_users.filter(is_active=True)  # same as before
    elif obj.role == 'coach':
        qs = obj.coached_users.filter(is_active=True)   # same as before
    ...
```

No change needed — reverse relation names preserved.

### UserSerializer — Remove scalar FK fields

Current UserSerializer includes `'supervisor'` and `'coach_id'` as fields. These reference the old FK columns and must be removed or replaced. AdminUsers.tsx currently reads `u.supervisor` and `u.coach` as scalar IDs to derive supervised/coached counts:

```typescript
users.filter(u => u.supervisor === user.id).length
users.filter(u => u.coach === user.id).length
```

After M2M, these scalar fields are gone. Options:
- Add `supervisor_ids: string[]` and `coach_ids: string[]` to UserSerializer (read lists from M2M)
- Or derive counts differently in AdminUsers.tsx

Recommendation: Add `supervisor_ids` and `coach_ids` to UserSerializer as `SerializerMethodField` returning lists. This allows AdminUsers.tsx to derive counts and pre-populate the edit form's multi-select without a separate API call.

### Frontend — AdminAssignments.tsx State Change

Current local state:
```typescript
Map<string, { supervisor_id: string | null; coach_id: string | null }>
```

New local state:
```typescript
Map<string, { supervisor_ids: string[]; coach_ids: string[] }>
```

The cell rendering changes from a single Radix `<Select>` (one value) to a Popover+Command multi-select (same pattern as AdminUsers.tsx lines 493–558) with chip badges below.

**Supervisor view toggle**: Add a `viewMode: 'missionary' | 'supervisor'` state. In missionary view, render the current table (missionaries as rows). In supervisor view, pivot the data: iterate `data.supervisors`, for each show their `supervised_users` (derived by inverting the missionary assignments map).

The toggle is a simple button group or tab above the table.

### Frontend — API Type Changes

```typescript
// users.ts: MissionaryAssignment changes from:
export interface MissionaryAssignment {
  id: string
  email: string
  full_name: string
  supervisor_id: string | null   // REMOVE
  coach_id: string | null        // REMOVE
}

// To:
export interface MissionaryAssignment {
  id: string
  email: string
  full_name: string
  supervisor_ids: string[]       // ADD
  coach_ids: string[]            // ADD
}

// AssignmentUpdate changes from:
export interface AssignmentUpdate {
  missionary_id: string
  supervisor_id: string | null   // REMOVE
  coach_id: string | null        // REMOVE
}

// To:
export interface AssignmentUpdate {
  missionary_id: string
  supervisor_ids: string[]       // ADD
  coach_ids: string[]            // ADD
  additive?: boolean             // ADD (for bulk apply)
}

// User interface loses:
supervisor: string | null        // REMOVE (scalar FK gone)
coach: string | null             // REMOVE (scalar FK gone)

// User interface gains:
supervisor_ids: string[]         // ADD
coach_ids: string[]              // ADD
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-select with search | Custom dropdown | Popover + Command (already in AdminUsers.tsx) | Already built, tested, matches existing UI |
| M2M data copy in migration | Custom SQL | `RunPython` with Django ORM | Safe, works with historical models |
| Chip/badge display | Custom chip component | shadcn `Badge` with `X` button | Already used in AdminUsers.tsx lines 544–557 |

---

## Common Pitfalls

### Pitfall 1: symmetrical=True on self-referencing M2M
**What goes wrong:** Django defaults self-referencing M2M to `symmetrical=True`, meaning if A supervises B, Django auto-adds B supervises A. This would corrupt the data model.
**How to avoid:** Always specify `symmetrical=False` on both `supervisors` and `coaches` M2M fields.

### Pitfall 2: Calling .update() on M2M reverse manager
**What goes wrong:** `user.supervised_users.update(supervisor=None)` works on FK reverse managers but fails silently or raises an error on M2M managers (M2M managers don't support `.update()`).
**How to avoid:** Use `.clear()`, `.add()`, `.remove()`, or `.set()` — the M2M manager methods.

### Pitfall 3: select_related() on M2M
**What goes wrong:** `select_related('supervisors')` raises an error — `select_related` only works on FK/O2O fields.
**How to avoid:** Use `prefetch_related('supervisors', 'coaches')` for M2M fields.

### Pitfall 4: Frontend supervisor_id scalar assumption in AdminUsers.tsx
**What goes wrong:** `users.filter(u => u.supervisor === user.id)` assumes `supervisor` is a scalar ID on each user. After M2M, this field is gone.
**How to avoid:** Switch to `users.filter(u => u.supervisor_ids?.includes(user.id))` after adding `supervisor_ids`/`coach_ids` to UserSerializer.

### Pitfall 5: openEditDialog() deriving supervised/coached lists from User.supervisor scalar
**What goes wrong:** Lines 137–141 in AdminUsers.tsx derive `editSupervisedUserIds` by filtering `users` for `u.supervisor === user.id`. After the FK is removed, this produces empty arrays.
**How to avoid:** Read `supervisor_ids`/`coach_ids` directly from the API response on the user object.

### Pitfall 6: Bulk additive vs. full replace semantics in PATCH
**What goes wrong:** If the PATCH always does `set()`, bulk apply replaces existing assignments instead of adding. Locked decision says bulk is additive.
**How to avoid:** PATCH item distinguishes additive mode (use `.add()`) vs. full-replace mode (use `.set()`).

### Pitfall 7: Migration ordering — RunPython before RemoveField
**What goes wrong:** If `RemoveField` runs before `RunPython`, the FK data is gone and cannot be copied to M2M.
**How to avoid:** Strictly: AddField M2M → RunPython copy → RemoveField FK. Matches established pattern from 0005_roles_redesign.py.

### Pitfall 8: Django admin references to supervisor/coach FK
**What goes wrong:** If any Django admin class (e.g., in UserAdmin) references `supervisor` or `coach` as list_display, list_filter, or fieldset fields, the removed FK will cause a startup error.
**How to avoid:** Check `apps/users/admin.py` for these references before migration.

---

## Code Examples

### Migration: FK to M2M with data preservation
```python
# Source: apps/users/migrations/0005_roles_redesign.py pattern

def copy_fk_to_m2m(apps, schema_editor):
    User = apps.get_model('users', 'User')
    for user in User.objects.filter(supervisor__isnull=False):
        user.supervisors.add(user.supervisor_id)
    for user in User.objects.filter(coach__isnull=False):
        user.coaches.add(user.coach_id)

class Migration(migrations.Migration):
    operations = [
        migrations.AddField(model_name='user', name='supervisors',
            field=models.ManyToManyField('self', symmetrical=False, blank=True,
                related_name='supervised_users')),
        migrations.AddField(model_name='user', name='coaches',
            field=models.ManyToManyField('self', symmetrical=False, blank=True,
                related_name='coached_users')),
        migrations.RunPython(copy_fk_to_m2m, migrations.RunPython.noop),
        migrations.RemoveField(model_name='user', name='supervisor'),
        migrations.RemoveField(model_name='user', name='coach'),
    ]
```

### AssignmentsView GET (new)
```python
# Source: apps/users/views_assignments.py analysis
missionaries = User.objects.filter(
    role='missionary', is_active=True
).prefetch_related('supervisors', 'coaches').order_by('last_name', 'first_name')

'supervisor_ids': [str(s.id) for s in m.supervisors.all()],
'coach_ids': [str(c.id) for c in m.coaches.all()],
```

### AssignmentsView PATCH (new)
```python
# Source: apps/users/views_assignments.py analysis
supervisor_ids = item.get('supervisor_ids', [])  # list of uuid strs
additive = item.get('additive', False)
supervisor_objs = list(User.objects.filter(id__in=supervisor_ids, role='supervisor'))
if additive:
    missionary.supervisors.add(*supervisor_objs)
else:
    missionary.supervisors.set(supervisor_objs)
# No missionary.save() needed — M2M operations write to join table directly
```

### UserAdminUpdateSerializer.update() (new)
```python
# Source: apps/users/serializers.py analysis
if supervised_ids is not None:
    # Clear this supervisor from all missionaries (reverse M2M clear)
    instance.supervised_users.clear()
    # Add to new missionaries
    for m in User.objects.filter(id__in=supervised_ids, is_active=True):
        m.supervisors.add(instance)
```

### Auto-unassign on role change
```python
# In UserAdminUpdateSerializer.update(), when role changes away from supervisor/coach:
old_role = instance.role
instance = super().update(instance, validated_data)  # role is updated here
new_role = instance.role
if old_role == 'supervisor' and new_role != 'supervisor':
    instance.supervised_users.clear()
if old_role == 'coach' and new_role != 'coach':
    instance.coached_users.clear()
```

### Frontend multi-select in table cell (reuse AdminUsers.tsx pattern)
```typescript
// Source: AdminUsers.tsx lines 493-558
// Popover + Command + Badge chips pattern already established
// supervisorIds: string[] from localAssignments Map
<Popover>
  <PopoverTrigger asChild>
    <Button variant="outline">
      {supervisorIds.length > 0 ? `${supervisorIds.length} assigned` : "Assign..."}
    </Button>
  </PopoverTrigger>
  <PopoverContent>
    <Command>
      <CommandInput placeholder="Search supervisors..." />
      <CommandList>
        {data?.supervisors.map(s => (
          <CommandItem onSelect={() => toggleSupervisor(missionaryId, s.id)}>
            <Check className={cn("mr-2 h-4 w-4",
              supervisorIds.includes(s.id) ? "opacity-100" : "opacity-0")} />
            {s.first_name} {s.last_name}
          </CommandItem>
        ))}
      </CommandList>
    </Command>
  </PopoverContent>
</Popover>
{supervisorIds.map(id => (
  <Badge key={id} variant="secondary" className="gap-1">
    {findSupervisorName(id)}
    <button onClick={() => removeSupervisor(missionaryId, id)}><X className="h-3 w-3"/></button>
  </Badge>
))}
```

---

## Full File Change Map

This section documents every file that needs modification:

### Backend
| File | Change |
|------|--------|
| `apps/users/models.py` | Replace `supervisor` FK + `coach` FK with `supervisors` M2M + `coaches` M2M (symmetrical=False, same related_names). Remove `can_view_contact()` changes — stays the same. |
| `apps/users/migrations/0006_m2m_supervisors.py` | New migration: AddField x2, RunPython (copy FK→M2M), RemoveField x2 |
| `apps/users/serializers.py` | `UserSerializer`: remove `supervisor`, `coach_id`; add `supervisor_ids`, `coach_ids` as SerializerMethodField. `UserAdminUpdateSerializer.update()`: replace `.update(supervisor=...)` with M2M `.add()`/`.clear()`. `CurrentUserSerializer.get_supervised_users()`: unchanged (reverse names preserved). |
| `apps/users/views_assignments.py` | GET: `select_related` → `prefetch_related`; return `supervisor_ids[]`/`coach_ids[]`. PATCH: receive arrays, use `.set()`/`.add()` per additive flag. Remove `missionary.save(update_fields=...)`. |
| `apps/core/permissions.py` | No change — `supervised_users`/`coached_users` reverse names preserved. |
| `apps/contacts/views.py` | No change — uses `get_visible_user_ids()`. |
| `apps/gifts/views.py` | No change — uses `get_visible_user_ids()`. |
| All other app views | No change — all scoping flows through `get_visible_user_ids()`. |

### Frontend
| File | Change |
|------|--------|
| `frontend/src/api/users.ts` | `MissionaryAssignment`: `supervisor_id→supervisor_ids[]`, `coach_id→coach_ids[]`. `AssignmentUpdate`: scalars→arrays + additive flag. `User`: remove `supervisor`/`coach` scalars; add `supervisor_ids[]`/`coach_ids[]`. |
| `frontend/src/pages/admin/AdminAssignments.tsx` | Replace Radix Select with Popover+Command multi-select. State Map type change. Add view mode toggle (missionary/supervisor). Bulk apply becomes additive (call add mode). |
| `frontend/src/pages/admin/AdminUsers.tsx` | `openEditDialog`: derive supervised/coached from `user.supervisor_ids`/`user.coach_ids` instead of `users.filter(u => u.supervisor === id)`. Count display: `user.supervisor_ids?.length` instead of filter count. |
| `frontend/src/hooks/useUsers.ts` | `AssignmentUpdate` type update flows through automatically. |

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| FK `supervisor_id` / `coach_id` columns on users table | M2M join tables (auto-generated) | No FK columns on users table; join tables handle many-to-many |
| `select_related('supervisor', 'coach')` | `prefetch_related('supervisors', 'coaches')` | Different ORM method; same query efficiency |
| `missionary.supervisor = obj; missionary.save()` | `missionary.supervisors.set([obj])` | M2M operations don't require model `.save()` |

---

## Open Questions

1. **Django admin UserAdmin configuration**
   - What we know: apps/users/admin.py likely references `supervisor`/`coach` FK fields for list_display or fieldsets
   - What's unclear: exact admin configuration not read
   - Recommendation: Read `apps/users/admin.py` in Wave 1 — remove/update FK references before running migration

2. **Supervisor view toggle exact layout**
   - What we know: rows = supervisors, showing all missionaries assigned to each
   - What's unclear: whether supervisor view is a separate table or a grouped view within the same table
   - Recommendation: Use a simple two-column table (supervisor name | assigned missionaries as chips) — same data already available from assignments API

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest-django (current version) |
| Config file | `pytest.ini` or `setup.cfg` (project root) |
| Quick run command | `pytest apps/users/tests/ -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map

Phase 46 is an extension of SUPV-01–04 (already complete). No new numbered requirements in REQUIREMENTS.md — this phase is a capability extension. Tests should cover the behavioral guarantees.

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Missionary can have 2+ supervisors assigned | unit | `pytest apps/users/tests/test_models.py -x -q` | Wave 0: add test |
| get_visible_user_ids() returns union across all supervisors | unit | `pytest apps/users/tests/ -x -q` | Wave 0: add test |
| AssignmentsView GET returns supervisor_ids[] array | integration | `pytest apps/users/tests/test_views.py -x -q` | Wave 0: add test |
| AssignmentsView PATCH with additive=True appends without replacing | integration | `pytest apps/users/tests/test_views.py -x -q` | Wave 0: add test |
| Role change to non-supervisor clears M2M assignments | unit | `pytest apps/users/tests/test_views.py -x -q` | Wave 0: add test |
| Migration: existing FK assignments preserved in M2M | migration | `pytest --migrations -x -q` | Wave 0: add test |

### Sampling Rate
- **Per task commit:** `pytest apps/users/tests/ -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/users/tests/test_m2m_assignments.py` — new test file for M2M behaviors (REQ: multi-supervisor assignment, additive bulk, role-change clear)
- [ ] `apps/users/tests/factories.py` — add `SupervisorUserFactory` and `CoachUserFactory` (currently missing from factories.py)
- [ ] Migration test fixture in `test_m2m_assignments.py` to verify FK→M2M data preservation

---

## Sources

### Primary (HIGH confidence)
- `apps/users/models.py` — exact FK field definitions, `supervised_users`/`coached_users` related_names, `can_view_contact()`
- `apps/core/permissions.py` — `get_visible_user_ids()` implementation, all role checks
- `apps/users/views_assignments.py` — current GET/PATCH structure
- `apps/users/serializers.py` — `UserAdminUpdateSerializer.update()` batch-clear pattern
- `apps/users/migrations/0005_roles_redesign.py` — RunPython before AlterField pattern
- `frontend/src/pages/admin/AdminAssignments.tsx` — complete current UI with state shape
- `frontend/src/pages/admin/AdminUsers.tsx` — Popover+Command multi-select chip pattern (lines 493–558)
- `frontend/src/api/users.ts` — `MissionaryAssignment`, `AssignmentUpdate`, `User` interfaces
- `apps/contacts/views.py`, `apps/gifts/views.py`, `apps/journals/views.py` — all use `get_visible_user_ids()`, no direct FK traversal
- `.planning/phases/46-multiple-supervisors-per-missionary/46-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- Django documentation pattern: `symmetrical=False` for self-referencing M2M (standard Django behavior, confirmed by field structure analysis)
- M2M manager API: `.set()`, `.add()`, `.clear()` — standard Django ORM, confirmed by project's established test patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed; no new dependencies
- Architecture: HIGH — all findings from direct source code reading; no speculation
- Pitfalls: HIGH — derived from actual code patterns that would break after FK removal
- Migration strategy: HIGH — follows established pattern from migration 0005 in same codebase

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable Django M2M patterns)
