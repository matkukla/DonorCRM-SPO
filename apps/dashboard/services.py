"""
Service functions for dashboard aggregations.
"""
from datetime import date, timedelta

from django.db.models import Count, Q, Sum

from apps.contacts.models import Contact, ContactStatus
from apps.donations.models import Donation
from apps.events.models import Event
from apps.pledges.models import Pledge, PledgeStatus
from apps.tasks.models import Task, TaskStatus


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


def get_at_risk_donors(user, days_threshold=60):
    """
    Identify donors who haven't given recently but have giving history.
    """
    cutoff_date = date.today() - timedelta(days=days_threshold)

    if user.role == 'admin':
        contacts = Contact.objects.all()
    else:
        contacts = Contact.objects.filter(owner=user)

    at_risk = contacts.filter(
        status=ContactStatus.DONOR,
        last_gift_date__lt=cutoff_date,
        gift_count__gte=2  # Has given multiple times before
    ).order_by('last_gift_date')

    return at_risk


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
    """
    if user.role == 'admin':
        pledges = Pledge.objects.all()
    else:
        pledges = Pledge.objects.filter(contact__owner=user)

    # Get active pledges
    active_pledges = pledges.filter(status=PledgeStatus.ACTIVE)

    # Calculate monthly equivalent
    total_monthly = sum(p.monthly_equivalent for p in active_pledges)

    # Get user's goal
    goal = float(user.monthly_goal) if user.monthly_goal else 0

    return {
        'current_monthly_support': total_monthly,
        'monthly_goal': goal,
        'percentage': (total_monthly / goal * 100) if goal > 0 else 0,
        'gap': max(0, goal - total_monthly),
        'active_pledge_count': active_pledges.count()
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


def get_dashboard_summary(user):
    """
    Get complete dashboard data in one call.
    """
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

    return {
        'what_changed': what_changed,
        'needs_attention': needs_attention,
        'at_risk_donors': list(get_at_risk_donors(user)[:5].values(
            'id', 'first_name', 'last_name', 'last_gift_date', 'total_given'
        )),
        'at_risk_count': get_at_risk_donors(user).count(),
        'thank_you_queue': list(get_thank_you_queue(user)[:5].values(
            'id', 'first_name', 'last_name', 'last_gift_amount', 'last_gift_date'
        )),
        'thank_you_count': get_thank_you_queue(user).count(),
        'support_progress': get_support_progress(user),
        'recent_gifts': list(get_recent_gifts(user).values(
            'id', 'amount', 'date', 'contact__first_name', 'contact__last_name'
        ))
    }
