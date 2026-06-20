"""Coach financial gating on the dashboard — PRD fix #2.

A coach (non-financial role) may view a coached missionary's dashboard (aggregate
tiles), but must NOT receive individual gift detail:
  - individual recent-gift rows and their total, and
  - last_gift_amount on the thank-you lists.

A missionary (financial role) still sees all of it (no over-gating). Each test fails
if its guard is reverted (project rule #1). The distinctive gift amount 7777.77 must
never appear in a coach response body.
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import Gift

User = get_user_model()

GIFT_CENTS = 777777  # $7,777.77 — distinctive, must be absent from any coach response


@pytest.fixture
def dash_setup(db):
    """Coach C coaches missionary M, who has one recent $7,777.77 gift."""
    missionary = User.objects.create_user(
        email="m-dash@example.com",
        password="pw",
        first_name="Mara",
        last_name="Missionary",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-dash@example.com",
        password="pw",
        first_name="Cole",
        last_name="Coach",
        role="coach",
    )
    coach.coached_users.add(missionary)

    contact = Contact.objects.create(
        owner=missionary,
        first_name="Dana",
        last_name="Donor",
        email="dana.dash@example.com",
        status="donor",
    )
    # Gift signal sets needs_thank_you=True and last_gift_amount on the contact.
    Gift.objects.create(donor_contact=contact, amount_cents=GIFT_CENTS, gift_date=date.today())
    contact.refresh_from_db()
    return {"missionary": missionary, "coach": coach, "contact": contact}


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestCoachDashboardGifts:
    def test_coach_dashboard_omits_recent_gift_rows_and_total(self, dash_setup):
        resp = _client(dash_setup["coach"]).get(
            f"/api/v1/dashboard/?user_id={dash_setup['missionary'].id}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["recent_gifts"] == []
        assert resp.data["recent_gifts_total"] in (None, 0, 0.0)
        assert "7777" not in str(resp.data)

    def test_coach_dashboard_strips_last_gift_amount(self, dash_setup):
        resp = _client(dash_setup["coach"]).get(
            f"/api/v1/dashboard/?user_id={dash_setup['missionary'].id}"
        )
        assert resp.status_code == status.HTTP_200_OK
        for entry in resp.data["thank_you_queue"]:
            assert "last_gift_amount" not in entry
        for entry in resp.data["needs_attention"]["thank_you_needed"]:
            assert "last_gift_amount" not in entry

    def test_coach_recent_gifts_endpoint_is_empty(self, dash_setup):
        resp = _client(dash_setup["coach"]).get(
            f"/api/v1/dashboard/recent-gifts/?user_id={dash_setup['missionary'].id}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["recent_gifts"] == []
        assert "7777" not in str(resp.data)

    def test_missionary_dashboard_includes_gift_detail(self, dash_setup):
        """Financial role still sees individual gift detail (no over-gating)."""
        resp = _client(dash_setup["missionary"]).get("/api/v1/dashboard/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["recent_gifts"]) == 1
        assert "7777" in str(resp.data)
        assert resp.data["thank_you_queue"][0]["last_gift_amount"] is not None

    def test_missionary_recent_gifts_endpoint_has_rows(self, dash_setup):
        resp = _client(dash_setup["missionary"]).get("/api/v1/dashboard/recent-gifts/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["recent_gifts"]) == 1

    def test_coach_what_changed_omits_donation_amount_event(self, dash_setup):
        """The donation-received event message carries the gift amount — withheld."""
        resp = _client(dash_setup["coach"]).get(
            f"/api/v1/dashboard/what-changed/?user_id={dash_setup['missionary'].id}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "7777" not in str(resp.data)

    def test_missionary_what_changed_includes_donation_event(self, dash_setup):
        resp = _client(dash_setup["missionary"]).get("/api/v1/dashboard/what-changed/")
        assert resp.status_code == status.HTTP_200_OK
        assert "7777" in str(resp.data)
