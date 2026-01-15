"""
Tests for Donation model.
"""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.contacts.models import ContactStatus
from apps.contacts.tests.factories import ContactFactory
from apps.donations.models import Donation, DonationType, PaymentMethod
from apps.donations.tests.factories import DonationFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestDonationModel:
    """Tests for Donation model methods and properties."""

    def test_donation_str(self):
        """Test donation string representation."""
        donation = DonationFactory(amount=Decimal('100.00'))
        assert '$100.00' in str(donation)
        assert str(donation.date) in str(donation)

    def test_donation_mark_thanked(self):
        """Test marking donation as thanked."""
        user = UserFactory()
        donation = DonationFactory(thanked=False)
        assert not donation.thanked
        assert donation.thanked_at is None

        donation.mark_thanked(user)

        assert donation.thanked
        assert donation.thanked_at is not None
        assert donation.thanked_by == user

    def test_donation_types(self):
        """Test donation type choices."""
        assert DonationType.ONE_TIME == 'one_time'
        assert DonationType.RECURRING == 'recurring'
        assert DonationType.SPECIAL == 'special'

    def test_payment_methods(self):
        """Test payment method choices."""
        assert PaymentMethod.CHECK == 'check'
        assert PaymentMethod.CASH == 'cash'
        assert PaymentMethod.CREDIT_CARD == 'credit_card'
        assert PaymentMethod.BANK_TRANSFER == 'bank_transfer'


@pytest.mark.django_db
class TestDonationSignals:
    """Tests for donation-related signals."""

    def test_donation_updates_contact_stats(self):
        """Test that creating a donation updates contact giving stats."""
        contact = ContactFactory()
        assert contact.total_given == 0
        assert contact.gift_count == 0

        donation = Donation.objects.create(
            contact=contact,
            amount=Decimal('100.00'),
            date=timezone.now().date()
        )

        contact.refresh_from_db()
        assert contact.total_given == Decimal('100.00')
        assert contact.gift_count == 1
        assert contact.first_gift_date == donation.date
        assert contact.last_gift_date == donation.date

    def test_donation_updates_contact_status_to_donor(self):
        """Test that first donation changes prospect to donor."""
        contact = ContactFactory(status=ContactStatus.PROSPECT)
        assert contact.status == ContactStatus.PROSPECT

        Donation.objects.create(
            contact=contact,
            amount=Decimal('50.00'),
            date=timezone.now().date()
        )

        contact.refresh_from_db()
        assert contact.status == ContactStatus.DONOR

    def test_donation_sets_needs_thank_you(self):
        """Test that new donation sets needs_thank_you flag."""
        contact = ContactFactory(needs_thank_you=False)

        Donation.objects.create(
            contact=contact,
            amount=Decimal('75.00'),
            date=timezone.now().date(),
            thanked=False
        )

        contact.refresh_from_db()
        assert contact.needs_thank_you is True

    def test_thanked_donation_doesnt_set_needs_thank_you(self):
        """Test that thanked donation doesn't set needs_thank_you flag."""
        contact = ContactFactory(needs_thank_you=False)

        Donation.objects.create(
            contact=contact,
            amount=Decimal('75.00'),
            date=timezone.now().date(),
            thanked=True
        )

        contact.refresh_from_db()
        assert contact.needs_thank_you is False

    def test_multiple_donations_aggregate_correctly(self):
        """Test that multiple donations aggregate correctly."""
        contact = ContactFactory()

        Donation.objects.create(
            contact=contact,
            amount=Decimal('100.00'),
            date=timezone.now().date()
        )
        Donation.objects.create(
            contact=contact,
            amount=Decimal('50.00'),
            date=timezone.now().date()
        )

        contact.refresh_from_db()
        assert contact.total_given == Decimal('150.00')
        assert contact.gift_count == 2

    def test_donation_delete_updates_stats(self):
        """Test that deleting a donation updates contact stats."""
        contact = ContactFactory()
        donation1 = Donation.objects.create(
            contact=contact,
            amount=Decimal('100.00'),
            date=timezone.now().date()
        )
        Donation.objects.create(
            contact=contact,
            amount=Decimal('50.00'),
            date=timezone.now().date()
        )

        contact.refresh_from_db()
        assert contact.total_given == Decimal('150.00')
        assert contact.gift_count == 2

        donation1.delete()

        contact.refresh_from_db()
        assert contact.total_given == Decimal('50.00')
        assert contact.gift_count == 1
