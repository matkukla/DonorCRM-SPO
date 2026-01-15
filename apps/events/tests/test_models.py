"""
Tests for Event model.
"""
import pytest
from django.utils import timezone

from apps.events.models import Event, EventSeverity, EventType
from apps.events.tests.factories import EventFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestEventModel:
    """Tests for Event model methods and properties."""

    def test_event_str(self):
        """Test event string representation."""
        event = EventFactory(
            event_type=EventType.DONATION_RECEIVED,
            title='Donation from John'
        )
        assert 'donation_received' in str(event)
        assert 'Donation from John' in str(event)

    def test_mark_read(self):
        """Test marking event as read."""
        event = EventFactory(is_read=False)
        assert event.is_read is False
        assert event.read_at is None

        event.mark_read()

        assert event.is_read is True
        assert event.read_at is not None

    def test_event_types(self):
        """Test event type choices."""
        # Donation events
        assert EventType.DONATION_RECEIVED == 'donation_received'
        assert EventType.FIRST_DONATION == 'first_donation'

        # Pledge events
        assert EventType.PLEDGE_CREATED == 'pledge_created'
        assert EventType.PLEDGE_LATE == 'pledge_late'

        # Contact events
        assert EventType.CONTACT_CREATED == 'contact_created'
        assert EventType.DONOR_LAPSED == 'donor_lapsed'

        # Alert events
        assert EventType.AT_RISK == 'at_risk'

    def test_event_severities(self):
        """Test event severity choices."""
        assert EventSeverity.INFO == 'info'
        assert EventSeverity.SUCCESS == 'success'
        assert EventSeverity.WARNING == 'warning'
        assert EventSeverity.ALERT == 'alert'

    def test_event_defaults(self):
        """Test event default values."""
        user = UserFactory()
        event = Event.objects.create(
            user=user,
            event_type=EventType.DONATION_RECEIVED,
            title='Test event'
        )

        assert event.severity == EventSeverity.INFO
        assert event.is_read is False
        assert event.is_new is True
        assert event.metadata == {}

    def test_event_with_metadata(self):
        """Test event with metadata."""
        user = UserFactory()
        metadata = {'amount': '100.00', 'date': '2024-01-15'}

        event = Event.objects.create(
            user=user,
            event_type=EventType.DONATION_RECEIVED,
            title='Donation received',
            metadata=metadata
        )

        assert event.metadata['amount'] == '100.00'
        assert event.metadata['date'] == '2024-01-15'
