"""
Tests for dashboard service functions.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.contacts.models import ContactStatus
from apps.contacts.tests.factories import ContactFactory
from apps.dashboard.services import (
    get_at_risk_donors,
    get_dashboard_summary,
    get_needs_attention,
    get_recent_gifts,
    get_support_progress,
    get_thank_you_queue,
    get_what_changed,
)
from apps.donations.tests.factories import DonationFactory
from apps.events.tests.factories import EventFactory
from apps.pledges.tests.factories import PledgeFactory
from apps.tasks.tests.factories import OverdueTaskFactory, TaskFactory
from apps.users.tests.factories import UserFactory


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

    def test_get_needs_attention_late_pledges(self):
        """Test getting needs attention with late pledges."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        PledgeFactory(contact=contact, is_late=True)

        result = get_needs_attention(user)

        assert result['late_pledge_count'] == 1

    def test_get_needs_attention_overdue_tasks(self):
        """Test getting needs attention with overdue tasks."""
        user = UserFactory(role='staff')
        OverdueTaskFactory(owner=user)

        result = get_needs_attention(user)

        assert result['overdue_task_count'] == 1

    def test_get_needs_attention_thank_you_needed(self):
        """Test getting needs attention with thank-you needed."""
        user = UserFactory(role='staff')
        ContactFactory(owner=user, needs_thank_you=True)

        result = get_needs_attention(user)

        assert result['thank_you_needed_count'] == 1


@pytest.mark.django_db
class TestGetAtRiskDonors:
    """Tests for get_at_risk_donors function."""

    def test_get_at_risk_donors(self):
        """Test getting at-risk donors."""
        user = UserFactory(role='staff')

        # Create at-risk donor (no gift in 60+ days, multiple gifts)
        at_risk = ContactFactory(
            owner=user,
            status=ContactStatus.DONOR,
            last_gift_date=timezone.now().date() - timedelta(days=90),
            gift_count=3
        )

        # Create active donor (recent gift)
        ContactFactory(
            owner=user,
            status=ContactStatus.DONOR,
            last_gift_date=timezone.now().date() - timedelta(days=10),
            gift_count=2
        )

        result = get_at_risk_donors(user)

        assert result.count() == 1
        assert at_risk in result

    def test_get_at_risk_donors_excludes_one_time_givers(self):
        """Test at-risk excludes one-time givers."""
        user = UserFactory(role='staff')

        # One-time giver (gift_count=1) should not be at-risk
        ContactFactory(
            owner=user,
            status=ContactStatus.DONOR,
            last_gift_date=timezone.now().date() - timedelta(days=90),
            gift_count=1
        )

        result = get_at_risk_donors(user)

        assert result.count() == 0


@pytest.mark.django_db
class TestGetThankYouQueue:
    """Tests for get_thank_you_queue function."""

    def test_get_thank_you_queue(self):
        """Test getting thank you queue."""
        user = UserFactory(role='staff')
        ContactFactory.create_batch(2, owner=user, needs_thank_you=True)
        ContactFactory(owner=user, needs_thank_you=False)

        result = get_thank_you_queue(user)

        assert result.count() == 2


@pytest.mark.django_db
class TestGetSupportProgress:
    """Tests for get_support_progress function."""

    def test_get_support_progress(self):
        """Test getting support progress."""
        user = UserFactory(role='staff', monthly_goal=Decimal('5000.00'))
        contact = ContactFactory(owner=user)

        # Create $100/month pledge
        PledgeFactory(contact=contact, amount=Decimal('100.00'), frequency='monthly')

        result = get_support_progress(user)

        assert result['current_monthly_support'] == 100.0
        assert result['monthly_goal'] == 5000.0
        assert result['percentage'] == 2.0
        assert result['gap'] == 4900.0
        assert result['active_pledge_count'] == 1


@pytest.mark.django_db
class TestGetRecentGifts:
    """Tests for get_recent_gifts function."""

    def test_get_recent_gifts(self):
        """Test getting recent gifts."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)

        # Recent donation
        DonationFactory(contact=contact, date=timezone.now().date() - timedelta(days=5))

        # Old donation
        DonationFactory(contact=contact, date=timezone.now().date() - timedelta(days=60))

        result = get_recent_gifts(user, days=30)

        assert result.count() == 1


@pytest.mark.django_db
class TestGetDashboardSummary:
    """Tests for get_dashboard_summary function."""

    def test_get_dashboard_summary(self):
        """Test getting complete dashboard summary."""
        user = UserFactory(role='staff', monthly_goal=Decimal('3000.00'))

        result = get_dashboard_summary(user)

        assert 'what_changed' in result
        assert 'needs_attention' in result
        assert 'at_risk_donors' in result
        assert 'thank_you_queue' in result
        assert 'support_progress' in result
        assert 'recent_gifts' in result

    def test_get_dashboard_summary_returns_serializable_data(self):
        """Test that dashboard summary returns JSON-serializable data."""
        import json

        user = UserFactory(role='staff')

        result = get_dashboard_summary(user)

        # Should not raise JSONDecodeError
        json_str = json.dumps(result, default=str)
        assert json_str is not None
