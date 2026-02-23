"""
Factories for Gift and RecurringGift model tests.
"""
from datetime import timedelta

import factory
from django.utils import timezone
from faker import Faker

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.models import (
    Gift,
    RecurringGift,
    RecurringGiftFrequency,
    RecurringGiftStatus,
)

fake = Faker()


class GiftFactory(factory.django.DjangoModelFactory):
    """Factory for creating Gift instances."""

    class Meta:
        model = Gift

    donor_contact = factory.SubFactory(ContactFactory)
    amount_cents = factory.LazyFunction(
        lambda: fake.random_element([2500, 5000, 10000, 15000, 20000, 50000])
    )
    gift_date = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=fake.random_int(1, 30))
    )
    description = ''


class RecurringGiftFactory(factory.django.DjangoModelFactory):
    """Factory for creating RecurringGift instances."""

    class Meta:
        model = RecurringGift

    donor_contact = factory.SubFactory(ContactFactory)
    amount_cents = factory.LazyFunction(
        lambda: fake.random_element([5000, 10000, 15000, 20000, 25000])
    )
    frequency = RecurringGiftFrequency.MONTHLY
    status = RecurringGiftStatus.ACTIVE
    start_date = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=30)
    )
    description = ''


class QuarterlyRecurringGiftFactory(RecurringGiftFactory):
    """Factory for quarterly recurring gifts."""
    frequency = RecurringGiftFrequency.QUARTERLY


class AnnualRecurringGiftFactory(RecurringGiftFactory):
    """Factory for annual recurring gifts."""
    frequency = RecurringGiftFrequency.ANNUALLY


class CancelledRecurringGiftFactory(RecurringGiftFactory):
    """Factory for cancelled recurring gifts."""
    status = RecurringGiftStatus.CANCELLED
