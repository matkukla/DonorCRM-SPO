"""Query-param widening cannot bypass gift owner-scoping.

GiftFilterSet exposes a `donor_contact` UUID filter. A missionary must not be
able to read another owner's gifts by passing the foreign contact's ID as
?donor_contact=. Scoping (donor_contact__owner_id__in=visible) is applied
before the filter, so the filter can only narrow within already-visible rows.
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import Gift

User = get_user_model()

FOREIGN_CENTS = 818181  # distinctive amount that must never reach the attacker


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def cross_owner_gift(db):
    attacker = User.objects.create_user(
        email="atk-gift@example.com", password="pw", role="missionary"
    )
    victim = User.objects.create_user(
        email="vic-gift@example.com", password="pw", role="missionary"
    )
    victim_contact = Contact.objects.create(owner=victim, first_name="Vera", last_name="Victim")
    Gift.objects.create(
        donor_contact=victim_contact, amount_cents=FOREIGN_CENTS, gift_date=date.today()
    )
    return {"attacker": attacker, "victim_contact": victim_contact}


@pytest.mark.django_db
class TestGiftParamWidening:
    def test_donor_contact_param_cannot_widen_scope(self, cross_owner_gift):
        cid = cross_owner_gift["victim_contact"].id
        resp = _client(cross_owner_gift["attacker"]).get(f"/api/v1/gifts/?donor_contact={cid}")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        assert results == []
        assert str(FOREIGN_CENTS) not in str(resp.data)
