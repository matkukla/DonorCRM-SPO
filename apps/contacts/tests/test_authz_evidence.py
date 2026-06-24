"""Authorization evidence tests for pilot review.

Three boundaries a customer security reviewer asks us to prove, that had no
negative test:

1. Supervisor default list isolation — a supervisor's bare /contacts/ list
   (no View-As header) must NOT include a non-assigned missionary's records.
2. Cross-user search leak — searching another owner's contact name returns
   nothing (scoping is applied before the search filter).
3. Coach financial-field redaction matrix — every financial field present in
   the contact list serializer is stripped for a coach, and present for a
   missionary (no over-gating).
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.contacts.serializers import FINANCIAL_CONTACT_FIELDS
from apps.gifts.models import Gift

User = get_user_model()


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestSupervisorDefaultListIsolation:
    def test_supervisor_bare_list_excludes_non_assigned_missionary(self, db):
        supervisor = User.objects.create_user(
            email="sup-iso@example.com", password="pw", role="supervisor"
        )
        non_assigned = User.objects.create_user(
            email="na-iso@example.com", password="pw", role="missionary"
        )
        # non_assigned is NOT in supervisor.supervised_users.
        Contact.objects.create(owner=non_assigned, first_name="Nadia", last_name="NonAssigned")

        resp = _client(supervisor).get("/api/v1/contacts/")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        assert all(r["last_name"] != "NonAssigned" for r in results)
        assert "Nadia" not in str(resp.data)


@pytest.mark.django_db
class TestCrossUserSearchLeak:
    def test_search_does_not_leak_foreign_contact(self, db):
        attacker = User.objects.create_user(
            email="atk-srch@example.com", password="pw", role="missionary"
        )
        victim = User.objects.create_user(
            email="vic-srch@example.com", password="pw", role="missionary"
        )
        Contact.objects.create(owner=victim, first_name="Zenobia", last_name="Foreign")

        resp = _client(attacker).get("/api/v1/contacts/search/?q=Zenobia")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        assert results == []
        assert "Zenobia" not in str(resp.data)


@pytest.mark.django_db
class TestCoachFinancialFieldMatrix:
    """Every financial field the list serializer can emit is stripped for a coach."""

    @pytest.fixture
    def coach_list_setup(self, db):
        missionary = User.objects.create_user(
            email="m-mtx@example.com", password="pw", role="missionary"
        )
        coach = User.objects.create_user(email="c-mtx@example.com", password="pw", role="coach")
        coach.coached_users.add(missionary)
        contact = Contact.objects.create(
            owner=missionary, first_name="Fin", last_name="Matrix", status="donor"
        )
        Gift.objects.create(donor_contact=contact, amount_cents=424242, gift_date=date.today())
        contact.refresh_from_db()
        return {"missionary": missionary, "coach": coach, "contact": contact}

    def _row(self, resp, contact_id):
        rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        return next(r for r in rows if r["id"] == str(contact_id))

    def test_coach_list_strips_all_financial_fields(self, coach_list_setup):
        resp = _client(coach_list_setup["coach"]).get("/api/v1/contacts/")
        assert resp.status_code == status.HTTP_200_OK
        row = self._row(resp, coach_list_setup["contact"].id)
        # Assert the full intersection of FINANCIAL_CONTACT_FIELDS with whatever
        # the list serializer emits is absent — a regression re-adding any one
        # (e.g. last_gift_date) fails here.
        leaked = [f for f in FINANCIAL_CONTACT_FIELDS if f in row]
        assert leaked == [], f"coach saw financial fields: {leaked}"
        assert "4242" not in str(resp.data)

    def test_missionary_list_keeps_financial_fields(self, coach_list_setup):
        resp = _client(coach_list_setup["missionary"]).get("/api/v1/contacts/")
        assert resp.status_code == status.HTTP_200_OK
        row = self._row(resp, coach_list_setup["contact"].id)
        # No over-gating: the financial fields the list serializer defines are present.
        assert "total_given" in row
        assert "gift_count" in row
