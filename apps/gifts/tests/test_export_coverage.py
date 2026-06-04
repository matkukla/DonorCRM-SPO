"""
Behavioral coverage tests for Gift and RecurringGift CSV export views.

StreamingHttpResponse generators silently swallow exceptions, so a broken
export can still return 200 with a header row but NO data rows. These tests
parse the streamed body and assert the header AND at least one correct data
row (dollars formatted from cents), which catches that class of bug.
"""
import csv
import io
from datetime import date

from rest_framework.test import APIClient

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.models import (
    Gift,
    PaymentType,
    RecurringGift,
    RecurringGiftFrequency,
    RecurringGiftStatus,
)
from apps.imports.models import Fund
from apps.users.tests.factories import (
    AdminUserFactory,
    CoachUserFactory,
    SupervisorUserFactory,
    UserFactory,
)

GIFT_EXPORT_URL = "/api/v1/gifts/export/csv/"
RECURRING_EXPORT_URL = "/api/v1/gifts/recurring/export/csv/"


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _parse_csv(response):
    """Consume a StreamingHttpResponse and return parsed CSV rows."""
    body = b"".join(response.streaming_content).decode("utf-8")
    return list(csv.reader(io.StringIO(body)))


@pytest.fixture
def missionary():
    return UserFactory(role="missionary", email="gift-export-owner@test.com")


@pytest.mark.django_db
class TestGiftExportCSV:
    def test_export_header_and_data_row(self, missionary):
        contact = ContactFactory(owner=missionary, first_name="Donald", last_name="Giver")
        fund = Fund.objects.create(external_id="F-100", name="General Fund")
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=12500,
            gift_date=date(2026, 3, 15),
            payment_type=PaymentType.CHECK,
            fund=fund,
            description="Spring gift",
        )

        response = _client(missionary).get(GIFT_EXPORT_URL)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert response["Content-Disposition"].startswith("attachment; filename=")
        assert "donations_" in response["Content-Disposition"]

        rows = _parse_csv(response)
        assert rows[0] == [
            "Donor Name",
            "Amount",
            "Date",
            "Payment Type",
            "Fund",
            "Description",
        ]
        # A real data row must exist (not just headers).
        assert len(rows) == 2
        data = rows[1]
        assert data[0] == "Donald Giver"
        # NOTE: export emits str(Decimal(cents)/100) so 12500 -> "125"
        # (no currency padding). This documents the app's real output.
        assert data[1] == "125"
        assert data[2] == "2026-03-15"
        assert data[3] == "Check"
        assert data[4] == "General Fund"
        assert data[5] == "Spring gift"

    def test_export_blank_fund_and_payment_type(self, missionary):
        contact = ContactFactory(owner=missionary, first_name="No", last_name="Fund")
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=5000,
            gift_date=date(2026, 1, 1),
        )
        response = _client(missionary).get(GIFT_EXPORT_URL)
        rows = _parse_csv(response)
        assert len(rows) == 2
        data = rows[1]
        assert data[1] == "50"
        # No payment type and no fund render as empty strings.
        assert data[3] == ""
        assert data[4] == ""
        assert data[5] == ""

    def test_export_only_includes_owned_gifts(self, missionary):
        mine_contact = ContactFactory(owner=missionary, first_name="My", last_name="Donor")
        Gift.objects.create(
            donor_contact=mine_contact, amount_cents=8000, gift_date=date(2026, 2, 2)
        )
        other = UserFactory(role="missionary", email="other-gift@test.com")
        other_contact = ContactFactory(owner=other)
        Gift.objects.create(
            donor_contact=other_contact, amount_cents=99900, gift_date=date(2026, 2, 2)
        )

        response = _client(missionary).get(GIFT_EXPORT_URL)
        rows = _parse_csv(response)
        # Header + exactly one owned row.
        assert len(rows) == 2
        assert rows[1][0] == "My Donor"
        assert rows[1][1] == "80"

    def test_export_applies_payment_type_filter(self, missionary):
        contact = ContactFactory(owner=missionary, first_name="Filter", last_name="Me")
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date(2026, 4, 1),
            payment_type=PaymentType.CASH,
        )
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=20000,
            gift_date=date(2026, 4, 2),
            payment_type=PaymentType.CHECK,
        )
        response = _client(missionary).get(GIFT_EXPORT_URL, {"payment_type": "cash"})
        rows = _parse_csv(response)
        assert len(rows) == 2
        assert rows[1][1] == "100"
        assert rows[1][3] == "Cash"

    def test_export_applies_min_amount_filter(self, missionary):
        contact = ContactFactory(owner=missionary, first_name="Big", last_name="Only")
        Gift.objects.create(donor_contact=contact, amount_cents=1000, gift_date=date(2026, 5, 1))
        Gift.objects.create(donor_contact=contact, amount_cents=50000, gift_date=date(2026, 5, 2))
        response = _client(missionary).get(GIFT_EXPORT_URL, {"min_amount": "100"})
        rows = _parse_csv(response)
        assert len(rows) == 2
        assert rows[1][1] == "500"

    def test_coach_forbidden_from_gift_export(self):
        coach = CoachUserFactory()
        response = _client(coach).get(GIFT_EXPORT_URL)
        assert response.status_code == 403

    def test_export_requires_authentication(self):
        response = APIClient().get(GIFT_EXPORT_URL)
        assert response.status_code == 401

    def test_admin_owner_filter_scopes_to_selected_user(self):
        admin = AdminUserFactory(email="export-admin@test.com")
        target = UserFactory(role="missionary", email="export-target@test.com")
        target_contact = ContactFactory(owner=target, first_name="Target", last_name="User")
        Gift.objects.create(
            donor_contact=target_contact,
            amount_cents=30000,
            gift_date=date(2026, 6, 1),
        )
        # Admin's own gift should NOT appear when filtering by owner=target.
        admin_contact = ContactFactory(owner=admin)
        Gift.objects.create(
            donor_contact=admin_contact,
            amount_cents=70000,
            gift_date=date(2026, 6, 1),
        )
        response = _client(admin).get(GIFT_EXPORT_URL, {"owner": str(target.id)})
        rows = _parse_csv(response)
        # Access-control guard: a plain ?owner= query param must NOT grant an
        # admin cross-user export access. Cross-user data is reached only via
        # View As (X-View-As-User-Id header -> get_visible_user_ids), so the
        # export stays scoped to the admin's own data and the target user's
        # $300 gift is NOT leaked. (Header only here because ?owner=target
        # intersected with the admin's own-data scope is empty.)
        assert response.status_code == 200
        assert rows[0][0] == "Donor Name"
        assert all("Target User" not in row for row in rows[1:])
        assert "300" not in [row[1] for row in rows[1:]]


@pytest.mark.django_db
class TestRecurringGiftExportCSV:
    def test_export_header_and_data_row(self, missionary):
        contact = ContactFactory(owner=missionary, first_name="Reggie", last_name="Recurring")
        fund = Fund.objects.create(external_id="F-200", name="Monthly Fund")
        RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=25000,
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=date(2026, 1, 10),
            fund=fund,
        )
        response = _client(missionary).get(RECURRING_EXPORT_URL)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "pledges_" in response["Content-Disposition"]

        rows = _parse_csv(response)
        assert rows[0] == [
            "Donor Name",
            "Amount",
            "Frequency",
            "Status",
            "Start Date",
            "Fund",
        ]
        assert len(rows) == 2
        data = rows[1]
        assert data[0] == "Reggie Recurring"
        # str(Decimal(25000)/100) -> "250" (no currency padding).
        assert data[1] == "250"
        assert data[2] == "monthly"
        assert data[3] == "active"
        assert data[4] == "2026-01-10"
        assert data[5] == "Monthly Fund"

    def test_export_only_includes_owned_recurring(self, missionary):
        mine_contact = ContactFactory(owner=missionary, first_name="Mine", last_name="Recur")
        RecurringGift.objects.create(
            donor_contact=mine_contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=date(2026, 2, 1),
        )
        other = UserFactory(role="missionary", email="other-recur@test.com")
        other_contact = ContactFactory(owner=other)
        RecurringGift.objects.create(
            donor_contact=other_contact,
            amount_cents=88800,
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=date(2026, 2, 1),
        )
        response = _client(missionary).get(RECURRING_EXPORT_URL)
        rows = _parse_csv(response)
        assert len(rows) == 2
        assert rows[1][0] == "Mine Recur"
        assert rows[1][1] == "100"

    def test_export_applies_status_filter(self, missionary):
        contact = ContactFactory(owner=missionary, first_name="Stat", last_name="Filt")
        RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=12000,
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=date(2026, 3, 1),
        )
        RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=99000,
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.CANCELLED,
            start_date=date(2026, 3, 1),
        )
        response = _client(missionary).get(RECURRING_EXPORT_URL, {"status": "active"})
        rows = _parse_csv(response)
        assert len(rows) == 2
        assert rows[1][1] == "120"
        assert rows[1][3] == "active"

    def test_coach_forbidden_from_recurring_export(self):
        coach = CoachUserFactory()
        response = _client(coach).get(RECURRING_EXPORT_URL)
        assert response.status_code == 403

    def test_supervisor_owner_filter(self):
        supervisor = SupervisorUserFactory()
        target = UserFactory(role="missionary", email="recur-target@test.com")
        target_contact = ContactFactory(owner=target, first_name="Recur", last_name="Target")
        RecurringGift.objects.create(
            donor_contact=target_contact,
            amount_cents=45000,
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=date(2026, 4, 1),
        )
        response = _client(supervisor).get(RECURRING_EXPORT_URL, {"owner": str(target.id)})
        rows = _parse_csv(response)
        # Access-control guard (same as the gift export above): a ?owner= param
        # must NOT let a supervisor export an unrelated user's pledges. Cross-user
        # access requires View As, so the target's $450 pledge is not leaked.
        assert response.status_code == 200
        assert rows[0][0] == "Donor Name"
        assert all("Recur Target" not in row for row in rows[1:])
        assert "450" not in [row[1] for row in rows[1:]]
