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
    Used only by admin-gated endpoints (UserListCreateView, UserDetailView).
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'supervisor', 'coach_id', 'monthly_goal', 'email_notifications',
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
            'monthly_goal', 'email_notifications', 'dashboard_layout'
        ]


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for admin updating any user.
    """
    supervised_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text='List of user IDs to assign as supervised users'
    )
    coached_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text='List of user IDs to assign as coached users'
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'role',
            'monthly_goal', 'email_notifications', 'is_active',
            'supervised_user_ids', 'coached_user_ids'
        ]

    def update(self, instance, validated_data):
        supervised_ids = validated_data.pop('supervised_user_ids', None)
        coached_ids = validated_data.pop('coached_user_ids', None)
        instance = super().update(instance, validated_data)
        if supervised_ids is not None:
            # Clear existing supervised users (set their supervisor to None)
            instance.supervised_users.update(supervisor=None)
            # Assign new supervised users
            User.objects.filter(id__in=supervised_ids, is_active=True).update(supervisor=instance)
        if coached_ids is not None:
            # Clear existing coached users (set their coach to None)
            instance.coached_users.update(coach=None)
            # Assign new coached users
            User.objects.filter(id__in=coached_ids, is_active=True).update(coach=instance)
        return instance


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
    supervised_users = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'monthly_goal', 'email_notifications',
            'date_joined', 'last_login_at',
            'contact_count', 'active_pledge_count', 'dashboard_layout',
            'supervised_users'
        ]
        read_only_fields = fields

    def get_contact_count(self, obj):
        """Get count of contacts owned by this user."""
        # Use annotated value if available (from view), otherwise query
        if hasattr(obj, '_contact_count'):
            return obj._contact_count
        if hasattr(obj, 'contacts'):
            return obj.contacts.count()
        return 0

    def get_active_pledge_count(self, obj):
        """Get count of active recurring gifts for contacts owned by this user."""
        # Use annotated value if available (from view), otherwise single query
        if hasattr(obj, '_active_pledge_count'):
            return obj._active_pledge_count

        from apps.gifts.models import RecurringGift, RecurringGiftStatus
        return RecurringGift.objects.filter(
            donor_contact__owner=obj,
            status=RecurringGiftStatus.ACTIVE
        ).count()

    def get_supervised_users(self, obj):
        """Return list of supervised/coached user summaries for supervisor or coach."""
        if obj.role == 'supervisor':
            qs = obj.supervised_users.filter(is_active=True)
        elif obj.role == 'coach':
            qs = obj.coached_users.filter(is_active=True)
        else:
            return []
        return list(
            qs.values('id', 'first_name', 'last_name', 'email')
            .order_by('last_name', 'first_name')
        )
