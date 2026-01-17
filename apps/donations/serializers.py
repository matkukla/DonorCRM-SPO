"""
Serializers for Donation model.
"""
from rest_framework import serializers

from apps.donations.models import Donation, DonationType, PaymentMethod


class DonationSerializer(serializers.ModelSerializer):
    """
    Serializer for Donation model.
    """
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    pledge_info = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = [
            'id', 'contact', 'contact_name', 'pledge', 'pledge_info',
            'amount', 'date', 'donation_type', 'payment_method',
            'external_id', 'thanked', 'thanked_at', 'thanked_by',
            'notes', 'imported_at', 'import_batch',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'thanked_at', 'thanked_by',
            'imported_at', 'import_batch',
            'created_at', 'updated_at'
        ]

    def get_pledge_info(self, obj):
        if obj.pledge:
            return {
                'id': str(obj.pledge.id),
                'amount': str(obj.pledge.amount),
                'frequency': obj.pledge.frequency
            }
        return None


class DonationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating donations.
    """
    class Meta:
        model = Donation
        fields = [
            'id', 'contact', 'pledge', 'amount', 'date',
            'donation_type', 'payment_method', 'external_id', 'notes'
        ]
        read_only_fields = ['id']

    def validate_contact(self, value):
        """Ensure user has permission to add donation to this contact."""
        request = self.context.get('request')
        if request:
            user = request.user
            # Admin and Finance can add donations to any contact
            if user.role in ['admin', 'finance']:
                return value
            # Staffs can only add to their own contacts
            if value.owner != user:
                raise serializers.ValidationError(
                    'You can only add donations to your own contacts.'
                )
        return value


class DonationSummarySerializer(serializers.Serializer):
    """
    Serializer for donation summary/aggregation data.
    """
    period = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    donation_count = serializers.IntegerField()
    unique_donors = serializers.IntegerField()
    average_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class DonationImportSerializer(serializers.Serializer):
    """
    Serializer for CSV import validation.
    """
    contact_email = serializers.EmailField(required=False)
    contact_first_name = serializers.CharField(required=False)
    contact_last_name = serializers.CharField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    date = serializers.DateField()
    donation_type = serializers.ChoiceField(
        choices=DonationType.choices,
        default=DonationType.ONE_TIME
    )
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices,
        default=PaymentMethod.CHECK
    )
    external_id = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
