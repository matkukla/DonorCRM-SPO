"""
Serializers for Contact model.
"""

from rest_framework import serializers

from apps.contacts.models import Contact
from apps.groups.serializers import GroupSerializer
from apps.journals.models import JournalContact, PipelineStage


class ContactListSerializer(serializers.ModelSerializer):
    """
    Serializer for contact list view (minimal fields).
    """

    full_name = serializers.CharField(read_only=True)
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)

    class Meta:
        model = Contact
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "organization_name",
            "email",
            "phone",
            "status",
            "total_given",
            "gift_count",
            "last_gift_date",
            "needs_thank_you",
            "owner",
            "owner_name",
        ]


class ContactDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for contact detail view (all fields).
    """

    full_name = serializers.CharField(read_only=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    full_address = serializers.CharField(read_only=True)
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    has_active_pledge = serializers.BooleanField(read_only=True)
    monthly_pledge_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    groups = GroupSerializer(many=True, read_only=True)
    group_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        model = Contact
        fields = [
            "id",
            "owner",
            "owner_name",
            "first_name",
            "last_name",
            "full_name",
            "organization_name",
            "email",
            "phone",
            "phone_secondary",
            "street_address",
            "city",
            "state",
            "postal_code",
            "country",
            "full_address",
            "status",
            "first_gift_date",
            "last_gift_date",
            "last_gift_amount",
            "total_given",
            "gift_count",
            "has_active_pledge",
            "monthly_pledge_amount",
            "last_thanked_at",
            "needs_thank_you",
            "notes",
            "external_id",
            "external_constituent_id",
            "groups",
            "group_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner",
            "first_gift_date",
            "last_gift_date",
            "last_gift_amount",
            "total_given",
            "gift_count",
            "external_id",
            "external_constituent_id",
            "created_at",
            "updated_at",
        ]

    def _visible_groups(self, group_ids):
        """Restrict group_ids to groups the requesting user can write to.

        Scope to owned groups plus shared (owner=None) groups. Respects
        View As by threading the request through get_visible_user_ids().
        """
        from django.db.models import Q

        from apps.core.permissions import get_visible_user_ids
        from apps.groups.models import Group

        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return Group.objects.none()

        visible = get_visible_user_ids(request.user, request=request)
        return Group.objects.filter(id__in=group_ids).filter(
            Q(owner_id__in=visible) | Q(owner__isnull=True)
        )

    def create(self, validated_data):
        group_ids = validated_data.pop("group_ids", [])
        contact = super().create(validated_data)
        if group_ids:
            contact.groups.set(self._visible_groups(group_ids))
        return contact

    def update(self, instance, validated_data):
        group_ids = validated_data.pop("group_ids", None)
        contact = super().update(instance, validated_data)
        if group_ids is not None:
            contact.groups.set(self._visible_groups(group_ids))
        return contact


class ContactCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating contacts.
    """

    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    group_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        model = Contact
        fields = [
            "id",
            "first_name",
            "last_name",
            "organization_name",
            "email",
            "phone",
            "phone_secondary",
            "street_address",
            "city",
            "state",
            "postal_code",
            "country",
            "status",
            "notes",
            "group_ids",
            "total_given",
            "gift_count",
            "needs_thank_you",
        ]
        read_only_fields = ["id", "total_given", "gift_count", "needs_thank_you"]

    def create(self, validated_data):
        group_ids = validated_data.pop("group_ids", [])

        # Set owner to current user
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["owner"] = request.user

        contact = Contact.objects.create(**validated_data)

        if group_ids:
            from django.db.models import Q

            from apps.core.permissions import get_visible_user_ids
            from apps.groups.models import Group

            if request and request.user.is_authenticated:
                visible = get_visible_user_ids(request.user, request=request)
                groups = Group.objects.filter(id__in=group_ids).filter(
                    Q(owner_id__in=visible) | Q(owner__isnull=True)
                )
                contact.groups.set(groups)

        return contact


class DuplicateCheckSerializer(serializers.Serializer):
    """Input for pre-creation duplicate check."""

    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")


class DuplicateMatchSerializer(serializers.Serializer):
    """Single duplicate match result."""

    id = serializers.UUIDField(source="contact.id")
    first_name = serializers.CharField(source="contact.first_name")
    last_name = serializers.CharField(source="contact.last_name")
    full_name = serializers.CharField(source="contact.full_name")
    email = serializers.EmailField(source="contact.email", allow_blank=True)
    phone = serializers.CharField(source="contact.phone", allow_blank=True)
    organization_name = serializers.CharField(source="contact.organization_name", allow_blank=True)
    status = serializers.CharField(source="contact.status")
    confidence = serializers.CharField()
    reasons = serializers.ListField(child=serializers.CharField())
    similarity = serializers.FloatField()


class MergeRequestSerializer(serializers.Serializer):
    """Input for merge operation."""

    survivor_id = serializers.UUIDField()
    loser_id = serializers.UUIDField()


class DismissRequestSerializer(serializers.Serializer):
    """Input for dismissing a duplicate pair."""

    contact_a_id = serializers.UUIDField()
    contact_b_id = serializers.UUIDField()


class ContactJournalMembershipSerializer(serializers.ModelSerializer):
    """Serializer for contact's journal memberships (for Journals tab)."""

    journal_id = serializers.UUIDField(source="journal.id", read_only=True)
    journal_name = serializers.CharField(source="journal.name", read_only=True)
    goal_amount = serializers.DecimalField(
        source="journal.goal_amount", max_digits=10, decimal_places=2, read_only=True
    )
    deadline = serializers.DateField(source="journal.deadline", read_only=True)

    # Current stage - computed from most recent event
    current_stage = serializers.SerializerMethodField()

    # Decision summary
    decision = serializers.SerializerMethodField()

    class Meta:
        model = JournalContact
        fields = [
            "id",
            "journal_id",
            "journal_name",
            "goal_amount",
            "deadline",
            "current_stage",
            "decision",
            "created_at",
        ]
        read_only_fields = fields

    def get_current_stage(self, obj):
        """Get most recent stage from prefetched events."""
        # Events are prefetched and ordered by -created_at
        events = getattr(obj, "prefetched_events", None)
        if events:
            return events[0].stage if events else PipelineStage.CONTACT
        # Fallback if not prefetched
        latest = obj.stage_events.order_by("-created_at").first()
        return latest.stage if latest else PipelineStage.CONTACT

    def get_decision(self, obj):
        """Get decision summary from prefetched decision."""
        decisions = getattr(obj, "prefetched_decisions", None)
        if decisions:
            decision = decisions[0] if decisions else None
        else:
            decision = obj.decisions.first()

        if not decision:
            return None

        summary = {
            "id": str(decision.id),
            "cadence": decision.cadence,
            "status": decision.status,
        }
        # Pledge amount is gated from non-financial roles (coach); pipeline
        # status + cadence remain visible (PRD fix #1).
        from apps.core.permissions import is_financial_role

        request = self.context.get("request")
        if request and is_financial_role(request.user):
            summary["amount"] = str(decision.amount)
        return summary
