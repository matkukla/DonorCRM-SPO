"""
Models for user-submitted feedback (bug reports, feature requests, etc.).
"""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class FeedbackType(models.TextChoices):
    """Type of feedback being submitted."""

    BUG = "bug", "Bug"
    FEATURE = "feature", "Feature Request"
    OTHER = "other", "Other"


class FeedbackStatus(models.TextChoices):
    """Triage status of a feedback entry."""

    NEW = "new", "New"
    TRIAGED = "triaged", "Triaged"
    RESOLVED = "resolved", "Resolved"
    DUPLICATE = "duplicate", "Duplicate"


class FeedbackEntry(TimeStampedModel):
    """
    A piece of feedback submitted by an authenticated user.

    Any authenticated user can create a feedback entry; only admins can
    list, read, update, or delete entries. Captures the page URL and user
    agent at submission time to aid triage.
    """

    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="feedback_submitted",
        db_index=True,
        help_text="User who submitted this feedback",
    )
    type = models.CharField(
        "type",
        max_length=20,
        choices=FeedbackType.choices,
        db_index=True,
    )
    title = models.CharField("title", max_length=255)
    description = models.TextField("description")
    status = models.CharField(
        "status",
        max_length=20,
        choices=FeedbackStatus.choices,
        default=FeedbackStatus.NEW,
        db_index=True,
    )
    page_url = models.CharField(
        "page url",
        max_length=500,
        blank=True,
        default="",
        help_text="Page URL where the feedback was submitted from",
    )
    user_agent = models.CharField(
        "user agent",
        max_length=500,
        blank=True,
        default="",
        help_text="Browser user agent at submission time",
    )

    class Meta:
        db_table = "feedback_entries"
        verbose_name = "feedback entry"
        verbose_name_plural = "feedback entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.get_type_display()}] {self.title}"
