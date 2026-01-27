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
class TestGetLateDonations:
    """Tests for get_late_donations function."""

    def test_get_late_donations(self):
        """Test getting late donations returns late active pledges."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)

        # Create a late active pledge
        PledgeFactory(
            contact=contact,
            is_late=True,
            days_late=15,
            frequency='monthly',
        )

        result = get_late_donations(user)

        assert len(result) == 1
        assert result[0]['contact_name'] == contact.full_name
        assert result[0]['days_late'] == 15

    def test_get_late_donations_excludes_non_late_pledges(self):
        """Test that on-track pledges don't appear."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)

        # Create an on-time pledge
        PledgeFactory(contact=contact, is_late=False)

        result = get_late_donations(user)

        assert len(result) == 0


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
        assert 'late_donations' in result
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
