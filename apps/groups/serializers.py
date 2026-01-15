"""
Serializers for Group model.
"""
from rest_framework import serializers

from apps.groups.models import Group


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer for Group model.
    """
    contact_count = serializers.IntegerField(source='annotated_contact_count', read_only=True)
    is_shared = serializers.BooleanField(read_only=True)

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'color',
            'owner', 'is_system', 'is_shared',
            'contact_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'is_system', 'created_at', 'updated_at']


class GroupCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating groups.
    """
    class Meta:
        model = Group
        fields = ['name', 'description', 'color']

    def create(self, validated_data):
        # Set owner to current user (private group)
        # To create shared groups, admin must set owner=None separately
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['owner'] = request.user
        return super().create(validated_data)
