"""
Tests for dashboard service functions.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.contacts.tests.factories import ContactFactory
from apps.dashboard.services import (
    get_dashboard_summary,
    get_late_donations,
    get_needs_attention,
    get_recent_gifts,
    get_support_progress,
    get_thank_you_queue,
    get_what_changed,
)
from apps.events.tests.factories import EventFactory
from apps.gifts.tests.factories import GiftFactory, RecurringGiftFactory
from apps.tasks.tests.factories import OverdueTaskFactory, TaskFactory
from apps.users.tests.factories import AdminUserFactory, UserFactory


@pytest.mark.django_db
class TestGetWhatChanged:
    """Tests for get_what_changed function."""

    def test_get_what_changed_with_events(self):
        """Test getting what changed with new events."""
        user = UserFactory()
        EventFactory.create_batch(3, user=user, is_new=True)
        EventFactory.create_batch(2, user=user, is_new=False)

        result = get_what_changed(user)

        assert result['total_new'] == 3
        assert len(result['recent_events']) <= 10

    def test_get_what_changed_no_events(self):
        """Test getting what changed with no events."""
        user = UserFactory()

        result = get_what_changed(user)

        assert result['total_new'] == 0


@pytest.mark.django_db
class TestGetNeedsAttention:
    """Tests for get_needs_attention function."""

    def test_get_needs_attention_late_pledges_always_zero(self):
        """Test that late_pledge_count is always 0 (RecurringGift has no is_late)."""
        user = UserFactory(role='missionary')

        result = get_needs_attention(user)

        assert result['late_pledge_count'] == 0

    def test_get_needs_attention_overdue_tasks(self):
        """Test getting needs attention with overdue tasks."""
        user = UserFactory(role='missionary')
        OverdueTaskFactory(owner=user)

        result = get_needs_attention(user)

        assert result['overdue_task_count'] == 1

    def test_get_needs_attention_thank_you_needed(self):
        """Test getting needs attention with thank-you needed."""
        user = UserFactory(role='missionary')
        ContactFactory(owner=user, needs_thank_you=True)

        result = get_needs_attention(user)

        assert result['thank_you_needed_count'] == 1


@pytest.mark.django_db
class TestGetLateDonations:
    """Tests for get_late_donations function."""

    def test_get_late_donations_returns_empty(self):
        """Test that get_late_donations always returns empty list (RecurringGift has no is_late)."""
        user = UserFactory(role='missionary')

        result = get_late_donations(user)

        assert len(result) == 0


@pytest.mark.django_db
class TestGetThankYouQueue:
    """Tests for get_thank_you_queue function."""

    def test_get_thank_you_queue(self):
        """Test getting thank you queue."""
        user = UserFactory(role='missionary')
        ContactFactory.create_batch(2, owner=user, needs_thank_you=True)
        ContactFactory(owner=user, needs_thank_you=False)

        result = get_thank_you_queue(user)

        assert result.count() == 2


@pytest.mark.django_db
class TestGetSupportProgress:
    """Tests for get_support_progress function."""

    def test_get_support_progress(self):
        """Test getting support progress with RecurringGift."""
        user = UserFactory(role='missionary', monthly_goal=Decimal('5000.00'))
        contact = ContactFactory(owner=user)

        # Create $100/month recurring gift (10000 cents)
        RecurringGiftFactory(donor_contact=contact, amount_cents=10000, frequency='monthly')

        result = get_support_progress(user)

        assert result['current_monthly_support'] == 100.0
        assert result['monthly_goal'] == 5000.0
        assert result['percentage'] == 2.0
        assert result['gap'] == 4900.0
        assert result['active_pledge_count'] == 1

    def test_missionary_only_sees_own_contacts_gifts(self):
        """Regression: missionary A must not see missionary B's recurring gifts.

        Root cause investigated: get_visible_user_ids returns {user.id} for
        missionary role, so filter is donor_contact__owner_id__in={A.id}.
        B's contacts are excluded — this verifies correct cross-user isolation.
        """
        missionary_a = UserFactory(role='missionary', monthly_goal=Decimal('5000.00'))
        missionary_b = UserFactory(role='missionary', monthly_goal=Decimal('3000.00'))

        contact_a = ContactFactory(owner=missionary_a)
        contact_b = ContactFactory(owner=missionary_b)

        # A has $100/month recurring gift
        RecurringGiftFactory(donor_contact=contact_a, amount_cents=10000, frequency='monthly')
        # B has $200/month recurring gift — must NOT appear in A's progress
        RecurringGiftFactory(donor_contact=contact_b, amount_cents=20000, frequency='monthly')

        result_a = get_support_progress(missionary_a)

        # A should only see their own $100/month, not B's $200/month
        assert result_a['current_monthly_support'] == 100.0
        assert result_a['active_pledge_count'] == 1

    def test_admin_support_progress_only_shows_own_contacts(self):
        """Regression: admin must only see their own contacts' recurring gifts.

        Bug: get_visible_user_ids returns None for admin, causing
        get_support_progress to use RecurringGift.objects.all() — this
        includes ALL missionaries' recurring gifts in the admin's personal
        Monthly Support Goal tile, inflating current_monthly_support.

        Fix: get_support_progress must scope admin to their own contacts
        (donor_contact__owner=user) so the dashboard shows personal progress only.
        """
        admin = AdminUserFactory(monthly_goal=Decimal('5000.00'))
        # Admin has no contacts or recurring gifts of their own

        # A different missionary has active recurring gifts
        missionary = UserFactory(role='missionary', monthly_goal=Decimal('3000.00'))
        contact = ContactFactory(owner=missionary)
        RecurringGiftFactory(donor_contact=contact, amount_cents=50000, frequency='monthly')

        result = get_support_progress(admin)

        # Admin has no personal donors — their support progress must be $0
        assert result['current_monthly_support'] == 0.0
        assert result['active_pledge_count'] == 0

    def test_bimonthly_gift_monthly_equivalent(self):
        """Regression: BIMONTHLY frequency (every 2 months) gives 0.5x monthly equivalent.

        A $200/bimonthly gift means one $200 payment every 2 months.
        Annual total = 6 x $200 = $1200.
        Monthly equivalent = $1200 / 12 = $100/month.
        Multiplier must be 0.5 (Decimal('1') / Decimal('2')).
        """
        user = UserFactory(role='missionary', monthly_goal=Decimal('5000.00'))
        contact = ContactFactory(owner=user)

        # $200 every 2 months (bimonthly) = $100/month equivalent
        RecurringGiftFactory(donor_contact=contact, amount_cents=20000, frequency='bimonthly')

        result = get_support_progress(user)

        # 20000 cents = $200, bimonthly (every 2 months) * 0.5 = $100/month
        assert result['current_monthly_support'] == 100.0
        assert result['active_pledge_count'] == 1


@pytest.mark.django_db
class TestGetRecentGifts:
    """Tests for get_recent_gifts function."""

    def test_get_recent_gifts(self):
        """Test getting recent gifts."""
        user = UserFactory(role='missionary')
        contact = ContactFactory(owner=user)

        # Recent gift
        GiftFactory(donor_contact=contact, gift_date=timezone.now().date() - timedelta(days=5))

        # Old gift
        GiftFactory(donor_contact=contact, gift_date=timezone.now().date() - timedelta(days=60))

        result = get_recent_gifts(user, days=30)

        assert result.count() == 1


@pytest.mark.django_db
class TestGetDashboardSummary:
    """Tests for get_dashboard_summary function."""

    def test_get_dashboard_summary(self):
        """Test getting complete dashboard summary."""
        user = UserFactory(role='missionary', monthly_goal=Decimal('3000.00'))

        result = get_dashboard_summary(user)

        assert 'what_changed' in result
        assert 'needs_attention' in result
        assert 'late_donations' in result
        assert 'thank_you_queue' in result
        assert 'support_progress' in result
        assert 'recent_gifts' in result

    def test_get_dashboard_summary_returns_serializable_data(self):
        """Test that dashboard summary returns JSON-serializable data."""
        import json

        user = UserFactory(role='missionary')

        result = get_dashboard_summary(user)

        # Should not raise JSONDecodeError
        json_str = json.dumps(result, default=str)
        assert json_str is not None
