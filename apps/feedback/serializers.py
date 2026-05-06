"""
Serializers for FeedbackEntry model.

Two serializers separate concerns:
- FeedbackEntryCreateSerializer: writeable for any authenticated user.
  Submitter and user_agent are set in the view.
- FeedbackEntrySerializer: admin read/update view. All fields read-only
  except status.
"""
from rest_framework import serializers

from apps.feedback.models import FeedbackEntry


class FeedbackEntryCreateSerializer(serializers.ModelSerializer):
    """Serializer for submitting new feedback. Only the user-facing fields
    are writeable; submitter and user_agent come from request context."""

    class Meta:
        model = FeedbackEntry
        fields = ["id", "type", "title", "description", "page_url"]
        read_only_fields = ["id"]

    def validate_title(self, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError("Title cannot be blank.")
        return trimmed

    def validate_description(self, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError("Description cannot be blank.")
        return trimmed


class FeedbackEntrySerializer(serializers.ModelSerializer):
    """Serializer for admin read/update view. Status is the only writeable field."""

    submitter_name = serializers.SerializerMethodField()
    submitter_email = serializers.EmailField(source="submitter.email", read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = FeedbackEntry
        fields = [
            "id",
            "submitter",
            "submitter_name",
            "submitter_email",
            "type",
            "type_display",
            "title",
            "description",
            "status",
            "status_display",
            "page_url",
            "user_agent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "submitter",
            "submitter_name",
            "submitter_email",
            "type",
            "type_display",
            "status_display",
            "title",
            "description",
            "page_url",
            "user_agent",
            "created_at",
            "updated_at",
        ]

    def get_submitter_name(self, obj: FeedbackEntry) -> str:
        submitter = getattr(obj, "submitter", None)
        if submitter is None:
            return ""
        return submitter.full_name or submitter.email
