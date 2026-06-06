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


# Admin Analytics Redesign (Issue #49)


class FiscalYearPaceResponseSerializer(serializers.Serializer):
    fy_start = serializers.CharField()
    fy_end = serializers.CharField()
    raised_cents = serializers.IntegerField()
    annual_goal_cents = serializers.IntegerField()
    annual_goal_source = serializers.ChoiceField(choices=["org_setting", "missionary_sum"])
    expected_by_today_cents = serializers.IntegerField()
    pace_percentage = serializers.FloatField()
    prior_year_raised_cents = serializers.IntegerField()
    yoy_delta_percentage = serializers.FloatField(allow_null=True)
    last_import_at = serializers.CharField(allow_null=True)


class OrgSettingsSerializer(serializers.Serializer):
    annual_goal_cents = serializers.IntegerField(min_value=0)


class MissionaryBehindGoalItemSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.CharField()
    monthly_goal_cents = serializers.IntegerField()
    this_month_raised_cents = serializers.IntegerField()
    pace_percentage = serializers.FloatField()


class MissionariesBehindGoalResponseSerializer(serializers.Serializer):
    missionaries = MissionaryBehindGoalItemSerializer(many=True)
    total_excluded_no_goal = serializers.IntegerField()
    total_missionaries = serializers.IntegerField()
    as_of_date = serializers.CharField()


class PipelineFunnelConversionStageSerializer(serializers.Serializer):
    stage = serializers.CharField()
    label = serializers.CharField()
    count_at_or_past = serializers.IntegerField()
    conversion_from_prior_percentage = serializers.FloatField(allow_null=True)
    is_weakest_transition = serializers.BooleanField()


class PipelineFunnelConversionResponseSerializer(serializers.Serializer):
    stages = PipelineFunnelConversionStageSerializer(many=True)
    total_in_pipeline = serializers.IntegerField()
    weakest_transition = serializers.DictField(allow_null=True)


class WeeklyEngagementPointSerializer(serializers.Serializer):
    week_start = serializers.CharField()
    week_label = serializers.CharField()
    active_missionaries = serializers.IntegerField()
    on_pace_missionaries = serializers.IntegerField()
    total_missionaries = serializers.IntegerField()


class WeeklyEngagementResponseSerializer(serializers.Serializer):
    weeks = WeeklyEngagementPointSerializer(many=True)


class FiscalYearDonationMonthSerializer(serializers.Serializer):
    month = serializers.CharField()
    short_label = serializers.CharField()
    current_cents = serializers.IntegerField(allow_null=True)
    prior_cents = serializers.IntegerField()
    is_future = serializers.BooleanField()


class FiscalYearDonationsResponseSerializer(serializers.Serializer):
    fy_start = serializers.CharField()
    fy_end = serializers.CharField()
    months = FiscalYearDonationMonthSerializer(many=True)
    current_fy_total_cents = serializers.IntegerField()
    prior_fy_total_cents = serializers.IntegerField()
