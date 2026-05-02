"""
Regression: when CELERY_ENABLED=False, the async contact-import path must
return a 400 with a clear message instead of silently calling .delay() on a
broker-less Celery (which would drop the job).
"""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.users.tests.factories import AdminUserFactory


@pytest.mark.django_db
@override_settings(CELERY_ENABLED=False)
def test_async_import_returns_400_when_celery_disabled():
    user = AdminUserFactory()
    client = APIClient()
    client.force_authenticate(user=user)

    csv_content = (
        "first_name,last_name,email,phone,address,city,state,zip,country\n"
        "Jane,Doe,jane@example.com,,,,,,US\n"
    )
    csv_bytes = csv_content.encode("utf-8")

    from io import BytesIO
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("contacts.csv", csv_bytes, content_type="text/csv")
    response = client.post(
        "/api/v1/imports/contacts/?async=true",
        {"file": upload},
        format="multipart",
    )

    assert response.status_code == 400
    body = response.json()
    assert "async" in body["detail"].lower() or "split" in body["detail"].lower()


@pytest.mark.django_db
@override_settings(CELERY_ENABLED=True)
def test_async_import_does_not_take_disabled_branch_when_enabled(monkeypatch):
    """When CELERY_ENABLED=True, the request bypasses the new 400 branch.
    We mock .delay() so this test stays focused on the gate, not Celery's eager
    runtime."""
    from apps.imports import views as imports_views

    called = {"value": False}

    class _FakeAsyncResult:
        def __init__(self):
            called["value"] = True

    def fake_delay(*args, **kwargs):
        return _FakeAsyncResult()

    monkeypatch.setattr(imports_views.import_contacts_async, "delay", fake_delay)

    user = AdminUserFactory()
    client = APIClient()
    client.force_authenticate(user=user)

    csv_content = (
        "first_name,last_name,email,phone,address,city,state,zip,country\n"
        "Jane,Doe,jane2@example.com,,,,,,US\n"
    )
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("contacts.csv", csv_content.encode("utf-8"),
                                content_type="text/csv")
    response = client.post(
        "/api/v1/imports/contacts/?async=true",
        {"file": upload},
        format="multipart",
    )

    # The new gate must NOT short-circuit when CELERY_ENABLED is True; .delay()
    # was invoked and the response is the queued-for-processing 202.
    assert called["value"] is True
    assert response.status_code == 202
