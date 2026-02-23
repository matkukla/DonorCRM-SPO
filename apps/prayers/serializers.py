"""
Serializers for PrayerIntention model.
"""
from django.utils import timezone
from rest_framework import serializers

from apps.prayers.models import PrayerIntention


class PrayerIntentionSerializer(serializers.ModelSerializer):
    """
    Serializer for PrayerIntention model with automatic status timestamp management.

    On status transitions:
    - active: clears answered_at and archived_at
    - answered: sets answered_at, clears archived_at
    - archived: sets archived_at, clears answered_at
    """
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)

    class Meta:
        model = PrayerIntention
        fields = [
            'id', 'contact', 'contact_name', 'title', 'description',
            'status', 'last_prayed_at', 'answered_at', 'archived_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'answered_at', 'archived_at', 'last_prayed_at',
            'created_at', 'updated_at',
        ]

    def update(self, instance, validated_data):
        new_status = validated_data.get('status')
        if new_status and new_status != instance.status:
            now = timezone.now()
            if new_status == 'answered':
                validated_data['answered_at'] = now
                validated_data['archived_at'] = None
            elif new_status == 'archived':
                validated_data['archived_at'] = now
                validated_data['answered_at'] = None
            elif new_status == 'active':
                validated_data['answered_at'] = None
                validated_data['archived_at'] = None
        return super().update(instance, validated_data)
