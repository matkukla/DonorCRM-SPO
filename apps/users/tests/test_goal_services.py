"""
Test stubs for goal progress service function.
GOAL-04: get_goal_progress(user) computes effective_monthly_support from journal-scoped donations.

Imports are deferred inside each test so pytest can collect all 4 items even before
apps/users/goal_services.py exists. Tests fail at runtime with ImportError (correct RED state).
"""
import pytest
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
def test_goal_progress_no_journals():
    """GOAL-04: When no GoalJournalSelections exist, effective_monthly_support == 0.0."""
    from apps.users.goal_services import get_goal_progress
    user = UserFactory()
    result = get_goal_progress(user)
    assert result["effective_monthly_support"] == 0.0


@pytest.mark.django_db
def test_goal_progress_recurring_only():
    """GOAL-04: When journal contacts have active RecurringGifts, recurring_monthly is correct.

    one_time_monthly should be 0 when no one-time fiscal-year gifts exist.
    """
    from apps.users.goal_services import get_goal_progress
    user = UserFactory()
    # Future: add RecurringGift fixtures via journal contacts
    result = get_goal_progress(user)
    assert "recurring_monthly" in result
    assert result["one_time_monthly"] == 0.0


@pytest.mark.django_db
def test_goal_progress_one_time_only():
    """GOAL-04: One-time gifts within the fiscal year are spread over months_remaining.

    one_time_monthly = fy_gifts_total / months_remaining. recurring_monthly == 0.
    """
    from apps.users.goal_services import get_goal_progress
    user = UserFactory()
    # Future: add one-time Donation fixtures via journal contacts
    result = get_goal_progress(user)
    assert "one_time_monthly" in result
    assert result["recurring_monthly"] == 0.0


@pytest.mark.django_db
def test_goal_progress_scoping():
    """GOAL-04: Gifts from contacts NOT in selected journals are excluded.

    Creating a second user's journal gifts should not appear in first user's result.
    """
    from apps.users.goal_services import get_goal_progress
    user = UserFactory()
    other_user = UserFactory()  # noqa: F841 — future fixture setup will use this
    # Future: create other_user journal with gifts, verify not in user's result
    result = get_goal_progress(user)
    # Result should only reflect user's own journals
    assert isinstance(result, dict)
    assert "effective_monthly_support" in result
