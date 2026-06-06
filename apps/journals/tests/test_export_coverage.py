"""
Behavioral coverage tests for the journal CSV export view and
serializer fallback/summary branches.

Verifies:
- CSV content-type, attachment header, header row, and data row values
- Owner-scoping of the export
- Archived inclusion/exclusion semantics
- FilterSet application (owner filter)
- JournalContactSerializer stage_events/decision summary branches
"""

import csv
import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from apps.contacts.models import Contact
from apps.journals.models import Decision, Journal, JournalContact, JournalStageEvent

User = get_user_model()


def _read_csv(response):
    """Drain a StreamingHttpResponse into parsed CSV rows."""
    content = b"".join(response.streaming_content).decode("utf-8")
    return list(csv.reader(io.StringIO(content)))


class JournalExportCSVTests(APITestCase):
    """Tests for the journal CSV export endpoint."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            email="a@example.com",
            password="pw",
            first_name="Ann",
            last_name="Apple",
            role="missionary",
        )
        self.user_b = User.objects.create_user(
            email="b@example.com",
            password="pw",
            first_name="Bob",
            last_name="Berry",
            role="missionary",
        )
        self.j_a = Journal.objects.create(
            owner=self.user_a,
            name="Alpha",
            goal_amount=Decimal("50000.00"),
            deadline="2026-06-30",
        )
        self.j_b = Journal.objects.create(
            owner=self.user_b, name="Beta", goal_amount=Decimal("30000.00")
        )
        self.url = reverse("journals:journal-export-csv")
        self.client.force_authenticate(user=self.user_a)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        )

    def test_content_type_and_disposition(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".csv", response["Content-Disposition"])

    def test_header_row(self):
        response = self.client.get(self.url)
        rows = _read_csv(response)
        self.assertEqual(
            rows[0], ["Name", "Goal Amount", "Deadline", "Archived", "Owner", "Created"]
        )

    def test_data_row_values_and_owner_scoping(self):
        response = self.client.get(self.url)
        rows = _read_csv(response)
        # Only user_a's journal should appear (owner scoped)
        data_rows = rows[1:]
        self.assertEqual(len(data_rows), 1)
        row = data_rows[0]
        self.assertEqual(row[0], "Alpha")
        self.assertEqual(row[1], "50000.00")
        self.assertEqual(row[2], "2026-06-30")
        self.assertEqual(row[3], "No")
        self.assertEqual(row[4], "Ann Apple")
        # Created date is today's ISO date
        self.assertRegex(row[5], r"^\d{4}-\d{2}-\d{2}$")

    def test_blank_deadline_renders_empty(self):
        Journal.objects.create(owner=self.user_a, name="NoDeadline", goal_amount=Decimal("100.00"))
        response = self.client.get(self.url)
        rows = _read_csv(response)
        names = {r[0]: r for r in rows[1:]}
        self.assertEqual(names["NoDeadline"][2], "")

    def test_archived_excluded_by_default(self):
        self.j_a.archive()
        response = self.client.get(self.url)
        rows = _read_csv(response)
        self.assertEqual(len(rows[1:]), 0)

    def test_archived_included_when_filter_present(self):
        self.j_a.archive()
        response = self.client.get(self.url, {"is_archived": "true"})
        rows = _read_csv(response)
        names = [r[0] for r in rows[1:]]
        self.assertIn("Alpha", names)
        # The archived flag column reflects archived state
        archived_row = next(r for r in rows[1:] if r[0] == "Alpha")
        self.assertEqual(archived_row[3], "Yes")

    def test_filterset_owner_filter_applies(self):
        # Admin-style owner filter param; for missionary, scoping still limits
        # to own journals so filtering by own owner id returns the journal.
        Journal.objects.create(owner=self.user_a, name="Second", goal_amount=Decimal("200.00"))
        response = self.client.get(self.url, {"owner": str(self.user_a.id)})
        rows = _read_csv(response)
        names = {r[0] for r in rows[1:]}
        self.assertIn("Alpha", names)
        self.assertIn("Second", names)

    def test_filterset_owner_filter_for_other_owner_returns_empty(self):
        # Filtering by user_b's id: owner-scoping intersects to nothing for user_a
        response = self.client.get(self.url, {"owner": str(self.user_b.id)})
        rows = _read_csv(response)
        self.assertEqual(len(rows[1:]), 0)


class JournalContactSerializerBranchTests(APITestCase):
    """
    Exercise JournalContactSerializer summary branches via the list endpoint
    (which prefetches) and the create endpoint (which does NOT prefetch,
    hitting the fallback paths).
    """

    def setUp(self):
        self.owner = User.objects.create_user(
            email="own@example.com",
            password="pw",
            first_name="Owen",
            last_name="Own",
            role="missionary",
        )
        self.journal = Journal.objects.create(
            owner=self.owner, name="J", goal_amount=Decimal("1000.00")
        )
        self.contact = Contact.objects.create(
            owner=self.owner,
            first_name="Cara",
            last_name="Cyan",
            status="prospect",
            email="cara@example.com",
        )
        self.client.force_authenticate(user=self.owner)

    def test_list_membership_summarizes_stage_events_and_decision(self):
        jc = JournalContact.objects.create(journal=self.journal, contact=self.contact)
        JournalStageEvent.objects.create(
            journal_contact=jc, stage="contact", event_type="call_logged", notes="hello world"
        )
        JournalStageEvent.objects.create(
            journal_contact=jc,
            stage="scheduled",
            event_type="meeting_scheduled",
            metadata={"scheduled_date": "2026-07-01"},
        )
        Decision.objects.create(
            journal_contact=jc, amount=Decimal("120.00"), cadence="monthly", status="active"
        )
        url = reverse("journals:journal-member-list")
        response = self.client.get(url, {"journal_id": str(self.journal.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]

        # Stage event summaries: contact has events, close does not
        stage_events = result["stage_events"]
        self.assertTrue(stage_events["contact"]["has_events"])
        self.assertEqual(stage_events["contact"]["event_count"], 1)
        self.assertEqual(stage_events["contact"]["last_event_type"], "call_logged")
        self.assertEqual(stage_events["contact"]["last_event_notes"], "hello world")
        self.assertFalse(stage_events["close"]["has_events"])
        self.assertIsNone(stage_events["close"]["last_event_date"])
        # Scheduled stage carries scheduled_date from metadata
        self.assertEqual(stage_events["scheduled"]["scheduled_date"], "2026-07-01")

        # Decision summary
        self.assertIsNotNone(result["decision"])
        self.assertEqual(result["decision"]["amount"], "120.00")
        self.assertEqual(result["decision"]["status"], "active")
        self.assertEqual(result["decision"]["monthly_equivalent"], "120.00")

        # Contact passthrough fields
        self.assertEqual(result["contact_name"], "Cara Cyan")
        self.assertEqual(result["contact_status"], "prospect")

    def test_create_membership_uses_fallback_summaries(self):
        # POST create serializes the new object WITHOUT prefetch attrs,
        # exercising the getattr(...) is None fallback branches.
        url = reverse("journals:journal-member-list")
        response = self.client.post(
            url,
            {"journal": str(self.journal.id), "contact": str(self.contact.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # No events / no decision yet -> all stages empty, decision is None
        self.assertIsNone(response.data["decision"])
        self.assertFalse(response.data["stage_events"]["contact"]["has_events"])
        self.assertIsNone(response.data["stage_events"]["scheduled"]["scheduled_date"])
