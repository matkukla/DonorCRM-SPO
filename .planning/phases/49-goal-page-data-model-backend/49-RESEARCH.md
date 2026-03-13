# Phase 49: Goal Page — Data Model & Backend - Research

**Researched:** 2026-03-12
**Domain:** Django data model migration, service layer, DRF API endpoints
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Monthly goal field migration**
- Rename `User.monthly_goal` (DecimalField, dollars) → `monthly_support_goal_cents` (PositiveBigIntegerField, cents)
- Data migration: multiply existing values × 100, rounded (e.g., 3500.00 → 350000 cents)
- Done in Phase 49 — Phase 50 gets a clean cents-based API to work with
- Add `goal_weeks` (PositiveIntegerField, default=52) to User model alongside the cents field
- Update all existing references: dashboard services (get_support_progress uses user.monthly_goal), Settings serializer, CurrentUser serializer, admin

**Serializer/Settings API**
- Add `monthly_support_goal_cents` and `goal_weeks` to the Settings serializer's writable fields (SettingsUpdateSerializer or equivalent) — keeps /api/users/me/ PATCH as the mechanism for profile updates
- Settings page UI change (remove/replace Fundraising Goal card) is deferred to Phase 50 — Phase 49 only updates the API

**GoalJournalSelection model**
- Lives in `apps/users/` — goal config is user-owned preferences, consistent with monthly_support_goal_cents on User
- Shape: `GoalJournalSelection(user FK→User, journal FK→Journal, unique_together=[user, journal])`
- Separate model (not M2M without through), following JournalContact pattern
- TimeStampedModel base class

**API endpoint**
- New dedicated endpoint: `GET /api/goals/me/` and `PATCH /api/goals/me/`
- GET returns: current goal (cents), goal_weeks, selected journal IDs, and calculated `effective_monthly_support`
- PATCH saves: goal amount, goal_weeks, journal selections (replace-all semantics for journal list)
- URL registered in `apps/users/urls.py` or a new `apps/users/urls_goals.py`

**Journal → gift attribution logic**
- Effective monthly support = active RecurringGifts whose `donor_contact` is a JournalContact.contact in any selected journal — scoped to requesting user
- One-time Gifts: sum Gifts where `gift_date` is in the current fiscal year AND `donor_contact` is in journal contacts — divide by months_remaining (minimum 1)
- Total = recurring_monthly_equivalent + (fiscal_year_gifts ÷ months_remaining)
- New `apps/users/goal_services.py` with `get_goal_progress(user)` — separate from dashboard's `get_support_progress()` which stays unchanged

**Fiscal year utility**
- New `apps/core/fiscal_year.py` — shared, importable by any app
- `fiscal_year_start(today)` → returns July 1 of the current fiscal year (July of current year if month >= 7, else July of prior year)
- `months_remaining(today)` → integer months from today to June 30 end of fiscal year, minimum 1
- `fiscal_year_end(today)` → returns June 30 of the current fiscal year end

### Claude's Discretion
- Whether to use SQL aggregation (like the existing `_monthly_equivalent_aggregate`) or Python iteration for the goal calculation — SQL preferred for performance consistency
- Exact URL path for the goals endpoint (`/api/goals/me/` vs `/api/users/goal/`)
- Whether GoalJournalSelection PATCH uses replace-all or add/remove semantics at the serializer level

### Deferred Ideas (OUT OF SCOPE)
- Frontend Settings page removal of Fundraising Goal card — Phase 50
- Goal history / trend chart — Phase backlog (GOAL-EX-01)
- Per-journal goal breakdown — Phase backlog (GOAL-EX-02)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FISC-01 | Fiscal year starts July 1 and resets annually — shared utility used by Goal page and dashboard calculations | `apps/core/fiscal_year.py` new module; July-based fiscal year is straightforward date arithmetic |
| FISC-02 | Months remaining in fiscal year calculated dynamically (minimum 1 to avoid division by zero) | `months_remaining(today)` function with `max(1, calculated)` guard |
| GOAL-02 | Missionary can set and save their monthly support goal (in dollars) | `monthly_support_goal_cents` on User + `UserUpdateSerializer` writable field; field stored cents, API accepts/returns cents |
| GOAL-03 | Missionary can select which journals count toward their goal (multi-select, persisted) | `GoalJournalSelection` model; PATCH `/api/goals/me/` with replace-all journal_ids list |
| GOAL-04 | Goal page displays effective monthly support calculated from selected journals | `get_goal_progress(user)` in `goal_services.py`; recurring SQL aggregate + one-time fiscal year sum ÷ months_remaining |
| GOAL-11 | Monthly support goal field removed from Settings page (or replaced with link to Goal page) | Phase 49 only updates the API layer — `monthly_goal` field removed from `UserUpdateSerializer`/`CurrentUserSerializer`; frontend Settings UI change is Phase 50 |
</phase_requirements>

---

## Summary

Phase 49 is a pure backend phase: rename the existing `User.monthly_goal` field, add two new User fields (`monthly_support_goal_cents`, `goal_weeks`), introduce the `GoalJournalSelection` through-model, build a fiscal year utility, write a new goal service, and expose a dedicated `GET/PATCH /api/goals/me/` endpoint.

The existing codebase gives us almost everything we need. The `_monthly_equivalent_aggregate()` helper in `apps/dashboard/services.py` is directly reusable (or extractable) for the goal calculation. `JournalContact` already provides the journal→contact join, `Gift` and `RecurringGift` both use cents-based `amount_cents` + `PositiveBigIntegerField` — the new User field must follow the same pattern. The migration sequence is: schema migration (rename + add fields + new model) then data migration (multiply old `monthly_goal` × 100 → `monthly_support_goal_cents`).

The key coordination risk is the `monthly_goal` rename — it is referenced in four locations outside the model itself: `apps/dashboard/services.py` (three functions), `apps/users/serializers.py` (four serializers), `apps/users/admin.py` (fieldsets), and `apps/users/tests/factories.py`. All must be updated atomically with the migration.

**Primary recommendation:** Write migration 0007 (schema + data combined), update all `monthly_goal` references in one PR, then add new service/view/URL as independent additions.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django ORM | 4.x (project) | Model definitions, migrations, querysets | Already in use project-wide |
| Django REST Framework | 3.x (project) | Serializers, APIView, permissions | Already in use project-wide |
| `dateutil.relativedelta` | project | Month arithmetic for fiscal year | Already imported in `dashboard/services.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `decimal.Decimal` | stdlib | Cents arithmetic without float precision loss | All money math in service layer |
| `datetime.date` | stdlib | Fiscal year start/end date construction | In `apps/core/fiscal_year.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Two separate migrations (schema + data) | One combined migration | CONTEXT.md specifies two migrations; combined is simpler but mixing schema + RunPython in one migration is acceptable Django practice |
| Reuse `_monthly_equivalent_aggregate` in-place | Extract to `apps/core/` shared helper | In-place reuse via import is simpler; extraction is premature — CONTEXT.md says "reuse or factor out" |

**Installation:** No new packages required. All dependencies are already installed.

---

## Architecture Patterns

### Recommended File Structure (new/modified)
```
apps/core/
└── fiscal_year.py          # NEW: fiscal_year_start(), fiscal_year_end(), months_remaining()

apps/users/
├── models.py               # MODIFY: rename monthly_goal → monthly_support_goal_cents,
│                           #         add goal_weeks, add GoalJournalSelection model
├── serializers.py          # MODIFY: update all 4 serializers; add new GoalSerializer
├── views.py                # KEEP: no changes needed
├── views_goals.py          # NEW: GoalView (GET/PATCH /api/goals/me/)
├── goal_services.py        # NEW: get_goal_progress(user)
├── urls.py                 # MODIFY: add path('goals/me/', ...)
├── admin.py                # MODIFY: rename monthly_goal → monthly_support_goal_cents in fieldsets
└── migrations/
    ├── 0007_goal_fields_schema.py   # Schema: rename + add fields + GoalJournalSelection
    └── 0008_goal_fields_data.py     # Data: multiply monthly_goal → monthly_support_goal_cents

apps/dashboard/
└── services.py             # MODIFY: 3 references to user.monthly_goal → new field
```

### Pattern 1: Cents Field with Dollars Property
All money fields in this codebase use `PositiveBigIntegerField` for storage and expose a read-only `amount_dollars` Decimal property for display. Apply identically to `monthly_support_goal_cents`:

```python
# apps/users/models.py — follow Gift/RecurringGift pattern exactly
monthly_support_goal_cents = models.PositiveBigIntegerField(
    'monthly support goal (cents)',
    default=0,
    help_text='Monthly support goal in cents (e.g., 350000 = $3,500.00)'
)

@property
def monthly_support_goal_dollars(self):
    """Return goal as Decimal dollars for display/calculations."""
    return Decimal(self.monthly_support_goal_cents) / Decimal(100)
```

### Pattern 2: Migration Sequence (Schema then Data)
The project has used `RunPython` for data migrations (see `0006_m2m_supervisors.py`). Two-migration approach:

```python
# 0007_goal_fields_schema.py
class Migration(migrations.Migration):
    dependencies = [('users', '0006_m2m_supervisors')]
    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='monthly_goal',
            new_name='monthly_support_goal_cents',
        ),
        migrations.AlterField(
            model_name='user',
            name='monthly_support_goal_cents',
            field=models.PositiveBigIntegerField(default=0, ...),
        ),
        migrations.AddField(
            model_name='user',
            name='goal_weeks',
            field=models.PositiveIntegerField(default=52, ...),
        ),
        migrations.CreateModel(
            name='GoalJournalSelection',
            fields=[...],
        ),
    ]
```

```python
# 0008_goal_fields_data.py — data migration only
def convert_monthly_goal_to_cents(apps, schema_editor):
    User = apps.get_model('users', 'User')
    for user in User.objects.all():
        # monthly_support_goal_cents currently holds old DecimalField value
        # after RenameField; value is a Decimal like 3500.00
        old_value = user.monthly_support_goal_cents or 0
        user.monthly_support_goal_cents = round(float(old_value) * 100)
        user.save(update_fields=['monthly_support_goal_cents'])

class Migration(migrations.Migration):
    dependencies = [('users', '0007_goal_fields_schema')]
    operations = [
        migrations.RunPython(
            convert_monthly_goal_to_cents,
            migrations.RunPython.noop
        ),
    ]
```

**Critical note on RenameField:** After `RenameField`, the column in the DB still holds the old Decimal data — the data migration reads it as the old type and converts. Django's `RenameField` + `AlterField` in the same migration may cause issues with some backends. Safer approach: `RenameField` in migration 0007 (leaves DecimalField type temporarily), then `AlterField` to PositiveBigIntegerField in migration 0008 after data conversion. See Pitfall 1 for details.

### Pattern 3: GoalJournalSelection Model
Follows `JournalContact` exactly — explicit through-model instead of bare M2M, `TimeStampedModel` base, `unique_together`:

```python
# apps/users/models.py
class GoalJournalSelection(TimeStampedModel):
    """Journals selected by a user to count toward their support goal."""
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='goal_journal_selections',
        db_index=True,
    )
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.CASCADE,
        related_name='goal_selections',
        db_index=True,
    )

    class Meta:
        db_table = 'goal_journal_selections'
        verbose_name = 'goal journal selection'
        verbose_name_plural = 'goal journal selections'
        unique_together = [['user', 'journal']]
        indexes = [
            models.Index(fields=['user', 'journal']),
        ]
```

### Pattern 4: Fiscal Year Utility
Pure functions, no Django dependency, easily testable:

```python
# apps/core/fiscal_year.py
from datetime import date

FISCAL_YEAR_START_MONTH = 7  # July


def fiscal_year_start(today: date) -> date:
    """Return July 1 of the current fiscal year."""
    if today.month >= FISCAL_YEAR_START_MONTH:
        return date(today.year, FISCAL_YEAR_START_MONTH, 1)
    return date(today.year - 1, FISCAL_YEAR_START_MONTH, 1)


def fiscal_year_end(today: date) -> date:
    """Return June 30 of the current fiscal year end."""
    fy_start = fiscal_year_start(today)
    return date(fy_start.year + 1, 6, 30)


def months_remaining(today: date) -> int:
    """Return months from today to June 30 of the current FY, minimum 1."""
    fy_end = fiscal_year_end(today)
    # Count months: if today is June 15 it's still 1 month remaining
    months = (fy_end.year - today.year) * 12 + (fy_end.month - today.month)
    return max(1, months)
```

### Pattern 5: Goal Service (SQL Aggregation)
Mirrors `get_support_progress()` pattern. Use SQL aggregation (`_monthly_equivalent_aggregate`) for recurring gifts; use `aggregate(Sum(...))` for one-time gifts:

```python
# apps/users/goal_services.py
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.core.fiscal_year import fiscal_year_start, months_remaining
from apps.gifts.models import Gift, RecurringGift, RecurringGiftStatus
from apps.journals.models import JournalContact
from apps.users.models import GoalJournalSelection


def get_goal_progress(user):
    """
    Calculate effective monthly support from user's selected journals.
    Returns dict with goal_cents, goal_weeks, selected_journal_ids,
    effective_monthly_support (dollars), recurring_monthly, one_time_monthly.
    """
    today = date.today()

    # Selected journals for this user
    selected_journal_ids = list(
        GoalJournalSelection.objects.filter(user=user)
        .values_list('journal_id', flat=True)
    )

    if not selected_journal_ids:
        return {
            'monthly_support_goal_cents': user.monthly_support_goal_cents,
            'goal_weeks': user.goal_weeks,
            'selected_journal_ids': [],
            'effective_monthly_support': 0.0,
            'recurring_monthly': 0.0,
            'one_time_monthly': 0.0,
        }

    # Contact IDs in selected journals (scoped to this user's journals via owner)
    contact_ids = list(
        JournalContact.objects.filter(
            journal__in=selected_journal_ids,
            journal__owner=user,
        ).values_list('contact_id', flat=True)
    )

    # 1. Recurring: active recurring gifts from journal contacts
    from apps.dashboard.services import _monthly_equivalent_aggregate
    active_recurring = RecurringGift.objects.filter(
        donor_contact_id__in=contact_ids,
        status=RecurringGiftStatus.ACTIVE,
    )
    recurring_monthly = float(_monthly_equivalent_aggregate(active_recurring))

    # 2. One-time: fiscal year gifts / months_remaining
    fy_start = fiscal_year_start(today)
    fy_gifts_cents = Gift.objects.filter(
        donor_contact_id__in=contact_ids,
        gift_date__gte=fy_start,
        gift_date__lte=today,
    ).aggregate(total=Sum('amount_cents'))['total'] or 0

    fy_gifts_dollars = float(Decimal(fy_gifts_cents) / Decimal(100))
    mo_remaining = months_remaining(today)
    one_time_monthly = fy_gifts_dollars / mo_remaining

    effective = recurring_monthly + one_time_monthly

    return {
        'monthly_support_goal_cents': user.monthly_support_goal_cents,
        'goal_weeks': user.goal_weeks,
        'selected_journal_ids': selected_journal_ids,
        'effective_monthly_support': round(effective, 2),
        'recurring_monthly': round(recurring_monthly, 2),
        'one_time_monthly': round(one_time_monthly, 2),
    }
```

### Pattern 6: Goal API View (GET/PATCH)
Follows `CurrentUserView` structure — `APIView`, `IsAuthenticated`, always scoped to `request.user`:

```python
# apps/users/views_goals.py
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.goal_services import get_goal_progress
from apps.users.models import GoalJournalSelection
from apps.journals.models import Journal


class GoalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = get_goal_progress(request.user)
        return Response(data)

    def patch(self, request):
        user = request.user
        data = request.data

        if 'monthly_support_goal_cents' in data:
            user.monthly_support_goal_cents = data['monthly_support_goal_cents']
        if 'goal_weeks' in data:
            user.goal_weeks = data['goal_weeks']
        user.save(update_fields=['monthly_support_goal_cents', 'goal_weeks', 'updated_at'])

        if 'journal_ids' in data:
            # Replace-all semantics
            journal_ids = data['journal_ids']
            valid_journals = Journal.objects.filter(id__in=journal_ids, owner=user)
            GoalJournalSelection.objects.filter(user=user).delete()
            GoalJournalSelection.objects.bulk_create([
                GoalJournalSelection(user=user, journal=j)
                for j in valid_journals
            ])

        return Response(get_goal_progress(user))
```

### URL Registration
Register under `/api/v1/goals/me/` by adding a new path entry to `config/api_urls.py`:

```python
path('goals/', include('apps.users.urls_goals')),
```

And create `apps/users/urls_goals.py`:

```python
from django.urls import path
from apps.users.views_goals import GoalView

urlpatterns = [
    path('me/', GoalView.as_view(), name='goal-me'),
]
```

### Anti-Patterns to Avoid
- **Float for money:** Never `float(user.monthly_support_goal_cents)` — use `Decimal` division for all dollar display math.
- **Python loop for recurring gift aggregation:** The existing `_monthly_equivalent_aggregate()` helper was built specifically to avoid O(N) Python iteration. The goal service must reuse it.
- **Storing goal_weeks on GoalJournalSelection:** It belongs on User (applies to the whole goal, not per-journal).
- **Deleting journals before validating:** In PATCH, validate journal IDs exist and belong to the user before deleting existing selections.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Monthly recurring gift aggregation | Python loop summing `rg.monthly_equivalent` | `_monthly_equivalent_aggregate()` from `apps/dashboard/services.py` | Already proven SQL CASE/WHEN approach; O(1) memory |
| Cents-to-dollars conversion | Custom Decimal math | `Decimal(cents) / Decimal(100)` pattern already used in `Gift.amount_dollars` | Consistent precision; avoid float |
| Fiscal month counting | Manual date diff logic | `dateutil.relativedelta` already in project | Handles month boundary edge cases |

**Key insight:** This phase has almost zero new algorithmic surface area. The recurring gift monthly calculation is already solved by `_monthly_equivalent_aggregate()`. The main work is data model plumbing + wiring.

---

## Common Pitfalls

### Pitfall 1: RenameField + AlterField Type Change in Same Migration
**What goes wrong:** `RenameField` + `AlterField` changing type (Decimal → PositiveBigInteger) in a single migration will try to cast old Decimal data as integer in the DB — PostgreSQL will error because 3500.00 is not a valid integer before the data conversion happens.

**Why it happens:** Django migration operations execute in order within the migration, but `AlterField` alters the column type at the DB level immediately. Old Decimal values like `3500.00` cannot be cast to integer without first converting them.

**How to avoid:** Use a three-step approach across two migrations:
1. Migration 0007: `RenameField` only (column still holds Decimal data; new name, same type)
2. Migration 0008: `RunPython` to multiply values × 100 → store result, then `AlterField` to `PositiveBigIntegerField`

The data migration must run before the `AlterField`. Keep them in the same migration file with `RunPython` before `AlterField`.

**Warning signs:** `django.db.utils.DataError: invalid input syntax for type integer` during `migrate`.

### Pitfall 2: `monthly_goal` References Not Fully Updated
**What goes wrong:** After renaming the model field, code that still references `user.monthly_goal` raises `AttributeError` at runtime — often only discovered when hitting specific API paths.

**Why it happens:** `monthly_goal` appears in four files outside `models.py`: three places in `apps/dashboard/services.py`, four serializer classes in `apps/users/serializers.py`, admin fieldsets in `apps/users/admin.py`, and `UserFactory.monthly_goal` in tests.

**How to avoid:** Run a global search for `monthly_goal` after all changes. The complete reference list:
- `apps/dashboard/services.py` lines ~173, ~232, ~285 (`float(user.monthly_goal)` and `user.monthly_goal`)
- `apps/users/serializers.py`: `UserSerializer.fields`, `UserCreateSerializer.fields`, `UserUpdateSerializer.fields`, `UserAdminUpdateSerializer.fields`, `CurrentUserSerializer.fields`
- `apps/users/admin.py`: `fieldsets` Role & Permissions entry
- `apps/users/tests/factories.py`: `UserFactory.monthly_goal`

**Warning signs:** Tests pass but manual API call to `/api/dashboard/` raises 500.

### Pitfall 3: Journal Scoping in Goal Calculation
**What goes wrong:** `GoalJournalSelection` stores journal FKs but the goal service queries all contacts in those journals without verifying journal ownership. A user could theoretically have a selection pointing to another user's journal (if data is corrupted), causing cross-user data leakage.

**Why it happens:** The FK from `GoalJournalSelection.journal` is not scoped to the user at the model level.

**How to avoid:** Always add `journal__owner=user` filter when querying `JournalContact` in `goal_services.py`. Also validate `journal.owner == user` in the PATCH view before creating selections.

### Pitfall 4: `months_remaining` Boundary at Fiscal Year End
**What goes wrong:** In June (the last month of the fiscal year), naive month subtraction returns 0, causing division by zero in one-time gift calculation.

**Why it happens:** If `today = June 15`, then `fy_end = June 30`, `(fy_end.month - today.month) = 0`.

**How to avoid:** The `months_remaining()` function must apply `max(1, calculated)`. This is already in the CONTEXT.md spec — make sure the implementation includes this guard. Test specifically with a `today` of June 1 and June 30.

### Pitfall 5: `_monthly_equivalent_aggregate` Import Coupling
**What goes wrong:** Importing `_monthly_equivalent_aggregate` from `apps.dashboard.services` in `apps.users.goal_services` creates a cross-app import from `users` → `dashboard`. This is acceptable but unusual (normally `users` is a dependency of `dashboard`, not the reverse).

**How to avoid:** Two options:
1. Accept the import (simplest — it's one private function, no circular dependency exists)
2. Move `_monthly_equivalent_aggregate` and `FREQUENCY_MULTIPLIERS` to `apps/core/gift_utils.py` and import from there in both `dashboard/services.py` and `users/goal_services.py`

**Recommendation (Claude's discretion):** Move to `apps/core/gift_utils.py`. It's a shared utility, not dashboard-specific. This avoids cross-app imports in the wrong direction and is cleaner long-term.

---

## Code Examples

Verified patterns from existing codebase:

### Existing cents-based field pattern (Gift model)
```python
# apps/gifts/models.py — confirmed pattern to follow for monthly_support_goal_cents
amount_cents = models.PositiveBigIntegerField(
    'amount (cents)',
    help_text='Gift amount in cents (e.g., 10000 = $100.00)'
)

@property
def amount_dollars(self):
    """Return amount as Decimal dollars for display."""
    return Decimal(self.amount_cents) / Decimal(100)
```

### Existing SQL aggregation pattern (dashboard services)
```python
# apps/dashboard/services.py — reuse _monthly_equivalent_aggregate() as-is
result = queryset.annotate(
    freq_multiplier=Case(
        *[When(frequency=freq, then=Value(mult)) for freq, mult in FREQUENCY_MULTIPLIERS.items()],
        default=Value(Decimal('1')),
        output_field=DecimalField(max_digits=20, decimal_places=10),
    ),
    monthly_cents=F('amount_cents') * F('freq_multiplier'),
).aggregate(total=Sum('monthly_cents'))
total_cents = result['total'] or Decimal('0')
return round(total_cents / Decimal('100'), 2)
```

### Existing through-model pattern (JournalContact)
```python
# apps/journals/models.py — GoalJournalSelection follows this exactly
class JournalContact(TimeStampedModel):
    journal = models.ForeignKey('Journal', on_delete=models.CASCADE, related_name='journal_contacts', db_index=True)
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE, related_name='journal_memberships', db_index=True)

    class Meta:
        db_table = 'journal_contacts'
        unique_together = [['journal', 'contact']]
```

### Existing data migration pattern (0006_m2m_supervisors.py)
```python
def copy_fk_to_m2m(apps, schema_editor):
    User = apps.get_model('users', 'User')
    for user in User.objects.filter(supervisor__isnull=False):
        user.supervisors.add(user.supervisor_id)

operations = [
    migrations.RunPython(copy_fk_to_m2m, migrations.RunPython.noop),
]
```

### CurrentUserSerializer field list (must update)
```python
# apps/users/serializers.py line ~174 — remove 'monthly_goal', add new fields
fields = [
    'id', 'email', 'first_name', 'last_name', 'full_name',
    'phone', 'role', 'monthly_goal',  # <-- RENAME TO monthly_support_goal_cents
    'email_notifications', 'date_joined', 'last_login_at',
    'contact_count', 'active_pledge_count', 'dashboard_layout', 'supervised_users'
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `DecimalField` for money (dollars) | `PositiveBigIntegerField` (cents) | Earlier phases | Avoids float precision loss; all new money fields use cents |
| Custom `monthly_equivalent` Python property per model | SQL CASE/WHEN aggregation via `_monthly_equivalent_aggregate()` | dashboard service refactor | O(1) DB memory instead of O(N) Python iteration |

---

## Open Questions

1. **`_monthly_equivalent_aggregate` extraction location**
   - What we know: Function currently lives in `apps/dashboard/services.py`; goal_services.py needs it
   - What's unclear: Whether to import cross-app or move to `apps/core/`
   - Recommendation: Move to `apps/core/gift_utils.py` during this phase; update both import sites

2. **URL namespace: `/api/v1/goals/me/` vs `/api/v1/users/goal/`**
   - What we know: CONTEXT.md lists both as options; `config/api_urls.py` currently has no `goals/` prefix
   - What's unclear: Whether Phase 50 frontend will need the `/goals/` prefix for REST clarity
   - Recommendation: Use `path('goals/', include('apps.users.urls_goals'))` in `config/api_urls.py` → endpoint becomes `/api/v1/goals/me/`. Cleaner resource separation from `/api/v1/users/`.

3. **Admin display of `monthly_support_goal_cents`**
   - What we know: Admin fieldset currently shows `monthly_goal` as raw Decimal
   - What's unclear: Whether admin should display cents (confusing) or dollars
   - Recommendation: Add `readonly_fields` with a `monthly_support_goal_dollars` display method, or simply show the cents field with clear label. Low-priority cosmetic concern.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest apps/core/tests/ apps/users/tests/ apps/dashboard/tests/ -x --no-cov` |
| Full suite command | `pytest --cov=apps --cov-fail-under=80` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FISC-01 | `fiscal_year_start()` returns July 1 of correct year | unit | `pytest apps/core/tests/test_fiscal_year.py -x --no-cov` | ❌ Wave 0 |
| FISC-02 | `months_remaining()` returns minimum 1, correct values | unit | `pytest apps/core/tests/test_fiscal_year.py -x --no-cov` | ❌ Wave 0 |
| GOAL-02 | `PATCH /api/v1/goals/me/` saves goal cents and weeks | integration | `pytest apps/users/tests/test_views_goals.py -x --no-cov` | ❌ Wave 0 |
| GOAL-03 | `PATCH /api/v1/goals/me/` persists journal selections (replace-all) | integration | `pytest apps/users/tests/test_views_goals.py -x --no-cov` | ❌ Wave 0 |
| GOAL-04 | `get_goal_progress()` computes recurring + one-time monthly correctly | unit | `pytest apps/users/tests/test_goal_services.py -x --no-cov` | ❌ Wave 0 |
| GOAL-11 | `monthly_goal` removed from `UserUpdateSerializer` and `CurrentUserSerializer` | unit | `pytest apps/users/tests/test_views.py -x --no-cov` | ✅ (existing, extend) |

### Sampling Rate
- **Per task commit:** `pytest apps/core/tests/ apps/users/tests/ apps/dashboard/tests/ -x --no-cov`
- **Per wave merge:** `pytest --cov=apps --cov-fail-under=80`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/core/tests/test_fiscal_year.py` — covers FISC-01, FISC-02 (boundary cases: July, June, January)
- [ ] `apps/users/tests/test_goal_services.py` — covers GOAL-04 (mock journals, contacts, gifts)
- [ ] `apps/users/tests/test_views_goals.py` — covers GOAL-02, GOAL-03 (API integration tests)
- [ ] Update `apps/users/tests/factories.py` — rename `monthly_goal` → `monthly_support_goal_cents`, add `goal_weeks`

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `apps/users/models.py` — confirmed `monthly_goal` field shape and all references
- Direct code inspection of `apps/dashboard/services.py` — confirmed `_monthly_equivalent_aggregate()` signature and all `user.monthly_goal` references
- Direct code inspection of `apps/users/serializers.py` — confirmed all four serializers with `monthly_goal` fields
- Direct code inspection of `apps/journals/models.py` — confirmed `JournalContact` pattern for `GoalJournalSelection`
- Direct code inspection of `apps/gifts/models.py` — confirmed cents-based field pattern
- Direct code inspection of `apps/core/models.py` — confirmed `TimeStampedModel` base class
- Direct code inspection of `config/api_urls.py` — confirmed URL structure; no existing `goals/` prefix
- Direct code inspection of `apps/users/admin.py` — confirmed `monthly_goal` in fieldsets
- Direct code inspection of `apps/users/migrations/0006_m2m_supervisors.py` — confirmed `RunPython` data migration pattern
- Direct code inspection of `conftest.py` + `pyproject.toml` — confirmed pytest framework and test fixture patterns

### Secondary (MEDIUM confidence)
- Migration type-change safety: Based on Django ORM behavior with `RenameField` + `AlterField` on PostgreSQL — standard Django migration documentation guidance

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies
- Architecture patterns: HIGH — all patterns confirmed from existing codebase code inspection
- Migration approach: HIGH — confirmed from existing migration `0006_m2m_supervisors.py`; type-change pitfall is well-documented Django behavior
- Pitfalls: HIGH — all derived from direct code inspection of actual reference sites

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable Django project; no fast-moving dependencies)
