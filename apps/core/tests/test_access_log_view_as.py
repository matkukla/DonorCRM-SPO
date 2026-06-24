"""View-As impersonation of donor PII is audit-logged.

When an admin/supervisor reads a missionary's PII while impersonating them via
the X-View-As-User-Id header, DataAccessLogMiddleware must record a row tying
the real actor to the impersonated user. This is the only evidence that
impersonated access to donor data is traceable; the feature existed but had no
test asserting the row is written.
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.core.models import DataAccessLog

User = get_user_model()


@pytest.mark.django_db
class TestViewAsAuditLogged:
    @pytest.fixture
    def view_as_setup(self, db):
        admin = User.objects.create_user(email="admin-va@example.com", password="pw", role="admin")
        missionary = User.objects.create_user(
            email="m-va@example.com", password="pw", role="missionary"
        )
        contact = Contact.objects.create(owner=missionary, first_name="Vic", last_name="ViewAs")
        return {"admin": admin, "missionary": missionary, "contact": contact}

    def test_view_as_get_writes_log_with_impersonated_user(self, view_as_setup):
        admin = view_as_setup["admin"]
        missionary = view_as_setup["missionary"]
        contact = view_as_setup["contact"]

        client = APIClient()
        client.force_authenticate(user=admin)
        resp = client.get(
            f"/api/v1/contacts/{contact.id}/",
            HTTP_X_VIEW_AS_USER_ID=str(missionary.id),
        )
        assert resp.status_code == status.HTTP_200_OK

        log = DataAccessLog.objects.filter(path=f"/api/v1/contacts/{contact.id}/").latest(
            "timestamp"
        )
        assert log.actor_id == admin.id
        assert log.view_as_user_id == missionary.id
        assert log.method == "GET"

    def test_non_impersonated_get_records_no_view_as_user(self, view_as_setup):
        admin = view_as_setup["admin"]
        own_contact = Contact.objects.create(owner=admin, first_name="Own", last_name="Admin")

        client = APIClient()
        client.force_authenticate(user=admin)
        resp = client.get(f"/api/v1/contacts/{own_contact.id}/")
        assert resp.status_code == status.HTTP_200_OK

        log = DataAccessLog.objects.filter(path=f"/api/v1/contacts/{own_contact.id}/").latest(
            "timestamp"
        )
        assert log.actor_id == admin.id
        assert log.view_as_user_id is None
