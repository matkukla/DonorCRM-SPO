"""
DRF serializers for insights/analytics endpoints.
"""
from rest_framework import serializers


# Nested serializers

class DonationSummarySerializer(serializers.Serializer):
    total_amount = serializers.FloatField()
    total_count = serializers.IntegerField()


class StalledContactSerializer(serializers.Serializer):
    id = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.CharField(allow_null=True, allow_blank=True)
    owner_email = serializers.CharField()
    owner_name = serializers.CharField()
    last_activity_date = serializers.CharField(allow_null=True)
    days_stalled = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()


class UserPerformanceItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    email = serializers.CharField()
    name = serializers.CharField()
    role = serializers.CharField()
    total_contacts = serializers.IntegerField()
    active_journals = serializers.IntegerField()
    decisions_logged = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    total_donations = serializers.FloatField()
    donation_count = serializers.IntegerField()


class FunnelStageSerializer(serializers.Serializer):
    stage = serializers.CharField(allow_null=True)
    label = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class TeamActivityItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    user_id = serializers.CharField()
    user_email = serializers.CharField()
    user_name = serializers.CharField()
    event_type = serializers.CharField()
    title = serializers.CharField()
    message = serializers.CharField(allow_blank=True)
    severity = serializers.CharField()
    contact_id = serializers.CharField(allow_null=True)
    contact_name = serializers.CharField(allow_null=True)
    created_at = serializers.CharField()


# Response serializers for 5 admin analytics endpoints

class DashboardOverviewSerializer(serializers.Serializer):
    total_contacts = serializers.IntegerField()
    active_journals = serializers.IntegerField()
    stalled_contacts = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    donations_12m = DonationSummarySerializer()


class StalledContactsResponseSerializer(serializers.Serializer):
    stalled_contacts = StalledContactSerializer(many=True)
    total_count = serializers.IntegerField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()


class UserPerformanceResponseSerializer(serializers.Serializer):
    users = UserPerformanceItemSerializer(many=True)


class ConversionFunnelResponseSerializer(serializers.Serializer):
    funnel = FunnelStageSerializer(many=True)
    total_contacts_in_pipeline = serializers.IntegerField()
    no_activity_count = serializers.IntegerField(default=0)


class TeamActivityResponseSerializer(serializers.Serializer):
    activities = TeamActivityItemSerializer(many=True)
    total_count = serializers.IntegerField()


class TrendDataPointSerializer(serializers.Serializer):
    week_start = serializers.CharField()
    week_label = serializers.CharField()
    decisions_logged = serializers.IntegerField()
    donations_received = serializers.IntegerField()
    stage_progressions = serializers.IntegerField()


class TeamTrendsResponseSerializer(serializers.Serializer):
    trends = TrendDataPointSerializer(many=True)
    weeks = serializers.IntegerField()


# User Detail Serializers (Phase 17)

class UserTrendDataPointSerializer(serializers.Serializer):
    week_start = serializers.CharField()
    week_label = serializers.CharField()
    decisions_logged = serializers.IntegerField()
    donations_received = serializers.IntegerField()
    stage_progressions = serializers.IntegerField()


class UserTrendsResponseSerializer(serializers.Serializer):
    trends = UserTrendDataPointSerializer(many=True)
    weeks = serializers.IntegerField()


class UserJournalItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    member_count = serializers.IntegerField()
    decision_count = serializers.IntegerField()
    active_member_count = serializers.IntegerField()
    created_at = serializers.CharField()


class UserJournalsResponseSerializer(serializers.Serializer):
    journals = UserJournalItemSerializer(many=True)


# Stage Contacts Serializers (Phase 18)

class StageContactItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.CharField(allow_null=True, allow_blank=True)
    owner_name = serializers.CharField()
    last_activity_date = serializers.CharField(allow_null=True)


class StageContactsResponseSerializer(serializers.Serializer):
    contacts = StageContactItemSerializer(many=True)
    total_count = serializers.IntegerField()
    stage = serializers.CharField()


# User Drilldown Serializers (Phase 18)

class UserDrilldownUserSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.CharField()
    role = serializers.CharField()


class UserDrilldownStatsSerializer(serializers.Serializer):
    total_contacts = serializers.IntegerField()
    active_journals = serializers.IntegerField()
    decisions_logged = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    total_donations = serializers.FloatField()
    donation_count = serializers.IntegerField()
    stalled_contacts = serializers.IntegerField()


class UserDrilldownJournalSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    member_count = serializers.IntegerField()
    decision_count = serializers.IntegerField()
    active_member_count = serializers.IntegerField()
    created_at = serializers.CharField()


class UserDrilldownResponseSerializer(serializers.Serializer):
    user = UserDrilldownUserSerializer()
    stats = UserDrilldownStatsSerializer()
    journals = UserDrilldownJournalSerializer(many=True)
