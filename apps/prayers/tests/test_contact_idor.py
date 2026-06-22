"""Prayer intention contact IDOR — security report #9.

PrayerIntentionSerializer left the contact FK globally writable, so a user could
attach an intention to another owner's contact (CWE-639). The contact FK is now
scoped to the requester's own contacts.

Each test fails if the guard is reverted (project rule #1).
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.prayers.models import PrayerIntention

User = get_user_model()


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def prayer_setup(db):
    user_a = User.objects.create_user(
        email="a-pray@example.com",
        password="pw",
        first_name="Amy",
        last_name="A",
        role="missionary",
    )
    user_b = User.objects.create_user(
        email="b-pray@example.com",
        password="pw",
        first_name="Ben",
        last_name="B",
        role="missionary",
    )
    contact_a = Contact.objects.create(
        owner=user_a, first_name="Dana", last_name="Donor", email="dana.p@example.com"
    )
    contact_b = Contact.objects.create(
        owner=user_b, first_name="Eli", last_name="Donor", email="eli.p@example.com"
    )
    return {"a": user_a, "b": user_b, "contact_a": contact_a, "contact_b": contact_b}


@pytest.mark.django_db
class TestPrayerContactIDOR:
    def test_cannot_create_intention_for_foreign_contact(self, prayer_setup):
        resp = _client(prayer_setup["b"]).post(
            "/api/v1/prayers/",
            {"title": "Pray for", "contact": str(prayer_setup["contact_a"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert not PrayerIntention.objects.filter(contact=prayer_setup["contact_a"]).exists()

    def test_can_create_intention_for_own_contact(self, prayer_setup):
        resp = _client(prayer_setup["b"]).post(
            "/api/v1/prayers/",
            {"title": "Pray for", "contact": str(prayer_setup["contact_b"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
