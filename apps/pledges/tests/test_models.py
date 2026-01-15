"""
Tests for Pledge model.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.contacts.tests.factories import ContactFactory
from apps.donations.models import Donation
from apps.pledges.models import Pledge, PledgeFrequency, PledgeStatus
from apps.pledges.tests.factories import (
    AnnualPledgeFactory,
    PledgeFactory,
    QuarterlyPledgeFactory,
)


@pytest.mark.django_db
class TestPledgeModel:
    """Tests for Pledge model methods and properties."""

    def test_pledge_str(self):
        """Test pledge string representation."""
        pledge = PledgeFactory(amount=Decimal('100.00'), frequency=PledgeFrequency.MONTHLY)
        assert '$100.00' in str(pledge)
        assert 'Monthly' in str(pledge)

    def test_monthly_equivalent_monthly(self):
        """Test monthly equivalent for monthly pledge."""
        pledge = PledgeFactory(amount=Decimal('100.00'), frequency=PledgeFrequency.MONTHLY)
        assert pledge.monthly_equivalent == 100.0

    def test_monthly_equivalent_quarterly(self):
        """Test monthly equivalent for quarterly pledge."""
        pledge = QuarterlyPledgeFactory(amount=Decimal('300.00'))
        assert pledge.monthly_equivalent == 100.0

    def test_monthly_equivalent_annual(self):
        """Test monthly equivalent for annual pledge."""
        pledge = AnnualPledgeFactory(amount=Decimal('1200.00'))
        assert pledge.monthly_equivalent == 100.0

    def test_fulfillment_percentage_zero(self):
        """Test fulfillment percentage with zero expected."""
        pledge = PledgeFactory(total_expected=Decimal('0'), total_received=Decimal('0'))
        assert pledge.fulfillment_percentage == 0

    def test_fulfillment_percentage_partial(self):
        """Test fulfillment percentage with partial fulfillment."""
        pledge = PledgeFactory(
            total_expected=Decimal('100.00'),
            total_received=Decimal('50.00')
        )
        assert pledge.fulfillment_percentage == 50.0

    def test_calculate_next_expected_date_monthly(self):
        """Test next expected date calculation for monthly pledge."""
        start = timezone.now().date()
        pledge = PledgeFactory(start_date=start, frequency=PledgeFrequency.MONTHLY)
        pledge.last_fulfilled_date = start

        next_date = pledge.calculate_next_expected_date()

        # Should be approximately one month from start
        assert next_date is not None
        assert (next_date - start).days >= 28
        assert (next_date - start).days <= 31

    def test_calculate_next_expected_date_quarterly(self):
        """Test next expected date calculation for quarterly pledge."""
        start = timezone.now().date()
        pledge = QuarterlyPledgeFactory(start_date=start)
        pledge.last_fulfilled_date = start

        next_date = pledge.calculate_next_expected_date()

        # Should be approximately three months from start
        assert next_date is not None
        assert (next_date - start).days >= 89
        assert (next_date - start).days <= 92

    def test_calculate_next_expected_date_inactive_pledge(self):
        """Test next expected date is None for inactive pledges."""
        pledge = PledgeFactory(status=PledgeStatus.PAUSED)
        assert pledge.calculate_next_expected_date() is None

    def test_check_late_status_not_late(self):
        """Test late status check for on-time pledge."""
        pledge = PledgeFactory()
        pledge.next_expected_date = timezone.now().date() + timedelta(days=15)
        pledge.check_late_status()

        assert pledge.is_late is False
        assert pledge.days_late == 0

    def test_check_late_status_late(self):
        """Test late status check for late pledge."""
        pledge = PledgeFactory()
        pledge.next_expected_date = timezone.now().date() - timedelta(days=20)
        pledge.check_late_status(grace_days=10)

        assert pledge.is_late is True
        assert pledge.days_late == 20

    def test_check_late_status_within_grace_period(self):
        """Test late status within grace period."""
        pledge = PledgeFactory()
        pledge.next_expected_date = timezone.now().date() - timedelta(days=5)
        pledge.check_late_status(grace_days=10)

        assert pledge.is_late is False
        assert pledge.days_late == 0


@pytest.mark.django_db
class TestPledgeStateTransitions:
    """Tests for pledge state transitions."""

    def test_pause_pledge(self):
        """Test pausing an active pledge."""
        pledge = PledgeFactory(status=PledgeStatus.ACTIVE, is_late=True, days_late=10)

        pledge.pause()

        assert pledge.status == PledgeStatus.PAUSED
        assert pledge.is_late is False
        assert pledge.days_late == 0

    def test_resume_pledge(self):
        """Test resuming a paused pledge."""
        pledge = PledgeFactory(status=PledgeStatus.PAUSED)

        pledge.resume()

        assert pledge.status == PledgeStatus.ACTIVE
        assert pledge.next_expected_date is not None

    def test_cancel_pledge(self):
        """Test cancelling a pledge."""
        pledge = PledgeFactory(status=PledgeStatus.ACTIVE, is_late=True)

        pledge.cancel()

        assert pledge.status == PledgeStatus.CANCELLED
        assert pledge.end_date == timezone.now().date()
        assert pledge.is_late is False

    def test_record_fulfillment(self):
        """Test recording pledge fulfillment from donation."""
        contact = ContactFactory()
        pledge = PledgeFactory(contact=contact, total_received=Decimal('0'))

        donation = Donation.objects.create(
            contact=contact,
            pledge=pledge,
            amount=Decimal('100.00'),
            date=timezone.now().date()
        )

        pledge.refresh_from_db()

        assert pledge.total_received == Decimal('100.00')
        assert pledge.last_fulfilled_date == donation.date
        assert pledge.is_late is False
