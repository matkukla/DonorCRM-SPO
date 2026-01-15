"""
Serializers for User model and authentication.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.users.models import User, UserRole


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model (read operations).
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'monthly_goal', 'email_notifications',
            'is_active', 'date_joined', 'last_login_at'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users (admin only).
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'role', 'monthly_goal', 'password', 'password_confirm'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone',
            'monthly_goal', 'email_notifications'
        ]


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for admin updating any user.
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'role',
            'monthly_goal', 'email_notifications', 'is_active'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'New passwords do not match.'
            })
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class CurrentUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the current authenticated user with additional stats.
    """
    full_name = serializers.CharField(read_only=True)
    contact_count = serializers.SerializerMethodField()
    active_pledge_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'monthly_goal', 'email_notifications',
            'date_joined', 'last_login_at',
            'contact_count', 'active_pledge_count'
        ]
        read_only_fields = fields

    def get_contact_count(self, obj):
        """Get count of contacts owned by this user."""
        if hasattr(obj, 'contacts'):
            return obj.contacts.count()
        return 0

    def get_active_pledge_count(self, obj):
        """Get count of active pledges for contacts owned by this user."""
        if hasattr(obj, 'contacts'):
            return sum(
                contact.pledges.filter(status='active').count()
                for contact in obj.contacts.all()
            )
        return 0
