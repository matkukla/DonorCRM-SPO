"""
Factories for Donation model tests.
"""
from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from faker import Faker

from apps.contacts.tests.factories import ContactFactory
from apps.donations.models import Donation, DonationType, PaymentMethod

fake = Faker()


class DonationFactory(factory.django.DjangoModelFactory):
    """Factory for creating Donation instances."""

    class Meta:
        model = Donation

    contact = factory.SubFactory(ContactFactory)
    amount = factory.LazyFunction(
        lambda: Decimal(fake.random_element([25, 50, 100, 150, 200, 500]))
    )
    date = factory.LazyFunction(lambda: timezone.now().date() - timedelta(days=fake.random_int(1, 30)))
    donation_type = DonationType.ONE_TIME
    payment_method = PaymentMethod.CHECK
    thanked = False
    notes = ''


class RecurringDonationFactory(DonationFactory):
    """Factory for recurring donations."""
    donation_type = DonationType.RECURRING


class SpecialDonationFactory(DonationFactory):
    """Factory for special gifts."""
    donation_type = DonationType.SPECIAL
    amount = factory.LazyFunction(
        lambda: Decimal(fake.random_element([500, 1000, 2500, 5000]))
    )
