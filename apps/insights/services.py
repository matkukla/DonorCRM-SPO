"""
Service functions for insights/reports data aggregations.
"""
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Sum, Q, OuterRef, Subquery, Value, CharField, DecimalField, IntegerField
from django.db.models.functions import TruncMonth, TruncYear, TruncWeek, Coalesce
from django.utils import timezone

from apps.contacts.models import Contact, ContactStatus
from apps.core.permissions import get_visible_user_ids
from apps.events.models import Event
from apps.gifts.models import Gift, RecurringGift, RecurringGiftStatus
from apps.journals.models import Journal, JournalContact, JournalStageEvent, PipelineStage, Decision
from apps.tasks.models import Task, TaskStatus
from apps.users.models import User


def _parse_date_range(date_from=None, date_to=None):
    """Parse date range strings to timezone-aware datetimes.
    Returns (dt_from, dt_to) tuple, either may be None.
    """
    from datetime import datetime as dt_class
    dt_from_val = None
    dt_to_val = None
    try:
        if date_from:
            dt_from_val = timezone.make_aware(dt_class.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            # Include entire day
            dt_to_val = timezone.make_aware(
                dt_class.strptime(date_to, '%Y-%m-%d')
            ) + timedelta(days=1)
    except ValueError:
        pass  # Invalid dates are silently ignored; callers validate at the view layer
    return dt_from_val, dt_to_val


def _scope_gifts(user, request=None):
    """Return gift queryset scoped by user role."""
    visible = get_visible_user_ids(user, request=request)
    if visible is None:
        return Gift.objects.all()
    return Gift.objects.filter(donor_contact__owner_id__in=visible)


def _scope_recurring_gifts(user, request=None):
    """Return recurring gift queryset scoped by user role."""
    visible = get_visible_user_ids(user, request=request)
    if visible is None:
        return RecurringGift.objects.all()
    return RecurringGift.objects.filter(donor_contact__owner_id__in=visible)


def _scope_tasks(user, request=None):
    """Return task queryset scoped by user role."""
    visible = get_visible_user_ids(user, request=request)
    if visible is None:
        return Task.objects.all()
    return Task.objects.filter(owner_id__in=visible)


def get_donations_by_month(user, year=None, request=None):
    """
    Get gift totals grouped by month for a given year.
    Defaults to current year.
    """
    if year is None:
        year = date.today().year

    gifts = _scope_gifts(user, request=request)

    monthly_data = (
        gifts.filter(gift_date__year=year)
        .annotate(month=TruncMonth('gift_date'))
        .values('month')
        .annotate(
            total=Sum('amount_cents'),
            count=Count('id')
        )
        .order_by('month')
    )

    # Build complete 12-month list (fill gaps with 0)
    monthly_map = {item['month'].month: item for item in monthly_data}

    result = []
    for month_num in range(1, 13):
        month_date = date(year, month_num, 1)
        month_data = monthly_map.get(month_num, {'total': 0, 'count': 0})
        result.append({
            'month': month_date.strftime('%Y-%m'),
            'label': month_date.strftime('%B %Y'),
            'short_label': month_date.strftime('%b'),
            'total': float(month_data['total'] or 0) / 100,
            'count': month_data['count'],
        })

    # Calculate year total
    year_total = sum(m['total'] for m in result)

    return {
        'year': year,
        'months': result,
        'year_total': year_total,
        'donation_count': sum(m['count'] for m in result),
    }


def get_donations_by_year(user, years=5, request=None):
    """
    Get gift totals grouped by year for the last N years.
    """
    current_year = date.today().year
    start_year = current_year - years + 1

    gifts = _scope_gifts(user, request=request)

    yearly_data = (
        gifts.filter(gift_date__year__gte=start_year)
        .annotate(year=TruncYear('gift_date'))
        .values('year')
        .annotate(
            total=Sum('amount_cents'),
            count=Count('id')
        )
        .order_by('year')
    )

    # Build map
    yearly_map = {item['year'].year: item for item in yearly_data}

    result = []
    for year in range(start_year, current_year + 1):
        year_data = yearly_map.get(year, {'total': 0, 'count': 0})
        result.append({
            'year': year,
            'total': float(year_data['total'] or 0) / 100,
            'count': year_data['count'],
        })

    return {
        'years': result,
        'grand_total': sum(y['total'] for y in result),
        'total_donations': sum(y['count'] for y in result),
    }


def get_monthly_commitments(user, request=None):
    """
    Get summary of active recurring gifts with monthly equivalents.
    """
    recurring_gifts = _scope_recurring_gifts(user, request=request)
    active_recurring = recurring_gifts.filter(status=RecurringGiftStatus.ACTIVE).select_related('donor_contact')

    # Group by frequency
    by_frequency = {}
    total_monthly = 0

    rg_list = []
    for rg in active_recurring:
        monthly_equiv = rg.monthly_equivalent
        total_monthly += monthly_equiv

        freq = rg.frequency
        if freq not in by_frequency:
            by_frequency[freq] = {'count': 0, 'monthly_total': 0}
        by_frequency[freq]['count'] += 1
        by_frequency[freq]['monthly_total'] += monthly_equiv

        rg_list.append({
            'id': str(rg.id),
            'contact_id': str(rg.donor_contact.id),
            'contact_name': rg.donor_contact.full_name,
            'amount': float(rg.amount_dollars),
            'frequency': rg.frequency,
            'monthly_equivalent': round(monthly_equiv, 2),
            'start_date': rg.start_date.isoformat(),
        })

    return {
        'pledges': rg_list,
        'total_monthly': round(total_monthly, 2),
        'total_annual': round(total_monthly * 12, 2),
        'active_count': len(rg_list),
        'by_frequency': [
            {
                'frequency': freq,
                'count': data['count'],
                'monthly_total': round(data['monthly_total'], 2),
            }
            for freq, data in by_frequency.items()
        ],
    }


def get_late_donations(user, limit=50):
    """
    Get late donations. RecurringGift has no is_late field, so this returns
    an empty structure. Kept for API compatibility.
    """
    return {'late_donations': [], 'total_count': 0}


def get_follow_ups(user, limit=50, request=None):
    """
    Get incomplete tasks ordered by due date (oldest first).
    """
    tasks = _scope_tasks(user, request=request)

    follow_ups = tasks.filter(
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
    ).select_related('contact', 'owner').order_by('due_date', '-priority')[:limit]

    today = date.today()

    return {
        'tasks': [{
            'id': str(t.id),
            'title': t.title,
            'description': t.description,
            'task_type': t.task_type,
            'priority': t.priority,
            'status': t.status,
            'due_date': t.due_date.isoformat(),
            'is_overdue': t.due_date < today,
            'contact_id': str(t.contact.id) if t.contact else None,
            'contact_name': t.contact.full_name if t.contact else None,
        } for t in follow_ups],
        'total_count': tasks.filter(status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]).count(),
        'overdue_count': tasks.filter(
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
            due_date__lt=today
        ).count(),
    }


def get_transactions(user, limit=100, offset=0, contact_id=None, date_from=None, date_to=None):
    """
    Get full transaction ledger (gifts).
    Admin/finance-only endpoint.
    """
    gifts = Gift.objects.all().select_related('donor_contact')

    # Apply filters
    if contact_id:
        gifts = gifts.filter(donor_contact_id=contact_id)
    if date_from:
        gifts = gifts.filter(gift_date__gte=date_from)
    if date_to:
        gifts = gifts.filter(gift_date__lte=date_to)

    total_count = gifts.count()
    transactions = gifts.order_by('-gift_date', '-created_at')[offset:offset + limit]

    return {
        'transactions': [{
            'id': str(d.id),
            'contact_id': str(d.donor_contact.id),
            'contact_name': d.donor_contact.full_name,
            'amount': float(d.amount_dollars),
            'date': d.gift_date.isoformat(),
            'notes': d.description,
        } for d in transactions],
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
    }


# Admin Analytics Endpoints (Phase 13)


def get_dashboard_overview(date_from=None, date_to=None):
    """
    Admin dashboard overview with cross-user aggregated stats.
    No user scoping — admin sees all data.
    Target: <10 queries.

    Args:
        date_from: Start date (YYYY-MM-DD string) for filtering
        date_to: End date (YYYY-MM-DD string) for filtering
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)

    # Filter contacts by created_at if date range provided
    contacts_qs = Contact.objects.all()
    if dt_from:
        contacts_qs = contacts_qs.filter(created_at__gte=dt_from)
    if dt_to:
        contacts_qs = contacts_qs.filter(created_at__lt=dt_to)
    total_contacts = contacts_qs.count()

    # Filter journals by created_at if date range provided
    journals_qs = Journal.objects.filter(is_archived=False)
    if dt_from:
        journals_qs = journals_qs.filter(created_at__gte=dt_from)
    if dt_to:
        journals_qs = journals_qs.filter(created_at__lt=dt_to)
    active_journals = journals_qs.count()

    # Stalled contacts count (last journal activity >14 days ago)
    # If date_to provided, use it as "now" for stalled calculation
    cutoff_date = (dt_to if dt_to else timezone.now()) - timedelta(days=14)
    last_activity = JournalStageEvent.objects.filter(
        journal_contact__contact=OuterRef('pk')
    ).order_by('-created_at').values('created_at')[:1]

    stalled_qs = Contact.objects.annotate(
        last_activity_date=Subquery(last_activity)
    ).filter(
        Q(last_activity_date__lt=cutoff_date) | Q(last_activity_date__isnull=True),
        # Only count contacts that are in at least one journal
        journal_memberships__isnull=False
    ).distinct()
    stalled_count = stalled_qs.count()

    # Conversion rate: contacts with a Decision / total contacts in journals
    contacts_in_journals = JournalContact.objects.values('contact').distinct().count()
    contacts_with_decision = Decision.objects.values('journal_contact__contact').distinct().count()
    conversion_rate = round(
        (contacts_with_decision / contacts_in_journals * 100) if contacts_in_journals > 0 else 0,
        1
    )

    # Gift summary - filter by date range if provided, else default to last 12 months
    if dt_from or dt_to:
        gift_qs = Gift.objects.all()
        if dt_from:
            gift_qs = gift_qs.filter(gift_date__gte=dt_from.date())
        if dt_to:
            gift_qs = gift_qs.filter(gift_date__lt=dt_to.date())
    else:
        twelve_months_ago = date.today() - relativedelta(months=12)
        gift_qs = Gift.objects.filter(gift_date__gte=twelve_months_ago)

    gift_stats = gift_qs.aggregate(
        total_amount=Sum('amount_cents'),
        total_count=Count('id')
    )

    return {
        'total_contacts': total_contacts,
        'active_journals': active_journals,
        'stalled_contacts': stalled_count,
        'conversion_rate': conversion_rate,
        'donations_12m': {
            'total_amount': float((gift_stats['total_amount'] or 0)) / 100,
            'total_count': gift_stats['total_count'] or 0,
        },
    }


def get_stalled_contacts(limit=50, offset=0, sort_by='days_stalled', sort_dir='desc', date_from=None, date_to=None):
    """
    Find contacts with last journal activity >14 days ago.
    Uses Subquery annotation per requirement API-04.
    Returns paginated results.
    Target: <5 queries.

    Args:
        limit: Max results to return
        offset: Pagination offset
        sort_by: Field to sort by (days_stalled, full_name, owner_name, last_activity_date)
        sort_dir: Sort direction (asc or desc)
        date_from: Start date (YYYY-MM-DD string) for filtering last_activity_date
        date_to: End date (YYYY-MM-DD string) - if provided, used as "now" for stalled calculation
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)

    last_activity = JournalStageEvent.objects.filter(
        journal_contact__contact=OuterRef('pk')
    ).order_by('-created_at').values('created_at')[:1]

    # Subquery for earliest journal membership date (for zero-activity contacts)
    journal_membership_date = JournalContact.objects.filter(
        contact=OuterRef('pk')
    ).order_by('created_at').values('created_at')[:1]

    # Use date_to as "now" if provided, else current time
    cutoff_date = (dt_to if dt_to else timezone.now()) - timedelta(days=14)

    base_qs = Contact.objects.annotate(
        last_activity_date=Subquery(last_activity),
        journal_membership_date=Subquery(journal_membership_date),
    ).filter(
        Q(last_activity_date__lt=cutoff_date) | Q(last_activity_date__isnull=True),
        journal_memberships__isnull=False
    ).distinct().select_related('owner')

    # Apply date range filter on last_activity_date if provided
    if dt_from:
        base_qs = base_qs.filter(
            Q(last_activity_date__gte=dt_from) | Q(last_activity_date__isnull=True)
        )

    total_count = base_qs.count()

    # Define allowed sort fields (security: prevent arbitrary field ordering)
    SORT_FIELDS = {
        'days_stalled': Coalesce('last_activity_date', 'journal_membership_date', Value('1970-01-01')),
        'full_name': 'first_name',
        'owner_name': 'owner__first_name',
        'last_activity_date': Coalesce('last_activity_date', Value('1970-01-01')),
    }

    # Apply sorting
    sort_field = SORT_FIELDS.get(sort_by, SORT_FIELDS['days_stalled'])

    # For days_stalled: older date = more stalled, so desc on days_stalled = asc on date
    # For date fields, we need to invert the direction
    if sort_by in ('days_stalled', 'last_activity_date'):
        # Invert direction for date-based sorting
        effective_dir = 'asc' if sort_dir == 'desc' else 'desc'
    else:
        effective_dir = sort_dir

    if hasattr(sort_field, 'asc'):
        # Expression object (Coalesce)
        ordering = sort_field.asc() if effective_dir == 'asc' else sort_field.desc()
    else:
        # String field name
        ordering = sort_field if effective_dir == 'asc' else f'-{sort_field}'

    # Apply pagination (limit=None means no limit for CSV export)
    if limit is not None:
        stalled = base_qs.order_by(ordering)[offset:offset + limit]
    else:
        stalled = base_qs.order_by(ordering)[offset:]

    # Use dt_to as reference point if provided, else current time
    reference_time = dt_to if dt_to else timezone.now()

    return {
        'stalled_contacts': [
            {
                'id': str(c.id),
                'full_name': c.full_name,
                'email': c.email,
                'owner_email': c.owner.email,
                'owner_name': f'{c.owner.first_name} {c.owner.last_name}'.strip(),
                'last_activity_date': c.last_activity_date.isoformat() if c.last_activity_date else None,
                'days_stalled': (
                    (reference_time - c.last_activity_date).days
                    if c.last_activity_date
                    else (reference_time - c.journal_membership_date).days
                    if c.journal_membership_date
                    else None
                ),
                'status': c.status,
            }
            for c in stalled
        ],
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
    }


def get_user_performance():
    """
    Per-missionary performance metrics aggregated at database level.
    Target: <10 queries.
    """
    # Subquery for gift totals per user (cents)
    gift_totals = Gift.objects.filter(
        donor_contact__owner=OuterRef('pk')
    ).values('donor_contact__owner').annotate(
        total=Sum('amount_cents')
    ).values('total')

    # Subquery for gift counts per user
    gift_counts = Gift.objects.filter(
        donor_contact__owner=OuterRef('pk')
    ).values('donor_contact__owner').annotate(
        count=Count('id')
    ).values('count')

    # Subquery for decision counts per user
    decision_counts = Decision.objects.filter(
        journal_contact__journal__owner=OuterRef('pk')
    ).values('journal_contact__journal__owner').annotate(
        count=Count('id')
    ).values('count')

    # Subquery for count of distinct contacts with decisions per user
    # Count the number of distinct contact IDs that have decisions for this user's journals
    contacts_with_decisions_subquery = Decision.objects.filter(
        journal_contact__journal__owner=OuterRef('pk')
    ).values('journal_contact__contact').distinct()

    users = User.objects.filter(
        role__in=['missionary', 'admin']
    ).annotate(
        total_contacts=Count('contacts', distinct=True),
        active_journals=Count(
            'journals',
            filter=Q(journals__is_archived=False),
            distinct=True
        ),
        total_gift_amount_cents=Coalesce(
            Subquery(gift_totals, output_field=IntegerField()),
            0
        ),
        gift_count=Coalesce(
            Subquery(gift_counts, output_field=IntegerField()),
            0
        ),
        decisions_logged=Coalesce(
            Subquery(decision_counts, output_field=IntegerField()),
            0
        ),
        _contacts_with_decisions=Count(
            'journals__journal_contacts__decisions__journal_contact__contact',
            distinct=True
        ),
    ).order_by('-total_contacts')

    result = []
    for user in users:
        conversion_rate = round(
            (user._contacts_with_decisions / user.total_contacts * 100) if user.total_contacts > 0 else 0,
            1
        )

        result.append({
            'id': str(user.id),
            'email': user.email,
            'name': f'{user.first_name} {user.last_name}'.strip(),
            'role': user.role,
            'total_contacts': user.total_contacts,
            'active_journals': user.active_journals,
            'decisions_logged': user.decisions_logged,
            'conversion_rate': conversion_rate,
            'total_donations': float(user.total_gift_amount_cents or 0) / 100,
            'donation_count': user.gift_count,
        })

    return {'users': result}


def get_conversion_funnel(date_from=None, date_to=None):
    """
    Pipeline stage distribution with counts and percentages across all missionaries.
    Reuses existing Journal 6-stage pipeline (PipelineStage).
    Target: <5 queries.

    Args:
        date_from: Start date (YYYY-MM-DD string) for filtering stage events
        date_to: End date (YYYY-MM-DD string) for filtering stage events
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)

    # Subquery to get most recent stage per journal_contact (with date filtering)
    stage_events_qs = JournalStageEvent.objects.all()
    if dt_from:
        stage_events_qs = stage_events_qs.filter(created_at__gte=dt_from)
    if dt_to:
        stage_events_qs = stage_events_qs.filter(created_at__lt=dt_to)

    latest_stage = stage_events_qs.filter(
        journal_contact=OuterRef('pk')
    ).order_by('-created_at').values('stage')[:1]

    # Annotate each journal_contact with current stage, aggregate counts
    breakdown = JournalContact.objects.annotate(
        current_stage=Subquery(latest_stage)
    ).values('current_stage').annotate(
        count=Count('id')
    ).order_by('current_stage')

    total = sum(item['count'] for item in breakdown)

    # Build ordered result using PipelineStage order
    stage_order = [s.value for s in PipelineStage]
    stage_labels = {s.value: s.label for s in PipelineStage}
    stage_counts = {item['current_stage']: item['count'] for item in breakdown}

    funnel = []
    for stage_value in stage_order:
        count = stage_counts.get(stage_value, 0)
        funnel.append({
            'stage': stage_value,
            'label': stage_labels.get(stage_value, stage_value),
            'count': count,
            'percentage': round((count / total * 100) if total > 0 else 0, 1),
        })

    # Include contacts with no stage events (null current_stage)
    null_count = stage_counts.get(None, 0)
    if null_count > 0:
        funnel.append({
            'stage': None,
            'label': 'No Activity',
            'count': null_count,
            'percentage': round((null_count / total * 100) if total > 0 else 0, 1),
        })

    return {
        'funnel': funnel,
        'total_contacts_in_pipeline': total,
    }


def get_team_activity(limit=50, date_from=None, date_to=None):
    """
    Recent activity across all users — journal updates, new contacts, decisions.
    Target: <10 queries.

    Args:
        limit: Max results to return
        date_from: Start date (YYYY-MM-DD string) for filtering events by created_at
        date_to: End date (YYYY-MM-DD string) for filtering events by created_at
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)

    events_qs = Event.objects.all()
    if dt_from:
        events_qs = events_qs.filter(created_at__gte=dt_from)
    if dt_to:
        events_qs = events_qs.filter(created_at__lt=dt_to)

    recent_events = events_qs.select_related(
        'user', 'contact'
    ).order_by('-created_at')[:limit]

    # Count with same filters for total_count
    total_count = events_qs.count()

    return {
        'activities': [
            {
                'id': str(e.id),
                'user_id': str(e.user.id),
                'user_email': e.user.email,
                'user_name': f'{e.user.first_name} {e.user.last_name}'.strip(),
                'event_type': e.event_type,
                'title': e.title,
                'message': e.message,
                'severity': e.severity,
                'contact_id': str(e.contact.id) if e.contact else None,
                'contact_name': e.contact.full_name if e.contact else None,
                'created_at': e.created_at.isoformat(),
            }
            for e in recent_events
        ],
        'total_count': total_count,
    }


def get_team_trends(weeks=12, date_from=None, date_to=None):
    """
    Get team activity trends over past N weeks.
    Returns weekly aggregated metrics: decisions logged, donations received, stage progressions.
    Cross-user aggregation (no user parameter) — admin sees all data.
    Target: <10 queries.

    Args:
        weeks: Number of weeks to return (default 12)
        date_from: Start date (YYYY-MM-DD string) - if provided, compute weekly buckets within range
        date_to: End date (YYYY-MM-DD string) - if provided, compute weekly buckets within range

    Returns:
        Dictionary with 'trends' list and 'weeks' count
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)

    # Calculate date range
    if dt_from and dt_to:
        # Use provided range
        start_date = dt_from.date()
        end_date = dt_to.date()
        # Calculate weeks from range
        weeks = max(1, ((end_date - start_date).days // 7) + 1)
        # Align to Monday
        days_since_monday = start_date.weekday()
        start_date = start_date - timedelta(days=days_since_monday)
    else:
        # Default: past N weeks from today
        today = timezone.now().date()
        # Get Monday of current week
        days_since_monday = today.weekday()
        current_week_monday = today - timedelta(days=days_since_monday)
        start_date = current_week_monday - timedelta(weeks=weeks - 1)

    # Query decisions by week
    decisions_by_week = Decision.objects.filter(
        created_at__gte=start_date
    ).annotate(
        week=TruncWeek('created_at')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')

    # Query gifts by week
    gifts_by_week = Gift.objects.filter(
        gift_date__gte=start_date
    ).annotate(
        week=TruncWeek('gift_date')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')

    # Query stage progressions by week
    stage_events_by_week = JournalStageEvent.objects.filter(
        created_at__gte=start_date
    ).annotate(
        week=TruncWeek('created_at')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')

    # Build maps for quick lookup
    # Note: TruncWeek on DateTimeField returns datetime, on DateField returns date
    def normalize_to_date(dt):
        """Convert datetime or date to date object."""
        return dt.date() if hasattr(dt, 'date') and callable(dt.date) else dt

    decisions_map = {normalize_to_date(item['week']): item['count'] for item in decisions_by_week}
    gifts_map = {normalize_to_date(item['week']): item['count'] for item in gifts_by_week}
    stage_events_map = {normalize_to_date(item['week']): item['count'] for item in stage_events_by_week}

    # Build complete week list (fill gaps with 0)
    result = []
    for week_num in range(weeks):
        week_start = start_date + timedelta(weeks=week_num)
        # Format label (e.g., "Feb 3")
        week_label = week_start.strftime('%b %-d')

        result.append({
            'week_start': week_start.isoformat(),
            'week_label': week_label,
            'decisions_logged': decisions_map.get(week_start, 0),
            'donations_received': gifts_map.get(week_start, 0),
            'stage_progressions': stage_events_map.get(week_start, 0),
        })

    return {
        'trends': result,
        'weeks': weeks,
    }


def get_user_trends(user_id, weeks=12):
    """
    Get user activity trends over past N weeks for a specific user.
    Returns weekly aggregated metrics: decisions logged, gifts received, stage progressions.
    User-scoped aggregation (filters by user_id) — admin sees data for one missionary.
    Target: <10 queries.

    Args:
        user_id: User ID to filter by
        weeks: Number of weeks to return (default 12)

    Returns:
        Dictionary with 'trends' list and 'weeks' count
    """
    # Calculate date range
    today = timezone.now().date()
    # Get Monday of current week
    days_since_monday = today.weekday()
    current_week_monday = today - timedelta(days=days_since_monday)
    start_date = current_week_monday - timedelta(weeks=weeks - 1)

    # Query decisions by week for this user
    decisions_by_week = Decision.objects.filter(
        journal_contact__journal__owner_id=user_id,
        created_at__gte=start_date
    ).annotate(
        week=TruncWeek('created_at')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')

    # Query gifts by week for this user
    gifts_by_week = Gift.objects.filter(
        donor_contact__owner_id=user_id,
        gift_date__gte=start_date
    ).annotate(
        week=TruncWeek('gift_date')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')

    # Query stage progressions by week for this user
    stage_events_by_week = JournalStageEvent.objects.filter(
        journal_contact__journal__owner_id=user_id,
        created_at__gte=start_date
    ).annotate(
        week=TruncWeek('created_at')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')

    # Build maps for quick lookup
    # Note: TruncWeek on DateTimeField returns datetime, on DateField returns date
    def normalize_to_date(dt):
        """Convert datetime or date to date object."""
        return dt.date() if hasattr(dt, 'date') and callable(dt.date) else dt

    decisions_map = {normalize_to_date(item['week']): item['count'] for item in decisions_by_week}
    gifts_map = {normalize_to_date(item['week']): item['count'] for item in gifts_by_week}
    stage_events_map = {normalize_to_date(item['week']): item['count'] for item in stage_events_by_week}

    # Build complete week list (fill gaps with 0)
    result = []
    for week_num in range(weeks):
        week_start = start_date + timedelta(weeks=week_num)
        # Format label (e.g., "Feb 3")
        week_label = week_start.strftime('%b %-d')

        result.append({
            'week_start': week_start.isoformat(),
            'week_label': week_label,
            'decisions_logged': decisions_map.get(week_start, 0),
            'donations_received': gifts_map.get(week_start, 0),
            'stage_progressions': stage_events_map.get(week_start, 0),
        })

    return {
        'trends': result,
        'weeks': weeks,
    }


def get_user_journals(user_id):
    """
    Get journals for a specific user with progress indicators.
    Returns journal list with member count, decision count, and active member count.
    User-scoped (filters by user_id) — admin sees data for one missionary.
    Target: <5 queries.

    Args:
        user_id: User ID to filter by

    Returns:
        Dictionary with 'journals' list
    """
    journals = Journal.objects.filter(
        owner_id=user_id,
        is_archived=False
    ).annotate(
        member_count=Count('journal_contacts', distinct=True),
        decision_count=Count('journal_contacts__decisions', distinct=True),
        active_member_count=Count(
            'journal_contacts',
            filter=Q(journal_contacts__decisions__isnull=False),
            distinct=True
        )
    ).order_by('-created_at')

    return {
        'journals': [
            {
                'id': str(j.id),
                'name': j.name,
                'member_count': j.member_count,
                'decision_count': j.decision_count,
                'active_member_count': j.active_member_count,
                'created_at': j.created_at.isoformat(),
            }
            for j in journals
        ]
    }


def get_stage_contacts(stage, limit=100):
    """
    Get contacts currently in a given pipeline stage.
    Returns contacts with their current stage from JournalStageEvent.
    Admin-only function (no user scoping) — admin sees all contacts.
    Target: <5 queries.

    Args:
        stage: PipelineStage value (string) or None for "No Activity" (contacts with no stage events)
        limit: Max results to return (default 100)

    Returns:
        Dictionary with 'contacts' list and 'total_count'
    """
    # Subquery to get most recent stage per journal_contact
    latest_stage = JournalStageEvent.objects.filter(
        journal_contact=OuterRef('pk')
    ).order_by('-created_at').values('stage')[:1]

    # Subquery for last activity date (most recent stage event)
    last_activity = JournalStageEvent.objects.filter(
        journal_contact__contact=OuterRef('pk')
    ).order_by('-created_at').values('created_at')[:1]

    # Get JournalContacts with current stage annotation
    journal_contacts_qs = JournalContact.objects.annotate(
        current_stage=Subquery(latest_stage, output_field=CharField())
    )

    # Filter by stage (handle None for "No Activity")
    if stage is None or stage == 'none':
        # Contacts with no stage events
        journal_contacts_qs = journal_contacts_qs.filter(current_stage__isnull=True)
    else:
        # Contacts in the specified stage
        journal_contacts_qs = journal_contacts_qs.filter(current_stage=stage)

    # Get distinct contact IDs from matching JournalContacts
    contact_ids = journal_contacts_qs.values_list('contact_id', flat=True).distinct()

    # Count total before applying limit
    total_count = contact_ids.count()

    # Get Contact objects with owner and last activity
    contacts = Contact.objects.filter(
        id__in=contact_ids[:limit]
    ).annotate(
        last_activity_date=Subquery(last_activity)
    ).select_related('owner')

    return {
        'contacts': [
            {
                'id': str(c.id),
                'full_name': c.full_name,
                'email': c.email,
                'owner_name': f'{c.owner.first_name} {c.owner.last_name}'.strip(),
                'last_activity_date': c.last_activity_date.isoformat() if c.last_activity_date else None,
            }
            for c in contacts
        ],
        'total_count': total_count,
        'stage': stage or 'none',
    }


def get_user_drilldown(user_id):
    """
    Get combined summary for quick user inspection (user drilldown panel).
    Returns user info, key stats, stalled count, and recent journals.
    Admin-only function (no user scoping) — admin sees specific user data.
    Target: <15 queries.

    Args:
        user_id: User ID to get drilldown data for

    Returns:
        Dictionary with 'user', 'stats', and 'journals' or error dict if user not found
    """
    # Fetch user object
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {'detail': 'User not found'}

    # Per-user stats (reusing patterns from get_user_performance)
    total_contacts = Contact.objects.filter(owner_id=user_id).count()
    active_journals = Journal.objects.filter(owner_id=user_id, is_archived=False).count()
    decisions_logged = Decision.objects.filter(journal_contact__journal__owner_id=user_id).count()

    # Conversion rate: contacts with decisions / total contacts * 100
    contacts_with_decision = Decision.objects.filter(
        journal_contact__journal__owner_id=user_id
    ).values('journal_contact__contact').distinct().count()
    conversion_rate = round(
        (contacts_with_decision / total_contacts * 100) if total_contacts > 0 else 0,
        1
    )

    # Gift stats
    gift_stats = Gift.objects.filter(
        donor_contact__owner_id=user_id
    ).aggregate(
        total_amount_cents=Sum('amount_cents'),
        gift_count=Count('id')
    )

    # Stalled contact count for this user (last journal activity >14 days ago)
    cutoff_date = timezone.now() - timedelta(days=14)
    last_activity = JournalStageEvent.objects.filter(
        journal_contact__contact=OuterRef('pk')
    ).order_by('-created_at').values('created_at')[:1]

    stalled_count = Contact.objects.filter(
        owner_id=user_id
    ).annotate(
        last_activity_date=Subquery(last_activity)
    ).filter(
        Q(last_activity_date__lt=cutoff_date) | Q(last_activity_date__isnull=True),
        journal_memberships__isnull=False
    ).distinct().count()

    # Recent journals (top 5, non-archived) with annotations
    recent_journals = Journal.objects.filter(
        owner_id=user_id,
        is_archived=False
    ).annotate(
        member_count=Count('journal_contacts', distinct=True),
        decision_count=Count('journal_contacts__decisions', distinct=True),
        active_member_count=Count(
            'journal_contacts',
            filter=Q(journal_contacts__decisions__isnull=False),
            distinct=True
        )
    ).order_by('-created_at')[:5]

    return {
        'user': {
            'id': str(user.id),
            'name': f'{user.first_name} {user.last_name}'.strip(),
            'email': user.email,
            'role': user.role,
        },
        'stats': {
            'total_contacts': total_contacts,
            'active_journals': active_journals,
            'decisions_logged': decisions_logged,
            'conversion_rate': conversion_rate,
            'total_donations': float((gift_stats['total_amount_cents'] or 0)) / 100,
            'donation_count': gift_stats['gift_count'] or 0,
            'stalled_contacts': stalled_count,
        },
        'journals': [
            {
                'id': str(j.id),
                'name': j.name,
                'member_count': j.member_count,
                'decision_count': j.decision_count,
                'active_member_count': j.active_member_count,
                'created_at': j.created_at.isoformat(),
            }
            for j in recent_journals
        ]
    }


def get_pace_calculation(date_from=None, date_to=None):
    """
    Calculate average days between consecutive stage transitions for contacts.
    Returns overall average pace across all contacts.
    Target: <10 queries.

    Args:
        date_from: Start date (YYYY-MM-DD string) for filtering stage events
        date_to: End date (YYYY-MM-DD string) for filtering stage events

    Returns:
        Dictionary with 'average_days_between_stages' (float or None)
    """
    dt_from, dt_to = _parse_date_range(date_from, date_to)

    # Query stage events with date filtering if provided
    stage_events_qs = JournalStageEvent.objects.all()
    if dt_from:
        stage_events_qs = stage_events_qs.filter(created_at__gte=dt_from)
    if dt_to:
        stage_events_qs = stage_events_qs.filter(created_at__lt=dt_to)

    # Get all stage events ordered by journal_contact and created_at
    stage_events = stage_events_qs.order_by(
        'journal_contact_id', 'created_at'
    ).values('journal_contact_id', 'created_at')

    # Calculate intervals between consecutive events for each contact
    intervals = []
    prev_contact_id = None
    prev_time = None

    for event in stage_events:
        contact_id = event['journal_contact_id']
        created_at = event['created_at']

        if contact_id == prev_contact_id and prev_time:
            # Calculate interval in days
            interval = (created_at - prev_time).days
            if interval > 0:  # Only count positive intervals
                intervals.append(interval)

        prev_contact_id = contact_id
        prev_time = created_at

    # Calculate average
    if intervals:
        average_pace = sum(intervals) / len(intervals)
        return {
            'average_days_between_stages': round(average_pace, 1),
            'total_intervals': len(intervals),
        }
    else:
        return {
            'average_days_between_stages': None,
            'total_intervals': 0,
        }
