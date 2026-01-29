"""
Service functions for insights/reports data aggregations.
"""
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth, TruncYear

from apps.donations.models import Donation
from apps.pledges.models import Pledge, PledgeStatus
from apps.tasks.models import Task, TaskStatus


def _scope_donations(user):
    """Return donation queryset scoped by user role."""
    if user.role in ['admin', 'finance', 'read_only']:
        return Donation.objects.all()
    return Donation.objects.filter(contact__owner=user)


def _scope_pledges(user):
    """Return pledge queryset scoped by user role."""
    if user.role in ['admin', 'finance', 'read_only']:
        return Pledge.objects.all()
    return Pledge.objects.filter(contact__owner=user)


def _scope_tasks(user):
    """Return task queryset scoped by user role."""
    if user.role == 'admin':
        return Task.objects.all()
    return Task.objects.filter(owner=user)


def get_donations_by_month(user, year=None):
    """
    Get donation totals grouped by month for a given year.
    Defaults to current year.
    """
    if year is None:
        year = date.today().year

    donations = _scope_donations(user)

    monthly_data = (
        donations.filter(date__year=year)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('month')
    )

    # Build complete 12-month list (fill gaps with 0)
    monthly_map = {item['month'].month: item for item in monthly_data}

    result = []
    for month_num in range(1, 13):
        month_date = date(year, month_num, 1)
        month_data = monthly_map.get(month_num, {'total': Decimal('0'), 'count': 0})
        result.append({
            'month': month_date.strftime('%Y-%m'),
            'label': month_date.strftime('%B %Y'),
            'short_label': month_date.strftime('%b'),
            'total': float(month_data['total'] or 0),
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


def get_donations_by_year(user, years=5):
    """
    Get donation totals grouped by year for the last N years.
    """
    current_year = date.today().year
    start_year = current_year - years + 1

    donations = _scope_donations(user)

    yearly_data = (
        donations.filter(date__year__gte=start_year)
        .annotate(year=TruncYear('date'))
        .values('year')
        .annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('year')
    )

    # Build map
    yearly_map = {item['year'].year: item for item in yearly_data}

    result = []
    for year in range(start_year, current_year + 1):
        year_data = yearly_map.get(year, {'total': Decimal('0'), 'count': 0})
        result.append({
            'year': year,
            'total': float(year_data['total'] or 0),
            'count': year_data['count'],
        })

    return {
        'years': result,
        'grand_total': sum(y['total'] for y in result),
        'total_donations': sum(y['count'] for y in result),
    }


def get_monthly_commitments(user):
    """
    Get summary of active recurring pledges with monthly equivalents.
    """
    pledges = _scope_pledges(user)
    active_pledges = pledges.filter(status=PledgeStatus.ACTIVE).select_related('contact')

    # Group by frequency
    by_frequency = {}
    total_monthly = 0

    pledge_list = []
    for pledge in active_pledges:
        monthly_equiv = pledge.monthly_equivalent
        total_monthly += monthly_equiv

        freq = pledge.frequency
        if freq not in by_frequency:
            by_frequency[freq] = {'count': 0, 'monthly_total': 0}
        by_frequency[freq]['count'] += 1
        by_frequency[freq]['monthly_total'] += monthly_equiv

        pledge_list.append({
            'id': str(pledge.id),
            'contact_id': str(pledge.contact.id),
            'contact_name': pledge.contact.full_name,
            'amount': float(pledge.amount),
            'frequency': pledge.frequency,
            'monthly_equivalent': round(monthly_equiv, 2),
            'start_date': pledge.start_date.isoformat(),
            'last_fulfilled_date': pledge.last_fulfilled_date.isoformat() if pledge.last_fulfilled_date else None,
        })

    return {
        'pledges': pledge_list,
        'total_monthly': round(total_monthly, 2),
        'total_annual': round(total_monthly * 12, 2),
        'active_count': len(pledge_list),
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
    Get active pledges that are late (expected gift hasn't arrived).
    """
    pledges = _scope_pledges(user)

    late_pledges = pledges.filter(
        status=PledgeStatus.ACTIVE,
        is_late=True,
    ).select_related('contact').order_by('-days_late')[:limit]

    return {
        'late_donations': [{
            'id': str(p.id),
            'contact_id': str(p.contact.id),
            'contact_name': p.contact.full_name,
            'amount': float(p.amount),
            'frequency': p.frequency,
            'monthly_equivalent': round(p.monthly_equivalent, 2),
            'last_gift_date': p.last_fulfilled_date.isoformat() if p.last_fulfilled_date else None,
            'days_late': p.days_late,
            'next_expected_date': p.next_expected_date.isoformat() if p.next_expected_date else None,
        } for p in late_pledges],
        'total_count': pledges.filter(status=PledgeStatus.ACTIVE, is_late=True).count(),
    }


def get_follow_ups(user, limit=50):
    """
    Get incomplete tasks ordered by due date (oldest first).
    """
    tasks = _scope_tasks(user)

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


def get_review_queue(user):
    """
    Get items pending admin review.
    Admin-only endpoint - returns empty if not admin.
    """
    if user.role != 'admin':
        return {'items': [], 'total_count': 0}

    # Placeholder for review queue items
    # In a real implementation, this would query items flagged for review
    # For now, we'll return contacts needing thank-you as a proxy
    from apps.contacts.models import Contact

    contacts_needing_thankyou = Contact.objects.filter(
        needs_thank_you=True
    ).order_by('-last_gift_date')[:50]

    return {
        'items': [{
            'id': str(c.id),
            'type': 'thank_you',
            'title': f'Send thank you to {c.full_name}',
            'contact_id': str(c.id),
            'contact_name': c.full_name,
            'last_gift_amount': float(c.last_gift_amount) if c.last_gift_amount else None,
            'last_gift_date': c.last_gift_date.isoformat() if c.last_gift_date else None,
        } for c in contacts_needing_thankyou],
        'total_count': Contact.objects.filter(needs_thank_you=True).count(),
    }


def get_transactions(user, limit=100, offset=0, contact_id=None, date_from=None, date_to=None):
    """
    Get full transaction ledger (donations).
    Admin/finance-only endpoint.
    """
    if user.role not in ['admin', 'finance']:
        return {'transactions': [], 'total_count': 0}

    donations = Donation.objects.all().select_related('contact', 'pledge')

    # Apply filters
    if contact_id:
        donations = donations.filter(contact_id=contact_id)
    if date_from:
        donations = donations.filter(date__gte=date_from)
    if date_to:
        donations = donations.filter(date__lte=date_to)

    total_count = donations.count()
    transactions = donations.order_by('-date', '-created_at')[offset:offset + limit]

    return {
        'transactions': [{
            'id': str(d.id),
            'contact_id': str(d.contact.id),
            'contact_name': d.contact.full_name,
            'amount': float(d.amount),
            'date': d.date.isoformat(),
            'donation_type': d.donation_type,
            'payment_method': d.payment_method,
            'pledge_id': str(d.pledge.id) if d.pledge else None,
            'thanked': d.thanked,
            'notes': d.notes,
        } for d in transactions],
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
    }
