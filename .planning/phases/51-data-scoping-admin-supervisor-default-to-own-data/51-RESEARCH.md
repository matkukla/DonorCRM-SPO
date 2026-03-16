# Phase 51: Data Scoping — Admin & Supervisor Default to Own Data - Research

**Researched:** 2026-03-13
**Domain:** Django permissions / queryset scoping (backend-only)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Roles affected:**
- `admin` role: changes from `None` (all data) to `{user.id}` (own data only)
- `supervisor` role: changes from `{own_id} + supervised IDs` to `{user.id}` (own data only)
- `finance` and `read_only` roles: unchanged — continue to return `None` (see all data)
- The change is a single-function update to `get_visible_user_ids()` in `apps/core/permissions.py`

**Admin Analytics carve-out:**
- Admin Analytics / Insights services (`apps/insights/services.py`) cross-user functions (lines 273+, 654+, 870+) have no user parameter — these are intentional aggregate views and must remain untouched
- MPD Overview tile (Phase 48) uses all-users aggregation — leave unchanged
- Admin's personal Dashboard tiles DO call `get_visible_user_ids()` — after this change, admin sees only their own MPD stats on the Dashboard (intended per SCOPE-01)

**Object-level permissions (IsOwnerOrAdmin):**
- `IsOwnerOrAdmin` permission class stays unchanged — admin can still access any individual object by direct URL
- Only list view queryset scoping changes

**Owner filter param (`?owner=`):**
- `?owner=<id>` param stays in place — needed for View As in Phase 53
- No code changes to owner param handling; the queryset fix handles restriction automatically
- Export views follow the same treatment

**Frontend:**
- Phase 51 is backend-only — no frontend changes
- Owner filter dropdowns remain in the UI; they will return empty results for non-self owners but are left for Phase 53

### Claude's Discretion
- Whether to add a docstring update to `get_visible_user_ids()` noting the new behavior
- Test approach for verifying the scoping change (unit test on the function or integration test on a view)

### Deferred Ideas (OUT OF SCOPE)
- Owner filter dropdown UI cleanup (Contacts, Journals, Gifts pages) — Phase 53 (View As frontend will repurpose it)
- Scoping `finance` and `read_only` roles to own data — not in requirements, defer to v2.4+ if needed
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCOPE-01 | Admin and supervisor roles default to seeing only their own data (owner=self) in all list views — same as missionary role | Handled by changing `get_visible_user_ids()` return for admin and supervisor; cascades to all 13 caller sites with no per-view changes |
| SCOPE-02 | Elevated cross-user data access only activates when a View As session is active | Confirmed: after Phase 51, the only path to cross-user data is an explicit View As mechanism (Phases 52–53); the `?owner=` param naturally becomes self-restricted |
</phase_requirements>

---

## Summary

Phase 51 is the narrowest possible scope change in the codebase: modify exactly two branches of a single 27-line Python function (`get_visible_user_ids()` in `apps/core/permissions.py`) and the cascading effect touches every list view, export view, and dashboard service across all 13 app modules with zero additional code changes required.

Currently `get_visible_user_ids()` returns `None` for admin (meaning "all data") and a set of `{own_id} + supervised_user_ids` for supervisors. The change makes both roles return only `{user.id}`. Every caller already has the pattern `if visible is None: queryset = Model.objects.all()` — after this change, admin and supervisor never trigger that branch; finance and read_only still do. The `visible is None` branches become dead code for admin/supervisor but must stay for the other roles.

The one edge to watch is the docstring in `permissions.py`: it currently documents admin/finance/read_only as all returning `None`. After this change admin no longer returns `None`, so the docstring needs updating to accurately reflect the new behavior. The admin insights functions (`get_dashboard_overview`, `get_stalled_contacts`, `get_user_performance`, `get_conversion_funnel`, `get_team_activity`, `get_team_trends`, `get_stage_contacts`, `get_pace_calculation`) take no user parameter and are completely independent of `get_visible_user_ids()` — they are untouched.

**Primary recommendation:** Change the admin branch of `get_visible_user_ids()` from `return None` to `return {user.id}`, change the supervisor branch from returning `{own_id} + supervised IDs` to returning `{user.id}`, update the docstring, and write a unit test for the function covering all six roles.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django ORM | 4.x (project) | Queryset scoping via `__in` filter | Already in use throughout all views |
| djangorestframework | 3.x (project) | Permission classes and APIViews | Already in use |
| pytest + pytest-django | project version | Unit tests for function behavior | Established pattern in `apps/core/tests/` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| factory_boy | project version | Create admin/supervisor/missionary User instances in tests | Test isolation without fixture files |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Unit test on `get_visible_user_ids()` | Integration test on a list view | Unit test is faster, simpler, and directly targets the function being changed; integration test adds Django test client overhead for no additional signal |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

No new files or directories needed. Changes are confined to:

```
apps/core/
├── permissions.py           # Only file modified (get_visible_user_ids function)
└── tests/
    └── test_permissions.py  # New test file (Wave 0 gap)
```

### Pattern 1: The None-Sentinel Pattern

**What:** `get_visible_user_ids()` returns either `None` (meaning "unrestricted, all users") or a `set` of integer user IDs. Callers branch on this sentinel.

**When to use:** Already established — every view uses this exact two-branch pattern.

**Current caller pattern (no changes to callers):**
```python
# Source: apps/contacts/views.py lines 64-68
visible = get_visible_user_ids(user)
if visible is None:
    queryset = Contact.objects.all()
else:
    queryset = Contact.objects.filter(owner_id__in=visible)
```

**Owner filter security check pattern (no changes needed):**
```python
# Source: apps/contacts/views.py lines 72-74
if owner_id and user.role in ['admin', 'supervisor', 'coach']:
    if visible is None or int(owner_id) in visible:
        queryset = queryset.filter(owner_id=owner_id)
```

After Phase 51: an admin passing `?owner=<other-user-id>` hits `int(owner_id) in visible` which evaluates to `int(other_id) in {user.id}` — False — so the filter is silently ignored and the admin sees only their own data. No special handling needed.

### Pattern 2: Insights Admin Functions Are Independent

**What:** Admin-analytics functions in `apps/insights/services.py` starting at line 273 (`get_dashboard_overview`, `get_stalled_contacts`, `get_user_performance`, `get_conversion_funnel`, `get_team_activity`, `get_team_trends`, `get_stage_contacts`, `get_pace_calculation`) take **no user parameter**. They query `Contact.objects.all()`, `Gift.objects.all()`, etc. directly.

**Why this matters:** These functions do NOT call `get_visible_user_ids()` and are completely unaffected by Phase 51. The user-scoped functions in insights (`_scope_gifts`, `_scope_recurring_gifts`, `_scope_tasks`, `get_donations_by_month`, `get_donations_by_year`, `get_monthly_commitments`, etc.) DO call `get_visible_user_ids()` and WILL be affected — admin users calling these functions will now see only their own data, which is correct per SCOPE-01.

### Anti-Patterns to Avoid

- **Modifying caller views:** Do not add special-case logic in ContactListCreateView, GiftsListView, etc. The single-function change cascades automatically.
- **Adding a migration:** This change is pure Python — no model schema changes, no migrations needed.
- **Removing the `visible is None` branches from callers:** Finance and read_only still return `None`; those branches remain active.
- **Changing `IsOwnerOrAdmin`:** Object-level permission for direct URL access is intentionally unchanged. Admin can still GET `/api/v1/contacts/<uuid>/` for any contact — list scoping and object access are separate concerns.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Role-based queryset scoping | Per-view role checks | `get_visible_user_ids()` choke point | All 13 callers already use this pattern; one-place change cascades everywhere |
| Test user creation | Manual `User.objects.create()` | `AdminUserFactory`, `SupervisorUserFactory`, `UserFactory` from `apps/users/tests/factories.py` | Factories handle password hashing, role defaults, required fields |

**Key insight:** The entire scoping system was architected as a choke point precisely for a change like this one.

---

## Common Pitfalls

### Pitfall 1: Forgetting the Docstring Is Part of the Contract

**What goes wrong:** The docstring of `get_visible_user_ids()` explicitly states "Admin/Finance/ReadOnly: returns None (sentinel for 'all users')". After the change, admin no longer returns None. The docstring at lines 21–27 documents behavior that other developers rely on.

**Why it happens:** Code changes without documentation updates are the norm.

**How to avoid:** Update the docstring in the same commit as the code change.

**Warning signs:** The class-level docstring in `permissions.py` lines 3–15 also lists "admin — Full access to all resources (all CRUD, all users' data)" — this too needs updating if a docstring update is chosen (Claude's discretion scope).

### Pitfall 2: Test Asserting Wrong Role Is Now Scoped

**What goes wrong:** Existing test `test_get_visible_user_ids_returns_missionary_for_both_supervisors` in `apps/users/tests/test_m2m_assignments.py` (lines 52–79) calls `get_visible_user_ids(sup1)` and asserts `missionary.id in visible_sup1`. After Phase 51, a supervisor returns only `{user.id}`, so `missionary.id` will NOT be in `visible_sup1`. This test will break.

**Why it happens:** The test was written against pre-Phase-51 supervisor behavior.

**How to avoid:** Update `test_get_visible_user_ids_returns_missionary_for_both_supervisors` to assert the new behavior: `visible_sup1 == {sup1.id}`. The test description will also need updating. Check whether any other tests in `apps/dashboard/tests/test_services.py` create AdminUserFactory and assert all-data visibility — those will also need review.

**Warning signs:** Any test that creates `AdminUserFactory()` or `SupervisorUserFactory()` and then asserts they can see another user's data in a list context is testing behavior that Phase 51 intentionally removes.

### Pitfall 3: Dashboard Services That Use get_visible_user_ids With Admin User

**What goes wrong:** `apps/dashboard/services.py` functions (`get_giving_summary`, `get_support_progress`, etc.) call `get_visible_user_ids(user)`. Tests in `apps/dashboard/tests/test_services.py` may create `AdminUserFactory()` and verify cross-user dashboard data. After Phase 51, those tests would fail if they assume admin sees all data via these functions.

**Why it happens:** Tests for dashboard services were written when admin returned None.

**How to avoid:** Review `apps/dashboard/tests/test_services.py` for any test using `AdminUserFactory` in a context where all-data visibility is assumed via `get_visible_user_ids()`.

### Pitfall 4: Coverage Requirement

**What goes wrong:** `pyproject.toml` requires `--cov-fail-under=80`. A new test file for `get_visible_user_ids()` that covers all six role branches will comfortably exceed this, but if tests are minimal (only admin + supervisor), the function change itself is covered while other roles are tested by other existing tests.

**Why it happens:** Coverage configuration is strict.

**How to avoid:** Write tests covering all six roles: admin, finance, read_only, supervisor, coach, missionary. This is a pure unit test with no DB hit needed for admin/supervisor/missionary (no M2M query). Supervisor and coach tests need `@pytest.mark.django_db` since they query `supervised_users`/`coached_users`.

---

## Code Examples

Verified patterns from reading source files:

### Current get_visible_user_ids (lines 20–46 of apps/core/permissions.py)

```python
# Source: apps/core/permissions.py
def get_visible_user_ids(user):
    """Return set of user IDs whose data this user can see, or None for 'all'.

    - Admin/Finance/ReadOnly: returns None (sentinel for 'all users')
    - Supervisor: returns {own_id} union {supervised user IDs}
    - Coach: returns {own_id} union {coached user IDs}
    - Missionary: returns {own_id}
    """
    if user.role in ['admin', 'finance', 'read_only']:
        return None
    if user.role == 'supervisor':
        ids = set(
            user.supervised_users
            .filter(is_active=True)
            .values_list('id', flat=True)
        )
        ids.add(user.id)
        return ids
    if user.role == 'coach':
        ids = set(
            user.coached_users
            .filter(is_active=True)
            .values_list('id', flat=True)
        )
        ids.add(user.id)
        return ids
    return {user.id}
```

### Target get_visible_user_ids (after Phase 51)

```python
# Source: derived from apps/core/permissions.py + CONTEXT.md decisions
def get_visible_user_ids(user):
    """Return set of user IDs whose data this user can see, or None for 'all'.

    Roles that see only their own data (return {user.id}):
      - admin, supervisor, coach, missionary

    Roles that see all users' data (return None sentinel):
      - finance, read_only

    Note: Admin cross-user access activates only via View As session (Phase 52+).
    Admin analytics endpoints (get_dashboard_overview, etc.) are unaffected —
    they do not call this function.
    """
    if user.role in ['finance', 'read_only']:
        return None
    if user.role == 'coach':
        ids = set(
            user.coached_users
            .filter(is_active=True)
            .values_list('id', flat=True)
        )
        ids.add(user.id)
        return ids
    return {user.id}
```

### Existing Supervisor Test That Needs Updating

```python
# Source: apps/users/tests/test_m2m_assignments.py lines 52-79
# THIS TEST WILL BREAK after Phase 51 — asserts supervised missionary is visible to supervisor
def test_get_visible_user_ids_returns_missionary_for_both_supervisors(self):
    ...
    visible_sup1 = get_visible_user_ids(sup1)
    assert missionary.id in visible_sup1  # FAILS after Phase 51 — sup1 sees only {sup1.id}
```

### Unit Test Pattern (matches apps/core/tests/ style)

```python
# Source: pattern derived from apps/core/tests/test_fiscal_year.py
import pytest
from apps.users.tests.factories import (
    AdminUserFactory, SupervisorUserFactory, FinanceUserFactory,
    ReadOnlyUserFactory, CoachUserFactory, UserFactory,
)


def test_admin_sees_only_own_data():
    from apps.core.permissions import get_visible_user_ids
    admin = AdminUserFactory.build()  # .build() avoids DB for simple roles
    result = get_visible_user_ids(admin)
    assert result == {admin.id}
    assert result is not None


def test_supervisor_sees_only_own_data():
    from apps.core.permissions import get_visible_user_ids
    sup = SupervisorUserFactory.build()
    result = get_visible_user_ids(sup)
    assert result == {sup.id}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Admin returns `None` (all data) | Admin returns `{user.id}` (own data only) | Phase 51 | Admin list views scope to own contacts/gifts/journals/tasks/prayers |
| Supervisor returns `{own} + supervised IDs` | Supervisor returns `{user.id}` | Phase 51 | Supervisor list views scope to own data only |
| Finance/read_only return `None` | Unchanged — still return `None` | N/A | No change |

**Deprecated/outdated after Phase 51:**
- Docstring claim "Admin/Finance/ReadOnly: returns None": admin no longer returns None
- Class docstring claim "admin — Full access to all resources (all CRUD, all users' data)": list access is now scoped (object-level admin access via direct URL unchanged)

---

## Open Questions

1. **Which dashboard/service tests use AdminUserFactory with cross-user data assumptions?**
   - What we know: `apps/dashboard/tests/test_services.py` imports `AdminUserFactory` (line 24) and tests functions that call `get_visible_user_ids()`
   - What's unclear: Whether any test asserts admin sees data belonging to a different user (would break after Phase 51)
   - Recommendation: Read `apps/dashboard/tests/test_services.py` fully before writing the plan task — identify any tests that need updating alongside the function change

2. **M2M assignment test update scope**
   - What we know: `test_get_visible_user_ids_returns_missionary_for_both_supervisors` directly asserts the old supervisor behavior
   - What's unclear: Whether other tests in `test_m2m_assignments.py` indirectly depend on supervisor seeing supervised users through `get_visible_user_ids()`
   - Recommendation: Include updating `test_m2m_assignments.py` as an explicit task step — don't treat it as optional cleanup

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django (pyproject.toml) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest apps/core/tests/test_permissions.py -x` |
| Full suite command | `pytest --cov=apps --cov-fail-under=80` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCOPE-01 | `get_visible_user_ids(admin)` returns `{admin.id}` not `None` | unit | `pytest apps/core/tests/test_permissions.py::test_admin_sees_only_own_data -x` | Wave 0 |
| SCOPE-01 | `get_visible_user_ids(supervisor)` returns `{supervisor.id}` not set-with-supervised | unit | `pytest apps/core/tests/test_permissions.py::test_supervisor_sees_only_own_data -x` | Wave 0 |
| SCOPE-01 | finance/read_only still return `None` (unchanged) | unit | `pytest apps/core/tests/test_permissions.py::test_finance_sees_all -x` | Wave 0 |
| SCOPE-01 | coach/missionary still return own-set (unchanged) | unit | `pytest apps/core/tests/test_permissions.py::test_coach_sees_own_and_coached -x` | Wave 0 |
| SCOPE-02 | Existing supervisor visibility test updated to reflect new behavior | unit | `pytest apps/users/tests/test_m2m_assignments.py::TestM2MModelBehaviors::test_get_visible_user_ids_returns_missionary_for_both_supervisors -x` | Exists (needs update) |

### Sampling Rate

- **Per task commit:** `pytest apps/core/tests/test_permissions.py -x`
- **Per wave merge:** `pytest --cov=apps --cov-fail-under=80`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `apps/core/tests/test_permissions.py` — covers SCOPE-01 (admin returns `{user.id}`, supervisor returns `{user.id}`, finance/read_only return `None`, coach/missionary unchanged)

*(Existing `test_m2m_assignments.py` exists but contains a test that asserts old behavior — needs updating, not a new file gap)*

---

## Sources

### Primary (HIGH confidence)

- `apps/core/permissions.py` — read directly; lines 20–46 are `get_visible_user_ids()`, lines 92–109 are `IsOwnerOrAdmin`
- `apps/contacts/views.py` — read directly; lines 64–74 show the canonical caller pattern
- `apps/insights/services.py` — read directly; lines 273+ confirm cross-user admin functions take no user param and are independent
- `apps/dashboard/services.py` — confirmed via grep; user-scoped functions call `get_visible_user_ids()`, admin analytics do not
- `apps/users/tests/test_m2m_assignments.py` — read directly; confirmed breaking test at lines 52–79
- `apps/users/tests/factories.py` — read directly; `AdminUserFactory`, `SupervisorUserFactory` available
- `pyproject.toml` — read directly; pytest config, coverage 80% threshold confirmed
- `51-CONTEXT.md` — read directly; all decisions locked

### Secondary (MEDIUM confidence)

- `apps/dashboard/tests/test_services.py` — partially read (first 60 lines); imports AdminUserFactory; full file not read to determine which tests need updating

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all files read directly from source
- Architecture: HIGH — caller pattern is consistent across all 13 modules confirmed via grep
- Pitfalls: HIGH — breaking test confirmed by reading test file directly; coverage requirement confirmed from pyproject.toml

**Research date:** 2026-03-13
**Valid until:** 2026-04-12 (stable internal code, not a fast-moving external library)
