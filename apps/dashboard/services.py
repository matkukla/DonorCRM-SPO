"""
Service functions for dashboard aggregations.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import TruncMonth

from apps.contacts.models import Contact
from apps.core.fiscal_year import fiscal_year_end, fiscal_year_start, months_elapsed_in_fiscal_year
from apps.core.gift_utils import _monthly_equivalent_aggregate
from apps.core.permissions import get_visible_user_ids
from apps.events.models import Event
from apps.imports.models import ImportBatch, ImportBatchStatus, ImportBatchType, MPDSnapshot
from apps.gifts.models import Gift, RecurringGift, RecurringGiftStatus
from apps.tasks.models import Task, TaskStatus

logger = logging.getLogger(__name__)

# Default monthly MPD cap in dollars when no snapshot exists for a user.
DEFAULT_MPD_CAP = 3600.0


def get_what_changed(user, since=None):
    """
    Get events/changes since the user's last login.
    """
    if since is None:
        since = user.last_login_at or (date.today() - timedelta(days=7))

    # Base queryset for user's events
    events = Event.objects.filter(user=user, is_new=True)

    # Get counts by type
    event_counts = events.values("event_type").annotate(count=Count("id"))

    # Get recent events (limit to 10)
    recent_events = events.order_by("-created_at")[:10]

    return {
        "event_counts": {e["event_type"]: e["count"] for e in event_counts},
        "recent_events": recent_events,
        "total_new": events.count(),
    }


def get_needs_attention(user):
    """
    Get items requiring user action.
    """
    visible = get_visible_user_ids(user)
    contacts = Contact.active.filter(owner_id__in=visible)
    tasks = Task.objects.filter(owner_id__in=visible)

    today = date.today()

    # Overdue tasks (exclude broadcasts — they have their own section)
    overdue_tasks = tasks.filter(
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
        due_date__lt=today,
        broadcast__isnull=True,
    )

    # Tasks due today (exclude broadcasts — they have their own section)
    tasks_due_today = tasks.filter(
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
        due_date=today,
        broadcast__isnull=True,
    )

    # Pending broadcast tasks (regardless of due date)
    broadcast_tasks = tasks.filter(
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
        broadcast__isnull=False,
    )

    # Contacts needing thank-you
    thank_you_needed = contacts.filter(needs_thank_you=True)

    # Total incomplete tasks (all PENDING + IN_PROGRESS, any due date)
    total_incomplete = tasks.filter(
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
    )

    return {
        "late_pledges": [],
        "late_pledge_count": 0,
        "overdue_tasks": overdue_tasks[:5],
        "overdue_task_count": overdue_tasks.count(),
        "tasks_due_today": tasks_due_today[:5],
        "tasks_due_today_count": tasks_due_today.count(),
        "broadcast_tasks": broadcast_tasks[:5],
        "broadcast_task_count": broadcast_tasks.count(),
        "thank_you_needed": thank_you_needed[:5],
        "thank_you_needed_count": thank_you_needed.count(),
        "total_incomplete_task_count": total_incomplete.count(),
    }


def get_late_donations(user, limit=10):
    """
    Get late donations for the user's own contacts.

    Delegates to apps.core.late_donations.compute_late_donations so the
    Dashboard tile and the /insights/late-donations page agree.
    """
    from apps.core.late_donations import base_recurring_for_owner, compute_late_donations

    return compute_late_donations(base_recurring_for_owner(user), limit=limit)


def get_thank_you_queue(user):
    """
    Get contacts needing thank-you acknowledgment.
    """
    visible = get_visible_user_ids(user)
    contacts = Contact.active.filter(owner_id__in=visible)

    return contacts.filter(needs_thank_you=True).select_related("owner")


def get_support_progress(user):
    """
    Calculate support progress toward monthly goal.

    Uses the shared compute_monthly_support helper so the Dashboard tile and
    the Goal page always agree on the formula:
        recurring_monthly + (FY one-time gifts / 12).

    Scoping: always filters by donor_contact__owner=user so the tile
    reflects this user's personal fundraising progress only — it compares
    against the user's own monthly_goal regardless of role.
    """
    from django.db.models import Q

    from apps.core.support_math import compute_monthly_support

    support = compute_monthly_support(Q(donor_contact__owner=user))
    total_monthly = support["effective_monthly_support"]

    goal = float(user.monthly_support_goal_cents) / 100 if user.monthly_support_goal_cents else 0

    return {
        "current_monthly_support": total_monthly,
        "recurring_monthly": support["recurring_monthly"],
        "one_time_monthly": support["one_time_monthly"],
        "monthly_goal": goal,
        "percentage": (total_monthly / goal * 100) if goal > 0 else 0,
        "gap": max(0, goal - total_monthly),
        "active_pledge_count": support["active_pledge_count"],
    }


def get_recent_gifts(user, days=30, limit=10):
    """
    Get recent gifts.
    """
    start_date = date.today() - timedelta(days=days)

    visible = get_visible_user_ids(user)
    gifts = Gift.objects.filter(donor_contact__owner_id__in=visible)

    return gifts.filter(gift_date__gte=start_date).select_related("donor_contact")[:limit]


def get_giving_summary(user, as_of_date=None):
    """
    Calculate giving summary for the Given & Expecting widget.
    Uses fiscal year (June 1 - May 31).
    """
    today = as_of_date or date.today()
    year_start = fiscal_year_start(today)
    year_end = fiscal_year_end(today)

    # Always scope to the requesting user's own contacts.
    # The Given & Expecting widget is personal — it compares against the
    # user's own monthly_goal, so must only count their own contacts' gifts.
    gifts = Gift.objects.filter(donor_contact__owner=user)
    recurring_gifts = RecurringGift.objects.filter(donor_contact__owner=user)

    # Given: sum of gifts this year (cents -> dollars)
    year_gifts = gifts.filter(gift_date__gte=year_start, gift_date__lte=year_end)
    total_cents = year_gifts.aggregate(total=Sum("amount_cents"))["total"] or 0
    given = Decimal(total_cents) / Decimal(100)

    # Active recurring gifts annualized via SQL aggregation (O(1) memory)
    active_recurring = recurring_gifts.filter(status=RecurringGiftStatus.ACTIVE)
    monthly_recurring = _monthly_equivalent_aggregate(active_recurring)
    annualized_recurring = monthly_recurring * 12

    # Expecting: annualized recurring minus recurring payments already received
    # this year. Only subtract recurring-sourced gifts to avoid one-time gifts
    # reducing the expected recurring amount.
    recurring_given_cents = (
        year_gifts.filter(
            recurring_gift__isnull=False,
        ).aggregate(
            total=Sum("amount_cents")
        )["total"]
        or 0
    )
    recurring_given = Decimal(recurring_given_cents) / Decimal(100)
    expecting = max(0, float(annualized_recurring) - float(recurring_given))

    # Goals
    monthly_goal = (
        float(user.monthly_support_goal_cents) / 100 if user.monthly_support_goal_cents else 0
    )
    annual_goal = monthly_goal * 12

    given_float = float(given)

    # Last completed gift-related import timestamp (scoped to this user's uploads)
    gift_import_types = [
        ImportBatchType.RE_GIFT,
        ImportBatchType.RE_RECURRING_GIFT,
        ImportBatchType.GENERIC_DONATIONS,
        ImportBatchType.SPO_GIFT,
    ]
    last_import_at = (
        ImportBatch.objects.filter(
            status=ImportBatchStatus.COMPLETED,
            import_type__in=gift_import_types,
            uploaded_by=user,
        )
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )

    return {
        "given": given_float,
        "expecting": expecting,
        "total": given_float + expecting,
        "recurring_pledges_annual": float(annualized_recurring),
        "recurring_pledges_monthly": float(annualized_recurring / 12)
        if annualized_recurring
        else 0,
        "annual_goal": annual_goal,
        "monthly_goal": monthly_goal,
        "percentage": ((given_float + expecting) / annual_goal * 100) if annual_goal > 0 else 0,
        "fiscal_year_label": f"FY {year_start.year}-{year_end.year}",
        "active_pledge_count": active_recurring.count(),
        "last_import_at": last_import_at.isoformat() if last_import_at else None,
    }


def get_monthly_gifts(user, months=12):
    """
    Get gift totals grouped by month for bar chart.
    Returns last N months including current month.
    """
    today = date.today()
    start_date = today.replace(day=1) - relativedelta(months=months - 1)

    # Always scope to the requesting user's own contacts.
    # This chart shows the user's personal giving history vs their monthly_goal.
    gifts = Gift.objects.filter(donor_contact__owner=user)

    monthly_data = (
        gifts.filter(gift_date__gte=start_date)
        .annotate(month=TruncMonth("gift_date"))
        .values("month")
        .annotate(total=Sum("amount_cents"))
        .order_by("month")
    )

    # Build map of month -> total (cents to dollars)
    monthly_map = {item["month"]: float(item["total"]) / 100 for item in monthly_data}

    # Build complete month list (fill gaps with 0)
    result = []
    for i in range(months):
        month_date = (start_date + relativedelta(months=i)).replace(day=1)
        result.append(
            {
                "month": month_date.strftime("%Y-%m"),
                "label": month_date.strftime("%b %Y"),
                "short_label": month_date.strftime("%b"),
                "total": monthly_map.get(month_date, 0),
            }
        )

    monthly_goal = (
        float(user.monthly_support_goal_cents) / 100 if user.monthly_support_goal_cents else 0
    )

    return {
        "months": result,
        "monthly_goal": monthly_goal,
    }


def get_dashboard_summary(user):
    """
    Get complete dashboard data in one call.
    Caches querysets to avoid duplicate database queries.
    """
    logger.info(f"Fetching dashboard summary for user {user.email}")

    what_changed = get_what_changed(user)
    # Convert querysets to lists of dicts
    what_changed["recent_events"] = list(
        what_changed["recent_events"].values(
            "id", "event_type", "title", "message", "severity", "created_at", "is_read"
        )
    )

    needs_attention = get_needs_attention(user)
    # late_pledges is already an empty list from get_needs_attention
    needs_attention["overdue_tasks"] = list(
        needs_attention["overdue_tasks"].values("id", "title", "due_date", "priority")
    )
    needs_attention["tasks_due_today"] = list(
        needs_attention["tasks_due_today"].values("id", "title", "due_date", "priority")
    )
    needs_attention["broadcast_tasks"] = list(
        needs_attention["broadcast_tasks"].values("id", "title", "due_date", "priority")
    )
    needs_attention["thank_you_needed"] = list(
        needs_attention["thank_you_needed"].values(
            "id", "first_name", "last_name", "last_gift_amount"
        )
    )

    # Late donations — limit the displayed list to 10 and compute the total
    # count separately so we don't allocate dicts for every late pledge on
    # tenants with thousands of stale recurring gifts.
    from apps.core.late_donations import base_recurring_for_owner, count_late_donations

    late_donations = get_late_donations(user, limit=10)
    late_donations_count = count_late_donations(base_recurring_for_owner(user))

    thank_you_qs = get_thank_you_queue(user)
    thank_you_list = list(
        thank_you_qs[:5].values(
            "id", "first_name", "last_name", "last_gift_amount", "last_gift_date"
        )
    )
    thank_you_count = thank_you_qs.count()

    logger.debug(
        f"Dashboard data fetched: {late_donations_count} late donations, {thank_you_count} thank-you needed"
    )

    # Pre-aggregate total of ALL recent gifts (not just the limited list)
    thirty_days_ago = date.today() - timedelta(days=30)
    recent_total_cents = (
        Gift.objects.filter(
            donor_contact__owner=user,
            gift_date__gte=thirty_days_ago,
        ).aggregate(
            total=Sum("amount_cents")
        )["total"]
        or 0
    )
    recent_gifts_total = float(Decimal(recent_total_cents) / Decimal(100))

    return {
        "what_changed": what_changed,
        "needs_attention": needs_attention,
        "late_donations": late_donations,
        "late_donations_count": late_donations_count,
        "thank_you_queue": thank_you_list,
        "thank_you_count": thank_you_count,
        "support_progress": get_support_progress(user),
        "recent_gifts_total": recent_gifts_total,
        "recent_gifts": list(
            get_recent_gifts(user)
            .annotate(
                amount=ExpressionWrapper(
                    F("amount_cents") * Value(Decimal("0.01")),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                date=F("gift_date"),
                contact_id=F("donor_contact_id"),
                contact__first_name=F("donor_contact__first_name"),
                contact__last_name=F("donor_contact__last_name"),
            )
            .values(
                "id", "amount", "date", "contact_id", "contact__first_name", "contact__last_name"
            )
        ),
    }


def _compute_mpd_from_totals(total_cents, mpd_cap, months_elapsed):
    """Shared math: turn per-user gift totals + mpd cap into the MPD dict."""
    if total_cents == 0:
        return {"has_data": False}

    total_dollars = float(Decimal(total_cents) / Decimal(100))
    monthly_average = total_dollars / months_elapsed
    diff = monthly_average - mpd_cap
    roll_forward_balance = total_dollars - (diff * months_elapsed)

    if diff != 0:
        months_remaining_str = str(round(roll_forward_balance / diff, 1))
    else:
        months_remaining_str = "infinite"

    return {
        "has_data": True,
        "monthly_average": str(round(monthly_average, 2)),
        "current_mpd_cap": str(round(mpd_cap, 2)),
        "latest_roll_forward_balance": str(round(roll_forward_balance, 2)),
        "months_remaining_rf": months_remaining_str,
    }


def get_mpd_computed(user):
    """
    Compute MPD tile values from actual Gift data for the current fiscal year.
    - Monthly Average = total gifts in FY / months elapsed
    - MPD Cap = from latest snapshot (fallback DEFAULT_MPD_CAP)
    - Roll Forward Balance = total - [(monthly_avg - mpd_cap) * months_elapsed]
    - Months Remaining = roll_forward_balance / (monthly_avg - mpd_cap)
    """
    today = date.today()
    fy_start = fiscal_year_start(today)
    months_elapsed = months_elapsed_in_fiscal_year(today)

    total_cents = (
        Gift.objects.filter(
            donor_contact__owner=user,
            gift_date__gte=fy_start,
            gift_date__lte=today,
        ).aggregate(total=Sum("amount_cents"))["total"]
        or 0
    )

    snapshot = MPDSnapshot.objects.filter(user=user).order_by("-upload__created_at").first()
    mpd_cap = (
        float(snapshot.current_mpd_cap) if snapshot and snapshot.current_mpd_cap else DEFAULT_MPD_CAP
    )

    return _compute_mpd_from_totals(total_cents, mpd_cap, months_elapsed)


def get_mpd_computed_batch(users, snapshot_map=None):
    """
    Batched version of get_mpd_computed for many users.

    Performs 2 queries total (gift totals + optional snapshots) instead of 2N.
    Returns dict of {user_id: computed_dict} with the same shape as get_mpd_computed.

    Args:
        users: iterable of User instances.
        snapshot_map: optional dict of {user_id: MPDSnapshot} to avoid refetching
            snapshots. If None, this function fetches the latest snapshot per user.
    """
    users = list(users)
    if not users:
        return {}

    today = date.today()
    fy_start = fiscal_year_start(today)
    months_elapsed = months_elapsed_in_fiscal_year(today)
    user_ids = [u.id for u in users]

    # Single aggregation: gift totals grouped by owner.
    totals_rows = (
        Gift.objects.filter(
            donor_contact__owner_id__in=user_ids,
            gift_date__gte=fy_start,
            gift_date__lte=today,
        )
        .values("donor_contact__owner_id")
        .annotate(total=Sum("amount_cents"))
    )
    totals_map = {row["donor_contact__owner_id"]: row["total"] or 0 for row in totals_rows}

    # Fetch snapshots only if caller did not supply them.
    if snapshot_map is None:
        snapshot_map = {}
        for snap in (
            MPDSnapshot.objects.filter(user_id__in=user_ids)
            .select_related("upload")
            .order_by("user_id", "-upload__created_at")
        ):
            if snap.user_id not in snapshot_map:
                snapshot_map[snap.user_id] = snap

    results = {}
    for user in users:
        total_cents = totals_map.get(user.id, 0)
        snapshot = snapshot_map.get(user.id)
        mpd_cap = (
            float(snapshot.current_mpd_cap)
            if snapshot and snapshot.current_mpd_cap
            else DEFAULT_MPD_CAP
        )
        results[user.id] = _compute_mpd_from_totals(total_cents, mpd_cap, months_elapsed)

    return results
