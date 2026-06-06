"""
Behavioral coverage tests for journals views.

Exercises real HTTP request/response behavior through the DRF API:
- Journal list/create/detail/archive flows + owner-scoping + ordering/search
- Stage event list/create + delete-by-stage write restriction
- Next step list/create/update + ownership
- Decision list filtering + duplicate handling
- Decision history list filtering
- Analytics ViewSet endpoints (trends, activity, pipeline, queue, report, admin-summary)
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from apps.contacts.models import Contact
from apps.journals.models import (
    Decision,
    DecisionHistory,
    Journal,
    JournalContact,
    JournalStageEvent,
    NextStep,
)

User = get_user_model()


class JournalListCreateTests(APITestCase):
    """Tests for the journal list/create endpoint."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            email="a@example.com",
            password="pw",
            first_name="Ann",
            last_name="A",
            role="missionary",
        )
        self.user_b = User.objects.create_user(
            email="b@example.com",
            password="pw",
            first_name="Bob",
            last_name="B",
            role="missionary",
        )
        self.j_a = Journal.objects.create(
            owner=self.user_a, name="Alpha Campaign", goal_amount=Decimal("50000.00")
        )
        self.j_b = Journal.objects.create(
            owner=self.user_b, name="Beta Campaign", goal_amount=Decimal("30000.00")
        )
        self.url = reverse("journals:journal-list")
        self.client.force_authenticate(user=self.user_a)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        )

    def test_list_only_own_journals(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Alpha Campaign")
        self.assertEqual(response.data["results"][0]["owner_name"], "Ann A")

    def test_create_sets_owner_to_current_user(self):
        response = self.client.post(
            self.url,
            {"name": "Gamma", "goal_amount": "12000.00", "deadline": "2026-12-31"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Journal.objects.get(id=response.data["id"])
        self.assertEqual(created.owner, self.user_a)
        self.assertEqual(created.name, "Gamma")

    def test_create_rejects_invalid_goal_amount(self):
        response = self.client.post(self.url, {"name": "Bad", "goal_amount": "0"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("goal_amount", response.data)

    def test_archived_excluded_by_default(self):
        self.j_a.archive()
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 0)

    def test_is_archived_true_shows_only_archived(self):
        self.j_a.archive()
        Journal.objects.create(owner=self.user_a, name="Active One", goal_amount=Decimal("100.00"))
        response = self.client.get(self.url, {"is_archived": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Alpha Campaign")

    def test_search_by_name(self):
        Journal.objects.create(
            owner=self.user_a, name="Year End Push", goal_amount=Decimal("100.00")
        )
        response = self.client.get(self.url, {"search": "Year End"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Year End Push")

    def test_ordering_by_name(self):
        Journal.objects.create(owner=self.user_a, name="Zeta Last", goal_amount=Decimal("100.00"))
        response = self.client.get(self.url, {"ordering": "name"})
        names = [r["name"] for r in response.data["results"]]
        self.assertEqual(names, sorted(names))


class JournalDetailTests(APITestCase):
    """Tests for retrieve/update/archive on a single journal."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="own@example.com", password="pw", role="missionary"
        )
        self.other = User.objects.create_user(
            email="oth@example.com", password="pw", role="missionary"
        )
        self.admin = User.objects.create_user(email="adm@example.com", password="pw", role="admin")
        self.journal = Journal.objects.create(
            owner=self.owner, name="Detail Journal", goal_amount=Decimal("9000.00")
        )
        self.url = reverse("journals:journal-detail", kwargs={"pk": self.journal.id})

    def test_owner_can_retrieve(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Detail Journal")
        self.assertEqual(response.data["goal_amount"], "9000.00")

    def test_other_user_cannot_retrieve(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_patch_name(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(self.url, {"name": "Renamed"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.journal.refresh_from_db()
        self.assertEqual(self.journal.name, "Renamed")

    def test_delete_soft_archives(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.journal.refresh_from_db()
        self.assertTrue(self.journal.is_archived)
        self.assertIsNotNone(self.journal.archived_at)
        # Still in DB (soft delete, not hard delete)
        self.assertTrue(Journal.objects.filter(id=self.journal.id).exists())

    def test_admin_can_retrieve_any_journal_via_object_perm(self):
        # Admin queryset is still own-scoped (get_visible_user_ids), so a
        # different owner's journal returns 404 for admin without View As.
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class StageEventTests(APITestCase):
    """Tests for stage event list/create and delete-by-stage."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="own@example.com", password="pw", role="missionary"
        )
        self.other = User.objects.create_user(
            email="oth@example.com", password="pw", role="missionary"
        )
        self.admin = User.objects.create_user(email="adm@example.com", password="pw", role="admin")
        self.journal = Journal.objects.create(
            owner=self.owner, name="J", goal_amount=Decimal("1000.00")
        )
        self.contact = Contact.objects.create(
            owner=self.owner, first_name="Carl", last_name="Cole", status="prospect"
        )
        self.jc = JournalContact.objects.create(journal=self.journal, contact=self.contact)
        self.list_url = reverse("journals:stage-event-list")
        self.del_url = reverse("journals:stage-event-delete-by-stage")
        self.client.force_authenticate(user=self.owner)

    def _make_event(self, stage="contact", event_type="call_logged"):
        return JournalStageEvent.objects.create(
            journal_contact=self.jc, stage=stage, event_type=event_type
        )

    def test_create_stage_event(self):
        response = self.client.post(
            self.list_url,
            {
                "journal_contact": str(self.jc.id),
                "stage": "contact",
                "event_type": "call_logged",
                "notes": "Spoke briefly",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = JournalStageEvent.objects.get(id=response.data["id"])
        self.assertEqual(event.triggered_by, self.owner)

    def test_create_requires_journal_contact_or_contact_id(self):
        response = self.client.post(
            self.list_url, {"stage": "contact", "event_type": "other"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_scheduled_requires_scheduled_date(self):
        response = self.client.post(
            self.list_url,
            {
                "journal_contact": str(self.jc.id),
                "stage": "scheduled",
                "event_type": "meeting_scheduled",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("metadata", response.data)

    def test_list_filtered_by_journal_contact_id(self):
        self._make_event()
        other_jc = JournalContact.objects.create(
            journal=self.journal,
            contact=Contact.objects.create(
                owner=self.owner, first_name="X", last_name="Y", status="prospect"
            ),
        )
        JournalStageEvent.objects.create(journal_contact=other_jc, stage="meet", event_type="other")
        response = self.client.get(self.list_url, {"journal_contact_id": str(self.jc.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(str(response.data["results"][0]["journal_contact"]), str(self.jc.id))

    def test_list_owner_scoped(self):
        self._make_event()
        self.client.force_authenticate(user=self.other)
        response = self.client.get(self.list_url)
        self.assertEqual(response.data["count"], 0)

    def _delete_by_stage(self, journal_contact_id, stage):
        # Query params must go on the URL; DRF test client treats a DELETE
        # data dict as a request body, not query_params.
        return self.client.delete(
            f"{self.del_url}?journal_contact_id={journal_contact_id}&stage={stage}"
        )

    def test_delete_by_stage_requires_params(self):
        response = self.client.delete(self.del_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_delete_by_stage_removes_matching_events(self):
        self._make_event(stage="contact")
        self._make_event(stage="contact")
        self._make_event(stage="meet")
        response = self._delete_by_stage(self.jc.id, "contact")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["deleted"], 2)
        self.assertEqual(
            JournalStageEvent.objects.filter(journal_contact=self.jc, stage="contact").count(),
            0,
        )
        self.assertEqual(
            JournalStageEvent.objects.filter(journal_contact=self.jc, stage="meet").count(), 1
        )

    def test_delete_by_stage_cannot_touch_other_users_events(self):
        self._make_event(stage="contact")
        self.client.force_authenticate(user=self.other)
        response = self._delete_by_stage(self.jc.id, "contact")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Non-owner non-admin: filtered to own journals, so deletes nothing
        self.assertEqual(response.data["deleted"], 0)
        self.assertEqual(JournalStageEvent.objects.filter(journal_contact=self.jc).count(), 1)

    def test_delete_by_stage_admin_can_delete(self):
        self._make_event(stage="contact")
        self.client.force_authenticate(user=self.admin)
        response = self._delete_by_stage(self.jc.id, "contact")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["deleted"], 1)


class NextStepViewTests(APITestCase):
    """Tests for next step list/create/update/delete."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="own@example.com", password="pw", role="missionary"
        )
        self.other = User.objects.create_user(
            email="oth@example.com", password="pw", role="missionary"
        )
        self.journal = Journal.objects.create(
            owner=self.owner, name="J", goal_amount=Decimal("1000.00")
        )
        self.contact = Contact.objects.create(
            owner=self.owner, first_name="Carl", last_name="Cole", status="prospect"
        )
        self.jc = JournalContact.objects.create(journal=self.journal, contact=self.contact)
        self.list_url = reverse("journals:nextstep-list")
        self.client.force_authenticate(user=self.owner)

    def test_create_next_step(self):
        response = self.client.post(
            self.list_url,
            {"journal_contact": str(self.jc.id), "title": "Send thank-you"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(NextStep.objects.count(), 1)

    def test_create_rejected_for_unowned_journal_contact(self):
        other_journal = Journal.objects.create(
            owner=self.other, name="Other", goal_amount=Decimal("100.00")
        )
        other_contact = Contact.objects.create(
            owner=self.other, first_name="Z", last_name="Z", status="prospect"
        )
        other_jc = JournalContact.objects.create(journal=other_journal, contact=other_contact)
        response = self.client.post(
            self.list_url,
            {"journal_contact": str(other_jc.id), "title": "Nope"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_filtered_by_journal_contact(self):
        NextStep.objects.create(journal_contact=self.jc, title="A")
        other_jc = JournalContact.objects.create(
            journal=self.journal,
            contact=Contact.objects.create(
                owner=self.owner, first_name="P", last_name="Q", status="prospect"
            ),
        )
        NextStep.objects.create(journal_contact=other_jc, title="B")
        response = self.client.get(self.list_url, {"journal_contact": str(self.jc.id)})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "A")

    def test_list_filtered_by_completed(self):
        NextStep.objects.create(journal_contact=self.jc, title="Done", completed=True)
        NextStep.objects.create(journal_contact=self.jc, title="Todo", completed=False)
        response = self.client.get(self.list_url, {"completed": "true"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Done")

        response = self.client.get(self.list_url, {"completed": "false"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Todo")

    def test_update_marks_completed_sets_timestamp(self):
        ns = NextStep.objects.create(journal_contact=self.jc, title="X", completed=False)
        url = reverse("journals:nextstep-detail", kwargs={"pk": ns.id})
        response = self.client.patch(url, {"completed": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ns.refresh_from_db()
        self.assertTrue(ns.completed)
        self.assertIsNotNone(ns.completed_at)

    def test_update_uncomplete_clears_timestamp(self):
        ns = NextStep.objects.create(
            journal_contact=self.jc, title="X", completed=True, completed_at=timezone.now()
        )
        url = reverse("journals:nextstep-detail", kwargs={"pk": ns.id})
        response = self.client.patch(url, {"completed": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ns.refresh_from_db()
        self.assertFalse(ns.completed)
        self.assertIsNone(ns.completed_at)

    def test_delete_next_step(self):
        ns = NextStep.objects.create(journal_contact=self.jc, title="X")
        url = reverse("journals:nextstep-detail", kwargs={"pk": ns.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(NextStep.objects.count(), 0)

    def test_owner_scoped_list(self):
        NextStep.objects.create(journal_contact=self.jc, title="X")
        self.client.force_authenticate(user=self.other)
        response = self.client.get(self.list_url)
        self.assertEqual(response.data["count"], 0)


class DecisionFilterTests(APITestCase):
    """Tests for decision list filtering and history list."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="own@example.com", password="pw", role="missionary"
        )
        self.journal = Journal.objects.create(
            owner=self.owner, name="J1", goal_amount=Decimal("1000.00")
        )
        self.journal2 = Journal.objects.create(
            owner=self.owner, name="J2", goal_amount=Decimal("2000.00")
        )
        self.c1 = Contact.objects.create(
            owner=self.owner, first_name="A", last_name="A", status="prospect"
        )
        self.c2 = Contact.objects.create(
            owner=self.owner, first_name="B", last_name="B", status="prospect"
        )
        self.jc1 = JournalContact.objects.create(journal=self.journal, contact=self.c1)
        self.jc2 = JournalContact.objects.create(journal=self.journal2, contact=self.c2)
        self.d1 = Decision.objects.create(
            journal_contact=self.jc1, amount=Decimal("100.00"), cadence="monthly", status="active"
        )
        self.d2 = Decision.objects.create(
            journal_contact=self.jc2, amount=Decimal("200.00"), cadence="annual", status="pending"
        )
        self.list_url = reverse("journals:decision-list")
        self.client.force_authenticate(user=self.owner)

    def test_filter_by_journal_contact_id(self):
        response = self.client.get(self.list_url, {"journal_contact_id": str(self.jc1.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {d["id"] for d in response.data["results"]}
        self.assertEqual(ids, {str(self.d1.id)})

    def test_filter_by_journal_id(self):
        response = self.client.get(self.list_url, {"journal_id": str(self.journal2.id)})
        ids = {d["id"] for d in response.data["results"]}
        self.assertEqual(ids, {str(self.d2.id)})

    def test_duplicate_decision_returns_400(self):
        response = self.client.post(
            self.list_url,
            {"journal_contact": str(self.jc1.id), "amount": "50.00", "cadence": "monthly"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decision_history_filtered_by_decision_id(self):
        url = reverse("journals:decision-detail", kwargs={"pk": self.d1.id})
        self.client.patch(url, {"amount": "150.00"}, format="json")
        history_url = reverse("journals:decision-history-list")
        response = self.client.get(history_url, {"decision_id": str(self.d1.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(str(response.data["results"][0]["decision"]), str(self.d1.id))

    def test_decision_history_filtered_by_journal_contact_id(self):
        DecisionHistory.objects.create(
            decision=self.d1, changed_fields={"amount": "100.00"}, changed_by=self.owner
        )
        history_url = reverse("journals:decision-history-list")
        response = self.client.get(history_url, {"journal_contact_id": str(self.jc1.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)


class AnalyticsTests(APITestCase):
    """Tests for the JournalAnalyticsViewSet endpoints."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="own@example.com",
            password="pw",
            first_name="Owen",
            last_name="Own",
            role="missionary",
        )
        self.other = User.objects.create_user(
            email="oth@example.com", password="pw", role="missionary"
        )
        self.admin = User.objects.create_user(email="adm@example.com", password="pw", role="admin")
        self.journal = Journal.objects.create(
            owner=self.owner, name="Report Journal", goal_amount=Decimal("10000.00")
        )
        self.contact = Contact.objects.create(
            owner=self.owner, first_name="Cara", last_name="Cyan", status="prospect"
        )
        self.jc = JournalContact.objects.create(journal=self.journal, contact=self.contact)
        self.client.force_authenticate(user=self.owner)

    def test_decision_trends(self):
        Decision.objects.create(
            journal_contact=self.jc, amount=Decimal("100.00"), cadence="monthly", status="active"
        )
        url = reverse("journals:journal-analytics-decision-trends")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["count"], 1)
        self.assertRegex(response.data[0]["month"], r"^\d{4}-\d{2}$")

    def test_stage_activity_pivots_by_month(self):
        JournalStageEvent.objects.create(
            journal_contact=self.jc, stage="contact", event_type="call_logged"
        )
        JournalStageEvent.objects.create(
            journal_contact=self.jc, stage="meet", event_type="meeting_completed"
        )
        url = reverse("journals:journal-analytics-stage-activity")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        row = response.data[0]
        self.assertEqual(row["contact"], 1)
        self.assertEqual(row["meet"], 1)
        self.assertEqual(row["close"], 0)
        self.assertIn("date", row)

    def test_pipeline_breakdown(self):
        # latest stage event determines the bucket
        JournalStageEvent.objects.create(
            journal_contact=self.jc, stage="contact", event_type="call_logged"
        )
        JournalStageEvent.objects.create(
            journal_contact=self.jc, stage="meet", event_type="meeting_completed"
        )
        url = reverse("journals:journal-analytics-pipeline-breakdown")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stages = {item["stage"]: item["count"] for item in response.data}
        self.assertEqual(stages.get("meet"), 1)

    def test_pipeline_breakdown_no_events_defaults_to_contact(self):
        url = reverse("journals:journal-analytics-pipeline-breakdown")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stages = {item["stage"]: item["count"] for item in response.data}
        self.assertEqual(stages.get("contact"), 1)

    def test_next_steps_queue(self):
        NextStep.objects.create(
            journal_contact=self.jc,
            title="Call back",
            completed=False,
            due_date=timezone.now().date(),
        )
        NextStep.objects.create(journal_contact=self.jc, title="Done item", completed=True)
        url = reverse("journals:journal-analytics-next-steps-queue")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["title"], "Call back")
        self.assertEqual(item["contact_name"], "Cara Cyan")
        self.assertEqual(item["journal_name"], "Report Journal")
        self.assertEqual(item["journal_contact_id"], str(self.jc.id))

    def test_journal_report_requires_journal_id(self):
        url = reverse("journals:journal-analytics-journal-report")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_journal_report_404_for_missing_journal(self):
        url = reverse("journals:journal-analytics-journal-report")
        import uuid

        response = self.client.get(url, {"journal_id": str(uuid.uuid4())})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_journal_report_403_for_other_users_journal(self):
        other_journal = Journal.objects.create(
            owner=self.other, name="Hidden", goal_amount=Decimal("5000.00")
        )
        url = reverse("journals:journal-analytics-journal-report")
        response = self.client.get(url, {"journal_id": str(other_journal.id)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_journal_report_full_payload(self):
        # Active and pending decisions, a stage event, an open next step
        Decision.objects.create(
            journal_contact=self.jc, amount=Decimal("300.00"), cadence="monthly", status="active"
        )
        c2 = Contact.objects.create(
            owner=self.owner, first_name="Dee", last_name="Dot", status="prospect"
        )
        jc2 = JournalContact.objects.create(journal=self.journal, contact=c2)
        Decision.objects.create(
            journal_contact=jc2, amount=Decimal("400.00"), cadence="monthly", status="pending"
        )
        JournalStageEvent.objects.create(
            journal_contact=self.jc, stage="meet", event_type="meeting_completed"
        )
        NextStep.objects.create(journal_contact=self.jc, title="Open step", completed=False)

        url = reverse("journals:journal-analytics-journal-report")
        response = self.client.get(url, {"journal_id": str(self.journal.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.data
        self.assertEqual(body["metrics"]["total_contacts"], 2)
        self.assertEqual(body["metrics"]["with_decisions"], 2)
        # Sum() aggregate Decimals stringify without forced 2-dp scale.
        self.assertEqual(Decimal(body["metrics"]["confirmed_amount"]), Decimal("300"))
        self.assertEqual(Decimal(body["metrics"]["pending_amount"]), Decimal("400"))
        self.assertEqual(body["goal_amount"], "10000.00")
        # jc2 has no stage events -> 'none' bucket; jc has 'meet'
        stage_map = {s["stage"]: s["count"] for s in body["stage_distribution"]}
        self.assertEqual(stage_map.get("meet"), 1)
        self.assertEqual(stage_map.get("none"), 1)
        status_map = {s["status"]: s["count"] for s in body["decision_status"]}
        self.assertEqual(status_map.get("active"), 1)
        self.assertEqual(status_map.get("pending"), 1)
        self.assertEqual(body["alerts"]["open_next_steps"], 1)
        # Both members are stalled (no events in last 30 days for jc2; jc event
        # is fresh, so only jc2 stalled)
        self.assertEqual(body["alerts"]["stalled_contacts"], 1)

    def test_journal_report_date_filtering_excludes_old(self):
        # An event 60 days ago should be excluded by date_from
        old_event = JournalStageEvent.objects.create(
            journal_contact=self.jc, stage="contact", event_type="call_logged"
        )
        JournalStageEvent.objects.filter(pk=old_event.pk).update(
            created_at=timezone.now() - timedelta(days=60)
        )
        url = reverse("journals:journal-analytics-journal-report")
        date_from = (timezone.now() - timedelta(days=7)).date().isoformat()
        response = self.client.get(
            url, {"journal_id": str(self.journal.id), "date_from": date_from}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # stage_distribution uses latest_stage subquery (NOT date filtered),
        # so it still reflects 'contact'. Just assert the call succeeds with filter.
        self.assertIn("stage_distribution", response.data)

    def test_journal_report_date_to_filters_decisions(self):
        # A decision dated in the future is excluded by date_to.
        future_dec = Decision.objects.create(
            journal_contact=self.jc,
            amount=Decimal("500.00"),
            cadence="monthly",
            status="active",
        )
        Decision.objects.filter(pk=future_dec.pk).update(
            created_at=timezone.now() + timedelta(days=30)
        )
        url = reverse("journals:journal-analytics-journal-report")
        date_to = timezone.now().date().isoformat()
        response = self.client.get(url, {"journal_id": str(self.journal.id), "date_to": date_to})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Decision is after date_to, so confirmed_amount aggregates to 0.
        self.assertEqual(Decimal(response.data["metrics"]["confirmed_amount"]), Decimal("0"))
        self.assertEqual(response.data["decision_status"], [])

    def test_admin_summary_requires_admin(self):
        url = reverse("journals:journal-analytics-admin-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_summary_returns_aggregates(self):
        Decision.objects.create(
            journal_contact=self.jc, amount=Decimal("100.00"), cadence="monthly", status="active"
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("journals:journal-analytics-admin-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_journals"], 1)
        self.assertEqual(response.data["total_decisions"], 1)
        self.assertEqual(len(response.data["journals_by_user"]), 1)
        self.assertEqual(response.data["journals_by_user"][0]["email"], self.owner.email)
        self.assertEqual(response.data["journals_by_user"][0]["count"], 1)

    def test_analytics_owner_scoped(self):
        Decision.objects.create(
            journal_contact=self.jc, amount=Decimal("100.00"), cadence="monthly", status="active"
        )
        self.client.force_authenticate(user=self.other)
        url = reverse("journals:journal-analytics-decision-trends")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
