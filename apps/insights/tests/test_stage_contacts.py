"""
Tests for stage contacts endpoint.
"""
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.journals.models import Journal, JournalContact, JournalStageEvent, PipelineStage
from apps.users.models import User


class TestStageContacts(TestCase):
    """Test admin stage contacts endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create admin user
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            role="admin",
        )

        # Create non-admin user
        self.staff = User.objects.create_user(
            email="staff@test.com",
            password="testpass123",
            first_name="Staff",
            last_name="User",
            role="missionary",
        )

        # Create contacts
        self.contact1 = Contact.objects.create(
            first_name="Alice",
            last_name="Contact",
            email="alice@test.com",
            owner=self.staff,
            status="active",
        )

        self.contact2 = Contact.objects.create(
            first_name="Bob",
            last_name="Contact",
            email="bob@test.com",
            owner=self.staff,
            status="active",
        )

        self.contact3 = Contact.objects.create(
            first_name="Charlie",
            last_name="Contact",
            email="charlie@test.com",
            owner=self.staff,
            status="active",
        )

        # Create journal
        self.journal = Journal.objects.create(
            name="Test Journal", owner=self.staff, goal_amount=10000.00
        )

        # Add contacts to journal
        self.jc1 = JournalContact.objects.create(journal=self.journal, contact=self.contact1)

        self.jc2 = JournalContact.objects.create(journal=self.journal, contact=self.contact2)

        self.jc3 = JournalContact.objects.create(journal=self.journal, contact=self.contact3)

        # Create stage events - contact1 in "contact" stage
        JournalStageEvent.objects.create(
            journal_contact=self.jc1, stage=PipelineStage.CONTACT.value
        )

        # Contact2 in "meet" stage
        JournalStageEvent.objects.create(
            journal_contact=self.jc2, stage=PipelineStage.CONTACT.value
        )
        JournalStageEvent.objects.create(journal_contact=self.jc2, stage=PipelineStage.MEET.value)

        # Contact3 has no stage events (No Activity)

    def test_admin_can_access_endpoint(self):
        """Test that admin can access the stage contacts endpoint."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("insights:admin-stage-contacts")
        response = self.client.get(url, {"stage": "contact"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("contacts", response.data)
        self.assertIn("total_count", response.data)
        self.assertIn("stage", response.data)

    def test_non_admin_gets_403(self):
        """Test that non-admin user gets 403 Forbidden."""
        self.client.force_authenticate(user=self.staff)
        url = reverse("insights:admin-stage-contacts")
        response = self.client.get(url, {"stage": "contact"})
        self.assertEqual(response.status_code, 403)

    def test_stage_parameter_is_required(self):
        """Test that stage parameter is required."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("insights:admin-stage-contacts")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
        self.assertIn("stage", response.data["detail"])

    def test_returns_contacts_in_correct_stage(self):
        """Test that endpoint returns contacts in the correct stage."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("insights:admin-stage-contacts")

        # Test "contact" stage - should return contact1
        response = self.client.get(url, {"stage": "contact"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(len(response.data["contacts"]), 1)
        self.assertEqual(response.data["contacts"][0]["full_name"], "Alice Contact")

        # Test "meet" stage - should return contact2
        response = self.client.get(url, {"stage": "meet"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(len(response.data["contacts"]), 1)
        self.assertEqual(response.data["contacts"][0]["full_name"], "Bob Contact")

    def test_returns_empty_list_for_stage_with_no_contacts(self):
        """Test that endpoint returns empty list for stage with no contacts."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("insights:admin-stage-contacts")
        response = self.client.get(url, {"stage": "close"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 0)
        self.assertEqual(len(response.data["contacts"]), 0)

    def test_none_stage_parameter_returns_contacts_with_no_stage_events(self):
        """Test that "none" stage parameter returns contacts with no stage events."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("insights:admin-stage-contacts")
        response = self.client.get(url, {"stage": "none"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(len(response.data["contacts"]), 1)
        self.assertEqual(response.data["contacts"][0]["full_name"], "Charlie Contact")

    def test_contact_data_structure(self):
        """Test that contact data includes required fields."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("insights:admin-stage-contacts")
        response = self.client.get(url, {"stage": "contact"})
        self.assertEqual(response.status_code, 200)

        contact = response.data["contacts"][0]
        self.assertIn("id", contact)
        self.assertIn("full_name", contact)
        self.assertIn("email", contact)
        self.assertIn("owner_name", contact)
        self.assertIn("last_activity_date", contact)
        self.assertEqual(contact["owner_name"], "Staff User")

    def test_limit_parameter(self):
        """Test that limit parameter restricts results."""
        self.client.force_authenticate(user=self.admin)

        # Create more contacts in "contact" stage
        for i in range(5):
            contact = Contact.objects.create(
                first_name=f"Test{i}",
                last_name="Contact",
                email=f"test{i}@test.com",
                owner=self.staff,
                status="active",
            )
            jc = JournalContact.objects.create(journal=self.journal, contact=contact)
            JournalStageEvent.objects.create(journal_contact=jc, stage=PipelineStage.CONTACT.value)

        url = reverse("insights:admin-stage-contacts")
        response = self.client.get(url, {"stage": "contact", "limit": 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 6)  # 1 original + 5 new
        self.assertEqual(len(response.data["contacts"]), 3)  # Limited to 3
