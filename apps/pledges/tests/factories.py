"""
Factories for Pledge model tests.
"""
from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from faker import Faker

from apps.contacts.tests.factories import ContactFactory
from apps.pledges.models import Pledge, PledgeFrequency, PledgeStatus

fake = Faker()


class PledgeFactory(factory.django.DjangoModelFactory):
    """Factory for creating Pledge instances."""

    class Meta:
        model = Pledge

    contact = factory.SubFactory(ContactFactory)
    amount = factory.LazyFunction(
        lambda: Decimal(fake.random_element([50, 100, 150, 200, 250]))
    )
    frequency = PledgeFrequency.MONTHLY
    status = PledgeStatus.ACTIVE
    start_date = factory.LazyFunction(lambda: timezone.now().date() - timedelta(days=30))
    notes = ''


class QuarterlyPledgeFactory(PledgeFactory):
    """Factory for quarterly pledges."""
    frequency = PledgeFrequency.QUARTERLY


class AnnualPledgeFactory(PledgeFactory):
    """Factory for annual pledges."""
    frequency = PledgeFrequency.ANNUAL


class PausedPledgeFactory(PledgeFactory):
    """Factory for paused pledges."""
    status = PledgeStatus.PAUSED


class CancelledPledgeFactory(PledgeFactory):
    """Factory for cancelled pledges."""
    status = PledgeStatus.CANCELLED
