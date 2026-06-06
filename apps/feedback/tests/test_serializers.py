"""
Tests for FeedbackEntry serializers.
"""

import pytest

from apps.feedback.models import FeedbackEntry, FeedbackType
from apps.feedback.serializers import FeedbackEntryCreateSerializer, FeedbackEntrySerializer
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestFeedbackEntryCreateSerializer:
    def test_valid_payload(self):
        serializer = FeedbackEntryCreateSerializer(
            data={
                "type": "bug",
                "title": "Login broken",
                "description": "Cannot log in with valid credentials.",
            }
        )
        assert serializer.is_valid(), serializer.errors

    def test_blank_title_rejected(self):
        serializer = FeedbackEntryCreateSerializer(
            data={"type": "bug", "title": "   ", "description": "detail"}
        )
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_blank_description_rejected(self):
        serializer = FeedbackEntryCreateSerializer(
            data={"type": "bug", "title": "A title", "description": ""}
        )
        assert not serializer.is_valid()
        assert "description" in serializer.errors

    def test_invalid_type_rejected(self):
        serializer = FeedbackEntryCreateSerializer(
            data={"type": "spam", "title": "A", "description": "B"}
        )
        assert not serializer.is_valid()
        assert "type" in serializer.errors


@pytest.mark.django_db
class TestFeedbackEntrySerializer:
    def test_exposes_submitter_metadata(self):
        user = UserFactory(email="alice@example.com", first_name="Alice", last_name="S")
        entry = FeedbackEntry.objects.create(
            submitter=user,
            type=FeedbackType.OTHER,
            title="Suggestion",
            description="Thanks for the app",
        )
        data = FeedbackEntrySerializer(entry).data
        assert data["submitter_email"] == "alice@example.com"
        assert data["submitter_name"]
        assert data["type_display"] == "Other"
        assert data["status_display"] == "New"
