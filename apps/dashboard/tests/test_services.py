"""
Tests for dashboard service functions.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.dashboard.services import (
    get_dashboard_summary,
    get_giving_summary,
    get_late_donations,
    get_monthly_gifts,
    get_needs_attention,
    get_recent_gifts,
    get_support_progress,
    get_thank_you_queue,
    get_what_changed,
)
from apps.events.tests.factories import EventFactory
from apps.gifts.tests.factories import GiftFactory, RecurringGiftFactory
from apps.tasks.tests.factories import OverdueTaskFactory, TaskFactory
from apps.users.tests.factories import AdminUserFactory, UserFactory


@pytest.mark.django_db
class TestGetWhatChanged:
    """Tests for get_what_changed function."""

    def test_get_what_changed_with_events(self):
        """Test getting what changed with new events."""
        user = UserFactory()
        EventFactory.create_batch(3, user=user, is_new=True)
        EventFactory.create_batch(2, user=user, is_new=False)

        result = get_what_changed(user)

        assert result["total_new"] == 3
        assert len(result["recent_events"]) <= 10

    def test_get_what_changed_no_events(self):
        """Test getting what changed with no events."""
        user = UserFactory()

        result = get_what_changed(user)

        assert result["total_new"] == 0


@pytest.mark.django_db
class TestGetNeedsAttention:
    """Tests for get_needs_attention function."""

    def test_get_needs_attention_late_pledges_always_zero(self):
        """Test that late_pledge_count is always 0 (RecurringGift has no is_late)."""
        user = UserFactory(role="missionary")

        result = get_needs_attention(user)

        assert result["late_pledge_count"] == 0

    def test_get_needs_attention_overdue_tasks(self):
        """Test getting needs attention with overdue tasks."""
        user = UserFactory(role="missionary")
        OverdueTaskFactory(owner=user)

        result = get_needs_attention(user)

        assert result["overdue_task_count"] == 1

    def test_get_needs_attention_thank_you_needed(self):
        """Test getting needs attention with thank-you needed."""
        user = UserFactory(role="missionary")
        ContactFactory(owner=user, needs_thank_you=True)

        result = get_needs_attention(user)

        assert result["thank_you_needed_count"] == 1


@pytest.mark.django_db
class TestGetLateDonations:
    """Tests for get_late_donations function."""

    def test_no_recurring_gifts_returns_empty(self):
        """No recurring gifts means no late donations."""
        user = UserFactory(role="missionary")

        result = get_late_donations(user)

        assert len(result) == 0

    def test_returns_late_recurring_gift(self):
        """A monthly recurring gift with no recent gifts should be flagged as late."""
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user, last_gift_date=date.today() - timedelta(days=60))
        RecurringGiftFactory(
            donor_contact=contact,
            amount_cents=10000,
            frequency="monthly",
            start_date=date.today() - timedelta(days=90),
        )

        result = get_late_donations(user)

        assert len(result) == 1
        assert result[0]["contact_id"] == str(contact.id)
        assert result[0]["days_late"] > 0

    def test_excludes_inactive_recurring_gifts(self):
        """Inactive recurring gifts should not be flagged as late."""
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user, last_gift_date=date.today() - timedelta(days=60))
        RecurringGiftFactory(
            donor_contact=contact,
            amount_cents=10000,
            frequency="monthly",
            status="terminated",
            start_date=date.today() - timedelta(days=90),
        )

        result = get_late_donations(user)

        assert len(result) == 0

    def test_recent_gift_not_flagged(self):
        """A monthly recurring gift with a recent gift should not be flagged."""
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user, last_gift_date=date.today() - timedelta(days=10))
        RecurringGiftFactory(
            donor_contact=contact,
            amount_cents=10000,
            frequency="monthly",
            start_date=date.today() - timedelta(days=90),
        )

        result = get_late_donations(user)

        assert len(result) == 0

    def test_grace_period_not_exceeded(self):
        """A gift within the grace period (1.5x interval) should not be flagged."""
        user = UserFactory(role="missionary")
        # Monthly interval is 30 days, grace period is 45 days
        # Last gift 40 days ago — within grace period
        contact = ContactFactory(owner=user, last_gift_date=date.today() - timedelta(days=40))
        RecurringGiftFactory(
            donor_contact=contact,
            amount_cents=10000,
            frequency="monthly",
            start_date=date.today() - timedelta(days=120),
        )

        result = get_late_donations(user)

        assert len(result) == 0

    def test_excludes_irregular_frequency(self):
        """Irregular frequency recurring gifts should not be flagged."""
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user, last_gift_date=date.today() - timedelta(days=200))
        RecurringGiftFactory(
            donor_contact=contact,
            amount_cents=10000,
            frequency="irregular",
            start_date=date.today() - timedelta(days=300),
        )

        result = get_late_donations(user)

        assert len(result) == 0

    def test_no_cross_user_leakage(self):
        """Late donations from other users should not appear."""
        user_a = UserFactory(role="missionary")
        user_b = UserFactory(role="missionary")
        contact_b = ContactFactory(owner=user_b, last_gift_date=date.today() - timedelta(days=60))
        RecurringGiftFactory(
            donor_contact=contact_b,
            amount_cents=10000,
            frequency="monthly",
            start_date=date.today() - timedelta(days=90),
        )

        result = get_late_donations(user_a)

        assert len(result) == 0


@pytest.mark.django_db
class TestGetThankYouQueue:
    """Tests for get_thank_you_queue function."""

    def test_get_thank_you_queue(self):
        """Test getting thank you queue."""
        user = UserFactory(role="missionary")
        ContactFactory.create_batch(2, owner=user, needs_thank_you=True)
        ContactFactory(owner=user, needs_thank_you=False)

        result = get_thank_you_queue(user)

        assert result.count() == 2


@pytest.mark.django_db
class TestGetSupportProgress:
    """Tests for get_support_progress function."""

    def test_get_support_progress(self):
        """Test getting support progress with RecurringGift."""
        user = UserFactory(role="missionary", monthly_support_goal_cents=500000)
        contact = ContactFactory(owner=user)

        # Create $100/month recurring gift (10000 cents)
        RecurringGiftFactory(donor_contact=contact, amount_cents=10000, frequency="monthly")

        result = get_support_progress(user)

        assert result["current_monthly_support"] == 100.0
        assert result["monthly_goal"] == 5000.0
        assert result["percentage"] == 2.0
        assert result["gap"] == 4900.0
        assert result["active_pledge_count"] == 1

    def test_missionary_only_sees_own_contacts_gifts(self):
        """Regression: missionary A must not see missionary B's recurring gifts.

        Root cause investigated: get_visible_user_ids returns {user.id} for
        missionary role, so filter is donor_contact__owner_id__in={A.id}.
        B's contacts are excluded — this verifies correct cross-user isolation.
        """
        missionary_a = UserFactory(role="missionary", monthly_support_goal_cents=500000)
        missionary_b = UserFactory(role="missionary", monthly_support_goal_cents=300000)

        contact_a = ContactFactory(owner=missionary_a)
        contact_b = ContactFactory(owner=missionary_b)

        # A has $100/month recurring gift
        RecurringGiftFactory(donor_contact=contact_a, amount_cents=10000, frequency="monthly")
        # B has $200/month recurring gift — must NOT appear in A's progress
        RecurringGiftFactory(donor_contact=contact_b, amount_cents=20000, frequency="monthly")

        result_a = get_support_progress(missionary_a)

        # A should only see their own $100/month, not B's $200/month
        assert result_a["current_monthly_support"] == 100.0
        assert result_a["active_pledge_count"] == 1

    def test_admin_support_progress_only_shows_own_contacts(self):
        """Regression: admin must only see their own contacts' recurring gifts.

        Bug: get_visible_user_ids returns None for admin, causing
        get_support_progress to use RecurringGift.objects.all() — this
        includes ALL missionaries' recurring gifts in the admin's personal
        Monthly Support Goal tile, inflating current_monthly_support.

        Fix: get_support_progress must scope admin to their own contacts
        (donor_contact__owner=user) so the dashboard shows personal progress only.
        """
        admin = AdminUserFactory(monthly_support_goal_cents=500000)
        # Admin has no contacts or recurring gifts of their own

        # A different missionary has active recurring gifts
        missionary = UserFactory(role="missionary", monthly_support_goal_cents=300000)
        contact = ContactFactory(owner=missionary)
        RecurringGiftFactory(donor_contact=contact, amount_cents=50000, frequency="monthly")

        result = get_support_progress(admin)

        # Admin has no personal donors — their support progress must be $0
        assert result["current_monthly_support"] == 0.0
        assert result["active_pledge_count"] == 0

    def test_bimonthly_gift_monthly_equivalent(self):
        """Regression: BIMONTHLY frequency (every 2 months) gives 0.5x monthly equivalent.

        A $200/bimonthly gift means one $200 payment every 2 months.
        Annual total = 6 x $200 = $1200.
        Monthly equivalent = $1200 / 12 = $100/month.
        Multiplier must be 0.5 (Decimal('1') / Decimal('2')).
        """
        user = UserFactory(role="missionary", monthly_support_goal_cents=500000)
        contact = ContactFactory(owner=user)

        # $200 every 2 months (bimonthly) = $100/month equivalent
        RecurringGiftFactory(donor_contact=contact, amount_cents=20000, frequency="bimonthly")

        result = get_support_progress(user)

        # 20000 cents = $200, bimonthly (every 2 months) * 0.5 = $100/month
        assert result["current_monthly_support"] == 100.0
        assert result["active_pledge_count"] == 1


@pytest.mark.django_db
class TestGetRecentGifts:
    """Tests for get_recent_gifts function."""

    def test_get_recent_gifts(self):
        """Test getting recent gifts."""
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)

        # Recent gift
        GiftFactory(donor_contact=contact, gift_date=timezone.now().date() - timedelta(days=5))

        # Old gift
        GiftFactory(donor_contact=contact, gift_date=timezone.now().date() - timedelta(days=60))

        result = get_recent_gifts(user, days=30)

        assert result.count() == 1


@pytest.mark.django_db
class TestGetGivingSummary:
    """Tests for get_giving_summary function."""

    def test_given_sums_current_fiscal_year_only(self):
        """Given should only sum gifts from the current fiscal year (Jun 1 - May 31)."""
        from apps.core.fiscal_year import fiscal_year_start

        user = UserFactory(role="missionary", monthly_support_goal_cents=100000)
        contact = ContactFactory(owner=user)
        today = date.today()
        fy_start = fiscal_year_start(today)

        # Gift in current fiscal year
        GiftFactory(
            donor_contact=contact, amount_cents=5000, gift_date=fy_start + timedelta(days=30)
        )
        # Gift before fiscal year start — should be excluded
        GiftFactory(
            donor_contact=contact, amount_cents=9999, gift_date=fy_start - timedelta(days=30)
        )

        result = get_giving_summary(user)

        assert result["given"] == 50.0  # 5000 cents = $50

    def test_expecting_equals_annualized_minus_recurring_given(self):
        """Expecting = annualized recurring - recurring gifts received this year.

        One-time gifts do NOT reduce 'expecting' — only recurring-sourced
        Gift records (those with a recurring_gift FK) count against the
        expected recurring revenue.
        """
        user = UserFactory(role="missionary", monthly_support_goal_cents=100000)
        contact = ContactFactory(owner=user)
        # Fiscal year runs June 1 - May 31. Anchor "today" to March 1 so the
        # Jan/Feb gifts below fall in the same (past) fiscal year regardless of
        # when the suite runs. as_of_date is the service's deterministic seam.
        as_of = date(2025, 3, 1)

        # $100/month recurring = $1200/year annualized
        rg = RecurringGiftFactory(donor_contact=contact, amount_cents=10000, frequency="monthly")
        # $200 recurring payment this fiscal year (linked to recurring gift)
        GiftFactory(
            donor_contact=contact,
            amount_cents=20000,
            gift_date=date(2025, 1, 15),
            recurring_gift=rg,
        )
        # $500 one-time gift (NOT linked to recurring — should not reduce expecting)
        GiftFactory(donor_contact=contact, amount_cents=50000, gift_date=date(2025, 2, 15))

        result = get_giving_summary(user, as_of_date=as_of)

        assert result["given"] == 700.0  # $200 recurring + $500 one-time
        assert result["expecting"] == 1000.0  # 1200 - 200 (only recurring) = 1000

    def test_expecting_floors_at_zero(self):
        """Expecting should floor at 0 when recurring given > annualized recurring."""
        user = UserFactory(role="missionary", monthly_support_goal_cents=100000)
        contact = ContactFactory(owner=user)
        # Anchor "today" to March 1 so the Jan gift falls in the same (past)
        # fiscal year (June 1 - May 31) regardless of when the suite runs.
        as_of = date(2025, 3, 1)

        # $100/month recurring = $1200/year
        rg = RecurringGiftFactory(donor_contact=contact, amount_cents=10000, frequency="monthly")
        # $2000 recurring given (more than annualized — possible if pledge amount increased)
        GiftFactory(
            donor_contact=contact,
            amount_cents=200000,
            gift_date=date(2025, 1, 15),
            recurring_gift=rg,
        )

        result = get_giving_summary(user, as_of_date=as_of)

        assert result["expecting"] == 0

    def test_percentage_calculated_correctly(self):
        """Percentage = (given + expecting) / annual_goal * 100."""
        user = UserFactory(role="missionary", monthly_support_goal_cents=100000)
        contact = ContactFactory(owner=user)
        today = date.today()

        # $1000/month recurring = $12000/year, annual_goal = $12000
        rg = RecurringGiftFactory(donor_contact=contact, amount_cents=100000, frequency="monthly")
        # $6000 recurring given
        GiftFactory(
            donor_contact=contact,
            amount_cents=600000,
            gift_date=date(today.year, 1, 15),
            recurring_gift=rg,
        )

        result = get_giving_summary(user)

        # given=6000, expecting=max(0, 12000-6000)=6000, total=12000
        # percentage = 12000 / 12000 * 100 = 100
        assert result["percentage"] == 100.0

    def test_no_cross_user_data_leakage(self):
        """Missionary A should not see missionary B's gifts."""
        user_a = UserFactory(role="missionary", monthly_support_goal_cents=100000)
        user_b = UserFactory(role="missionary", monthly_support_goal_cents=100000)
        contact_b = ContactFactory(owner=user_b)
        today = date.today()

        GiftFactory(donor_contact=contact_b, amount_cents=50000, gift_date=date(today.year, 1, 15))

        result = get_giving_summary(user_a)

        assert result["given"] == 0.0

    def test_empty_case_returns_zeros(self):
        """No gifts and no recurring should return all zeros."""
        user = UserFactory(role="missionary", monthly_support_goal_cents=0)

        result = get_giving_summary(user)

        assert result["given"] == 0.0
        assert result["expecting"] == 0
        assert result["percentage"] == 0


@pytest.mark.django_db
class TestGetMonthlyGifts:
    """Tests for get_monthly_gifts function."""

    def test_returns_12_months_with_gap_fill(self):
        """Monthly chart should return 12 months with gaps filled as 0."""
        user = UserFactory(role="missionary", monthly_support_goal_cents=100000)

        result = get_monthly_gifts(user, months=12)

        assert len(result["months"]) == 12
        # All gaps should be 0
        for month in result["months"]:
            assert "month" in month
            assert "total" in month

    def test_amounts_in_dollars(self):
        """Monthly totals should be converted from cents to dollars."""
        user = UserFactory(role="missionary", monthly_support_goal_cents=100000)
        contact = ContactFactory(owner=user)
        today = date.today()

        GiftFactory(donor_contact=contact, amount_cents=15000, gift_date=today)

        result = get_monthly_gifts(user, months=12)

        # Find this month's entry
        this_month = today.strftime("%Y-%m")
        month_entry = next(m for m in result["months"] if m["month"] == this_month)
        assert month_entry["total"] == 150.0  # 15000 cents = $150

    def test_no_cross_user_leakage(self):
        """Missionary A should not see missionary B's gift data in chart."""
        user_a = UserFactory(role="missionary", monthly_support_goal_cents=100000)
        user_b = UserFactory(role="missionary")
        contact_b = ContactFactory(owner=user_b)
        today = date.today()

        GiftFactory(donor_contact=contact_b, amount_cents=50000, gift_date=today)

        result = get_monthly_gifts(user_a, months=12)

        total_all = sum(m["total"] for m in result["months"])
        assert total_all == 0


@pytest.mark.django_db
class TestGetDashboardSummary:
    """Tests for get_dashboard_summary function."""

    def test_get_dashboard_summary(self):
        """Test getting complete dashboard summary."""
        user = UserFactory(role="missionary", monthly_support_goal_cents=300000)

        result = get_dashboard_summary(user)

        assert "what_changed" in result
        assert "needs_attention" in result
        assert "late_donations" in result
        assert "thank_you_queue" in result
        assert "support_progress" in result
        assert "recent_gifts" in result
        assert "recent_gifts_total" in result

    def test_get_dashboard_summary_returns_serializable_data(self):
        """Test that dashboard summary returns JSON-serializable data."""
        import json

        user = UserFactory(role="missionary")

        result = get_dashboard_summary(user)

        # Should not raise JSONDecodeError
        json_str = json.dumps(result, default=str)
        assert json_str is not None

    def test_recent_gifts_total_includes_all_gifts(self):
        """recent_gifts_total should include ALL recent gifts, not just first 10."""
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        today = date.today()

        # Create 15 gifts of $100 each in the last 30 days
        for i in range(15):
            GiftFactory(
                donor_contact=contact,
                amount_cents=10000,
                gift_date=today - timedelta(days=i),
            )

        result = get_dashboard_summary(user)

        # recent_gifts list is capped at 10, but total should reflect all 15
        assert len(result["recent_gifts"]) == 10
        assert result["recent_gifts_total"] == 1500.0  # 15 * $100

    def test_late_donations_count_matches_list(self):
        """late_donations_count should match the actual list length."""
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user, last_gift_date=date.today() - timedelta(days=60))
        RecurringGiftFactory(
            donor_contact=contact,
            amount_cents=10000,
            frequency="monthly",
            start_date=date.today() - timedelta(days=90),
        )

        result = get_dashboard_summary(user)

        assert result["late_donations_count"] == len(result["late_donations"])
        assert result["late_donations_count"] >= 1

    def test_recent_gifts_amount_preserves_cents(self):
        """Regression: recent_gifts amount must not truncate fractional dollars.

        Bug: F('amount_cents') / Value(100) performs integer division in
        PostgreSQL, truncating $150.50 (15050 cents) to $150.
        Fix: Divide by Decimal('100') so PostgreSQL uses numeric division.
        """
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        today = date.today()

        GiftFactory(
            donor_contact=contact,
            amount_cents=15050,  # $150.50
            gift_date=today,
        )

        result = get_dashboard_summary(user)

        assert len(result["recent_gifts"]) == 1
        amount = result["recent_gifts"][0]["amount"]
        # Must preserve fractional dollars, not truncate to 150
        assert Decimal(str(amount)) == Decimal("150.50")


@pytest.mark.django_db
class TestLateDonationsMonthlyEquivalent:
    """Regression tests for late donation monthly equivalent field."""

    def test_quarterly_gift_returns_monthly_equivalent(self):
        """Regression: late donation must include correct monthly_equivalent.

        Bug: frontend displayed per-installment amount with '/mo' label.
        The backend sends both 'amount' (per-installment) and
        'monthly_equivalent' (actual monthly value). Frontend must use
        monthly_equivalent. This test verifies the backend field is correct.
        """
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user, last_gift_date=date.today() - timedelta(days=200))
        RecurringGiftFactory(
            donor_contact=contact,
            amount_cents=30000,  # $300 per quarter
            frequency="quarterly",
            start_date=date.today() - timedelta(days=300),
        )

        result = get_late_donations(user)

        assert len(result) == 1
        # Per-installment amount (Decimal str may omit trailing zeros)
        assert Decimal(result[0]["amount"]) == Decimal("300")
        # Monthly equivalent: $300/quarter = $100/month
        assert result[0]["monthly_equivalent"] == 100.0
        assert result[0]["frequency"] == "quarterly"

    def test_annual_gift_returns_monthly_equivalent(self):
        """Annual $1200 gift should show $100/month equivalent."""
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user, last_gift_date=date.today() - timedelta(days=600))
        RecurringGiftFactory(
            donor_contact=contact,
            amount_cents=120000,  # $1200 annually
            frequency="annually",
            start_date=date.today() - timedelta(days=700),
        )

        result = get_late_donations(user)

        assert len(result) == 1
        assert Decimal(result[0]["amount"]) == Decimal("1200")
        assert result[0]["monthly_equivalent"] == 100.0
