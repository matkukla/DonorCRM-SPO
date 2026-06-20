"""Integration guard: the contacts CSV export fails loudly, not silently (PRD reliability).

A StreamingHttpResponse can't turn a mid-stream error into a 500 (headers already sent).
This asserts that when row generation raises after the header, the download contains the
__ERROR__ sentinel rather than a truncated-but-plausible CSV.
"""

from unittest import mock

from django.contrib.auth import get_user_model

from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact

User = get_user_model()


@pytest.mark.django_db
def test_contacts_export_appends_error_sentinel_on_midstream_failure():
    user = User.objects.create_user(email="exp@example.com", password="pw", role="missionary")
    Contact.objects.create(owner=user, first_name="Dana", last_name="Donor", status="donor")

    client = APIClient()
    client.force_authenticate(user=user)

    # Force the first data row to raise; the header has already been yielded.
    with mock.patch(
        "apps.contacts.export_views.sanitize_csv_value", side_effect=RuntimeError("boom")
    ):
        response = client.get("/api/v1/contacts/export/csv/")
        body = b"".join(response.streaming_content).decode()

    assert "Name,Email" in body  # header preserved (partial output)
    assert "__ERROR__" in body  # loud failure signal, not silent truncation
    assert "boom" not in body  # raw exception text never written to the file
