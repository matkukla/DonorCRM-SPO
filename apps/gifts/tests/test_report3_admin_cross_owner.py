"""Regression tests for the 2026-06-22 report_3 re-scan findings #2/#4/#6/#8.

The gift/recurring-gift ownership validators short-circuited for admins
(`if user.role == "admin": return value`), letting an admin create or retarget
a gift/pledge onto ANY user's contact (CWE-639). The documented policy is
"admin — cross-user access via read-only View-As only", and View-As blocks all
mutations, so there is no sanctioned cross-owner write path. Admins must obey
the same own-contact rule as everyone else.

  #4 — admin gift create with a foreign contact is rejected
  #8 — admin gift update (retarget) to a foreign contact is rejected
  #6 — admin recurring-gift create with a foreign contact is rejected
  #2 — admin recurring-gift update (retarget) to a foreign contact is rejected

Positive cases prove no over-gating: an admin can still write to their OWN
contacts. Each test fails if an admin early-return is reintroduced (rule #1).
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
def admin_setup(db):
    """An admin who owns a contact (plus a gift + pledge), and a missionary
    who owns a separate contact the admin must not be able to write onto."""
    admin = User.objects.create_user(
        email="admin-r3@example.com",
        password="pw",
        first_name="Ada",
        last_name="Admin",
        role="admin",
    )
    missionary = User.objects.create_user(
        email="m-r3-admin@example.com",
        password="pw",
        first_name="Ben",
        last_name="B",
        role="missionary",
    )
    contact_admin = Contact.objects.create(
        owner=admin, first_name="Owen", last_name="OwnedByAdmin", status="donor"
    )
    contact_foreign = Contact.objects.create(
        owner=missionary, first_name="Bea", last_name="ForeignDonor", status="donor"
    )
    gift = Gift.objects.create(
        donor_contact=contact_admin, amount_cents=10000, gift_date=date.today()
    )
    pledge = RecurringGift.objects.create(
        donor_contact=contact_admin,
        amount_cents=5000,
        frequency="monthly",
        start_date=date.today(),
        status="active",
    )
    return {
        "admin": admin,
        "contact_admin": contact_admin,
        "contact_foreign": contact_foreign,
        "gift": gift,
        "pledge": pledge,
    }


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestAdminGiftCrossOwner:
    def test_admin_gift_create_on_foreign_contact_is_rejected(self, admin_setup):
        s = admin_setup
        resp = _client(s["admin"]).post(
            "/api/v1/gifts/",
            {
                "donor_contact": str(s["contact_foreign"].id),
                "amount_cents": 2500,
                "gift_date": date.today().isoformat(),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        # No gift was created on the foreign contact.
        assert not Gift.objects.filter(donor_contact=s["contact_foreign"]).exists()

    def test_admin_gift_retarget_to_foreign_contact_is_rejected(self, admin_setup):
        s = admin_setup
        resp = _client(s["admin"]).patch(
            f"/api/v1/gifts/{s['gift'].id}/",
            {"donor_contact": str(s["contact_foreign"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        s["gift"].refresh_from_db()
        assert s["gift"].donor_contact_id == s["contact_admin"].id

    def test_admin_gift_create_on_own_contact_is_allowed(self, admin_setup):
        """No over-gating: an admin can still create a gift on their own contact."""
        s = admin_setup
        resp = _client(s["admin"]).post(
            "/api/v1/gifts/",
            {
                "donor_contact": str(s["contact_admin"].id),
                "amount_cents": 2500,
                "gift_date": date.today().isoformat(),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestAdminRecurringGiftCrossOwner:
    def test_admin_recurring_create_on_foreign_contact_is_rejected(self, admin_setup):
        s = admin_setup
        resp = _client(s["admin"]).post(
            "/api/v1/gifts/recurring/",
            {
                "donor_contact": str(s["contact_foreign"].id),
                "amount_cents": 2500,
                "frequency": "monthly",
                "start_date": date.today().isoformat(),
                "status": "active",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert not RecurringGift.objects.filter(donor_contact=s["contact_foreign"]).exists()

    def test_admin_recurring_retarget_to_foreign_contact_is_rejected(self, admin_setup):
        s = admin_setup
        resp = _client(s["admin"]).patch(
            f"/api/v1/gifts/recurring/{s['pledge'].id}/",
            {"donor_contact": str(s["contact_foreign"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        s["pledge"].refresh_from_db()
        assert s["pledge"].donor_contact_id == s["contact_admin"].id

    def test_admin_recurring_create_on_own_contact_is_allowed(self, admin_setup):
        s = admin_setup
        resp = _client(s["admin"]).post(
            "/api/v1/gifts/recurring/",
            {
                "donor_contact": str(s["contact_admin"].id),
                "amount_cents": 2500,
                "frequency": "monthly",
                "start_date": date.today().isoformat(),
                "status": "active",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
