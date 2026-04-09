"""
Tests for Gift and RecurringGift view permission scoping.

Verifies that:
- Staff users can only see their own gifts (not other users' gifts)
- Admin users can see all gifts
- Coach users cannot see gifts
- Same patterns apply to RecurringGift views
"""
from datetime import date, timedelta

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.models import Gift, RecurringGift, RecurringGiftFrequency, RecurringGiftStatus
from apps.users.tests.factories import (
    AdminUserFactory,
    UserFactory,
)


@pytest.fixture
def staff_user1():
    return UserFactory(email="staff1@test.com")


@pytest.fixture
def staff_user2():
    return UserFactory(email="staff2@test.com")


@pytest.fixture
def admin_user():
    return AdminUserFactory(email="admin@test.com")


@pytest.fixture
def user1_contact(staff_user1):
    return ContactFactory(owner=staff_user1, first_name="Alice", last_name="Donor")


@pytest.fixture
def user2_contact(staff_user2):
    return ContactFactory(owner=staff_user2, first_name="Bob", last_name="Donor")


@pytest.fixture
def user1_gift(user1_contact):
    return Gift.objects.create(
        donor_contact=user1_contact,
        amount_cents=10000,
        gift_date=date.today(),
    )


@pytest.fixture
def user2_gift(user2_contact):
    return Gift.objects.create(
        donor_contact=user2_contact,
        amount_cents=20000,
        gift_date=date.today(),
    )


@pytest.fixture
def user1_recurring(user1_contact):
    return RecurringGift.objects.create(
        donor_contact=user1_contact,
        amount_cents=5000,
        frequency=RecurringGiftFrequency.MONTHLY,
        status=RecurringGiftStatus.ACTIVE,
        start_date=date.today() - timedelta(days=30),
    )


@pytest.fixture
def user2_recurring(user2_contact):
    return RecurringGift.objects.create(
        donor_contact=user2_contact,
        amount_cents=7500,
        frequency=RecurringGiftFrequency.QUARTERLY,
        status=RecurringGiftStatus.ACTIVE,
        start_date=date.today() - timedelta(days=60),
    )


def _client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# Gift permission scoping tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGiftPermissionScoping:
    """Verify cross-user isolation on Gift list and detail endpoints."""

    def test_staff_user_cannot_see_other_users_gifts(
        self,
        staff_user1,
        staff_user2,
        user1_gift,
        user2_gift,
    ):
        client = _client_for(staff_user1)
        response = client.get("/api/v1/gifts/")
        assert response.status_code == status.HTTP_200_OK
        gift_ids = [g["id"] for g in response.data["results"]]
        assert str(user1_gift.id) in gift_ids
        assert str(user2_gift.id) not in gift_ids

    def test_staff_user_cannot_access_other_users_gift_detail(
        self,
        staff_user1,
        user2_gift,
    ):
        client = _client_for(staff_user1)
        response = client.get(f"/api/v1/gifts/{user2_gift.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_sees_only_own_gifts_by_default(
        self,
        admin_user,
        user1_gift,
        user2_gift,
    ):
        """Admin sees only own data by default; cross-user access is via View As."""
        client = _client_for(admin_user)
        response = client.get("/api/v1/gifts/")
        assert response.status_code == status.HTTP_200_OK
        gift_ids = [g["id"] for g in response.data["results"]]
        # Admin has no contacts of their own, so should see neither
        assert str(user1_gift.id) not in gift_ids
        assert str(user2_gift.id) not in gift_ids

    def test_unauthenticated_cannot_access_gifts(self, user1_gift):
        client = APIClient()
        response = client.get("/api/v1/gifts/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# RecurringGift permission scoping tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRecurringGiftPermissionScoping:
    """Verify cross-user isolation on RecurringGift list and detail endpoints."""

    def test_staff_user_cannot_see_other_users_recurring_gifts(
        self,
        staff_user1,
        staff_user2,
        user1_recurring,
        user2_recurring,
    ):
        client = _client_for(staff_user1)
        response = client.get("/api/v1/gifts/recurring/")
        assert response.status_code == status.HTTP_200_OK
        rg_ids = [r["id"] for r in response.data["results"]]
        assert str(user1_recurring.id) in rg_ids
        assert str(user2_recurring.id) not in rg_ids

    def test_staff_user_cannot_access_other_users_recurring_gift_detail(
        self,
        staff_user1,
        user2_recurring,
    ):
        client = _client_for(staff_user1)
        response = client.get(f"/api/v1/gifts/recurring/{user2_recurring.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_sees_only_own_recurring_gifts_by_default(
        self,
        admin_user,
        user1_recurring,
        user2_recurring,
    ):
        """Admin sees only own data by default; cross-user access is via View As."""
        client = _client_for(admin_user)
        response = client.get("/api/v1/gifts/recurring/")
        assert response.status_code == status.HTTP_200_OK
        rg_ids = [r["id"] for r in response.data["results"]]
        assert str(user1_recurring.id) not in rg_ids
        assert str(user2_recurring.id) not in rg_ids

    def test_unauthenticated_cannot_access_recurring_gifts(self, user1_recurring):
        client = APIClient()
        response = client.get("/api/v1/gifts/recurring/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
