"""Regression test for the 2026-06-22 re-scan finding #8.

Prayer detail (update/delete) and mark-prayed are writes. A coach can read a
coached user's prayer intentions but must not mutate them (CWE-862). The owning
missionary still can, and the coach can still read.

Each test fails if the IsStaffOrAbove gate is reverted (project rule #1).
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.prayers.models import PrayerIntention

User = get_user_model()


@pytest.fixture
def prayer_setup(db):
    missionary = User.objects.create_user(
        email="m-pray@example.com",
        password="pw",
        first_name="Mara",
        last_name="M",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-pray@example.com",
        password="pw",
        first_name="Cole",
        last_name="C",
        role="coach",
    )
    coach.coached_users.add(missionary)
    contact = Contact.objects.create(
        owner=missionary, first_name="Dana", last_name="Donor", status="donor"
    )
    intention = PrayerIntention.objects.create(
        contact=contact, title="Original intention", status="active"
    )
    return {"missionary": missionary, "coach": coach, "intention": intention}


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestPrayerCoachWriteAuthorization:
    def test_coach_can_read_coached_prayer(self, prayer_setup):
        s = prayer_setup
        resp = _client(s["coach"]).get(f"/api/v1/prayers/{s['intention'].id}/")
        assert resp.status_code == status.HTTP_200_OK

    def test_coach_cannot_patch_coached_prayer(self, prayer_setup):
        s = prayer_setup
        resp = _client(s["coach"]).patch(
            f"/api/v1/prayers/{s['intention'].id}/", {"title": "Hijacked"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        s["intention"].refresh_from_db()
        assert s["intention"].title == "Original intention"

    def test_coach_cannot_mark_coached_prayer(self, prayer_setup):
        s = prayer_setup
        resp = _client(s["coach"]).post(f"/api/v1/prayers/{s['intention'].id}/prayed/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        s["intention"].refresh_from_db()
        assert s["intention"].last_prayed_at is None

    def test_owner_can_patch_own_prayer(self, prayer_setup):
        s = prayer_setup
        resp = _client(s["missionary"]).patch(
            f"/api/v1/prayers/{s['intention'].id}/", {"title": "Updated"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        s["intention"].refresh_from_db()
        assert s["intention"].title == "Updated"

    def test_owner_can_mark_own_prayer(self, prayer_setup):
        s = prayer_setup
        resp = _client(s["missionary"]).post(f"/api/v1/prayers/{s['intention'].id}/prayed/")
        assert resp.status_code == status.HTTP_200_OK
        s["intention"].refresh_from_db()
        assert s["intention"].last_prayed_at is not None
