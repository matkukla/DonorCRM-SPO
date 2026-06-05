"""
Tests for the scheduled pipeline stage.

Tests verify:
- PipelineStage.SCHEDULED enum value exists with correct value/label
- JournalStageEvent creation with stage='scheduled' and valid metadata succeeds
- Serializer validates scheduled_date is required in metadata for scheduled stage
- Serializer accepts scheduled_date with optional scheduled_time
- get_stage_events summary enriches scheduled stage with scheduled_date
- get_stage_events summary for scheduled stage with no events has scheduled_date=None
- Goal services calls_count excludes meeting_scheduled events
- Goal services meetings_count excludes meeting_scheduled events
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIRequestFactory

from apps.contacts.models import Contact
from apps.journals.models import Journal, JournalContact, JournalStageEvent, PipelineStage
from apps.journals.serializers import JournalContactSerializer, JournalStageEventSerializer

User = get_user_model()


class ScheduledStageModelTests(TestCase):
    """Tests for the scheduled pipeline stage enum and model behavior."""

    def test_scheduled_enum_exists(self):
        """Test 1: PipelineStage.SCHEDULED exists with value 'scheduled' and label 'Scheduled'."""
        self.assertEqual(PipelineStage.SCHEDULED.value, "scheduled")
        self.assertEqual(PipelineStage.SCHEDULED.label, "Scheduled")

    def test_scheduled_between_contact_and_meet(self):
        """Verify SCHEDULED is positioned between CONTACT and MEET in the enum."""
        values = PipelineStage.values
        contact_idx = values.index("contact")
        scheduled_idx = values.index("scheduled")
        meet_idx = values.index("meet")
        self.assertEqual(scheduled_idx, contact_idx + 1)
        self.assertEqual(meet_idx, scheduled_idx + 1)

    def test_create_event_with_scheduled_stage_and_valid_metadata(self):
        """Test 2: Creating JournalStageEvent with stage='scheduled',
        event_type='meeting_scheduled', metadata={'scheduled_date': '2026-04-15'} succeeds."""
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="Test",
            last_name="User",
            role="missionary",
        )
        journal = Journal.objects.create(
            owner=user,
            name="Test Journal",
            goal_amount=Decimal("10000.00"),
        )
        contact = Contact.objects.create(
            owner=user,
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
        )
        jc = JournalContact.objects.create(journal=journal, contact=contact)

        event = JournalStageEvent.objects.create(
            journal_contact=jc,
            stage="scheduled",
            event_type="meeting_scheduled",
            metadata={"scheduled_date": "2026-04-15"},
            triggered_by=user,
        )
        self.assertEqual(event.stage, "scheduled")
        self.assertEqual(event.event_type, "meeting_scheduled")
        self.assertEqual(event.metadata["scheduled_date"], "2026-04-15")


class ScheduledStageSerializerTests(TestCase):
    """Tests for serializer validation of scheduled stage metadata."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="Test",
            last_name="User",
            role="missionary",
        )
        self.journal = Journal.objects.create(
            owner=self.user,
            name="Test Journal",
            goal_amount=Decimal("10000.00"),
        )
        self.contact = Contact.objects.create(
            owner=self.user,
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
        )
        self.jc = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact,
        )
        self.factory = APIRequestFactory()

    def _get_request(self):
        request = self.factory.post("/fake/")
        request.user = self.user
        return request

    def test_scheduled_stage_without_scheduled_date_fails(self):
        """Test 3: Creating JournalStageEvent with stage='scheduled' and empty metadata
        raises ValidationError containing 'scheduled_date is required'."""
        serializer = JournalStageEventSerializer(
            data={
                "journal_contact": str(self.jc.id),
                "stage": "scheduled",
                "event_type": "meeting_scheduled",
                "metadata": {},
            },
            context={"request": self._get_request()},
        )
        self.assertFalse(serializer.is_valid())
        errors_str = str(serializer.errors)
        self.assertIn("scheduled_date", errors_str.lower())

    def test_scheduled_stage_with_date_and_time_succeeds(self):
        """Test 4: Creating JournalStageEvent with stage='scheduled' and metadata with
        scheduled_date and scheduled_time succeeds."""
        serializer = JournalStageEventSerializer(
            data={
                "journal_contact": str(self.jc.id),
                "stage": "scheduled",
                "event_type": "meeting_scheduled",
                "metadata": {
                    "scheduled_date": "2026-04-15",
                    "scheduled_time": "14:30",
                },
            },
            context={"request": self._get_request()},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_scheduled_stage_with_date_only_succeeds(self):
        """Scheduled stage with only scheduled_date (no time) succeeds."""
        serializer = JournalStageEventSerializer(
            data={
                "journal_contact": str(self.jc.id),
                "stage": "scheduled",
                "event_type": "meeting_scheduled",
                "metadata": {
                    "scheduled_date": "2026-04-15",
                },
            },
            context={"request": self._get_request()},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ScheduledStageSummaryTests(TestCase):
    """Tests for get_stage_events summary enrichment for scheduled stage."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="Test",
            last_name="User",
            role="missionary",
        )
        self.journal = Journal.objects.create(
            owner=self.user,
            name="Test Journal",
            goal_amount=Decimal("10000.00"),
        )
        self.contact = Contact.objects.create(
            owner=self.user,
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
        )
        self.jc = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact,
        )

    def test_scheduled_summary_includes_scheduled_date(self):
        """Test 5: get_stage_events summary for 'scheduled' stage includes 'scheduled_date'
        key extracted from most recent event's metadata."""
        JournalStageEvent.objects.create(
            journal_contact=self.jc,
            stage="scheduled",
            event_type="meeting_scheduled",
            metadata={"scheduled_date": "2026-04-15"},
            triggered_by=self.user,
        )
        factory = APIRequestFactory()
        request = factory.get("/fake/")
        request.user = self.user

        serializer = JournalContactSerializer(self.jc, context={"request": request})
        stage_events = serializer.data["stage_events"]
        scheduled = stage_events["scheduled"]

        self.assertTrue(scheduled["has_events"])
        self.assertIn("scheduled_date", scheduled)
        self.assertEqual(scheduled["scheduled_date"], "2026-04-15")

    def test_scheduled_summary_no_events_has_null_scheduled_date(self):
        """Test 6: get_stage_events summary for 'scheduled' stage with no events
        has scheduled_date=None."""
        factory = APIRequestFactory()
        request = factory.get("/fake/")
        request.user = self.user

        serializer = JournalContactSerializer(self.jc, context={"request": request})
        stage_events = serializer.data["stage_events"]
        scheduled = stage_events["scheduled"]

        self.assertFalse(scheduled["has_events"])
        self.assertIn("scheduled_date", scheduled)
        self.assertIsNone(scheduled["scheduled_date"])


class GoalExclusionTests(TestCase):
    """Tests to verify goal services exclude meeting_scheduled events."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="Test",
            last_name="User",
            role="missionary",
            monthly_support_goal_cents=500000,
        )
        self.journal = Journal.objects.create(
            owner=self.user,
            name="Test Journal",
            goal_amount=Decimal("10000.00"),
        )
        self.contact = Contact.objects.create(
            owner=self.user,
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
        )
        self.jc = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact,
        )
        # Select this journal for goal tracking
        from apps.users.models import GoalJournalSelection

        GoalJournalSelection.objects.create(user=self.user, journal=self.journal)

    def test_calls_count_excludes_meeting_scheduled(self):
        """Test 7: Goal services calls_count excludes meeting_scheduled events."""
        # Create a meeting_scheduled event (should NOT count as a call)
        JournalStageEvent.objects.create(
            journal_contact=self.jc,
            stage="scheduled",
            event_type="meeting_scheduled",
            metadata={"scheduled_date": "2026-04-15"},
            triggered_by=self.user,
        )
        # Create an actual call event (should count)
        JournalStageEvent.objects.create(
            journal_contact=self.jc,
            stage="contact",
            event_type="call_logged",
            triggered_by=self.user,
        )

        from apps.users.goal_services import get_goal_progress

        progress = get_goal_progress(self.user)

        self.assertEqual(progress["calls_count"], 1)

    def test_meetings_count_excludes_meeting_scheduled(self):
        """Test 8: Goal services meetings_count excludes meeting_scheduled events."""
        # Create a meeting_scheduled event (should NOT count as meeting)
        JournalStageEvent.objects.create(
            journal_contact=self.jc,
            stage="scheduled",
            event_type="meeting_scheduled",
            metadata={"scheduled_date": "2026-04-15"},
            triggered_by=self.user,
        )
        # Create an actual meeting completed event (should count)
        JournalStageEvent.objects.create(
            journal_contact=self.jc,
            stage="meet",
            event_type="meeting_completed",
            triggered_by=self.user,
        )

        from apps.users.goal_services import get_goal_progress

        progress = get_goal_progress(self.user)

        self.assertEqual(progress["meetings_count"], 1)
