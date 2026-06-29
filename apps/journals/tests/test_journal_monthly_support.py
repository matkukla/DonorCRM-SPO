"""Tests for issue #167: journal-tab goal measurement counts a one-time gift as
its monthly-equivalent (amount / 12), while recurring gifts count at their
monthly-equivalent (monthly = face value).

The journal tab must measure goal progress from *actual gifts* the same way the
Goal tab already does (apps.core.support_math.compute_monthly_support), scoped to
the journal's member contacts. The ÷12 for one-time gifts is applied only in this
measurement — the stored gift amount is never changed.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import Gift, RecurringGift, RecurringGiftFrequency, RecurringGiftStatus
from apps.journals.models import Journal, JournalContact
from apps.journals.services import get_journal_monthly_support

User = get_user_model()

# A reference date comfortably inside a fiscal year (FY runs Jun 1 - May 31).
# October 15, 2025 -> FY start Jun 1, 2025.
TODAY = date(2025, 10, 15)
FY_GIFT_DATE = date(2025, 8, 1)  # inside the same fiscal year


def _make_journal_with_contact(owner):
    journal = Journal.objects.create(owner=owner, name="MPD 2026", goal_amount=Decimal("1000.00"))
    contact = Contact.objects.create(
        owner=owner, first_name="Dana", last_name="Donor", status="donor"
    )
    JournalContact.objects.create(journal=journal, contact=contact)
    return journal, contact


@pytest.fixture
def missionary(db):
    return User.objects.create_user(
        email="m167@example.com",
        password="pw",
        first_name="Mona",
        last_name="M",
        role="missionary",
    )


@pytest.mark.django_db
class TestJournalMonthlySupportService:
    def test_one_time_gift_counts_as_amount_divided_by_12(self, missionary):
        journal, contact = _make_journal_with_contact(missionary)
        Gift.objects.create(
            donor_contact=contact, amount_cents=120000, gift_date=FY_GIFT_DATE
        )  # $1200 one-time

        result = get_journal_monthly_support(journal, today=TODAY)

        # $1200 / 12 = $100.00 monthly-equivalent
        assert result["one_time_monthly"] == 100.0
        assert result["recurring_monthly"] == 0.0
        assert result["effective_monthly_support"] == 100.0

    def test_recurring_monthly_gift_counts_at_face_value(self, missionary):
        journal, contact = _make_journal_with_contact(missionary)
        RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=20000,  # $200/month
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=FY_GIFT_DATE,
        )

        result = get_journal_monthly_support(journal, today=TODAY)

        # Monthly recurring is NOT divided — counts at face value.
        assert result["recurring_monthly"] == 200.0
        assert result["one_time_monthly"] == 0.0
        assert result["effective_monthly_support"] == 200.0

    def test_recurring_annual_gift_is_monthly_equivalent(self, missionary):
        journal, contact = _make_journal_with_contact(missionary)
        RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=120000,  # $1200/year
            frequency=RecurringGiftFrequency.ANNUALLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=FY_GIFT_DATE,
        )

        result = get_journal_monthly_support(journal, today=TODAY)

        # Annual recurring is already normalized: $1200 / 12 = $100/mo.
        assert result["recurring_monthly"] == 100.0
        assert result["effective_monthly_support"] == 100.0

    def test_mixed_gifts_sum_correctly(self, missionary):
        journal, contact = _make_journal_with_contact(missionary)
        Gift.objects.create(
            donor_contact=contact, amount_cents=120000, gift_date=FY_GIFT_DATE
        )  # $1200 one-time -> $100/mo
        RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=5000,  # $50/month
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=FY_GIFT_DATE,
        )

        result = get_journal_monthly_support(journal, today=TODAY)

        assert result["effective_monthly_support"] == 150.0

    def test_cents_rounding_is_consistent(self, missionary):
        """$100.00 / 12 = $8.3333... must round to the nearest cent ($8.33)."""
        journal, contact = _make_journal_with_contact(missionary)
        Gift.objects.create(
            donor_contact=contact, amount_cents=10000, gift_date=FY_GIFT_DATE
        )  # $100 one-time

        result = get_journal_monthly_support(journal, today=TODAY)

        assert result["one_time_monthly"] == 8.33

    def test_stored_gift_amount_is_unchanged(self, missionary):
        journal, contact = _make_journal_with_contact(missionary)
        gift = Gift.objects.create(
            donor_contact=contact, amount_cents=120000, gift_date=FY_GIFT_DATE
        )

        get_journal_monthly_support(journal, today=TODAY)

        gift.refresh_from_db()
        assert gift.amount_cents == 120000  # the real gift is untouched

    def test_only_this_journals_contacts_count(self, missionary):
        """Gifts from a contact NOT in the journal must not leak into measurement."""
        journal, contact = _make_journal_with_contact(missionary)
        outsider = Contact.objects.create(
            owner=missionary, first_name="Out", last_name="Sider", status="donor"
        )
        Gift.objects.create(donor_contact=outsider, amount_cents=120000, gift_date=FY_GIFT_DATE)

        result = get_journal_monthly_support(journal, today=TODAY)

        assert result["effective_monthly_support"] == 0.0


@pytest.mark.django_db
class TestJournalReportMonthlySupportEndpoint:
    """The journal-report endpoint exposes monthly_support, financial-gated."""

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_missionary_report_includes_monthly_support(self, missionary):
        journal, contact = _make_journal_with_contact(missionary)
        Gift.objects.create(donor_contact=contact, amount_cents=120000, gift_date=date.today())

        resp = self._client(missionary).get(
            f"/api/v1/journals/analytics/journal-report/?journal_id={journal.id}"
        )

        assert resp.status_code == status.HTTP_200_OK
        ms = resp.data["monthly_support"]
        assert ms is not None
        # $1200 one-time / 12 = $100/mo
        assert ms["effective_monthly_support"] == 100.0

    def test_coach_report_omits_monthly_support(self, missionary):
        coach = User.objects.create_user(
            email="c167@example.com",
            password="pw",
            first_name="Cory",
            last_name="C",
            role="coach",
        )
        coach.coached_users.add(missionary)
        journal, contact = _make_journal_with_contact(missionary)
        Gift.objects.create(donor_contact=contact, amount_cents=120000, gift_date=date.today())

        resp = self._client(coach).get(
            f"/api/v1/journals/analytics/journal-report/?journal_id={journal.id}"
        )

        assert resp.status_code == status.HTTP_200_OK
        # Financial figure withheld from non-financial role (CWE-200).
        assert resp.data["monthly_support"] is None
        assert "100.0" not in str(resp.data)
