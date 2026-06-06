"""
Tests for FeedbackEntry model.
"""

import pytest

from apps.feedback.models import FeedbackEntry, FeedbackStatus, FeedbackType
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestFeedbackEntryModel:
    """Tests for FeedbackEntry model defaults, choices, and ordering."""

    def test_default_status_is_new(self):
        entry = FeedbackEntry.objects.create(
            submitter=UserFactory(),
            type=FeedbackType.BUG,
            title="Test",
            description="Test description",
        )
        assert entry.status == FeedbackStatus.NEW

    def test_string_representation(self):
        entry = FeedbackEntry.objects.create(
            submitter=UserFactory(),
            type=FeedbackType.FEATURE,
            title="Add dark mode",
            description="Would love dark mode",
        )
        assert "Add dark mode" in str(entry)
        assert "Feature Request" in str(entry)

    def test_ordering_newest_first(self):
        user = UserFactory()
        first = FeedbackEntry.objects.create(
            submitter=user,
            type=FeedbackType.BUG,
            title="First",
            description="x",
        )
        second = FeedbackEntry.objects.create(
            submitter=user,
            type=FeedbackType.BUG,
            title="Second",
            description="x",
        )
        ordered = list(FeedbackEntry.objects.all())
        assert ordered[0] == second
        assert ordered[1] == first

    def test_all_type_choices(self):
        choice_values = {choice for choice, _ in FeedbackType.choices}
        assert choice_values == {"bug", "feature", "other"}

    def test_all_status_choices(self):
        choice_values = {choice for choice, _ in FeedbackStatus.choices}
        assert choice_values == {"new", "triaged", "resolved", "duplicate"}
