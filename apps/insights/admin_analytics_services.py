"""
Service functions for the /admin/analytics redesign (Issue #49).

Five leadership-focused services:
  - get_fiscal_year_pace: hero pace metric
  - get_missionaries_behind_goal: coaching accountability list
  - get_pipeline_funnel_with_conversion: stage-to-stage conversion funnel
  - get_weekly_engagement: active + on-pace missionaries over N weeks
  - get_fiscal_year_donations: monthly FYTD totals vs prior year

Scoping note: these endpoints are admin-only. When `request.view_as_user` is
set, data is scoped to that user via get_visible_user_ids(); otherwise the
services compute org-wide aggregates (matching existing admin analytics
endpoints such as get_dashboard_overview, which intentionally bypass user
scoping for cross-tenant views).
"""
from calendar import monthrange
from datetime import date, timedelta

from django.db.models import Case, IntegerField, Max, Sum, Value, When
from django.db.models.functions import TruncMonth, TruncWeek

from apps.core.fiscal_year import (
    get_current_fiscal_year_bounds,
    get_prior_fiscal_year_bounds,
    months_elapsed_in_fiscal_year,
)
from apps.core.permissions import get_visible_user_ids
from apps.gifts.models import Gift
from apps.imports.models import ImportBatch, ImportBatchStatus, ImportBatchType
from apps.journals.models import JournalStageEvent, PipelineStage
from apps.users.models import User, UserRole

# --- Pipeline stage ordering ---------------------------------------------------

STAGE_ORDER = [
    PipelineStage.CONTACT.value,
    PipelineStage.SCHEDULED.value,
    PipelineStage.MEET.value,
    PipelineStage.CLOSE.value,
    PipelineStage.DECISION.value,
    PipelineStage.THANK.value,
    PipelineStage.NEXT_STEPS.value,
]
STAGE_LABELS = {s.value: s.label for s in PipelineStage}

# Import types that represent gift data (used for "last import at" timestamp).
GIFT_IMPORT_TYPES = [
    ImportBatchType.RE_GIFT,
    ImportBatchType.RE_RECURRING_GIFT,
    ImportBatchType.GENERIC_DONATIONS,
    ImportBatchType.SPO_GIFT,
]


def _admin_scope_owner_ids(request):
    """Return a set of owner user IDs to filter by, or None for no filter.

    Admin analytics default to org-wide aggregates (no filter). When View As
    is active, we scope to the target user by delegating to
    get_visible_user_ids(), which returns {view_as_user.id}.
    """
    if getattr(request, "view_as_user", None) is not None:
        return get_visible_user_ids(request.user, request=request)
    return None


def _filter_gifts_by_owner(queryset, owner_ids):
    if owner_ids is None:
        return queryset
    return queryset.filter(donor_contact__owner_id__in=owner_ids)


def _filter_users_by_scope(queryset, owner_ids):
    if owner_ids is None:
        return queryset
    return queryset.filter(id__in=owner_ids)


def _filter_stage_events_by_owner(queryset, owner_ids):
    if owner_ids is None:
        return queryset
    return queryset.filter(journal_contact__journal__owner_id__in=owner_ids)


def _active_missionaries(owner_ids):
    """Return the base queryset of active missionary users in scope."""
    qs = User.objects.filter(role=UserRole.MISSIONARY, is_active=True)
    return _filter_users_by_scope(qs, owner_ids)


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _last_gift_import_at(owner_ids=None):
    """Return ISO timestamp of the most recent completed gift-related import,
    or None.

    When `owner_ids` is None (admin viewing org-wide aggregates), returns the
    most recent import across the org. When `owner_ids` is set (admin in
    View-As mode inspecting a single missionary), scopes to imports the viewed
    user uploaded so the timestamp on the FY Pace tile matches the data being
    shown.
    """
    qs = ImportBatch.objects.filter(
        status=ImportBatchStatus.COMPLETED,
        import_type__in=GIFT_IMPORT_TYPES,
    )
    if owner_ids is not None:
        qs = qs.filter(uploaded_by_id__in=owner_ids)
    last = qs.order_by("-created_at").values_list("created_at", flat=True).first()
    return last.isoformat() if last else None


# --- 1. Fiscal year pace --------------------------------------------------------


def get_fiscal_year_pace(request):
    """Hero tile: raised vs annual goal with pace %, YoY, and last-import stamp."""
    today = date.today()
    fy_start, fy_end = get_current_fiscal_year_bounds(today)
    prior_start, prior_end = get_prior_fiscal_year_bounds(today)
    owner_ids = _admin_scope_owner_ids(request)

    # Current FY gifts up to today
    current_qs = Gift.objects.filter(gift_date__gte=fy_start, gift_date__lte=today)
    current_qs = _filter_gifts_by_owner(current_qs, owner_ids)
    raised_cents = current_qs.aggregate(total=Sum("amount_cents"))["total"] or 0

    # Prior FY gifts through same day-of-year (one year ago)
    prior_today = (
        today.replace(year=today.year - 1)
        if not (today.month == 2 and today.day == 29)
        else date(today.year - 1, 2, 28)
    )
    prior_qs = Gift.objects.filter(gift_date__gte=prior_start, gift_date__lte=prior_today)
    prior_qs = _filter_gifts_by_owner(prior_qs, owner_ids)
    prior_year_raised_cents = prior_qs.aggregate(total=Sum("amount_cents"))["total"] or 0

    # Annual goal: prefer the org-wide setting if the admin has set one;
    # otherwise fall back to summing each active missionary's monthly goal * 12.
    # The View-As path (owner_ids != None) keeps the missionary-sum fallback so
    # admins inspecting a single user see that user's own goal, not the org's.
    from apps.core.models import OrgSettings

    org_annual_goal_cents = (
        OrgSettings.objects.values_list("annual_goal_cents", flat=True).first() or 0
    )

    if owner_ids is None and org_annual_goal_cents > 0:
        annual_goal_cents = int(org_annual_goal_cents)
        annual_goal_source = "org_setting"
    else:
        goal_qs = _active_missionaries(owner_ids).filter(monthly_support_goal_cents__gt=0)
        monthly_goal_sum = (
            goal_qs.aggregate(total=Sum("monthly_support_goal_cents"))["total"] or 0
        )
        annual_goal_cents = int(monthly_goal_sum * 12)
        annual_goal_source = "missionary_sum"

    months_elapsed = months_elapsed_in_fiscal_year(today)
    expected_by_today_cents = (
        int(annual_goal_cents * months_elapsed / 12) if annual_goal_cents else 0
    )

    if expected_by_today_cents > 0:
        raw_pace = raised_cents / expected_by_today_cents * 100
        pace_percentage = round(_clamp(raw_pace, 0, 150), 1)
    else:
        pace_percentage = 0.0

    if prior_year_raised_cents > 0:
        yoy_delta_percentage = round(
            (raised_cents - prior_year_raised_cents) / prior_year_raised_cents * 100, 1
        )
    else:
        yoy_delta_percentage = None

    return {
        "fy_start": fy_start.isoformat(),
        "fy_end": fy_end.isoformat(),
        "raised_cents": int(raised_cents),
        "annual_goal_cents": int(annual_goal_cents),
        "annual_goal_source": annual_goal_source,
        "expected_by_today_cents": int(expected_by_today_cents),
        "pace_percentage": pace_percentage,
        "prior_year_raised_cents": int(prior_year_raised_cents),
        "yoy_delta_percentage": yoy_delta_percentage,
        "last_import_at": _last_gift_import_at(owner_ids),
    }


# --- 2. Missionaries behind goal -----------------------------------------------


def get_missionaries_behind_goal(request, limit=10):
    """Ranked list (ascending pace %) of missionaries behind their monthly goal."""
    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = monthrange(today.year, today.month)[1]
    day_of_month = today.day
    owner_ids = _admin_scope_owner_ids(request)

    with_goal = _active_missionaries(owner_ids).filter(monthly_support_goal_cents__gt=0)
    without_goal_count = (
        _active_missionaries(owner_ids).filter(monthly_support_goal_cents=0).count()
    )
    total_missionaries = _active_missionaries(owner_ids).count()

    user_rows = list(
        with_goal.values("id", "first_name", "last_name", "email", "monthly_support_goal_cents")
    )
    user_ids = [row["id"] for row in user_rows]

    # Single aggregate: gifts this month grouped by owner. `user_ids` is
    # already scoped by `owner_ids` via `with_goal`, so no separate scope
    # filter is needed here.
    month_totals = (
        Gift.objects.filter(
            gift_date__gte=month_start,
            gift_date__lte=today,
            donor_contact__owner_id__in=user_ids,
        )
        .values("donor_contact__owner_id")
        .annotate(total=Sum("amount_cents"))
    )
    owner_to_total = {
        row["donor_contact__owner_id"]: int(row["total"] or 0) for row in month_totals
    }

    # Expected pace at this point in the month (prorated linearly).
    ratio = day_of_month / days_in_month

    rows = []
    for user in user_rows:
        goal = int(user["monthly_support_goal_cents"])
        raised = owner_to_total.get(user["id"], 0)
        expected = goal * ratio
        if expected > 0:
            pace_pct = round(_clamp(raised / expected * 100, 0, 150), 1)
        else:
            pace_pct = 0.0
        rows.append(
            {
                "user_id": str(user["id"]),
                "name": f'{user["first_name"]} {user["last_name"]}'.strip(),
                "email": user["email"],
                "monthly_goal_cents": goal,
                "this_month_raised_cents": raised,
                "pace_percentage": pace_pct,
            }
        )

    rows.sort(key=lambda r: r["pace_percentage"])
    rows = rows[:limit]

    return {
        "missionaries": rows,
        "total_excluded_no_goal": int(without_goal_count),
        "total_missionaries": int(total_missionaries),
        "as_of_date": today.isoformat(),
    }


# --- 3. Pipeline funnel with stage-to-stage conversion -------------------------


def get_pipeline_funnel_with_conversion(request):
    """Cumulative-reach funnel: for each stage, count journal contacts whose
    deepest stage reached is >= that stage. Conversion = count[N] / count[N-1].
    """
    owner_ids = _admin_scope_owner_ids(request)
    # Index each stage event via Case/When then take the max index per journal_contact.
    stage_cases = [
        When(stage=stage_value, then=Value(idx)) for idx, stage_value in enumerate(STAGE_ORDER)
    ]
    events_qs = JournalStageEvent.objects.all()
    events_qs = _filter_stage_events_by_owner(events_qs, owner_ids)
    max_indexes = events_qs.values("journal_contact_id").annotate(
        max_idx=Max(Case(*stage_cases, default=Value(-1), output_field=IntegerField()))
    )

    # Build count_at_or_past[N] = # journal_contacts whose max_idx >= N.
    counts_at_or_past = [0] * len(STAGE_ORDER)
    total_in_pipeline = 0
    for row in max_indexes:
        idx = row["max_idx"]
        if idx is None or idx < 0:
            continue
        total_in_pipeline += 1
        for n in range(idx + 1):
            counts_at_or_past[n] += 1

    stages = []
    weakest = None
    for i, stage_value in enumerate(STAGE_ORDER):
        count = counts_at_or_past[i]
        if i == 0:
            conversion = None
        else:
            prior = counts_at_or_past[i - 1]
            conversion = round((count / prior * 100), 1) if prior > 0 else None
        stages.append(
            {
                "stage": stage_value,
                "label": STAGE_LABELS[stage_value],
                "count_at_or_past": count,
                "conversion_from_prior_percentage": conversion,
                "is_weakest_transition": False,
            }
        )
        if conversion is not None and (weakest is None or conversion < weakest["rate"]):
            weakest = {
                "from": STAGE_ORDER[i - 1],
                "to": stage_value,
                "rate": conversion,
                "index": i,
            }

    if weakest is not None:
        stages[weakest["index"]]["is_weakest_transition"] = True

    return {
        "stages": stages,
        "total_in_pipeline": int(total_in_pipeline),
        "weakest_transition": (
            {
                "from": weakest["from"],
                "to": weakest["to"],
                "rate": weakest["rate"],
            }
            if weakest is not None
            else None
        ),
    }


# --- 4. Weekly engagement ------------------------------------------------------


def _week_start(d):
    """Return Monday (ISO) of the week containing d."""
    return d - timedelta(days=d.weekday())


def get_weekly_engagement(request, weeks=12):
    """Last N weeks: active-missionary count + on-pace-missionary count.

    On-pace interpretation (month-to-date): a missionary is on-pace in week W
    if their MTD raised (through the week-end date that is <= today) is at
    least monthly_goal * day_of_month(week_end) / days_in_month(week_end).
    """
    today = date.today()
    owner_ids = _admin_scope_owner_ids(request)

    # Build the list of week starts (Monday) for the last `weeks` weeks.
    current_week_start = _week_start(today)
    week_starts = [current_week_start - timedelta(weeks=weeks - 1 - i) for i in range(weeks)]

    # Active missionaries per week: distinct stage-event-triggering users.
    active_qs = JournalStageEvent.objects.filter(
        created_at__date__gte=week_starts[0],
        created_at__date__lte=today,
    )
    active_qs = _filter_stage_events_by_owner(active_qs, owner_ids)
    active_rows = (
        active_qs.annotate(w=TruncWeek("created_at"))
        .values("w", "journal_contact__journal__owner_id")
        .distinct()
    )
    week_to_active_users = {ws: set() for ws in week_starts}
    for row in active_rows:
        w_date = row["w"].date() if hasattr(row["w"], "date") else row["w"]
        if w_date in week_to_active_users:
            week_to_active_users[w_date].add(row["journal_contact__journal__owner_id"])

    # On-pace calc. Pull goals + monthly gift totals covering up to the current month.
    goal_rows = list(
        _active_missionaries(owner_ids)
        .filter(monthly_support_goal_cents__gt=0)
        .values("id", "monthly_support_goal_cents")
    )
    goal_map = {r["id"]: int(r["monthly_support_goal_cents"]) for r in goal_rows}
    user_ids_with_goals = list(goal_map.keys())
    total_missionaries = _active_missionaries(owner_ids).count()

    # Gifts grouped by (owner, month) across the window months.
    earliest_week_end_month = (week_starts[0] + timedelta(days=6)).replace(day=1)
    gifts_qs = Gift.objects.filter(
        gift_date__gte=earliest_week_end_month,
        gift_date__lte=today,
        donor_contact__owner_id__in=user_ids_with_goals,
    )
    if owner_ids is not None:
        gifts_qs = gifts_qs.filter(donor_contact__owner_id__in=owner_ids)
    # Per-day totals let us compute MTD through any week-end cheaply.
    daily_totals = gifts_qs.values("donor_contact__owner_id", "gift_date").annotate(
        total=Sum("amount_cents")
    )
    # Nested map: user_id -> {gift_date: total_cents}
    user_day_totals = {}
    for row in daily_totals:
        uid = row["donor_contact__owner_id"]
        user_day_totals.setdefault(uid, {})[row["gift_date"]] = int(row["total"] or 0)

    weeks_out = []
    for ws in week_starts:
        week_end = min(ws + timedelta(days=6), today)
        # week_end may be before "today" for past weeks and equals today for current.
        month_start = week_end.replace(day=1)
        days_in_month = monthrange(week_end.year, week_end.month)[1]
        ratio = week_end.day / days_in_month

        on_pace = 0
        for uid, goal in goal_map.items():
            per_day = user_day_totals.get(uid, {})
            mtd = sum(amt for d, amt in per_day.items() if month_start <= d <= week_end)
            expected = goal * ratio
            if expected > 0 and mtd >= expected:
                on_pace += 1

        weeks_out.append(
            {
                "week_start": ws.isoformat(),
                "week_label": ws.strftime("%b %-d"),
                "active_missionaries": len(week_to_active_users.get(ws, set())),
                "on_pace_missionaries": on_pace,
                "total_missionaries": int(total_missionaries),
            }
        )

    return {"weeks": weeks_out}


# --- 5. Fiscal year donations --------------------------------------------------


def get_fiscal_year_donations(request):
    """Monthly FYTD donations vs prior year, Jun -> May.
    current_cents is null for months beyond the current month."""
    today = date.today()
    fy_start, fy_end = get_current_fiscal_year_bounds(today)
    prior_start, prior_end = get_prior_fiscal_year_bounds(today)
    owner_ids = _admin_scope_owner_ids(request)

    current_qs = _filter_gifts_by_owner(
        Gift.objects.filter(gift_date__gte=fy_start, gift_date__lte=today),
        owner_ids,
    )
    prior_qs = _filter_gifts_by_owner(
        Gift.objects.filter(gift_date__gte=prior_start, gift_date__lte=prior_end),
        owner_ids,
    )

    current_by_month = {
        row["m"].date() if hasattr(row["m"], "date") else row["m"]: int(row["total"] or 0)
        for row in current_qs.annotate(m=TruncMonth("gift_date"))
        .values("m")
        .annotate(total=Sum("amount_cents"))
    }
    prior_by_month = {
        row["m"].date() if hasattr(row["m"], "date") else row["m"]: int(row["total"] or 0)
        for row in prior_qs.annotate(m=TruncMonth("gift_date"))
        .values("m")
        .annotate(total=Sum("amount_cents"))
    }

    months = []
    # 12 entries starting at fy_start month (June), running through May.
    for i in range(12):
        month_year = fy_start.year + (1 if (fy_start.month + i) > 12 else 0)
        month_num = ((fy_start.month - 1 + i) % 12) + 1
        current_month = date(month_year, month_num, 1)
        prior_month = date(month_year - 1, month_num, 1)

        # is_future: month starts after the current month
        is_future = current_month > today.replace(day=1)
        current_cents = None if is_future else current_by_month.get(current_month, 0)
        prior_cents = prior_by_month.get(prior_month, 0)

        months.append(
            {
                "month": current_month.isoformat(),
                "short_label": current_month.strftime("%b"),
                "current_cents": current_cents,
                "prior_cents": prior_cents,
                "is_future": is_future,
            }
        )

    current_total = sum(current_by_month.values())
    prior_total = sum(prior_by_month.values())

    return {
        "fy_start": fy_start.isoformat(),
        "fy_end": fy_end.isoformat(),
        "months": months,
        "current_fy_total_cents": int(current_total),
        "prior_fy_total_cents": int(prior_total),
    }
