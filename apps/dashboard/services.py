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
from apps.core.gift_utils import FREQUENCY_MULTIPLIERS, _monthly_equivalent_aggregate
from apps.core.permissions import get_visible_user_ids
from apps.events.models import Event
from apps.gifts.models import Gift, RecurringGift, RecurringGiftStatus
from apps.tasks.models import Task, TaskStatus

logger = logging.getLogger(__name__)


def get_what_changed(user, since=None):
    """
    Get events/changes since the user's last login.
    """
    if since is None:
        since = user.last_login_at or (date.today() - timedelta(days=7))

    # Base queryset for user's events
    events = Event.objects.filter(user=user, is_new=True)

    # Get counts by type
    event_counts = events.values('event_type').annotate(count=Count('id'))

    # Get recent events (limit to 10)
    recent_events = events.order_by('-created_at')[:10]

    return {
        'event_counts': {e['event_type']: e['count'] for e in event_counts},
        'recent_events': recent_events,
        'total_new': events.count()
    }


def get_needs_attention(user):
    """
    Get items requiring user action.
    """
    visible = get_visible_user_ids(user)
    if visible is None:
        contacts = Contact.objects.all()
        tasks = Task.objects.all()
    else:
        contacts = Contact.objects.filter(owner_id__in=visible)
        tasks = Task.objects.filter(owner_id__in=visible)

    today = date.today()

    # Overdue tasks
    overdue_tasks = tasks.filter(
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
        due_date__lt=today
    )

    # Tasks due today
    tasks_due_today = tasks.filter(
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
        due_date=today
    )

    # Contacts needing thank-you
    thank_you_needed = contacts.filter(needs_thank_you=True)

    return {
        'late_pledges': [],
        'late_pledge_count': 0,
        'overdue_tasks': overdue_tasks[:5],
        'overdue_task_count': overdue_tasks.count(),
        'tasks_due_today': tasks_due_today[:5],
        'tasks_due_today_count': tasks_due_today.count(),
        'thank_you_needed': thank_you_needed[:5],
        'thank_you_needed_count': thank_you_needed.count()
    }


def get_late_donations(user, limit=10):
    """
    Get late donations by comparing each active recurring gift's expected
    interval against the linked contact's last_gift_date.

    A recurring gift is "late" if enough time has passed since the contact's
    last gift based on the frequency, with a 50% grace period.
    """
    # Frequency -> expected days between gifts
    frequency_days = {
        RecurringGiftFrequency.WEEKLY: 7,
        RecurringGiftFrequency.BIWEEKLY: 14,
        RecurringGiftFrequency.MONTHLY: 30,
        RecurringGiftFrequency.BIMONTHLY: 60,
        RecurringGiftFrequency.QUARTERLY: 90,
        RecurringGiftFrequency.SEMI_ANNUALLY: 180,
        RecurringGiftFrequency.ANNUALLY: 365,
    }

    today = date.today()
    active_recurring = RecurringGift.objects.filter(
        donor_contact__owner=user,
        status=RecurringGiftStatus.ACTIVE,
    ).select_related('donor_contact').exclude(
        frequency=RecurringGiftFrequency.IRREGULAR,
    )

    late = []
    for rg in active_recurring:
        interval = frequency_days.get(rg.frequency)
        if not interval:
            continue

        contact = rg.donor_contact
        last_date = contact.last_gift_date or rg.start_date
        # 50% grace period
        threshold = timedelta(days=int(interval * 1.5))
        if today - last_date > threshold:
            days_late = (today - last_date).days - interval
            monthly_eq = float(rg.monthly_equivalent)
            late.append({
                'id': str(rg.id),
                'contact_id': str(contact.id),
                'contact_name': f'{contact.first_name} {contact.last_name}'.strip(),
                'amount': str(rg.amount_dollars),
                'frequency': rg.frequency,
                'monthly_equivalent': monthly_eq,
                'last_gift_date': last_date.isoformat() if last_date else None,
                'days_late': days_late,
                'next_expected_date': (last_date + timedelta(days=interval)).isoformat(),
            })

    # Sort by days late descending, limit results
    late.sort(key=lambda x: x['days_late'], reverse=True)
    return late[:limit]


def get_thank_you_queue(user):
    """
    Get contacts needing thank-you acknowledgment.
    """
    visible = get_visible_user_ids(user)
    if visible is None:
        contacts = Contact.objects.all()
    else:
        contacts = Contact.objects.filter(owner_id__in=visible)

    return contacts.filter(needs_thank_you=True).select_related('owner')


def get_support_progress(user):
    """
    Calculate support progress toward monthly goal.
    Uses SQL aggregation with CASE/WHEN for frequency multipliers
    instead of loading all RecurringGifts into Python.

    Scoping: always filters by donor_contact__owner=user so the tile
    reflects this user's personal fundraising progress only.

    Admin/finance/read_only roles return None from get_visible_user_ids
    (all-access sentinel for other views), but the Monthly Support Goal
    tile must still scope to the requesting user's own contacts. Without
    this fix, admin would see all missionaries' recurring gifts summed
    against their personal monthly_goal — inflating current_monthly_support.
    """
    # Always scope support progress to the requesting user's own contacts.
    # get_visible_user_ids returns None (all-access) for admin/finance/read_only,
    # but that sentinel is not appropriate here — this tile is personal.
    recurring_gifts = RecurringGift.objects.filter(donor_contact__owner=user)

    # Get active recurring gifts
    active_recurring = recurring_gifts.filter(status=RecurringGiftStatus.ACTIVE)

    # Calculate monthly equivalent via SQL aggregation (O(1) memory)
    total_monthly = float(_monthly_equivalent_aggregate(active_recurring))
    rg_count = active_recurring.count()

    # Get user's goal
    goal = float(user.monthly_goal) if user.monthly_goal else 0

    return {
        'current_monthly_support': total_monthly,
        'monthly_goal': goal,
        'percentage': (total_monthly / goal * 100) if goal > 0 else 0,
        'gap': max(0, goal - total_monthly),
        'active_pledge_count': rg_count
    }


def get_recent_gifts(user, days=30, limit=10):
    """
    Get recent gifts.
    """
    start_date = date.today() - timedelta(days=days)

    visible = get_visible_user_ids(user)
    if visible is None:
        gifts = Gift.objects.all()
    else:
        gifts = Gift.objects.filter(donor_contact__owner_id__in=visible)

    return gifts.filter(gift_date__gte=start_date).select_related('donor_contact')[:limit]


def get_giving_summary(user, year=None):
    """
    Calculate giving summary for the Given & Expecting widget.
    Default: current calendar year.
    """
    if year is None:
        year = date.today().year

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    # Always scope to the requesting user's own contacts.
    # get_visible_user_ids returns None (all-access) for admin/finance/read_only,
    # but the Given & Expecting widget is personal — it compares against the
    # user's own monthly_goal, so must only count their own contacts' gifts.
    gifts = Gift.objects.filter(donor_contact__owner=user)
    recurring_gifts = RecurringGift.objects.filter(donor_contact__owner=user)

    # Given: sum of gifts this year (cents -> dollars)
    total_cents = gifts.filter(
        gift_date__gte=year_start, gift_date__lte=year_end
    ).aggregate(total=Sum('amount_cents'))['total'] or 0
    given = Decimal(total_cents) / Decimal(100)

    # Active recurring gifts annualized via SQL aggregation (O(1) memory)
    active_recurring = recurring_gifts.filter(status=RecurringGiftStatus.ACTIVE)
    monthly_recurring = _monthly_equivalent_aggregate(active_recurring)
    annualized_recurring = monthly_recurring * 12

    # Expecting: annualized recurring minus what's already given this year
    expecting = max(0, float(annualized_recurring) - float(given))

    # Goals
    monthly_goal = float(user.monthly_goal) if user.monthly_goal else 0
    annual_goal = monthly_goal * 12

    given_float = float(given)

    return {
        'given': given_float,
        'expecting': expecting,
        'total': given_float + expecting,
        'recurring_pledges_annual': float(annualized_recurring),
        'recurring_pledges_monthly': float(annualized_recurring / 12) if annualized_recurring else 0,
        'annual_goal': annual_goal,
        'monthly_goal': monthly_goal,
        'percentage': ((given_float + expecting) / annual_goal * 100) if annual_goal > 0 else 0,
        'year': year,
        'active_pledge_count': active_recurring.count(),
    }


def get_monthly_gifts(user, months=12):
    """
    Get gift totals grouped by month for bar chart.
    Returns last N months including current month.
    """
    today = date.today()
    start_date = (today.replace(day=1) - relativedelta(months=months - 1))

    # Always scope to the requesting user's own contacts.
    # This chart shows the user's personal giving history vs their monthly_goal.
    gifts = Gift.objects.filter(donor_contact__owner=user)

    monthly_data = (
        gifts.filter(gift_date__gte=start_date)
        .annotate(month=TruncMonth('gift_date'))
        .values('month')
        .annotate(total=Sum('amount_cents'))
        .order_by('month')
    )

    # Build map of month -> total (cents to dollars)
    monthly_map = {item['month']: float(item['total']) / 100 for item in monthly_data}

    # Build complete month list (fill gaps with 0)
    result = []
    for i in range(months):
        month_date = (start_date + relativedelta(months=i)).replace(day=1)
        result.append({
            'month': month_date.strftime('%Y-%m'),
            'label': month_date.strftime('%b %Y'),
            'short_label': month_date.strftime('%b'),
            'total': monthly_map.get(month_date, 0),
        })

    monthly_goal = float(user.monthly_goal) if user.monthly_goal else 0

    return {
        'months': result,
        'monthly_goal': monthly_goal,
    }


def get_dashboard_summary(user):
    """
    Get complete dashboard data in one call.
    Caches querysets to avoid duplicate database queries.
    """
    logger.info(f'Fetching dashboard summary for user {user.email}')

    what_changed = get_what_changed(user)
    # Convert querysets to lists of dicts
    what_changed['recent_events'] = list(what_changed['recent_events'].values(
        'id', 'event_type', 'title', 'message', 'severity', 'created_at', 'is_read'
    ))

    needs_attention = get_needs_attention(user)
    # late_pledges is already an empty list from get_needs_attention
    needs_attention['overdue_tasks'] = list(needs_attention['overdue_tasks'].values(
        'id', 'title', 'due_date', 'priority'
    ))
    needs_attention['tasks_due_today'] = list(needs_attention['tasks_due_today'].values(
        'id', 'title', 'due_date', 'priority'
    ))
    needs_attention['thank_you_needed'] = list(needs_attention['thank_you_needed'].values(
        'id', 'first_name', 'last_name', 'last_gift_amount'
    ))

    # Late donations
    late_donations = get_late_donations(user)
    late_donations_count = len(late_donations)

    thank_you_qs = get_thank_you_queue(user)
    thank_you_list = list(thank_you_qs[:5].values(
        'id', 'first_name', 'last_name', 'last_gift_amount', 'last_gift_date'
    ))
    thank_you_count = thank_you_qs.count()

    logger.debug(f'Dashboard data fetched: {late_donations_count} late donations, {thank_you_count} thank-you needed')

    # Pre-aggregate total of ALL recent gifts (not just the limited list)
    thirty_days_ago = date.today() - timedelta(days=30)
    recent_total_cents = Gift.objects.filter(
        donor_contact__owner=user,
        gift_date__gte=thirty_days_ago,
    ).aggregate(total=Sum('amount_cents'))['total'] or 0
    recent_gifts_total = float(Decimal(recent_total_cents) / Decimal(100))

    return {
        'what_changed': what_changed,
        'needs_attention': needs_attention,
        'late_donations': late_donations,
        'late_donations_count': late_donations_count,
        'thank_you_queue': thank_you_list,
        'thank_you_count': thank_you_count,
        'support_progress': get_support_progress(user),
        'recent_gifts_total': recent_gifts_total,
        'recent_gifts': list(get_recent_gifts(user).annotate(
            amount=ExpressionWrapper(
                F('amount_cents') / Value(100),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            date=F('gift_date'),
            contact_id=F('donor_contact_id'),
            contact__first_name=F('donor_contact__first_name'),
            contact__last_name=F('donor_contact__last_name'),
        ).values(
            'id', 'amount', 'date', 'contact_id',
            'contact__first_name', 'contact__last_name'
        )),
    }
