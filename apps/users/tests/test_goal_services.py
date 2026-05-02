"""
Tests for goal progress service functions.
GOAL-04: get_goal_progress(user) computes effective_monthly_support from journal-scoped donations.
GH-26: get_decisions_progress(user) computes monthly-normalized decision amounts vs journal goal sums.
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory, RecurringGiftFactory
from apps.users.goal_services import get_goal_progress, get_decisions_progress
from apps.users.models import GoalJournalSelection
from apps.users.tests.factories import UserFactory
from apps.journals.models import Decision, Journal, JournalContact


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
    """One-time gifts within the fiscal year are divided by 12."""
    user = UserFactory()
    contact = ContactFactory(owner=user)
    today = date.today()
    # $600 gift this fiscal year
    GiftFactory(donor_contact=contact, amount_cents=60000, gift_date=today)

    journal = _make_journal(user, contacts=[contact])
    _select_journals(user, [journal])

    result = get_goal_progress(user)

    # $600 / 12 = $50/mo
    assert result['one_time_monthly'] == 50.0
    assert result['recurring_monthly'] == 0.0
    assert result['effective_monthly_support'] == 50.0


@pytest.mark.django_db
def test_goal_progress_excludes_recurring_sourced_gifts():
    """Regression: gifts generated from an active recurring pledge must NOT be
    counted in one_time_monthly — they are already represented via
    recurring_monthly. Otherwise pledge payments are double-counted.
    """
    user = UserFactory()
    contact = ContactFactory(owner=user)

    # $100/mo active pledge
    pledge = RecurringGiftFactory(
        donor_contact=contact, amount_cents=10000, frequency='monthly',
    )
    # 3 prior pledge payments this fiscal year ($300 total)
    today = date.today()
    for _ in range(3):
        GiftFactory(donor_contact=contact, amount_cents=10000,
                    gift_date=today, recurring_gift=pledge)

    journal = _make_journal(user, contacts=[contact])
    _select_journals(user, [journal])

    result = get_goal_progress(user)

    # recurring_monthly should be the pledge value; one_time_monthly should be 0
    assert result['recurring_monthly'] == 100.0
    assert result['one_time_monthly'] == 0.0
    assert result['effective_monthly_support'] == 100.0


@pytest.mark.django_db
def test_goal_progress_recurring_plus_one_time():
    """Combined: $100/mo pledge + $1200 one-time = $100 + $100 = $200/mo."""
    user = UserFactory()
    contact = ContactFactory(owner=user)
    today = date.today()

    RecurringGiftFactory(donor_contact=contact, amount_cents=10000, frequency='monthly')
    GiftFactory(donor_contact=contact, amount_cents=120000, gift_date=today)

    journal = _make_journal(user, contacts=[contact])
    _select_journals(user, [journal])

    result = get_goal_progress(user)

    assert result['recurring_monthly'] == 100.0
    assert result['one_time_monthly'] == 100.0
    assert result['effective_monthly_support'] == 200.0


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


# ---------------------------------------------------------------------------
# Tests for get_decisions_progress  (GH-26)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_decisions_progress_no_selected_journals():
    """GH-26: No selected journals returns all zeros."""
    user = UserFactory()
    result = get_decisions_progress(user)
    assert result['decisions_current'] == 0.0
    assert result['decisions_goal'] == 0.0
    assert result['decisions_percentage'] == 0.0


@pytest.mark.django_db
def test_decisions_progress_monthly_and_one_time():
    """GH-26: Monthly $200 active + one_time $1200 pending => $300/mo current, goal=5000."""
    user = UserFactory()
    contact1 = ContactFactory(owner=user)
    contact2 = ContactFactory(owner=user)
    journal = Journal.objects.create(
        owner=user, name='J1', goal_amount=Decimal('5000.00'),
    )
    jc1 = JournalContact.objects.create(journal=journal, contact=contact1)
    jc2 = JournalContact.objects.create(journal=journal, contact=contact2)
    _select_journals(user, [journal])

    Decision.objects.create(journal_contact=jc1, amount=Decimal('200.00'),
                            cadence='monthly', status='active')
    Decision.objects.create(journal_contact=jc2, amount=Decimal('1200.00'),
                            cadence='one_time', status='pending')

    result = get_decisions_progress(user)
    assert result['decisions_current'] == 300.0   # 200 + 1200/12
    assert result['decisions_goal'] == 5000.0
    assert result['decisions_percentage'] == 6.0   # (300/5000)*100 = 6.0


@pytest.mark.django_db
def test_decisions_progress_quarterly():
    """GH-26: Quarterly $300 active => $100/mo."""
    user = UserFactory()
    contact = ContactFactory(owner=user)
    journal = Journal.objects.create(
        owner=user, name='J1', goal_amount=Decimal('10000.00'),
    )
    jc = JournalContact.objects.create(journal=journal, contact=contact)
    _select_journals(user, [journal])

    Decision.objects.create(journal_contact=jc, amount=Decimal('300.00'),
                            cadence='quarterly', status='active')

    result = get_decisions_progress(user)
    assert result['decisions_current'] == 100.0


@pytest.mark.django_db
def test_decisions_progress_annual():
    """GH-26: Annual $1200 active => $100/mo."""
    user = UserFactory()
    contact = ContactFactory(owner=user)
    journal = Journal.objects.create(
        owner=user, name='J1', goal_amount=Decimal('10000.00'),
    )
    jc = JournalContact.objects.create(journal=journal, contact=contact)
    _select_journals(user, [journal])

    Decision.objects.create(journal_contact=jc, amount=Decimal('1200.00'),
                            cadence='annual', status='active')

    result = get_decisions_progress(user)
    assert result['decisions_current'] == 100.0


@pytest.mark.django_db
def test_decisions_progress_excludes_declined_paused():
    """GH-26: Declined and paused decisions are excluded."""
    user = UserFactory()
    contact1 = ContactFactory(owner=user)
    contact2 = ContactFactory(owner=user)
    journal = Journal.objects.create(
        owner=user, name='J1', goal_amount=Decimal('10000.00'),
    )
    jc1 = JournalContact.objects.create(journal=journal, contact=contact1)
    jc2 = JournalContact.objects.create(journal=journal, contact=contact2)
    _select_journals(user, [journal])

    Decision.objects.create(journal_contact=jc1, amount=Decimal('500.00'),
                            cadence='monthly', status='declined')
    Decision.objects.create(journal_contact=jc2, amount=Decimal('500.00'),
                            cadence='monthly', status='paused')

    result = get_decisions_progress(user)
    assert result['decisions_current'] == 0.0


@pytest.mark.django_db
def test_decisions_progress_scoping():
    """GH-26: Only decisions from selected journals are counted."""
    user = UserFactory()
    contact = ContactFactory(owner=user)

    journal_selected = Journal.objects.create(
        owner=user, name='Selected', goal_amount=Decimal('5000.00'),
    )
    journal_other = Journal.objects.create(
        owner=user, name='Other', goal_amount=Decimal('5000.00'),
    )
    jc_selected = JournalContact.objects.create(journal=journal_selected, contact=contact)
    jc_other = JournalContact.objects.create(journal=journal_other, contact=contact)

    # Only select one journal
    _select_journals(user, [journal_selected])

    Decision.objects.create(journal_contact=jc_selected, amount=Decimal('100.00'),
                            cadence='monthly', status='active')
    Decision.objects.create(journal_contact=jc_other, amount=Decimal('999.00'),
                            cadence='monthly', status='active')

    result = get_decisions_progress(user)
    assert result['decisions_current'] == 100.0
    assert result['decisions_goal'] == 5000.0


@pytest.mark.django_db
def test_decisions_progress_multiple_journals_sum_goals():
    """GH-26: Multiple selected journals sum their goal_amounts."""
    user = UserFactory()
    j1 = Journal.objects.create(owner=user, name='J1', goal_amount=Decimal('3000.00'))
    j2 = Journal.objects.create(owner=user, name='J2', goal_amount=Decimal('2000.00'))
    _select_journals(user, [j1, j2])

    result = get_decisions_progress(user)
    assert result['decisions_goal'] == 5000.0
    assert result['decisions_current'] == 0.0
    assert result['decisions_percentage'] == 0.0


@pytest.mark.django_db
def test_goal_api_includes_decisions_fields():
    """GH-26: GET /api/v1/goals/me/ includes decisions_current, decisions_goal, decisions_percentage."""
    from rest_framework.test import APIClient
    user = UserFactory()
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    response = api_client.get('/api/v1/goals/me/')
    assert response.status_code == 200
    data = response.data
    assert 'decisions_current' in data
    assert 'decisions_goal' in data
    assert 'decisions_percentage' in data
