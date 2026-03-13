"""
Tests for goal progress service function.
GOAL-04: get_goal_progress(user) computes effective_monthly_support from journal-scoped donations.
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory, RecurringGiftFactory
from apps.users.goal_services import get_goal_progress
from apps.users.models import GoalJournalSelection
from apps.users.tests.factories import UserFactory
from apps.journals.models import Journal, JournalContact


def _make_journal(user, contacts=None):
    """Create a Journal owned by user and optionally link contacts to it."""
    journal = Journal.objects.create(
        owner=user,
        name='Test Journal',
        goal_amount=Decimal('10000.00'),
    )
    for contact in (contacts or []):
        JournalContact.objects.create(journal=journal, contact=contact)
    return journal


def _select_journals(user, journals):
    """Create GoalJournalSelection entries linking user to the given journals."""
    GoalJournalSelection.objects.bulk_create([
        GoalJournalSelection(user=user, journal=j) for j in journals
    ])


@pytest.mark.django_db
def test_goal_progress_no_journals():
    """GOAL-04: When no GoalJournalSelections exist, effective_monthly_support == 0.0."""
    user = UserFactory()
    result = get_goal_progress(user)
    assert result['effective_monthly_support'] == 0.0
    assert result['recurring_monthly'] == 0.0
    assert result['one_time_monthly'] == 0.0
    assert result['selected_journal_ids'] == []


@pytest.mark.django_db
def test_goal_progress_recurring_only():
    """GOAL-04: Journal contacts with active RecurringGifts are summed into recurring_monthly."""
    user = UserFactory()
    contact = ContactFactory(owner=user)
    # $100/month recurring
    RecurringGiftFactory(donor_contact=contact, amount_cents=10000, frequency='monthly')

    journal = _make_journal(user, contacts=[contact])
    _select_journals(user, [journal])

    result = get_goal_progress(user)

    assert result['recurring_monthly'] == 100.0
    assert result['one_time_monthly'] == 0.0
    assert result['effective_monthly_support'] == 100.0


@pytest.mark.django_db
def test_goal_progress_one_time_only():
    """GOAL-04: One-time gifts within the fiscal year are spread over months_remaining."""
    from apps.core.fiscal_year import months_remaining
    user = UserFactory()
    contact = ContactFactory(owner=user)
    today = date.today()
    # $600 gift this fiscal year
    GiftFactory(donor_contact=contact, amount_cents=60000, gift_date=today)

    journal = _make_journal(user, contacts=[contact])
    _select_journals(user, [journal])

    result = get_goal_progress(user)

    expected_monthly = round(600.0 / months_remaining(today), 2)
    assert result['one_time_monthly'] == expected_monthly
    assert result['recurring_monthly'] == 0.0


@pytest.mark.django_db
def test_goal_progress_scoping():
    """GOAL-04: Gifts from contacts NOT in selected journals are excluded."""
    user_a = UserFactory()
    user_b = UserFactory()

    contact_a = ContactFactory(owner=user_a)
    contact_b = ContactFactory(owner=user_b)

    # $200/month recurring for user_b's contact — should NOT appear in user_a's result
    RecurringGiftFactory(donor_contact=contact_b, amount_cents=20000, frequency='monthly')

    journal_a = _make_journal(user_a, contacts=[contact_a])
    _select_journals(user_a, [journal_a])

    result = get_goal_progress(user_a)

    assert result['recurring_monthly'] == 0.0
    assert result['effective_monthly_support'] == 0.0


@pytest.mark.django_db
def test_goal_progress_excludes_cancelled_recurring():
    """Cancelled recurring gifts should not count toward recurring_monthly."""
    from apps.gifts.models import RecurringGiftStatus
    user = UserFactory()
    contact = ContactFactory(owner=user)
    RecurringGiftFactory(donor_contact=contact, amount_cents=10000, frequency='monthly',
                         status=RecurringGiftStatus.CANCELLED)

    journal = _make_journal(user, contacts=[contact])
    _select_journals(user, [journal])

    result = get_goal_progress(user)

    assert result['recurring_monthly'] == 0.0


@pytest.mark.django_db
def test_goal_progress_returns_goal_fields():
    """Result always includes monthly_support_goal_cents and goal_weeks from the user."""
    user = UserFactory(monthly_support_goal_cents=320000, goal_weeks=52)
    result = get_goal_progress(user)

    assert result['monthly_support_goal_cents'] == 320000
    assert result['goal_weeks'] == 52
