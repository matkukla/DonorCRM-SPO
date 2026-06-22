"""Regression tests for the 2026-06-22 re-scan findings #3 and #4.

A staff user may update their own gift / recurring gift, but the update path
must NOT let them retarget the record to a contact they do not own (CWE-639).
The create serializers validated donor_contact ownership; the update path used
the read serializer (donor_contact writable, unvalidated), so PATCH could
repoint an owned gift at another user's contact.

Each test fails if the validate_donor_contact guard on the read/update
serializer is reverted (project rule #1).
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import Gift, RecurringGift

User = get_user_model()


@pytest.fixture
def retarget_setup(db):
    """Two missionaries, each with a contact. user_a owns a gift + pledge."""
    user_a = User.objects.create_user(
        email="a-retarget@example.com",
        password="pw",
        first_name="Amy",
        last_name="A",
        role="missionary",
    )
    user_b = User.objects.create_user(
        email="b-retarget@example.com",
        password="pw",
        first_name="Ben",
        last_name="B",
        role="missionary",
    )
    contact_a = Contact.objects.create(
        owner=user_a, first_name="Dana", last_name="DonorA", status="donor"
    )
    contact_a2 = Contact.objects.create(
        owner=user_a, first_name="Dale", last_name="DonorA2", status="donor"
    )
    contact_b = Contact.objects.create(
        owner=user_b, first_name="Bea", last_name="DonorB", status="donor"
    )
    gift = Gift.objects.create(donor_contact=contact_a, amount_cents=10000, gift_date=date.today())
    pledge = RecurringGift.objects.create(
        donor_contact=contact_a,
        amount_cents=5000,
        frequency="monthly",
        start_date=date.today(),
        status="active",
    )
    return {
        "user_a": user_a,
        "user_b": user_b,
        "contact_a2": contact_a2,
        "contact_b": contact_b,
        "gift": gift,
        "pledge": pledge,
    }


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestGiftRetarget:
    def test_patch_gift_to_foreign_contact_is_rejected(self, retarget_setup):
        s = retarget_setup
        resp = _client(s["user_a"]).patch(
            f"/api/v1/gifts/{s['gift'].id}/",
            {"donor_contact": str(s["contact_b"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        s["gift"].refresh_from_db()
        # Ownership unchanged — the gift still points at user_a's contact.
        assert s["gift"].donor_contact.owner_id == s["user_a"].id

    def test_patch_gift_to_own_other_contact_is_allowed(self, retarget_setup):
        """No over-gating: moving a gift between the user's own contacts works."""
        s = retarget_setup
        resp = _client(s["user_a"]).patch(
            f"/api/v1/gifts/{s['gift'].id}/",
            {"donor_contact": str(s["contact_a2"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        s["gift"].refresh_from_db()
        assert s["gift"].donor_contact_id == s["contact_a2"].id


@pytest.mark.django_db
class TestRecurringGiftRetarget:
    def test_patch_pledge_to_foreign_contact_is_rejected(self, retarget_setup):
        s = retarget_setup
        resp = _client(s["user_a"]).patch(
            f"/api/v1/gifts/recurring/{s['pledge'].id}/",
            {"donor_contact": str(s["contact_b"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        s["pledge"].refresh_from_db()
        assert s["pledge"].donor_contact.owner_id == s["user_a"].id

    def test_patch_pledge_to_own_other_contact_is_allowed(self, retarget_setup):
        s = retarget_setup
        resp = _client(s["user_a"]).patch(
            f"/api/v1/gifts/recurring/{s['pledge'].id}/",
            {"donor_contact": str(s["contact_a2"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        s["pledge"].refresh_from_db()
        assert s["pledge"].donor_contact_id == s["contact_a2"].id
