"""
API integration tests for duplicate detection and merge endpoints.

Tests mock TrigramSimilarity-dependent service functions for SQLite compatibility
while still testing the full HTTP request/response cycle.
"""
import uuid
from unittest.mock import patch

from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact, DismissedDuplicate
from apps.contacts.tests.factories import ContactFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestDuplicateCheck:
    """Tests for POST /api/v1/contacts/duplicates/check/"""

    def test_duplicate_check_returns_matches(self, auth_client, user):
        """POST with matching email returns match with confidence='high'."""
        contact = ContactFactory(owner=user, email="existing@example.com")
        mock_result = [
            {
                "contact": contact,
                "confidence": "high",
                "reasons": ["Exact email match"],
                "similarity": 1.0,
            }
        ]
        with patch("apps.contacts.views.find_duplicates_for_contact", return_value=mock_result):
            resp = auth_client.post(
                "/api/v1/contacts/duplicates/check/",
                {"email": "existing@example.com"},
                format="json",
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["confidence"] == "high"
        assert data[0]["id"] == str(contact.id)
        assert data[0]["email"] == "existing@example.com"

    def test_duplicate_check_empty_returns_empty(self, auth_client, user):
        """POST with unique data returns empty list."""
        with patch("apps.contacts.views.find_duplicates_for_contact", return_value=[]):
            resp = auth_client.post(
                "/api/v1/contacts/duplicates/check/",
                {"first_name": "UniquelyUniqueName", "last_name": "Nobody"},
                format="json",
            )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_duplicate_check_unauthenticated_403(self, api_client):
        """Unauthenticated request returns 401."""
        resp = api_client.post(
            "/api/v1/contacts/duplicates/check/",
            {"email": "test@example.com"},
            format="json",
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestMergeContacts:
    """Tests for POST /api/v1/contacts/duplicates/merge/"""

    def test_merge_success(self, auth_client, user):
        """POST with valid survivor_id/loser_id returns survivor data."""
        survivor = ContactFactory(owner=user, first_name="Alice", last_name="Smith")
        loser = ContactFactory(owner=user, first_name="Alice", last_name="Smithe")

        resp = auth_client.post(
            "/api/v1/contacts/duplicates/merge/",
            {
                "survivor_id": str(survivor.id),
                "loser_id": str(loser.id),
            },
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(survivor.id)
        assert data["first_name"] == "Alice"

        # Verify loser is now soft-deleted
        loser.refresh_from_db()
        assert loser.is_merged is True
        assert loser.merged_into_id == survivor.id

    def test_merge_invalid_ids_404(self, auth_client, user):
        """POST with nonexistent IDs returns 404."""
        resp = auth_client.post(
            "/api/v1/contacts/duplicates/merge/",
            {
                "survivor_id": str(uuid.uuid4()),
                "loser_id": str(uuid.uuid4()),
            },
            format="json",
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestDismissDuplicate:
    """Tests for POST /api/v1/contacts/duplicates/dismiss/"""

    def test_dismiss_success(self, auth_client, user):
        """POST with two contact IDs creates DismissedDuplicate."""
        c1 = ContactFactory(owner=user)
        c2 = ContactFactory(owner=user)
        resp = auth_client.post(
            "/api/v1/contacts/duplicates/dismiss/",
            {
                "contact_a_id": str(c1.id),
                "contact_b_id": str(c2.id),
            },
            format="json",
        )
        assert resp.status_code == 201
        assert DismissedDuplicate.objects.count() == 1


@pytest.mark.django_db
class TestContactListExcludesMerged:
    """Tests for GET /api/v1/contacts/ filtering merged contacts."""

    def test_contact_list_excludes_merged(self, auth_client, user):
        """GET /api/v1/contacts/ does not include is_merged=True contacts."""
        active = ContactFactory(owner=user, first_name="Active")
        merged = ContactFactory(owner=user, first_name="Merged", is_merged=True)

        resp = auth_client.get("/api/v1/contacts/")
        assert resp.status_code == 200
        data = resp.json()
        # Response may be paginated
        results = data.get("results", data)
        ids = [r["id"] for r in results]
        assert str(active.id) in ids
        assert str(merged.id) not in ids
