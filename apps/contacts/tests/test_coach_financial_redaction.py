"""Coach financial-field redaction on contacts — security report #3/#4.

Coaches may see coached missionaries' non-financial contact data but must not
receive donor giving totals/amounts (CWE-200):
  - #3: total_given / gift_count etc. stripped from list/detail/export.
  - #4: gift and pledge subresources denied (403).

Missionaries (financial role) still see everything (no over-gating). Each test
fails if its guard is reverted (project rule #1).
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import Gift

User = get_user_model()

GIFT_CENTS = 654321  # distinctive amount that must never reach a coach


@pytest.fixture
def coach_contact_setup(db):
    missionary = User.objects.create_user(
        email="m-fin@example.com",
        password="pw",
        first_name="Mara",
        last_name="M",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-fin@example.com", password="pw", first_name="Cole", last_name="C", role="coach"
    )
    coach.coached_users.add(missionary)
    contact = Contact.objects.create(
        owner=missionary,
        first_name="Dana",
        last_name="Donor",
        email="dana@example.com",
        status="donor",
    )
    Gift.objects.create(donor_contact=contact, amount_cents=GIFT_CENTS, gift_date=date.today())
    contact.refresh_from_db()
    return {"missionary": missionary, "coach": coach, "contact": contact}


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestCoachContactFinancialRedaction:
    def test_coach_list_omits_financial_fields(self, coach_contact_setup):
        resp = _client(coach_contact_setup["coach"]).get("/api/v1/contacts/")
        assert resp.status_code == status.HTTP_200_OK
        rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        target = next(r for r in rows if r["id"] == str(coach_contact_setup["contact"].id))
        assert "total_given" not in target
        assert "gift_count" not in target

    def test_coach_detail_access_denied(self, coach_contact_setup):
        # Contact detail is owner/admin-only (IsContactOwnerOrReadAccess), so a
        # coach cannot read a coached contact's detail at all — stronger than
        # field redaction. (Serializer redaction remains as defense-in-depth.)
        cid = coach_contact_setup["contact"].id
        resp = _client(coach_contact_setup["coach"]).get(f"/api/v1/contacts/{cid}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_coach_donations_subresource_denied(self, coach_contact_setup):
        cid = coach_contact_setup["contact"].id
        resp = _client(coach_contact_setup["coach"]).get(f"/api/v1/contacts/{cid}/donations/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_coach_pledges_subresource_denied(self, coach_contact_setup):
        cid = coach_contact_setup["contact"].id
        resp = _client(coach_contact_setup["coach"]).get(f"/api/v1/contacts/{cid}/pledges/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_coach_export_omits_financial_columns(self, coach_contact_setup):
        resp = _client(coach_contact_setup["coach"]).get("/api/v1/contacts/export/csv/")
        assert resp.status_code == status.HTTP_200_OK
        body = b"".join(resp.streaming_content).decode()
        assert "Total Given" not in body
        assert "6543" not in body  # the gift amount must not appear


@pytest.mark.django_db
class TestMissionaryNotOverGated:
    def test_missionary_detail_includes_financial_fields(self, coach_contact_setup):
        cid = coach_contact_setup["contact"].id
        resp = _client(coach_contact_setup["missionary"]).get(f"/api/v1/contacts/{cid}/")
        assert resp.status_code == status.HTTP_200_OK
        assert "total_given" in resp.data
        assert resp.data["gift_count"] == 1

    def test_missionary_donations_subresource_allowed(self, coach_contact_setup):
        cid = coach_contact_setup["contact"].id
        resp = _client(coach_contact_setup["missionary"]).get(f"/api/v1/contacts/{cid}/donations/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_missionary_export_includes_financial_columns(self, coach_contact_setup):
        resp = _client(coach_contact_setup["missionary"]).get("/api/v1/contacts/export/csv/")
        assert resp.status_code == status.HTTP_200_OK
        body = b"".join(resp.streaming_content).decode()
        assert "Total Given" in body
