"""Regression test for the 2026-06-22 re-scan finding #7.

The contact "thank" action is a workflow write. A coach has read visibility of
a coached missionary's contact, but must not be able to mutate its thank-you
state (CWE-862). The owning missionary still can.

Each test fails if the IsStaffOrAbove gate is reverted (project rule #1).
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact

User = get_user_model()


@pytest.fixture
def thank_setup(db):
    missionary = User.objects.create_user(
        email="m-thank@example.com",
        password="pw",
        first_name="Mara",
        last_name="M",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-thank@example.com",
        password="pw",
        first_name="Cole",
        last_name="C",
        role="coach",
    )
    coach.coached_users.add(missionary)
    contact = Contact.objects.create(
        owner=missionary,
        first_name="Dana",
        last_name="Donor",
        status="donor",
        needs_thank_you=True,
    )
    return {"missionary": missionary, "coach": coach, "contact": contact}


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestContactThankAuthorization:
    def test_coach_cannot_thank_coached_contact(self, thank_setup):
        s = thank_setup
        resp = _client(s["coach"]).post(f"/api/v1/contacts/{s['contact'].id}/thank/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        s["contact"].refresh_from_db()
        # State untouched — still needs a thank-you.
        assert s["contact"].needs_thank_you is True

    def test_owner_can_thank_own_contact(self, thank_setup):
        s = thank_setup
        resp = _client(s["missionary"]).post(f"/api/v1/contacts/{s['contact'].id}/thank/")
        assert resp.status_code == status.HTTP_200_OK
        s["contact"].refresh_from_db()
        assert s["contact"].needs_thank_you is False
