"""
Serializers for Contact model.
"""
from rest_framework import serializers

from apps.contacts.models import Contact, ContactStatus
from apps.groups.serializers import GroupSerializer


class ContactListSerializer(serializers.ModelSerializer):
    """
    Serializer for contact list view (minimal fields).
    """
    full_name = serializers.CharField(read_only=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)

    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'status',
            'total_given', 'gift_count', 'last_gift_date',
            'needs_thank_you', 'owner', 'owner_name'
        ]


class ContactDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for contact detail view (all fields).
    """
    full_name = serializers.CharField(read_only=True)
    full_address = serializers.CharField(read_only=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    has_active_pledge = serializers.BooleanField(read_only=True)
    monthly_pledge_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    groups = GroupSerializer(many=True, read_only=True)
    group_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Contact
        fields = [
            'id', 'owner', 'owner_name',
            'first_name', 'last_name', 'full_name',
            'email', 'phone', 'phone_secondary',
            'street_address', 'city', 'state', 'postal_code', 'country',
            'full_address', 'status',
            'first_gift_date', 'last_gift_date', 'last_gift_amount',
            'total_given', 'gift_count',
            'has_active_pledge', 'monthly_pledge_amount',
            'last_thanked_at', 'needs_thank_you',
            'notes', 'groups', 'group_ids',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'first_gift_date', 'last_gift_date',
            'last_gift_amount', 'total_given', 'gift_count',
            'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        group_ids = validated_data.pop('group_ids', [])
        contact = super().create(validated_data)
        if group_ids:
            from apps.groups.models import Group
            groups = Group.objects.filter(id__in=group_ids)
            contact.groups.set(groups)
        return contact

    def update(self, instance, validated_data):
        group_ids = validated_data.pop('group_ids', None)
        contact = super().update(instance, validated_data)
        if group_ids is not None:
            from apps.groups.models import Group
            groups = Group.objects.filter(id__in=group_ids)
            contact.groups.set(groups)
        return contact


class ContactCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating contacts.
    """
    group_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'phone_secondary',
            'street_address', 'city', 'state', 'postal_code', 'country',
            'status', 'notes', 'group_ids',
            'total_given', 'gift_count', 'needs_thank_you'
        ]
        read_only_fields = ['id', 'total_given', 'gift_count', 'needs_thank_you']

    def create(self, validated_data):
        group_ids = validated_data.pop('group_ids', [])

        # Set owner to current user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['owner'] = request.user

        contact = Contact.objects.create(**validated_data)

        if group_ids:
            from apps.groups.models import Group
            groups = Group.objects.filter(id__in=group_ids)
            contact.groups.set(groups)

        return contact


class ContactImportSerializer(serializers.Serializer):
    """
    Serializer for CSV import validation.
    """
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    street_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=50, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, default='USA')
    notes = serializers.CharField(required=False, allow_blank=True)
