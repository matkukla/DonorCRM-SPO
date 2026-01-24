"""
Serializers for Journal models.
"""
from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.journals.models import (
    Decision,
    DecisionHistory,
    Journal,
    JournalContact,
    JournalStageEvent,
)


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


class JournalContactSerializer(serializers.ModelSerializer):
    """
    Serializer for journal contact membership with ownership validation.
    """
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    contact_email = serializers.EmailField(source='contact.email', read_only=True)
    contact_status = serializers.CharField(source='contact.status', read_only=True)

    class Meta:
        model = JournalContact
        fields = [
            'id', 'journal', 'contact', 'contact_name',
            'contact_email', 'contact_status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        """
        Validate that the user owns both the journal and contact.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Authentication required')

        user = request.user
        journal = attrs.get('journal')
        contact = attrs.get('contact')

        # Check journal ownership (unless admin)
        if user.role != 'admin' and journal.owner != user:
            raise serializers.ValidationError({
                'journal': 'You do not have permission to add contacts to this journal.'
            })

        # Check contact ownership (unless admin)
        if user.role != 'admin' and contact.owner != user:
            raise serializers.ValidationError({
                'contact': 'You do not have permission to use this contact.'
            })

        return attrs


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


class DecisionSerializer(serializers.ModelSerializer):
    """
    Serializer for decision CRUD with atomic history tracking.
    """
    monthly_equivalent = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Decision
        fields = [
            'id', 'journal_contact', 'amount', 'cadence', 'status',
            'monthly_equivalent', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'monthly_equivalent', 'created_at', 'updated_at']

    def validate_journal_contact(self, value):
        """
        Validate that the user owns the journal_contact's journal.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Authentication required')

        user = request.user
        journal = value.journal

        # Check journal ownership (unless admin)
        if user.role != 'admin' and journal.owner != user:
            raise serializers.ValidationError(
                'You do not have permission to create decisions for this journal contact.'
            )

        return value

    def create(self, validated_data):
        """
        Create decision with atomic transaction and handle duplicate constraint.
        """
        try:
            with transaction.atomic():
                decision = Decision.objects.create(**validated_data)
                return decision
        except IntegrityError as e:
            if 'unique' in str(e).lower():
                raise serializers.ValidationError(
                    'A decision already exists for this contact in this journal.'
                )
            raise

    def update(self, instance, validated_data):
        """
        Update decision with atomic history tracking.
        Before updating, create DecisionHistory record with old values.
        """
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        with transaction.atomic():
            # Build changed_fields dict
            changed_fields = {}
            for field in ['amount', 'cadence', 'status']:
                if field in validated_data:
                    old_value = getattr(instance, field)
                    new_value = validated_data[field]

                    # Compare values (convert Decimal to string for comparison)
                    if old_value != new_value:
                        # Convert Decimal to string for JSON serialization
                        if isinstance(old_value, Decimal):
                            changed_fields[field] = str(old_value)
                        else:
                            changed_fields[field] = old_value

            # Create history record if changes exist
            if changed_fields:
                DecisionHistory.objects.create(
                    decision=instance,
                    changed_fields=changed_fields,
                    changed_by=user
                )

            # Update instance fields
            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()

            return instance


class DecisionHistorySerializer(serializers.ModelSerializer):
    """
    Read-only serializer for decision history records.
    """
    changed_by_email = serializers.EmailField(
        source='changed_by.email',
        read_only=True,
        default=None
    )

    class Meta:
        model = DecisionHistory
        fields = ['id', 'decision', 'changed_fields', 'changed_by', 'changed_by_email', 'created_at']
        read_only_fields = ['id', 'decision', 'changed_fields', 'changed_by', 'changed_by_email', 'created_at']
