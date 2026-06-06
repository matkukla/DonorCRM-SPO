"""
Behavioral coverage tests for apps/insights/services.py.

These exercise service functions that are reachable but previously untested:
  - get_donations_by_month / get_donations_by_year (monetary sums in dollars)
  - get_follow_ups (incomplete-task ledger, overdue flagging)
  - get_transactions (admin gift ledger with filters + pagination)
  - get_single_user_performance (single-row variant + None on miss)
  - get_pace_calculation (avg days between stage transitions)
  - _parse_date_range malformed-input branches (ValidationError -> 400)
  - date-filter branches in get_team_trends / get_conversion_funnel

Time is pinned mid-fiscal-year so gifts/events dated near boundaries stay in
the past, matching the convention in test_admin_analytics_services.py.
"""

from datetime import date, timedelta

from django.utils import timezone

from rest_framework.exceptions import ValidationError

import pytest
from freezegun import freeze_time

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import (
    AnnualRecurringGiftFactory,
    CancelledRecurringGiftFactory,
    GiftFactory,
    QuarterlyRecurringGiftFactory,
    RecurringGiftFactory,
)
from apps.insights.services import (
    _parse_date_range,
    get_conversion_funnel,
    get_donations_by_month,
    get_donations_by_year,
    get_follow_ups,
    get_monthly_commitments,
    get_pace_calculation,
    get_single_user_performance,
    get_team_trends,
    get_transactions,
    get_user_trends,
)
from apps.journals.models import (
    Journal,
    JournalContact,
    JournalStageEvent,
    PipelineStage,
    StageEventType,
)
from apps.tasks.models import TaskPriority, TaskStatus, TaskType
from apps.tasks.tests.factories import TaskFactory
from apps.users.tests.factories import UserFactory


def _set_created_at(instance, when):
    """Force a TimeStampedModel created_at (bypasses auto_now_add via .update)."""
    type(instance).objects.filter(pk=instance.pk).update(created_at=when)


# --- _parse_date_range ---------------------------------------------------------


@pytest.mark.django_db
class TestParseDateRange:
    def test_valid_range_returns_aware_datetimes(self):
        dt_from, dt_to = _parse_date_range("2026-01-01", "2026-01-31")
        assert dt_from is not None and dt_to is not None
        assert timezone.is_aware(dt_from) and timezone.is_aware(dt_to)
        # date_to is exclusive: the function adds one day so the whole end day
        # is included by a `< dt_to` filter.
        assert dt_to.date() == date(2026, 2, 1)

    def test_none_inputs_return_none(self):
        assert _parse_date_range(None, None) == (None, None)

    def test_malformed_date_from_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            _parse_date_range(date_from="not-a-date")
        assert "date_from" in exc.value.detail

    def test_malformed_date_to_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc:
            _parse_date_range(date_to="13/40/2026")
        assert "date_to" in exc.value.detail


# --- get_donations_by_month ----------------------------------------------------


@pytest.mark.django_db
class TestDonationsByMonth:
    def test_empty_year_returns_twelve_zero_months(self):
        user = UserFactory(role="missionary")
        result = get_donations_by_month(user, year=2026)
        assert len(result["months"]) == 12
        assert result["year"] == 2026
        assert result["year_total"] == 0
        assert result["donation_count"] == 0
        assert all(m["total"] == 0 and m["count"] == 0 for m in result["months"])
        # Labels are formatted, not raw
        assert result["months"][0]["month"] == "2026-01"
        assert result["months"][0]["short_label"] == "Jan"

    def test_sums_gifts_into_correct_month_in_dollars(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        # Two gifts in March 2026 totalling $300.00, one in July 2026 ($50.00)
        GiftFactory(donor_contact=contact, amount_cents=25000, gift_date=date(2026, 3, 5))
        GiftFactory(donor_contact=contact, amount_cents=5000, gift_date=date(2026, 3, 20))
        GiftFactory(donor_contact=contact, amount_cents=5000, gift_date=date(2026, 7, 1))
        # Gift in a different year must be excluded
        GiftFactory(donor_contact=contact, amount_cents=99999, gift_date=date(2025, 3, 5))

        result = get_donations_by_month(user, year=2026)
        by_month = {m["month"]: m for m in result["months"]}
        assert by_month["2026-03"]["total"] == 300.0  # dollars, not cents
        assert by_month["2026-03"]["count"] == 2
        assert by_month["2026-07"]["total"] == 50.0
        assert result["year_total"] == 350.0
        assert result["donation_count"] == 3

    @freeze_time("2026-10-15")
    def test_defaults_to_current_year_when_year_none(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        GiftFactory(donor_contact=contact, amount_cents=10000, gift_date=date(2026, 6, 1))
        result = get_donations_by_month(user)
        assert result["year"] == 2026
        assert result["year_total"] == 100.0

    def test_owner_scoping_excludes_other_users_gifts(self):
        user = UserFactory(role="missionary")
        other = UserFactory(role="missionary")
        GiftFactory(
            donor_contact=ContactFactory(owner=other),
            amount_cents=80000,
            gift_date=date(2026, 4, 1),
        )
        result = get_donations_by_month(user, year=2026)
        assert result["year_total"] == 0


# --- get_donations_by_year -----------------------------------------------------


@pytest.mark.django_db
class TestDonationsByYear:
    @freeze_time("2026-10-15")
    def test_returns_n_years_with_grand_total_in_dollars(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        GiftFactory(donor_contact=contact, amount_cents=20000, gift_date=date(2026, 1, 10))
        GiftFactory(donor_contact=contact, amount_cents=30000, gift_date=date(2024, 6, 10))
        result = get_donations_by_year(user, years=5)
        years = {y["year"]: y for y in result["years"]}
        assert set(years) == {2022, 2023, 2024, 2025, 2026}
        assert years[2026]["total"] == 200.0
        assert years[2026]["count"] == 1
        assert years[2024]["total"] == 300.0
        assert result["grand_total"] == 500.0
        assert result["total_donations"] == 2

    @freeze_time("2026-10-15")
    def test_gift_older_than_window_excluded(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        # years=2 -> window is 2025, 2026. A 2023 gift must not be counted.
        GiftFactory(donor_contact=contact, amount_cents=70000, gift_date=date(2023, 5, 1))
        result = get_donations_by_year(user, years=2)
        assert [y["year"] for y in result["years"]] == [2025, 2026]
        assert result["grand_total"] == 0


# --- get_follow_ups ------------------------------------------------------------


@pytest.mark.django_db
class TestFollowUps:
    @freeze_time("2026-10-15")
    def test_flags_overdue_and_counts(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        today = date(2026, 10, 15)
        # Overdue pending task
        overdue = TaskFactory(
            owner=user,
            contact=contact,
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            task_type=TaskType.CALL,
            due_date=today - timedelta(days=3),
        )
        # Future in-progress task (not overdue)
        TaskFactory(
            owner=user,
            contact=contact,
            status=TaskStatus.IN_PROGRESS,
            due_date=today + timedelta(days=5),
        )
        # Completed task must be excluded entirely
        TaskFactory(owner=user, contact=contact, status=TaskStatus.COMPLETED)

        result = get_follow_ups(user)
        ids = [t["id"] for t in result["tasks"]]
        assert str(overdue.id) in ids
        assert result["total_count"] == 2  # pending + in_progress only
        assert result["overdue_count"] == 1
        overdue_row = next(t for t in result["tasks"] if t["id"] == str(overdue.id))
        assert overdue_row["is_overdue"] is True
        assert overdue_row["contact_id"] == str(contact.id)
        assert overdue_row["contact_name"] == contact.full_name
        # Oldest due_date sorts first
        assert result["tasks"][0]["id"] == str(overdue.id)

    @freeze_time("2026-10-15")
    def test_task_without_contact_has_null_contact_fields(self):
        user = UserFactory(role="missionary")
        task = TaskFactory(
            owner=user,
            contact=None,
            status=TaskStatus.PENDING,
            due_date=date(2026, 10, 20),
        )
        result = get_follow_ups(user)
        row = next(t for t in result["tasks"] if t["id"] == str(task.id))
        assert row["contact_id"] is None
        assert row["contact_name"] is None
        assert row["is_overdue"] is False

    def test_limit_caps_returned_tasks_but_not_total(self):
        user = UserFactory(role="missionary")
        for _ in range(4):
            TaskFactory(owner=user, status=TaskStatus.PENDING)
        result = get_follow_ups(user, limit=2)
        assert len(result["tasks"]) == 2
        assert result["total_count"] == 4

    def test_owner_scoping_excludes_other_users_tasks(self):
        user = UserFactory(role="missionary")
        other = UserFactory(role="missionary")
        TaskFactory(owner=other, status=TaskStatus.PENDING)
        result = get_follow_ups(user)
        assert result["total_count"] == 0
        assert result["tasks"] == []


# --- get_transactions (admin ledger) ------------------------------------------


@pytest.mark.django_db
class TestTransactions:
    def test_returns_all_gifts_in_dollars(self):
        admin = UserFactory(role="admin")
        c1 = ContactFactory()
        c2 = ContactFactory()
        GiftFactory(donor_contact=c1, amount_cents=12345, gift_date=date(2026, 2, 1))
        GiftFactory(donor_contact=c2, amount_cents=67800, gift_date=date(2026, 3, 1))
        result = get_transactions(admin)
        assert result["total_count"] == 2
        amounts = sorted(t["amount"] for t in result["transactions"])
        assert amounts == [123.45, 678.0]
        # Newest gift_date first
        assert result["transactions"][0]["date"] == "2026-03-01"

    def test_contact_filter(self):
        admin = UserFactory(role="admin")
        c1 = ContactFactory()
        c2 = ContactFactory()
        GiftFactory(donor_contact=c1, amount_cents=10000, gift_date=date(2026, 2, 1))
        GiftFactory(donor_contact=c2, amount_cents=20000, gift_date=date(2026, 2, 2))
        result = get_transactions(admin, contact_id=str(c1.id))
        assert result["total_count"] == 1
        assert result["transactions"][0]["contact_id"] == str(c1.id)

    def test_date_range_filter(self):
        admin = UserFactory(role="admin")
        contact = ContactFactory()
        GiftFactory(donor_contact=contact, amount_cents=10000, gift_date=date(2026, 1, 1))
        GiftFactory(donor_contact=contact, amount_cents=10000, gift_date=date(2026, 6, 1))
        GiftFactory(donor_contact=contact, amount_cents=10000, gift_date=date(2026, 12, 1))
        result = get_transactions(admin, date_from=date(2026, 5, 1), date_to=date(2026, 7, 1))
        assert result["total_count"] == 1
        assert result["transactions"][0]["date"] == "2026-06-01"

    def test_pagination_offset_and_limit(self):
        admin = UserFactory(role="admin")
        contact = ContactFactory()
        for day in range(1, 6):
            GiftFactory(
                donor_contact=contact, amount_cents=1000 * day, gift_date=date(2026, 2, day)
            )
        result = get_transactions(admin, limit=2, offset=2)
        assert result["total_count"] == 5  # total ignores pagination
        assert len(result["transactions"]) == 2
        assert result["limit"] == 2
        assert result["offset"] == 2


# --- get_single_user_performance ----------------------------------------------


@pytest.mark.django_db
class TestSingleUserPerformance:
    def test_returns_serialized_row_for_missionary(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        GiftFactory(donor_contact=contact, amount_cents=45000, gift_date=date(2026, 2, 1))
        result = get_single_user_performance(user.id)
        assert result is not None
        assert result["id"] == str(user.id)
        assert result["email"] == user.email
        assert result["total_contacts"] == 1
        assert result["total_donations"] == 450.0
        assert result["donation_count"] == 1

    def test_returns_none_for_missing_user(self):
        import uuid

        assert get_single_user_performance(uuid.uuid4()) is None

    def test_returns_none_for_coach_role(self):
        coach = UserFactory(role="coach")
        # Coaches are not in the allowed role set, so the row is filtered out.
        assert get_single_user_performance(coach.id) is None


# --- get_pace_calculation ------------------------------------------------------


@pytest.mark.django_db
class TestPaceCalculation:
    def _journal_contact(self):
        owner = UserFactory(role="missionary")
        journal = Journal.objects.create(owner=owner, name="J", goal_amount=1000)
        contact = ContactFactory(owner=owner)
        return JournalContact.objects.create(journal=journal, contact=contact)

    def _stage_event(self, jc, when):
        event = JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.CONTACT,
            event_type=StageEventType.NOTE_ADDED,
        )
        _set_created_at(event, when)
        return event

    def test_no_events_returns_none(self):
        result = get_pace_calculation()
        assert result["average_days_between_stages"] is None
        assert result["total_intervals"] == 0

    def test_averages_intervals_between_consecutive_events(self):
        jc = self._journal_contact()
        base = timezone.make_aware(timezone.datetime(2026, 1, 1, 12, 0))
        # 3 events for same contact: gaps of 4 and 10 days -> avg 7.0
        self._stage_event(jc, base)
        self._stage_event(jc, base + timedelta(days=4))
        self._stage_event(jc, base + timedelta(days=14))

        result = get_pace_calculation()
        assert result["total_intervals"] == 2
        assert result["average_days_between_stages"] == 7.0

    def test_intervals_not_crossing_contact_boundary(self):
        jc1 = self._journal_contact()
        jc2 = self._journal_contact()
        base = timezone.make_aware(timezone.datetime(2026, 1, 1, 12, 0))
        # Each contact has a single 2-day interval; no cross-contact interval.
        self._stage_event(jc1, base)
        self._stage_event(jc1, base + timedelta(days=2))
        self._stage_event(jc2, base + timedelta(days=100))
        self._stage_event(jc2, base + timedelta(days=102))

        result = get_pace_calculation()
        assert result["total_intervals"] == 2
        assert result["average_days_between_stages"] == 2.0

    def test_date_range_filter_excludes_events(self):
        jc = self._journal_contact()
        base = timezone.make_aware(timezone.datetime(2026, 1, 1, 12, 0))
        self._stage_event(jc, base)
        self._stage_event(jc, base + timedelta(days=5))
        # Restrict to a window that contains only the first event -> no interval.
        result = get_pace_calculation(date_from="2025-12-31", date_to="2026-01-02")
        assert result["total_intervals"] == 0
        assert result["average_days_between_stages"] is None


# --- date-filter branches in other aggregations --------------------------------


@pytest.mark.django_db
class TestDateFilterBranches:
    def test_team_trends_with_explicit_range(self):
        # Exercises the dt_from and dt_to branch of get_team_trends.
        result = get_team_trends(date_from="2026-01-01", date_to="2026-02-28")
        # Range spans ~8.5 weeks -> weeks recomputed from the range, not default 12.
        assert result["weeks"] == len(result["trends"])
        assert result["weeks"] >= 8
        # First bucket aligned to a Monday on/before the range start.
        first = date.fromisoformat(result["trends"][0]["week_start"])
        assert first.weekday() == 0

    def test_conversion_funnel_with_date_range_runs(self):
        # Exercises the dt_from/dt_to filtering branch of get_conversion_funnel.
        result = get_conversion_funnel(date_from="2026-01-01", date_to="2026-12-31")
        assert result["total_contacts_in_pipeline"] == 0
        assert "funnel" in result

    def test_user_trends_buckets_recent_activity_by_week(self):
        # Exercises get_user_trends including the per-row normalize_to_date path.
        user = UserFactory(role="missionary")
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        contact = ContactFactory(owner=user)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        # A stage event "now" lands in the current (last) week bucket.
        JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.CONTACT,
            event_type=StageEventType.NOTE_ADDED,
        )
        # A gift today contributes to donations_received for the current week.
        GiftFactory(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=timezone.now().date(),
        )

        result = get_user_trends(user_id=user.id, weeks=4)
        assert result["weeks"] == 4
        assert len(result["trends"]) == 4
        current_week = result["trends"][-1]
        assert current_week["stage_progressions"] >= 1
        assert current_week["donations_received"] >= 1

    def test_user_trends_other_users_excluded(self):
        user = UserFactory(role="missionary")
        other = UserFactory(role="missionary")
        journal = Journal.objects.create(owner=other, name="J", goal_amount=1000)
        contact = ContactFactory(owner=other)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.CONTACT,
            event_type=StageEventType.NOTE_ADDED,
        )
        result = get_user_trends(user_id=user.id, weeks=4)
        # No activity belongs to `user`, so every week is zero.
        assert all(w["stage_progressions"] == 0 for w in result["trends"])


# --- get_monthly_commitments frequency mix (covers monthly_equivalent paths) ---


@pytest.mark.django_db
class TestMonthlyCommitmentsCoverage:
    def test_mixes_frequencies_and_reports_last_fulfilled(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        # Monthly $100 -> $100/mo; Quarterly $300 -> $100/mo; Annual $1200 -> $100/mo
        monthly = RecurringGiftFactory(donor_contact=contact, amount_cents=10000)
        QuarterlyRecurringGiftFactory(donor_contact=contact, amount_cents=30000)
        AnnualRecurringGiftFactory(donor_contact=contact, amount_cents=120000)
        # Cancelled pledge must be excluded from active totals.
        CancelledRecurringGiftFactory(donor_contact=contact, amount_cents=99999)
        # A paid gift linked to the monthly pledge sets last_fulfilled_date.
        GiftFactory(
            donor_contact=contact,
            recurring_gift=monthly,
            amount_cents=10000,
            gift_date=date(2026, 5, 1),
        )

        result = get_monthly_commitments(user)
        assert result["active_count"] == 3
        assert result["total_monthly"] == pytest.approx(300.0, rel=0.01)
        assert result["total_annual"] == pytest.approx(3600.0, rel=0.01)
        freqs = {row["frequency"] for row in result["by_frequency"]}
        assert {"monthly", "quarterly", "annually"} <= freqs
        monthly_row = next(p for p in result["pledges"] if p["id"] == str(monthly.id))
        assert monthly_row["last_fulfilled_date"] == "2026-05-01"
        # A pledge that never paid reports None.
        unpaid = next(p for p in result["pledges"] if p["frequency"] == "annually")
        assert unpaid["last_fulfilled_date"] is None
