"""
Serializers for Journal models.
"""
from rest_framework import serializers

from apps.journals.models import Journal, JournalStageEvent


class JournalListSerializer(serializers.ModelSerializer):
    """
    Serializer for journal list view (minimal fields).
    """
    class Meta:
        model = Journal
        fields = [
            'id', 'name', 'goal_amount', 'deadline',
            'is_archived', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_archived']


class JournalDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for journal detail view (all fields).
    """
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Journal
        fields = [
            'id', 'name', 'goal_amount', 'deadline',
            'is_archived', 'archived_at', 'owner',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'is_archived', 'archived_at',
            'created_at', 'updated_at'
        ]


class JournalCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating journals.
    """
    class Meta:
        model = Journal
        fields = ['id', 'name', 'goal_amount', 'deadline']
        read_only_fields = ['id']

    def create(self, validated_data):
        # Set owner to current user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['owner'] = request.user

        journal = Journal.objects.create(**validated_data)
        return journal


class JournalStageEventSerializer(serializers.ModelSerializer):
    """
    Serializer for journal stage events.
    """
    class Meta:
        model = JournalStageEvent
        fields = [
            'id', 'journal_contact', 'stage', 'event_type',
            'notes', 'metadata', 'triggered_by', 'created_at'
        ]
        read_only_fields = ['id', 'triggered_by', 'created_at']

    def create(self, validated_data):
        # Set triggered_by to current user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['triggered_by'] = request.user

        stage_event = JournalStageEvent.objects.create(**validated_data)
        return stage_event
