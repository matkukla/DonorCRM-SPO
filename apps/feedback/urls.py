"""
URL patterns for feedback endpoints.
"""

from django.urls import path

from apps.feedback.views import FeedbackDetailView, FeedbackListCreateView

app_name = "feedback"

urlpatterns = [
    path("", FeedbackListCreateView.as_view(), name="feedback-list"),
    path("<uuid:pk>/", FeedbackDetailView.as_view(), name="feedback-detail"),
]
