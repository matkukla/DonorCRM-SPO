"""
Serializers for Pledge model.
"""
from rest_framework import serializers

from apps.pledges.models import Pledge, PledgeFrequency, PledgeStatus


class PledgeSerializer(serializers.ModelSerializer):
    """
    Serializer for Pledge model.
    """
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    monthly_equivalent = serializers.SerializerMethodField()
    fulfillment_percentage = serializers.FloatField(read_only=True)

    def get_monthly_equivalent(self, obj):
        """Return monthly equivalent as a string with 2 decimal places."""
        return f'{obj.monthly_equivalent:.2f}'

    class Meta:
        model = Pledge
        fields = [
            'id', 'contact', 'contact_name',
            'amount', 'frequency', 'status',
            'start_date', 'end_date',
            'last_fulfilled_date', 'next_expected_date',
            'total_expected', 'total_received',
            'monthly_equivalent', 'fulfillment_percentage',
            'is_late', 'days_late', 'late_notified_at',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'last_fulfilled_date', 'next_expected_date',
            'total_expected', 'total_received',
            'is_late', 'days_late', 'late_notified_at',
            'created_at', 'updated_at'
        ]


class PledgeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating pledges.
    """
    monthly_equivalent = serializers.SerializerMethodField()

    def get_monthly_equivalent(self, obj):
        """Return monthly equivalent as a string with 2 decimal places."""
        return f'{obj.monthly_equivalent:.2f}'

    class Meta:
        model = Pledge
        fields = [
            'id', 'contact', 'amount', 'frequency', 'status',
            'start_date', 'end_date', 'notes', 'monthly_equivalent'
        ]
        read_only_fields = ['id', 'monthly_equivalent']

    def validate_contact(self, value):
        """Ensure user has permission to create pledge for this contact."""
        request = self.context.get('request')
        if request:
            user = request.user
            # Admin can create for any contact
            if user.role == 'admin':
                return value
            # Others can only create for their own contacts
            if value.owner != user:
                raise serializers.ValidationError(
                    'You can only create pledges for your own contacts.'
                )
        return value


class PledgeSummarySerializer(serializers.Serializer):
    """
    Serializer for pledge summary statistics.
    """
    total_monthly_pledges = serializers.DecimalField(max_digits=12, decimal_places=2)
    active_pledge_count = serializers.IntegerField()
    late_pledge_count = serializers.IntegerField()
    total_pledged_annually = serializers.DecimalField(max_digits=12, decimal_places=2)
