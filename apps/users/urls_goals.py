"""
URL patterns for Goal tracking endpoints.
"""
from django.urls import path

from apps.users.views_goals import GoalView

urlpatterns = [
    path("me/", GoalView.as_view(), name="goal-me"),
]
