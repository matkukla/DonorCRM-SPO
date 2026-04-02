"""
Serializers for Gift and RecurringGift models.
"""
from rest_framework import serializers

from apps.gifts.models import Gift, GiftCredit, RecurringGift


class GiftSerializer(serializers.ModelSerializer):
    """
    Serializer for Gift model (read operations).
    """

    amount_dollars = serializers.DecimalField(read_only=True, max_digits=12, decimal_places=2)
    donor_contact_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    fund_name = serializers.CharField(source="fund.name", read_only=True, default=None)
    payment_type_display = serializers.SerializerMethodField()
    recurring_gift = serializers.PrimaryKeyRelatedField(read_only=True)
    is_recurring = serializers.SerializerMethodField()
    recurring_gift_frequency = serializers.SerializerMethodField()
    recurring_gift_status = serializers.SerializerMethodField()

    class Meta:
        model = Gift
        fields = [
            "id",
            "donor_contact",
            "donor_contact_name",
            "owner_name",
            "fund",
            "fund_name",
            "external_gift_id",
            "amount_cents",
            "amount_dollars",
            "gift_date",
            "description",
            "payment_type",
            "payment_type_display",
            "recurring_gift",
            "is_recurring",
            "recurring_gift_frequency",
            "recurring_gift_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_donor_contact_name(self, obj):
        return obj.donor_contact.full_name if obj.donor_contact else None

    def get_owner_name(self, obj):
        contact = getattr(obj, "donor_contact", None)
        if contact:
            owner = getattr(contact, "owner", None)
            return owner.full_name if owner else None
        return None

    def get_payment_type_display(self, obj):
        return obj.get_payment_type_display() or None

    def get_is_recurring(self, obj):
        return obj.recurring_gift_id is not None

    def get_recurring_gift_frequency(self, obj):
        if obj.recurring_gift_id and obj.recurring_gift:
            return obj.recurring_gift.get_frequency_display()
        return None

    def get_recurring_gift_status(self, obj):
        if obj.recurring_gift_id and obj.recurring_gift:
            return obj.recurring_gift.get_status_display()
        return None


class GiftCreditReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for GiftCredit with solicitor name.
    """

    solicitor_name = serializers.CharField(source="solicitor.normalized_name", read_only=True)
    amount_dollars = serializers.DecimalField(read_only=True, max_digits=12, decimal_places=2)

    class Meta:
        model = GiftCredit
        fields = ["id", "solicitor", "solicitor_name", "amount_cents", "amount_dollars"]
        read_only_fields = ["id", "solicitor", "solicitor_name", "amount_cents", "amount_dollars"]


class GiftDetailSerializer(GiftSerializer):
    """
    Extended Gift serializer with nested solicitor credit breakdown.
    Used for retrieve (detail) views.
    """

    credits = GiftCreditReadSerializer(many=True, read_only=True)

    class Meta(GiftSerializer.Meta):
        fields = GiftSerializer.Meta.fields + ["credits"]


class GiftCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating gifts.
    """

    class Meta:
        model = Gift
        fields = [
            "id",
            "donor_contact",
            "fund",
            "amount_cents",
            "gift_date",
            "description",
            "payment_type",
            "external_gift_id",
        ]
        read_only_fields = ["id"]

    def validate_donor_contact(self, value):
        """Ensure user has permission to add gift to this contact."""
        request = self.context.get("request")
        if request:
            user = request.user
            if user.role in ["admin", "finance"]:
                return value
            if value.owner != user:
                raise serializers.ValidationError("You can only add gifts to your own contacts.")
        return value


class RecurringGiftSerializer(serializers.ModelSerializer):
    """
    Serializer for RecurringGift model (read operations).
    """

    amount_dollars = serializers.DecimalField(read_only=True, max_digits=12, decimal_places=2)
    monthly_equivalent = serializers.DecimalField(read_only=True, max_digits=12, decimal_places=2)
    donor_contact_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    fund_name = serializers.CharField(source="fund.name", read_only=True, default=None)
    payment_type_display = serializers.SerializerMethodField()

    class Meta:
        model = RecurringGift
        fields = [
            "id",
            "donor_contact",
            "donor_contact_name",
            "owner_name",
            "fund",
            "fund_name",
            "external_gift_id",
            "amount_cents",
            "amount_dollars",
            "frequency",
            "start_date",
            "end_date",
            "status",
            "monthly_equivalent",
            "payment_type",
            "payment_type_display",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_donor_contact_name(self, obj):
        return obj.donor_contact.full_name if obj.donor_contact else None

    def get_owner_name(self, obj):
        contact = getattr(obj, "donor_contact", None)
        if contact:
            owner = getattr(contact, "owner", None)
            return owner.full_name if owner else None
        return None

    def get_payment_type_display(self, obj):
        return obj.get_payment_type_display() or None


class RecurringGiftCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating recurring gifts.
    """

    class Meta:
        model = RecurringGift
        fields = [
            "id",
            "donor_contact",
            "fund",
            "amount_cents",
            "frequency",
            "status",
            "start_date",
            "end_date",
            "description",
            "payment_type",
            "external_gift_id",
        ]
        read_only_fields = ["id"]

    def validate_donor_contact(self, value):
        """Ensure user has permission to add recurring gift to this contact."""
        request = self.context.get("request")
        if request:
            user = request.user
            if user.role in ["admin", "finance"]:
                return value
            if value.owner != user:
                raise serializers.ValidationError(
                    "You can only add recurring gifts to your own contacts."
                )
        return value
