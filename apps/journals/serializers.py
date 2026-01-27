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
    NextStep,
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


class StageEventSummarySerializer(serializers.Serializer):
    """
    Summary of events for a single stage cell in the grid.
    """
    has_events = serializers.BooleanField()
    event_count = serializers.IntegerField()
    last_event_date = serializers.DateTimeField(allow_null=True)
    last_event_type = serializers.CharField(allow_null=True)
    last_event_notes = serializers.CharField(allow_null=True)


class JournalContactSerializer(serializers.ModelSerializer):
    """
    Serializer for journal contact membership with ownership validation.
    Includes stage_events summary for grid display.
    """
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    contact_email = serializers.EmailField(source='contact.email', read_only=True)
    contact_status = serializers.CharField(source='contact.status', read_only=True)
    stage_events = serializers.SerializerMethodField()
    decision = serializers.SerializerMethodField()

    class Meta:
        model = JournalContact
        fields = [
            'id', 'journal', 'contact', 'contact_name',
            'contact_email', 'contact_status', 'stage_events',
            'decision', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_stage_events(self, obj):
        """
        Get stage event summaries grouped by stage for grid display.
        Returns a dict with stage names as keys and summary objects as values.
        """
        from django.db.models import Count, Max
        from apps.journals.models import PipelineStage

        # Get all events for this journal contact
        events = obj.stage_events.values('stage').annotate(
            event_count=Count('id'),
            last_event_date=Max('created_at')
        )

        # Build summary dict for all stages
        summaries = {}
        for stage in PipelineStage.values:
            summaries[stage] = {
                'has_events': False,
                'event_count': 0,
                'last_event_date': None,
                'last_event_type': None,
                'last_event_notes': None,
            }

        # Fill in summaries for stages that have events
        for event_data in events:
            stage = event_data['stage']
            # Get the most recent event for this stage
            last_event = obj.stage_events.filter(stage=stage).order_by('-created_at').first()
            if last_event:
                summaries[stage] = {
                    'has_events': True,
                    'event_count': event_data['event_count'],
                    'last_event_date': last_event.created_at.isoformat(),
                    'last_event_type': last_event.event_type,
                    'last_event_notes': last_event.notes[:100] if last_event.notes else None,
                }

        return summaries

    def get_decision(self, obj):
        """
        Get current decision summary for grid display.
        Returns the first (should be only) decision for this journal contact.
        """
        decision = obj.decisions.first()
        if decision:
            return {
                'id': str(decision.id),
                'amount': str(decision.amount),
                'cadence': decision.cadence,
                'status': decision.status,
                'monthly_equivalent': str(decision.monthly_equivalent),
            }
        return None

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

    Accepts either `journal_contact` (existing membership) or `contact_id`
    (auto-resolves/creates membership in the user's first active journal).
    """
    contact_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = JournalStageEvent
        fields = [
            'id', 'journal_contact', 'contact_id', 'stage', 'event_type',
            'notes', 'metadata', 'triggered_by', 'created_at'
        ]
        read_only_fields = ['id', 'triggered_by', 'created_at']
        extra_kwargs = {
            'journal_contact': {'required': False},
        }

    def validate(self, attrs):
        if not attrs.get('journal_contact') and not attrs.get('contact_id'):
            raise serializers.ValidationError(
                "Either journal_contact or contact_id is required."
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None

        contact_id = validated_data.pop('contact_id', None)

        if not validated_data.get('journal_contact') and contact_id:
            from apps.contacts.models import Contact

            contact = Contact.objects.get(id=contact_id)
            journal = Journal.objects.filter(
                owner=user, is_archived=False
            ).first()
            if not journal:
                # Auto-create a default journal for the user
                journal = Journal.objects.create(
                    owner=user,
                    name="My Journal",
                    goal_amount=Decimal('0.01'),
                )
            jc, _ = JournalContact.objects.get_or_create(
                journal=journal, contact=contact
            )
            validated_data['journal_contact'] = jc

        if user and user.is_authenticated:
            validated_data['triggered_by'] = user

        return JournalStageEvent.objects.create(**validated_data)


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


class NextStepSerializer(serializers.ModelSerializer):
    """Serializer for NextStep model with ownership validation."""

    class Meta:
        model = NextStep
        fields = [
            'id', 'journal_contact', 'title', 'notes',
            'due_date', 'completed', 'completed_at', 'order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'completed_at', 'created_at', 'updated_at']

    def validate_journal_contact(self, value):
        """Ensure user owns the journal that contains this contact."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            if user.role != 'admin' and value.journal.owner != user:
                raise serializers.ValidationError(
                    "You don't have permission to add next steps to this journal contact."
                )
        return value

    def update(self, instance, validated_data):
        """Handle completed timestamp when marking complete."""
        from django.utils import timezone

        if validated_data.get('completed') and not instance.completed:
            validated_data['completed_at'] = timezone.now()
        elif 'completed' in validated_data and not validated_data['completed']:
            validated_data['completed_at'] = None
        return super().update(instance, validated_data)
