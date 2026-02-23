"""
Serializers for Gift and RecurringGift models.
"""
from rest_framework import serializers

from apps.gifts.models import Gift, GiftCredit, RecurringGift


class GiftSerializer(serializers.ModelSerializer):
    """
    Serializer for Gift model (read operations).
    """
    amount_dollars = serializers.DecimalField(
        read_only=True, max_digits=12, decimal_places=2
    )
    donor_contact_name = serializers.SerializerMethodField()
    fund_name = serializers.CharField(
        source='fund.name', read_only=True, default=None
    )

    class Meta:
        model = Gift
        fields = [
            'id', 'donor_contact', 'donor_contact_name', 'fund', 'fund_name',
            'external_gift_id', 'amount_cents', 'amount_dollars',
            'gift_date', 'description',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_donor_contact_name(self, obj):
        return obj.donor_contact.full_name if obj.donor_contact else None


class GiftCreditReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for GiftCredit with solicitor name.
    """
    solicitor_name = serializers.CharField(
        source='solicitor.normalized_name', read_only=True
    )
    amount_dollars = serializers.DecimalField(
        read_only=True, max_digits=12, decimal_places=2
    )

    class Meta:
        model = GiftCredit
        fields = ['id', 'solicitor', 'solicitor_name', 'amount_cents', 'amount_dollars']
        read_only_fields = ['id', 'solicitor', 'solicitor_name', 'amount_cents', 'amount_dollars']


class GiftDetailSerializer(GiftSerializer):
    """
    Extended Gift serializer with nested solicitor credit breakdown.
    Used for retrieve (detail) views.
    """
    credits = GiftCreditReadSerializer(many=True, read_only=True)

    class Meta(GiftSerializer.Meta):
        fields = GiftSerializer.Meta.fields + ['credits']


class GiftCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating gifts.
    """
    class Meta:
        model = Gift
        fields = [
            'id', 'donor_contact', 'fund', 'amount_cents',
            'gift_date', 'description', 'external_gift_id',
        ]
        read_only_fields = ['id']

    def validate_donor_contact(self, value):
        """Ensure user has permission to add gift to this contact."""
        request = self.context.get('request')
        if request:
            user = request.user
            if user.role in ['admin', 'finance']:
                return value
            if value.owner != user:
                raise serializers.ValidationError(
                    'You can only add gifts to your own contacts.'
                )
        return value


class RecurringGiftSerializer(serializers.ModelSerializer):
    """
    Serializer for RecurringGift model (read operations).
    """
    amount_dollars = serializers.DecimalField(
        read_only=True, max_digits=12, decimal_places=2
    )
    monthly_equivalent = serializers.DecimalField(
        read_only=True, max_digits=12, decimal_places=2
    )
    donor_contact_name = serializers.SerializerMethodField()
    fund_name = serializers.CharField(
        source='fund.name', read_only=True, default=None
    )

    class Meta:
        model = RecurringGift
        fields = [
            'id', 'donor_contact', 'donor_contact_name', 'fund', 'fund_name',
            'external_gift_id', 'amount_cents', 'amount_dollars',
            'frequency', 'start_date', 'end_date', 'status',
            'monthly_equivalent', 'description',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_donor_contact_name(self, obj):
        return obj.donor_contact.full_name if obj.donor_contact else None


class RecurringGiftCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating recurring gifts.
    """
    class Meta:
        model = RecurringGift
        fields = [
            'id', 'donor_contact', 'fund', 'amount_cents',
            'frequency', 'status', 'start_date', 'end_date',
            'description', 'external_gift_id',
        ]
        read_only_fields = ['id']

    def validate_donor_contact(self, value):
        """Ensure user has permission to add recurring gift to this contact."""
        request = self.context.get('request')
        if request:
            user = request.user
            if user.role in ['admin', 'finance']:
                return value
            if value.owner != user:
                raise serializers.ValidationError(
                    'You can only add recurring gifts to your own contacts.'
                )
        return value
