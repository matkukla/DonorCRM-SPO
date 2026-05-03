"""
Tests for the org-wide annual goal setting and its effect on the
Fiscal Year Pace tile.
"""
import pytest
from rest_framework.test import APIClient

from apps.contacts.tests.factories import ContactFactory
from apps.core.models import OrgSettings
from apps.gifts.tests.factories import GiftFactory
from apps.users.tests.factories import AdminUserFactory, UserFactory


@pytest.mark.django_db
def test_org_settings_default_is_zero():
    """First fetch creates the row with annual_goal_cents=0."""
    admin = AdminUserFactory()
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get("/api/v1/insights/admin/org-settings/")
    assert response.status_code == 200
    assert response.json() == {"annual_goal_cents": 0}


@pytest.mark.django_db
def test_org_settings_patch_persists():
    admin = AdminUserFactory()
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.patch(
        "/api/v1/insights/admin/org-settings/",
        {"annual_goal_cents": 12_000_000},
        format="json",
    )
    assert response.status_code == 200
    assert response.json() == {"annual_goal_cents": 12_000_000}

    assert OrgSettings.get_solo().annual_goal_cents == 12_000_000


@pytest.mark.django_db
def test_org_settings_rejects_negative():
    admin = AdminUserFactory()
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.patch(
        "/api/v1/insights/admin/org-settings/",
        {"annual_goal_cents": -100},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_org_settings_admin_only():
    user = UserFactory(role="missionary")
    client = APIClient()
    client.force_authenticate(user=user)

    assert client.get("/api/v1/insights/admin/org-settings/").status_code == 403
    assert client.patch(
        "/api/v1/insights/admin/org-settings/",
        {"annual_goal_cents": 1},
        format="json",
    ).status_code == 403


@pytest.mark.django_db
def test_fy_pace_uses_org_setting_when_set():
    """When admin sets an org-wide annual goal, FY Pace tile uses it."""
    admin = AdminUserFactory()
    # Missionary with monthly_support_goal_cents = 100,000 ($1k/mo => $12k annual)
    missionary = UserFactory(role="missionary", monthly_support_goal_cents=100_000)
    contact = ContactFactory(owner=missionary)
    GiftFactory(donor_contact=contact, amount_cents=50_000)

    OrgSettings.objects.update_or_create(
        pk=OrgSettings._solo_uuid(),
        defaults={"annual_goal_cents": 5_000_000},  # $50k org-wide override
    )

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/v1/insights/admin/fiscal-year-pace/")

    body = response.json()
    assert response.status_code == 200
    assert body["annual_goal_cents"] == 5_000_000
    assert body["annual_goal_source"] == "org_setting"


@pytest.mark.django_db
def test_fy_pace_falls_back_to_missionary_sum_when_no_org_setting():
    """When org-wide goal is 0, the tile falls back to summing missionary goals."""
    admin = AdminUserFactory()
    UserFactory(role="missionary", monthly_support_goal_cents=100_000)
    UserFactory(role="missionary", monthly_support_goal_cents=200_000)

    # Default OrgSettings has annual_goal_cents=0 — fallback engaged.
    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/v1/insights/admin/fiscal-year-pace/")

    body = response.json()
    assert response.status_code == 200
    assert body["annual_goal_cents"] == (100_000 + 200_000) * 12
    assert body["annual_goal_source"] == "missionary_sum"
