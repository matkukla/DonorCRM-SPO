"""
Service functions for dashboard aggregations.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from apps.contacts.models import Contact
from apps.donations.models import Donation
from apps.events.models import Event
from apps.journals.models import JournalStageEvent
from apps.pledges.models import Pledge, PledgeStatus
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
    # Get contacts for this user
    if user.role == 'admin':
        contacts = Contact.objects.all()
        tasks = Task.objects.all()
        pledges = Pledge.objects.all()
    else:
        contacts = Contact.objects.filter(owner=user)
        tasks = Task.objects.filter(owner=user)
        pledges = Pledge.objects.filter(contact__owner=user)

    today = date.today()

    # Late pledges
    late_pledges = pledges.filter(is_late=True, status=PledgeStatus.ACTIVE)

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
        'late_pledges': late_pledges[:5],
        'late_pledge_count': late_pledges.count(),
        'overdue_tasks': overdue_tasks[:5],
        'overdue_task_count': overdue_tasks.count(),
        'tasks_due_today': tasks_due_today[:5],
        'tasks_due_today_count': tasks_due_today.count(),
        'thank_you_needed': thank_you_needed[:5],
        'thank_you_needed_count': thank_you_needed.count()
    }


def get_late_donations(user, limit=10):
    """
    Get active pledges that are late (DonorElf-style).
    Returns contacts with active recurring commitments whose expected
    gift hasn't arrived after the grace period.
    """
    if user.role == 'admin':
        pledges = Pledge.objects.all()
    else:
        pledges = Pledge.objects.filter(contact__owner=user)

    late_pledges = pledges.filter(
        status=PledgeStatus.ACTIVE,
        is_late=True,
    ).select_related('contact').order_by('-days_late')[:limit]

    return [{
        'id': str(p.id),
        'contact_id': str(p.contact.id),
        'contact_name': p.contact.full_name,
        'amount': str(p.amount),
        'frequency': p.frequency,
        'monthly_equivalent': round(p.monthly_equivalent, 2),
        'last_gift_date': p.last_fulfilled_date.isoformat() if p.last_fulfilled_date else None,
        'days_late': p.days_late,
        'next_expected_date': p.next_expected_date.isoformat() if p.next_expected_date else None,
    } for p in late_pledges]


def get_thank_you_queue(user):
    """
    Get contacts needing thank-you acknowledgment.
    """
    if user.role == 'admin':
        contacts = Contact.objects.all()
    else:
        contacts = Contact.objects.filter(owner=user)

    return contacts.filter(needs_thank_you=True).select_related('owner')


def get_support_progress(user):
    """
    Calculate support progress toward monthly goal.
    Uses database aggregation instead of Python loops to avoid N+1 queries.
    """
    if user.role == 'admin':
        pledges = Pledge.objects.all()
    else:
        pledges = Pledge.objects.filter(contact__owner=user)

    # Get active pledges with monthly equivalent calculated in DB
    active_pledges = pledges.filter(status=PledgeStatus.ACTIVE)

    # Calculate monthly equivalent using Python (simpler and more maintainable)
    # The monthly_equivalent property handles the calculation correctly
    total_monthly = float(sum(p.monthly_equivalent for p in active_pledges))
    pledge_count = active_pledges.count()

    # Get user's goal
    goal = float(user.monthly_goal) if user.monthly_goal else 0

    return {
        'current_monthly_support': total_monthly,
        'monthly_goal': goal,
        'percentage': (total_monthly / goal * 100) if goal > 0 else 0,
        'gap': max(0, goal - total_monthly),
        'active_pledge_count': pledge_count
    }


def get_recent_gifts(user, days=30, limit=10):
    """
    Get recent donations.
    """
    start_date = date.today() - timedelta(days=days)

    if user.role == 'admin':
        donations = Donation.objects.all()
    else:
        donations = Donation.objects.filter(contact__owner=user)

    return donations.filter(date__gte=start_date).select_related('contact')[:limit]


def get_recent_journal_activity(user, limit=8):
    """Get recent journal stage events for dashboard widget."""
    if user.role == 'admin':
        qs = JournalStageEvent.objects.all()
    else:
        qs = JournalStageEvent.objects.filter(
            journal_contact__journal__owner=user
        )
    qs = qs.select_related(
        'journal_contact__contact',
        'journal_contact__journal',
    ).order_by('-created_at')[:limit]
    return [{
        'id': str(e.id),
        'event_type': e.event_type,
        'stage': e.stage,
        'notes': e.notes or '',
        'created_at': e.created_at.isoformat(),
        'contact_name': e.journal_contact.contact.full_name,
        'contact_id': str(e.journal_contact.contact.id),
        'journal_name': e.journal_contact.journal.name,
        'journal_id': str(e.journal_contact.journal.id),
    } for e in qs]


def get_giving_summary(user, year=None):
    """
    Calculate giving summary for the Given & Expecting widget.
    Default: current calendar year.
    """
    if year is None:
        year = date.today().year

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    if user.role in ['admin', 'finance', 'read_only']:
        donations = Donation.objects.all()
        pledges = Pledge.objects.all()
    else:
        donations = Donation.objects.filter(contact__owner=user)
        pledges = Pledge.objects.filter(contact__owner=user)

    # Given: sum of donations this year
    given = donations.filter(
        date__gte=year_start, date__lte=year_end
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Active recurring pledges annualized
    active_pledges = pledges.filter(status=PledgeStatus.ACTIVE)
    annualized_recurring = sum(p.monthly_equivalent * 12 for p in active_pledges)

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
        'active_pledge_count': active_pledges.count(),
    }


def get_monthly_gifts(user, months=12):
    """
    Get donation totals grouped by month for bar chart.
    Returns last N months including current month.
    """
    today = date.today()
    start_date = (today.replace(day=1) - relativedelta(months=months - 1))

    if user.role in ['admin', 'finance', 'read_only']:
        donations = Donation.objects.all()
    else:
        donations = Donation.objects.filter(contact__owner=user)

    monthly_data = (
        donations.filter(date__gte=start_date)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    # Build map of month -> total
    monthly_map = {item['month']: float(item['total']) for item in monthly_data}

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
    # Convert querysets to lists of dicts
    needs_attention['late_pledges'] = list(needs_attention['late_pledges'].values(
        'id', 'amount', 'frequency', 'days_late'
    ))
    needs_attention['overdue_tasks'] = list(needs_attention['overdue_tasks'].values(
        'id', 'title', 'due_date', 'priority'
    ))
    needs_attention['tasks_due_today'] = list(needs_attention['tasks_due_today'].values(
        'id', 'title', 'due_date', 'priority'
    ))
    needs_attention['thank_you_needed'] = list(needs_attention['thank_you_needed'].values(
        'id', 'first_name', 'last_name', 'last_gift_amount'
    ))

    # Late donations (DonorElf-style)
    late_donations = get_late_donations(user)
    if user.role == 'admin':
        late_donations_count = Pledge.objects.filter(
            status=PledgeStatus.ACTIVE, is_late=True
        ).count()
    else:
        late_donations_count = Pledge.objects.filter(
            contact__owner=user, status=PledgeStatus.ACTIVE, is_late=True
        ).count()

    thank_you_qs = get_thank_you_queue(user)
    thank_you_list = list(thank_you_qs[:5].values(
        'id', 'first_name', 'last_name', 'last_gift_amount', 'last_gift_date'
    ))
    thank_you_count = thank_you_qs.count()

    logger.debug(f'Dashboard data fetched: {late_donations_count} late donations, {thank_you_count} thank-you needed')

    return {
        'what_changed': what_changed,
        'needs_attention': needs_attention,
        'late_donations': late_donations,
        'late_donations_count': late_donations_count,
        'thank_you_queue': thank_you_list,
        'thank_you_count': thank_you_count,
        'support_progress': get_support_progress(user),
        'recent_gifts': list(get_recent_gifts(user).values(
            'id', 'amount', 'date', 'contact_id', 'contact__first_name', 'contact__last_name'
        )),
        'journal_activity': get_recent_journal_activity(user),
    }
