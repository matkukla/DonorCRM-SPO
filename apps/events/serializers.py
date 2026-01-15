"""
Serializers for Event model.
"""
from rest_framework import serializers

from apps.events.models import Event


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for Event model.
    """
    contact_name = serializers.CharField(source='contact.full_name', read_only=True, allow_null=True)

    class Meta:
        model = Event
        fields = [
            'id', 'user', 'event_type', 'severity',
            'title', 'message',
            'contact', 'contact_name',
            'is_read', 'read_at', 'is_new',
            'metadata', 'created_at'
        ]
        read_only_fields = fields


class EventSummarySerializer(serializers.Serializer):
    """
    Serializer for event summary/counts.
    """
    unread_count = serializers.IntegerField()
    new_count = serializers.IntegerField()
