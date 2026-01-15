"""
Serializers for Task model.
"""
from rest_framework import serializers

from apps.tasks.models import Task


class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for Task model.
    """
    contact_name = serializers.CharField(source='contact.full_name', read_only=True, allow_null=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'owner', 'owner_name',
            'contact', 'contact_name',
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


class TaskCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating tasks.
    """
    class Meta:
        model = Task
        fields = [
            'id', 'contact', 'title', 'description', 'task_type',
            'priority', 'status', 'due_date', 'due_time', 'reminder_date'
        ]
        read_only_fields = ['id', 'status']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['owner'] = request.user
        return super().create(validated_data)
