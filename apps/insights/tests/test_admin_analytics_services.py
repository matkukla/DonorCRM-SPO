"""
Unit tests for admin analytics redesign service functions (Issue #49).

Covers:
  - get_fiscal_year_pace
  - get_missionaries_behind_goal
  - get_pipeline_funnel_with_conversion
  - get_weekly_engagement
  - get_fiscal_year_donations
"""
from calendar import monthrange
from datetime import date, timedelta
from unittest.mock import patch

from rest_framework.test import APIRequestFactory

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.core.fiscal_year import get_current_fiscal_year_bounds, get_prior_fiscal_year_bounds
from apps.gifts.tests.factories import GiftFactory
from apps.insights.admin_analytics_services import (
    get_fiscal_year_donations,
    get_fiscal_year_pace,
    get_missionaries_behind_goal,
    get_pipeline_funnel_with_conversion,
    get_weekly_engagement,
)
from apps.journals.models import (
    Journal,
    JournalContact,
    JournalStageEvent,
    PipelineStage,
    StageEventType,
)
from apps.users.tests.factories import AdminUserFactory, UserFactory


def _admin_request(admin_user=None):
    """Return a DRF request authenticated as an admin."""
    request = APIRequestFactory().get("/")
    request.user = admin_user or AdminUserFactory()
    return request


# --- get_fiscal_year_pace ------------------------------------------------------


@pytest.mark.django_db
class TestFiscalYearPace:
    def test_zero_state(self):
        request = _admin_request()
        result = get_fiscal_year_pace(request)
        assert result["raised_cents"] == 0
        assert result["annual_goal_cents"] == 0
        assert result["pace_percentage"] == 0.0
        assert result["yoy_delta_percentage"] is None

    def test_sums_current_fy_gifts(self):
        request = _admin_request()
        fy_start, _ = get_current_fiscal_year_bounds()
        # One missionary with a goal
        missionary = UserFactory(role="missionary", monthly_support_goal_cents=100_000)
        contact = ContactFactory(owner=missionary)
        # Gift in current FY
        GiftFactory(
            donor_contact=contact, amount_cents=50_000, gift_date=fy_start + timedelta(days=10)
        )
        # Gift before FY -> must not count
        GiftFactory(
            donor_contact=contact, amount_cents=99_999, gift_date=fy_start - timedelta(days=1)
        )

        result = get_fiscal_year_pace(request)
        assert result["raised_cents"] == 50_000
        assert result["annual_goal_cents"] == 100_000 * 12

    def test_yoy_delta_populated_when_prior_year_has_gifts(self):
        request = _admin_request()
        fy_start, _ = get_current_fiscal_year_bounds()
        prior_start, _ = get_prior_fiscal_year_bounds()
        missionary = UserFactory(role="missionary", monthly_support_goal_cents=100_000)
        contact = ContactFactory(owner=missionary)
        GiftFactory(
            donor_contact=contact, amount_cents=200_000, gift_date=fy_start + timedelta(days=1)
        )
        GiftFactory(
            donor_contact=contact, amount_cents=100_000, gift_date=prior_start + timedelta(days=1)
        )

        result = get_fiscal_year_pace(request)
        assert result["yoy_delta_percentage"] is not None
        # +100% growth expected
        assert result["yoy_delta_percentage"] == pytest.approx(100.0, rel=0.01)

    def test_excludes_users_with_zero_goal(self):
        request = _admin_request()
        UserFactory(role="missionary", monthly_support_goal_cents=0)
        UserFactory(role="missionary", monthly_support_goal_cents=50_000)
        result = get_fiscal_year_pace(request)
        assert result["annual_goal_cents"] == 50_000 * 12


# --- get_missionaries_behind_goal ----------------------------------------------


@pytest.mark.django_db
class TestMissionariesBehindGoal:
    def test_empty_state(self):
        request = _admin_request()
        result = get_missionaries_behind_goal(request)
        assert result["missionaries"] == []
        assert result["total_missionaries"] == 0
        assert result["total_excluded_no_goal"] == 0

    def test_excludes_zero_goal_missionaries(self):
        request = _admin_request()
        UserFactory(role="missionary", monthly_support_goal_cents=0)
        m2 = UserFactory(role="missionary", monthly_support_goal_cents=100_000)
        result = get_missionaries_behind_goal(request)
        assert len(result["missionaries"]) == 1
        assert result["missionaries"][0]["user_id"] == str(m2.id)
        assert result["total_excluded_no_goal"] == 1
        assert result["total_missionaries"] == 2

    def test_sorts_ascending_by_pace(self):
        request = _admin_request()
        today = date.today()
        month_start = today.replace(day=1)
        days_in_month = monthrange(today.year, today.month)[1]
        ratio = today.day / days_in_month

        # Missionary behind (0 raised)
        m_low = UserFactory(role="missionary", monthly_support_goal_cents=100_000)
        # Missionary on-pace: raised exactly expected amount
        m_high = UserFactory(role="missionary", monthly_support_goal_cents=100_000)
        contact = ContactFactory(owner=m_high)
        expected = int(100_000 * ratio)
        GiftFactory(donor_contact=contact, amount_cents=expected, gift_date=month_start)

        result = get_missionaries_behind_goal(request)
        assert [m["user_id"] for m in result["missionaries"]] == [str(m_low.id), str(m_high.id)]
        assert (
            result["missionaries"][0]["pace_percentage"]
            < result["missionaries"][1]["pace_percentage"]
        )

    def test_limit_respected(self):
        request = _admin_request()
        for _ in range(5):
            UserFactory(role="missionary", monthly_support_goal_cents=100_000)
        result = get_missionaries_behind_goal(request, limit=3)
        assert len(result["missionaries"]) == 3


# --- get_pipeline_funnel_with_conversion --------------------------------------


@pytest.mark.django_db
class TestPipelineFunnelWithConversion:
    def test_empty_pipeline(self):
        request = _admin_request()
        result = get_pipeline_funnel_with_conversion(request)
        assert result["total_in_pipeline"] == 0
        assert result["weakest_transition"] is None
        for stage in result["stages"]:
            assert stage["count_at_or_past"] == 0
            assert stage["is_weakest_transition"] is False

    def test_cumulative_reach_counts_and_weakest_flag(self):
        request = _admin_request()
        missionary = UserFactory(role="missionary")
        journal = Journal.objects.create(owner=missionary, name="J", goal_amount=1000)

        def _make_jc_with_max_stage(max_stage):
            contact = ContactFactory(owner=missionary)
            jc = JournalContact.objects.create(journal=journal, contact=contact)
            JournalStageEvent.objects.create(
                journal_contact=jc,
                stage=max_stage,
                event_type=StageEventType.NOTE_ADDED,
            )
            return jc

        # 10 journal contacts reached CONTACT
        for _ in range(10):
            _make_jc_with_max_stage(PipelineStage.CONTACT)
        # 5 reached SCHEDULED
        for _ in range(5):
            _make_jc_with_max_stage(PipelineStage.SCHEDULED)
        # 1 reached MEET
        for _ in range(1):
            _make_jc_with_max_stage(PipelineStage.MEET)

        result = get_pipeline_funnel_with_conversion(request)
        counts = {s["stage"]: s["count_at_or_past"] for s in result["stages"]}
        assert counts[PipelineStage.CONTACT.value] == 16
        assert counts[PipelineStage.SCHEDULED.value] == 6
        assert counts[PipelineStage.MEET.value] == 1
        assert counts[PipelineStage.CLOSE.value] == 0

        # weakest = MEET->CLOSE (0%)
        weakest = result["weakest_transition"]
        assert weakest is not None
        assert weakest["from"] == PipelineStage.MEET.value
        assert weakest["to"] == PipelineStage.CLOSE.value
        # Exactly one stage flagged
        flagged = [s for s in result["stages"] if s["is_weakest_transition"]]
        assert len(flagged) == 1


# --- get_weekly_engagement ----------------------------------------------------


@pytest.mark.django_db
class TestWeeklyEngagement:
    def test_returns_requested_number_of_weeks(self):
        request = _admin_request()
        result = get_weekly_engagement(request, weeks=12)
        assert len(result["weeks"]) == 12

    def test_counts_distinct_active_missionaries(self):
        request = _admin_request()
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        for m in (m1, m2):
            j = Journal.objects.create(owner=m, name="J", goal_amount=1000)
            c = ContactFactory(owner=m)
            jc = JournalContact.objects.create(journal=j, contact=c)
            JournalStageEvent.objects.create(
                journal_contact=jc,
                stage=PipelineStage.CONTACT,
                event_type=StageEventType.NOTE_ADDED,
            )
        result = get_weekly_engagement(request, weeks=2)
        # Current week should reflect 2 distinct missionaries.
        current_week = result["weeks"][-1]
        assert current_week["active_missionaries"] == 2


# --- get_fiscal_year_donations ------------------------------------------------


@pytest.mark.django_db
class TestFiscalYearDonations:
    def test_returns_twelve_months(self):
        request = _admin_request()
        result = get_fiscal_year_donations(request)
        assert len(result["months"]) == 12

    def test_future_months_marked_and_nulled(self):
        request = _admin_request()
        with patch("apps.insights.admin_analytics_services.date") as mock_date:
            # Force "today" to be Aug 15, 2025 (FY 2025-2026, month index 2 of FY)
            mock_date.today.return_value = date(2025, 8, 15)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = get_fiscal_year_donations(request)

        # Jul + Aug are non-future, Sep..Jun are future
        future_flags = [m["is_future"] for m in result["months"]]
        assert future_flags[:2] == [False, False]
        assert all(future_flags[2:])
        for m in result["months"]:
            if m["is_future"]:
                assert m["current_cents"] is None
            else:
                assert m["current_cents"] is not None

    def test_sums_current_and_prior_year_gifts(self):
        request = _admin_request()
        fy_start, _ = get_current_fiscal_year_bounds()
        prior_start, _ = get_prior_fiscal_year_bounds()
        missionary = UserFactory(role="missionary")
        contact = ContactFactory(owner=missionary)
        GiftFactory(
            donor_contact=contact, amount_cents=25_000, gift_date=fy_start + timedelta(days=5)
        )
        GiftFactory(
            donor_contact=contact, amount_cents=40_000, gift_date=prior_start + timedelta(days=5)
        )

        result = get_fiscal_year_donations(request)
        assert result["current_fy_total_cents"] == 25_000
        assert result["prior_fy_total_cents"] == 40_000
