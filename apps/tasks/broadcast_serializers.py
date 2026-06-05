"""
Serializers for broadcast task operations.

Provides list, detail, and create serializers for the BroadcastTask model.
"""
from rest_framework import serializers

from apps.tasks.models import BroadcastTask, TaskPriority, TaskType


class BroadcastTaskListSerializer(serializers.ModelSerializer):
    """Serializer for broadcast task list views with completion stats."""

    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    total_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = BroadcastTask
        fields = [
            "id",
            "sender",
            "sender_name",
            "title",
            "description",
            "task_type",
            "priority",
            "due_date",
            "target_type",
            "recipient_count",
            "completed_count",
            "total_count",
            "is_cancelled",
            "cancelled_at",
            "created_at",
        ]


class BroadcastTaskDetailSerializer(BroadcastTaskListSerializer):
    """Extended serializer that includes recipient_ids for detail views."""

    class Meta(BroadcastTaskListSerializer.Meta):
        fields = BroadcastTaskListSerializer.Meta.fields + ["recipient_ids"]


class BroadcastCreateSerializer(serializers.Serializer):
    """Serializer for validating broadcast creation requests."""

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="")
    task_type = serializers.ChoiceField(
        choices=TaskType.choices,
        default=TaskType.OTHER,
    )
    priority = serializers.ChoiceField(
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
    )
    due_date = serializers.DateField()
    target_type = serializers.ChoiceField(
        choices=[
            ("all_missionaries", "All Missionaries"),
            ("all_supervisors", "All Supervisors"),
            ("specific_users", "Specific Users"),
            ("my_team", "My Team"),
        ],
    )
    specific_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        target_type = attrs.get("target_type")
        specific_user_ids = attrs.get("specific_user_ids", [])

        # Require specific_user_ids when target_type is 'specific_users'
        if target_type == "specific_users" and not specific_user_ids:
            raise serializers.ValidationError(
                {
                    "specific_user_ids": (
                        "At least one user ID is required for specific_users target type."
                    )
                }
            )

        # Supervisor role restrictions
        request = self.context.get("request")
        if request and request.user.role == "supervisor":
            if target_type in ("all_missionaries", "all_supervisors"):
                raise serializers.ValidationError(
                    {
                        "target_type": (
                            "Supervisors cannot target all missionaries or all supervisors."
                        )
                    }
                )

        return attrs


class BroadcastUpdateSerializer(serializers.Serializer):
    """Serializer for validating broadcast update requests (all fields optional)."""

    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    task_type = serializers.ChoiceField(choices=TaskType.choices, required=False)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, required=False)
    due_date = serializers.DateField(required=False)
