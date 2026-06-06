"""
Admin registration for FeedbackEntry — secondary surface alongside the
React /admin/feedback page. Feedback may contain PII; admin role only.
"""

from django.contrib import admin

from apps.feedback.models import FeedbackEntry


@admin.register(FeedbackEntry)
class FeedbackEntryAdmin(admin.ModelAdmin):
    list_display = ["created_at", "type", "status", "title", "submitter"]
    list_filter = ["type", "status", "created_at"]
    search_fields = ["title", "description", "submitter__email"]
    readonly_fields = [
        "id",
        "submitter",
        "type",
        "title",
        "description",
        "page_url",
        "user_agent",
        "created_at",
        "updated_at",
    ]
    fields = [
        "id",
        "created_at",
        "updated_at",
        "submitter",
        "type",
        "title",
        "description",
        "status",
        "page_url",
        "user_agent",
    ]
