"""
Service functions for Goal tracking calculations.
"""
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.core.fiscal_year import fiscal_year_start, months_remaining
from apps.core.gift_utils import _monthly_equivalent_aggregate
from apps.gifts.models import Gift, RecurringGift, RecurringGiftStatus
from apps.journals.models import Decision, Journal, JournalContact, JournalStageEvent
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


# Cadence multipliers for monthly normalization of decisions.
# NOTE: Differs from Decision.monthly_equivalent property which treats ONE_TIME as 0.
# Per GH-26 spec: one-time decisions are divided by 12.
_DECISION_CADENCE_MULTIPLIERS = {
    'one_time': Decimal('1') / Decimal('12'),
    'monthly': Decimal('1'),
    'quarterly': Decimal('1') / Decimal('3'),
    'annual': Decimal('1') / Decimal('12'),
}


def get_decisions_progress(user):
    """
    Calculate monthly-normalized decision amounts vs journal goal sums for the user's
    selected journals.

    Only active + pending decisions are counted. One-time / 12, monthly * 1,
    quarterly / 3, annual / 12.

    Returns:
        dict with keys:
            decisions_current (float, dollars) - sum of monthly-normalized decision amounts
            decisions_goal (float, dollars)    - sum of Journal.goal_amount for selected journals
            decisions_percentage (float)       - (current / goal) * 100, or 0.0 if no goal
    """
    selected_journal_ids = list(
        GoalJournalSelection.objects.filter(user=user)
        .values_list('journal_id', flat=True)
    )

    if not selected_journal_ids:
        return {
            'decisions_current': 0.0,
            'decisions_goal': 0.0,
            'decisions_percentage': 0.0,
        }

    # Sum journal goal amounts (dollars, DecimalField)
    goal_total = (
        Journal.objects.filter(id__in=selected_journal_ids, owner=user)
        .aggregate(total=Sum('goal_amount'))['total']
    ) or Decimal('0')
    decisions_goal = float(goal_total)

    # Query active + pending decisions scoped to selected journals + user ownership
    decisions = Decision.objects.filter(
        journal_contact__journal_id__in=selected_journal_ids,
        journal_contact__journal__owner=user,
        status__in=['active', 'pending'],
    ).values_list('amount', 'cadence')

    # Compute monthly-normalized sum
    monthly_total = Decimal('0')
    for amount, cadence in decisions:
        multiplier = _DECISION_CADENCE_MULTIPLIERS.get(cadence, Decimal('0'))
        monthly_total += amount * multiplier

    decisions_current = float(round(monthly_total, 2))
    decisions_percentage = round((decisions_current / decisions_goal) * 100, 2) if decisions_goal > 0 else 0.0

    return {
        'decisions_current': decisions_current,
        'decisions_goal': decisions_goal,
        'decisions_percentage': decisions_percentage,
    }
