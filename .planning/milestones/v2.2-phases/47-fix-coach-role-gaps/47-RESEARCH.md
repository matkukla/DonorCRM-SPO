# Phase 47: Fix Coach Role Gaps - Research

**Researched:** 2026-03-10
**Domain:** Django permissions, DRF serializers, pytest fixtures, role-based access control
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ROLE-01 | DB and UI use `missionary` (not `staff`) everywhere; test suite passes with correct role names | 4 files identified with stale `role='staff'` or `role='staff'` assertions; all are simple string replacements |
| ROLE-03 | Coach users can access contacts for their assigned missionaries (no 403) | `IsStaffOrAbove` at `apps/core/permissions.py:89` excludes `'coach'`; one-line fix to add coach for GET methods |
| ROLE-04 | Admin can assign coaches to missionaries via AdminUsers page (coached_user_ids persisted) | Backend serializer already handles `coached_user_ids`; frontend already sends it; root cause is the GET query in AdminUsers.tsx reading stale FK assumptions resolved by Phase 46 M2M |
| ROLE-05 | `/team/:userId` Contacts tab works for coach users | Same `IsStaffOrAbove` gap as ROLE-03; fixing permissions.py resolves both |
</phase_requirements>

---

## Summary

Phase 47 is a targeted gap-closure phase with two distinct repair tracks. The first track (Plan 01) is pure mechanical text replacement: four test files still use `role='staff'` (deleted in Phase 43 migration 0005), causing `AttributeError` or silent permission failures on any test run touching those fixtures. The second track (Plan 02) has two sub-problems with the same root: `IsStaffOrAbove` omits `'coach'` from its allowed roles list, blocking coach GET requests to `/api/v1/contacts/`, and the `UserAdminUpdateSerializer` may have a subtle M2M direction issue with `coached_user_ids` that needs verification.

The audit found that the `UserAdminUpdateSerializer.update()` "silently drops" `coached_user_ids`. Code inspection shows the serializer field is defined and the update handler calls `instance.coached_users.set(coached_users)`. The `coached_users` reverse relation is the correct M2M accessor for "missionaries coached by this coach user." This appears to already be correct code; the "silent drop" described in the audit may have been accurate at an earlier point (pre-Phase 46) and should be verified with a targeted test.

All changes are surgical: no migrations, no new models, no frontend rebuilds required for the permission fix. The contacts permission fix touches a single line in `apps/core/permissions.py`.

**Primary recommendation:** Fix `IsStaffOrAbove` to allow coach read access, replace 4 stale `role='staff'` strings, and add regression tests to lock both behaviors.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-django | installed | Django test runner | Project standard, see pyproject.toml |
| factory_boy | installed | Test fixtures | `UserFactory`, `CoachUserFactory`, `SupervisorUserFactory` already exist in `apps/users/tests/factories.py` |
| Django REST Framework permissions | installed | `IsStaffOrAbove` base class | Project permission system |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rest_framework.permissions.SAFE_METHODS` | installed | `('GET', 'HEAD', 'OPTIONS')` tuple | Used in `IsStaffOrAbove` to gate reads vs writes separately |

**Run command:**
```bash
cd /home/matkukla/projects/DonorCRM && python -m pytest apps/contacts/tests/ apps/users/tests/ apps/imports/tests/ apps/insights/tests/ -x -q
```

---

## Architecture Patterns

### Existing Permission Class Structure

```python
# apps/core/permissions.py line 76-89
class IsStaffOrAbove(permissions.BasePermission):
    """
    Permission class that allows Missionary, Finance, Supervisor, or Admin users.
    Excludes read-only and coach users from write operations.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Read-only users can only perform safe methods
        if request.user.role == 'read_only':
            return request.method in permissions.SAFE_METHODS

        return request.user.role in ['admin', 'finance', 'missionary', 'supervisor']
        # ^^^ coach is missing — this is the ROLE-03/ROLE-05 bug
```

### Fix Pattern for Coach Read Access

The audit specifies two options:
1. Add `'coach'` to the `IsStaffOrAbove` allowed list (but differentiate reads vs writes)
2. Switch `ContactListCreateView` to `IsAuthenticated` with scoping in `get_queryset()`

Option 1 is lower risk. Coach should be allowed GET but blocked from POST/PUT/PATCH/DELETE on contacts (they are read-only for contacts). The `read_only` pattern already exists in the same class — mirror it for coach:

```python
# Proposed fix
def has_permission(self, request, view):
    if not request.user.is_authenticated:
        return False
    # Read-only and coach users can only perform safe methods
    if request.user.role in ['read_only', 'coach']:
        return request.method in permissions.SAFE_METHODS
    return request.user.role in ['admin', 'finance', 'missionary', 'supervisor']
```

This matches the existing design: `read_only` gets safe-method-only access, `coach` should too.

Note: `get_visible_user_ids()` already handles coach correctly — it returns `{own_id} union {coached user IDs}`. The `ContactListCreateView.get_queryset()` already uses `get_visible_user_ids()`. So data scoping is already correct; only the permission gate is broken.

### Stale Role Strings — Complete File List

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `conftest.py` | 25 | `user_factory(role='staff')` | Change to `role='missionary'` |
| `apps/imports/tests/test_spo_views.py` | 74 | `role='staff'` in `_make_staff()` | Change to `role='missionary'` |
| `apps/imports/tests/test_spo_csv_fixture_mapping.py` | 40 | `role='staff'` in `_make_staff_owner()` | Change to `role='missionary'` |
| `apps/insights/tests/test_user_drilldown.py` | 171 | `assertEqual(...['role'], 'staff')` assertion | Change assertion to `'missionary'` |

Note: `apps/users/managers.py:53-55` has a `staff_users()` method with the comment "Return active missionary users" but the code already uses `role='missionary'` — this was already corrected and is NOT stale.

### M2M Direction in UserAdminUpdateSerializer

The User model has:
- `User.coaches` — M2M field pointing TO coaches (on the missionary side)
- `User.coached_users` — reverse accessor (on the coach side, list of missionaries this coach coaches)
- `User.supervisors` — M2M field pointing TO supervisors (on the missionary side)
- `User.supervised_users` — reverse accessor (on the supervisor side)

When admin updates a **coach user** with `coached_user_ids = [missionary_id_1, missionary_id_2]`, the intent is: "set the list of missionaries that this coach coaches."

Current serializer code:
```python
if coached_ids is not None:
    coached_users = User.objects.filter(id__in=coached_ids, is_active=True)
    instance.coached_users.set(coached_users)
```

`instance.coached_users` is the reverse relation — the missionaries coached by `instance`. `.set()` on a reverse M2M replaces that set. This is semantically correct.

However, there is a potential issue: `User.save()` has an auto-clear guard:
```python
if old_role == UserRole.COACH and self.role != UserRole.COACH:
    self.coached_users.clear()
```

In `UserAdminUpdateSerializer.update()`, `super().update(instance, validated_data)` saves the instance (including any role change), then the M2M `.set()` is called. If the role changes FROM coach to something else in the same request, `save()` would clear coached_users, then `.set()` would add them back. This is a subtle ordering issue that could cause unexpected behavior but is unlikely to occur in normal use (you wouldn't set coached_user_ids while changing role away from coach).

**Conclusion:** The serializer logic is correct for the ROLE-04 case. The "silently drops" audit finding was likely accurate before Phase 46 (when it was FK-based). The current M2M implementation should work. A targeted test is needed to verify and lock this behavior.

### Anti-Patterns to Avoid

- **Don't change `IsStaffOrAbove` to `IsAuthenticated` on ContactListCreateView** — this would allow `read_only` users to POST contacts, breaking their restriction.
- **Don't add `'coach'` to the full allowed list** without limiting to SAFE_METHODS — coaches must not create/edit/delete contacts.
- **Don't assume all `role='staff'` strings are bugs** — Django admin's `is_staff` boolean field is unrelated and uses the string "staff" legitimately in some Django internals.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Checking safe methods | Custom method whitelist | `permissions.SAFE_METHODS` | DRF constant, already used in same class |
| Creating test coach users | Manual `User.objects.create_user(role='coach')` | `CoachUserFactory` from `apps/users/tests/factories.py` | Already exists with unique email sequences |

---

## Common Pitfalls

### Pitfall 1: Fixing Only the conftest.py authenticated_client Fixture
**What goes wrong:** `conftest.py` line 25 is the root, but `test_spo_views.py`, `test_spo_csv_fixture_mapping.py`, and `test_user_drilldown.py` have their own local `_make_staff()` helpers and assertions that also need fixing.
**Why it happens:** Grep for `role='staff'` shows all four locations.
**How to avoid:** Fix all four files in Plan 01. Run full test suite to confirm zero `role='staff'` failures.

### Pitfall 2: Breaking read_only Behavior When Adding coach to IsStaffOrAbove
**What goes wrong:** If `'coach'` is added to the flat allowed-roles list (line 89), coach users would be able to POST/PATCH/DELETE contacts — violating the access model.
**Why it happens:** The existing `read_only` guard short-circuits before the allowed list. Coach needs the same treatment.
**How to avoid:** Add `'coach'` to the `read_only` early-return check, not to the final allowed list.

### Pitfall 3: Testing Only the List Endpoint
**What goes wrong:** Fixing `ContactListCreateView` permissions but forgetting that `ContactDetailView` (or other views) may also use `IsStaffOrAbove` and block coach access.
**Why it happens:** The audit specifically calls out "ContactListCreateView" — but coach needs read access to individual contact records too when viewing missionary profiles.
**Warning signs:** Coach can list contacts but gets 403 on contact detail.
**How to avoid:** Check `ContactDetailView` permission classes and apply the same fix if needed.

### Pitfall 4: Confusing coached_users vs coaches M2M Direction
**What goes wrong:** Setting `instance.coaches.set(...)` instead of `instance.coached_users.set(...)` when updating a coach user — this would set who the coach's own coaches are (self-referential), not who they coach.
**Why it happens:** Both M2M fields use `'self'` as the target model.
**How to avoid:** For a coach user, the missions they are assigned to coach are accessed via `coach_user_instance.coached_users` (reverse relation).

---

## Code Examples

Verified patterns from source inspection:

### Current IsStaffOrAbove (Broken for Coach)
```python
# apps/core/permissions.py line 81-89
def has_permission(self, request, view):
    if not request.user.is_authenticated:
        return False
    # Read-only users can only perform safe methods
    if request.user.role == 'read_only':
        return request.method in permissions.SAFE_METHODS
    return request.user.role in ['admin', 'finance', 'missionary', 'supervisor']
```

### Fixed IsStaffOrAbove (Coach Gets Read-Only Access)
```python
def has_permission(self, request, view):
    if not request.user.is_authenticated:
        return False
    # Read-only and coach users can only perform safe methods
    if request.user.role in ['read_only', 'coach']:
        return request.method in permissions.SAFE_METHODS
    return request.user.role in ['admin', 'finance', 'missionary', 'supervisor']
```

### Coach Factory (Already Exists)
```python
# apps/users/tests/factories.py
class CoachUserFactory(UserFactory):
    """Factory for creating Coach users."""
    role = UserRole.COACH
    email = factory.Sequence(lambda n: f"coach{n}@example.com")
```

### get_visible_user_ids Already Handles Coach (No Change Needed)
```python
# apps/core/permissions.py line 38-45
if user.role == 'coach':
    ids = set(
        user.coached_users
        .filter(is_active=True)
        .values_list('id', flat=True)
    )
    ids.add(user.id)
    return ids
```

### ContactListCreateView get_queryset Already Scopes Coach (No Change Needed)
```python
# apps/contacts/views.py line 62-76
def get_queryset(self):
    user = self.request.user
    visible = get_visible_user_ids(user)
    if visible is None:
        queryset = Contact.objects.all()
    else:
        queryset = Contact.objects.filter(owner_id__in=visible)
    ...
    return queryset.select_related('owner')
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `role='staff'` | `role='missionary'` | Phase 43 migration 0005 | Test fixtures using old string cause failures |
| Coach FK field | Coach M2M field (`coaches`/`coached_users`) | Phase 46 | `UserAdminUpdateSerializer` now uses `.set()` not FK assignment |

---

## Open Questions

1. **Does ContactDetailView also need the coach fix?**
   - What we know: The audit calls out `ContactListCreateView` specifically. `ContactDetailView` also uses `IsStaffOrAbove` (same permission class).
   - What's unclear: Whether the `/team/:userId` Contacts tab only calls the list endpoint or also fetches individual contacts.
   - Recommendation: Fix both `ContactListCreateView` and `ContactDetailView` in the same permission fix — they use the same class so fixing the class fixes both simultaneously.

2. **Is the coached_user_ids serializer actually broken in production?**
   - What we know: The code in `UserAdminUpdateSerializer.update()` looks correct. The audit finding predates Phase 46.
   - What's unclear: Whether any real-world coach assignment via AdminUsers page has ever silently dropped.
   - Recommendation: Add a focused test for the full flow: admin updates coach user with `coached_user_ids`, verify via GET that the user's `coached_users` M2M is populated. If the test passes, ROLE-04 is already fixed and only needs the test lock. If it fails, investigate the M2M direction.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest-django (pyproject.toml) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest apps/contacts/tests/ apps/users/tests/ -x -q` |
| Full suite command | `python -m pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ROLE-01 | `authenticated_client` fixture creates `role='missionary'` user, not `role='staff'` | unit | `python -m pytest conftest.py apps/imports/tests/test_spo_views.py apps/imports/tests/test_spo_csv_fixture_mapping.py apps/insights/tests/test_user_drilldown.py -x -q` | Exists (failing) |
| ROLE-03 | Coach GET `/api/v1/contacts/` returns 200 (not 403) | integration | `python -m pytest apps/contacts/tests/test_integration.py -x -q` | Exists (gap — no coach test) |
| ROLE-04 | Admin PATCH to coach user with coached_user_ids persists M2M | integration | `python -m pytest apps/users/tests/test_views.py -x -q` | Exists (gap — no coached_user_ids test) |
| ROLE-05 | Coach GET `/api/v1/contacts/?owner=<missionary_id>` returns 200 | integration | `python -m pytest apps/contacts/tests/test_integration.py -x -q` | Exists (gap — no coach scoping test) |

### Sampling Rate
- **Per task commit:** `python -m pytest apps/contacts/tests/ apps/users/tests/ apps/imports/tests/ apps/insights/tests/ -x -q`
- **Per wave merge:** `python -m pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/contacts/tests/test_integration.py` — needs new test class `TestCoachContactAccess` covering ROLE-03 and ROLE-05
- [ ] `apps/users/tests/test_views.py` — needs `test_admin_can_set_coached_user_ids` covering ROLE-04

*(The 4 stale-role files already exist; they are broken, not missing. Wave 0 for Plan 01 is fixing those strings, not creating new files.)*

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection of `apps/core/permissions.py` — `IsStaffOrAbove` implementation confirmed
- Direct source inspection of `conftest.py`, `test_spo_views.py`, `test_spo_csv_fixture_mapping.py`, `test_user_drilldown.py` — stale role strings confirmed
- Direct source inspection of `apps/users/serializers.py` — `UserAdminUpdateSerializer.update()` implementation confirmed
- Direct source inspection of `apps/users/models.py` — M2M field names and auto-clear logic confirmed
- `.planning/v2.2-MILESTONE-AUDIT.md` — gap descriptions and file locations

### Secondary (MEDIUM confidence)
- `apps/contacts/views.py` — `ContactListCreateView` uses `IsStaffOrAbove` and `get_visible_user_ids`; scoping is already correct for coach

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- Architecture: HIGH — all files identified and inspected directly
- Pitfalls: HIGH — root causes confirmed by source code inspection

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable codebase; no fast-moving dependencies)
