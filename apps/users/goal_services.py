"""
Service functions for Goal tracking calculations.
"""
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.core.fiscal_year import fiscal_year_start, months_remaining
from apps.core.gift_utils import _monthly_equivalent_aggregate
from apps.gifts.models import Gift, RecurringGift, RecurringGiftStatus
from apps.journals.models import JournalContact, JournalStageEvent
from apps.users.models import GoalJournalSelection


def get_goal_progress(user):
    """
    Calculate effective monthly support from user's selected journals.

    Effective monthly support = recurring monthly equivalent (from active RecurringGifts)
    + (fiscal-year one-time gifts / months remaining in fiscal year).

    Returns:
        dict with keys:
            monthly_support_goal_cents (int)
            goal_weeks (int)
            selected_journal_ids (list[str])
            effective_monthly_support (float, dollars)
            recurring_monthly (float, dollars)
            one_time_monthly (float, dollars)
    """
    today = date.today()

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
            'calls_count': 0,
            'meetings_count': 0,
        }

    # Contact IDs in selected journals — enforce journal ownership scoping
    contact_ids = list(
        JournalContact.objects.filter(
            journal__in=selected_journal_ids,
            journal__owner=user,
        ).values_list('contact_id', flat=True)
    )

    # 1. Recurring: SQL aggregate of active recurring gifts from journal contacts
    active_recurring = RecurringGift.objects.filter(
        donor_contact_id__in=contact_ids,
        status=RecurringGiftStatus.ACTIVE,
    )
    recurring_monthly = float(_monthly_equivalent_aggregate(active_recurring))

    # 2. One-time: fiscal year gifts / months remaining (minimum 1 to avoid zero division)
    fy_start = fiscal_year_start(today)
    fy_gifts_cents = (
        Gift.objects.filter(
            donor_contact_id__in=contact_ids,
            gift_date__gte=fy_start,
            gift_date__lte=today,
        ).aggregate(total=Sum('amount_cents'))['total'] or 0
    )
    fy_gifts_dollars = float(Decimal(fy_gifts_cents) / Decimal(100))
    mo_remaining = months_remaining(today)
    one_time_monthly = fy_gifts_dollars / mo_remaining

    effective = recurring_monthly + one_time_monthly

    # Activity counts: count JournalStageEvents via journal_contact__journal_id__in
    calls_count = JournalStageEvent.objects.filter(
        journal_contact__journal_id__in=selected_journal_ids,
        event_type='call_logged',
    ).count()
    meetings_count = JournalStageEvent.objects.filter(
        journal_contact__journal_id__in=selected_journal_ids,
        event_type='meeting_completed',
    ).count()

    return {
        'monthly_support_goal_cents': user.monthly_support_goal_cents,
        'goal_weeks': user.goal_weeks,
        'selected_journal_ids': [str(jid) for jid in selected_journal_ids],
        'effective_monthly_support': round(effective, 2),
        'recurring_monthly': round(recurring_monthly, 2),
        'one_time_monthly': round(one_time_monthly, 2),
        'calls_count': calls_count,
        'meetings_count': meetings_count,
    }
