"""
Serializers for Task model.
"""
from rest_framework import serializers

from apps.tasks.models import Task
from apps.journals.models import Journal


class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for Task model.
    """
    contact_name = serializers.CharField(source='contact.full_name', read_only=True, allow_null=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    # Journal field with ownership validation
    journal = serializers.PrimaryKeyRelatedField(
        queryset=Journal.objects.all(),
        required=False,
        allow_null=True
    )
    journal_name = serializers.CharField(source='journal.name', read_only=True, allow_null=True)

    class Meta:
        model = Task
        fields = [
            'id', 'owner', 'owner_name',
            'contact', 'contact_name',
            'journal', 'journal_name',
            'title', 'description', 'task_type',
            'priority', 'status',
            'due_date', 'due_time', 'reminder_date',
            'is_overdue', 'completed_at', 'completed_by',
            'auto_generated', 'source_event',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'completed_at', 'completed_by',
            'auto_generated', 'source_event',
            'created_at', 'updated_at'
        ]

    def validate_journal(self, value):
        """Ensure journal belongs to the request user."""
        if value and value.owner != self.context['request'].user:
            raise serializers.ValidationError("Journal does not belong to you")
        return value


class TaskCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating tasks.
    """
    journal = serializers.PrimaryKeyRelatedField(
        queryset=Journal.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Task
        fields = [
            'id', 'contact', 'journal', 'title', 'description', 'task_type',
            'priority', 'status', 'due_date', 'due_time', 'reminder_date'
        ]
        read_only_fields = ['id', 'status']

    def validate_journal(self, value):
        """Ensure journal belongs to the request user."""
        if value and value.owner != self.context['request'].user:
            raise serializers.ValidationError("Journal does not belong to you")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['owner'] = request.user
        return super().create(validated_data)
