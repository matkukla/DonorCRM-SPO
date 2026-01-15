"""
Factories for Event model tests.
"""
import factory
from faker import Faker

from apps.contacts.tests.factories import ContactFactory
from apps.events.models import Event, EventSeverity, EventType
from apps.users.tests.factories import UserFactory

fake = Faker()


class EventFactory(factory.django.DjangoModelFactory):
    """Factory for creating Event instances."""

    class Meta:
        model = Event

    user = factory.SubFactory(UserFactory)
    event_type = EventType.DONATION_RECEIVED
    severity = EventSeverity.INFO
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=4))
    message = factory.LazyFunction(fake.paragraph)
    contact = factory.SubFactory(ContactFactory)
    is_read = False
    is_new = True


class DonationEventFactory(EventFactory):
    """Factory for donation received events."""
    event_type = EventType.DONATION_RECEIVED
    severity = EventSeverity.SUCCESS


class PledgeLateEventFactory(EventFactory):
    """Factory for late pledge events."""
    event_type = EventType.PLEDGE_LATE
    severity = EventSeverity.WARNING


class AtRiskEventFactory(EventFactory):
    """Factory for at-risk donor events."""
    event_type = EventType.AT_RISK
    severity = EventSeverity.WARNING


class AlertEventFactory(EventFactory):
    """Factory for alert events."""
    event_type = EventType.DONOR_LAPSED
    severity = EventSeverity.ALERT
