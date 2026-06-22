"""Regression tests for the 2026-06-22 re-scan findings #1, #2, #10, #11.

#1/#2: the legacy contact and donation CSV exports include financial fields
       (total_given, gift_count; gift amounts/dates). A coach (non-financial
       role) must be blocked (CWE-200).
#10/#11: the generic-contact and MPD imports must reject oversized row counts
       up front rather than processing an unbounded file synchronously
       (CWE-400).

Each test fails if the guard it covers is reverted (project rule #1).
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import Gift

User = get_user_model()


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def export_setup(db):
    """Coach C coaches missionary M, who has a donor with one $321.00 gift."""
    missionary = User.objects.create_user(
        email="m-export@example.com",
        password="pw",
        first_name="Mara",
        last_name="M",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-export@example.com",
        password="pw",
        first_name="Cole",
        last_name="C",
        role="coach",
    )
    coach.coached_users.add(missionary)
    contact = Contact.objects.create(
        owner=missionary, first_name="Dana", last_name="Donor", status="donor"
    )
    Gift.objects.create(donor_contact=contact, amount_cents=32100, gift_date=date.today())
    return {"missionary": missionary, "coach": coach}


@pytest.mark.django_db
class TestLegacyExportCoachGating:
    def test_coach_contact_export_forbidden(self, export_setup):
        resp = _client(export_setup["coach"]).get("/api/v1/imports/export/contacts/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_coach_donation_export_forbidden(self, export_setup):
        resp = _client(export_setup["coach"]).get("/api/v1/imports/export/donations/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_missionary_contact_export_allowed(self, export_setup):
        """Financial role still gets the export (no over-gating)."""
        resp = _client(export_setup["missionary"]).get("/api/v1/imports/export/contacts/")
        assert resp.status_code == status.HTTP_200_OK

    def test_missionary_donation_export_allowed(self, export_setup):
        resp = _client(export_setup["missionary"]).get("/api/v1/imports/export/donations/")
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestImportRowCaps:
    def test_generic_contact_import_rejects_oversized_file(self, monkeypatch):
        """A CSV past the row cap is rejected with 400 before any DB write."""
        import apps.imports.views as views

        monkeypatch.setattr(views, "MAX_GENERIC_IMPORT_ROWS", 5)
        admin = User.objects.create_user(
            email="admin-imp@example.com",
            password="pw",
            role="admin",
            is_staff=True,
        )
        header = "first_name,last_name,email\n"
        rows = "".join(f"F{i},L{i},f{i}@e.com\n" for i in range(10))
        from io import BytesIO

        upload = BytesIO((header + rows).encode("utf-8"))
        upload.name = "contacts.csv"
        resp = _client(admin).post(
            "/api/v1/imports/generic/contacts/",
            {"file": upload, "match_by": "email"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceeds" in resp.data["detail"].lower()
        # Nothing was imported.
        assert Contact.objects.count() == 0

    def test_mpd_parse_csv_rejects_oversized_file(self, monkeypatch):
        """parse_csv stops and raises once past the cap instead of materializing all rows."""
        import apps.imports.mpd_services as mpd

        monkeypatch.setattr(mpd, "MAX_IMPORT_ROWS", 5)
        header = "First Name,Last Name\n"
        rows = "".join(f"F{i},L{i}\n" for i in range(10))
        with pytest.raises(mpd.ImportTooLargeError):
            mpd.parse_csv((header + rows).encode("utf-8"))

    def test_mpd_parse_csv_accepts_within_cap(self, monkeypatch):
        import apps.imports.mpd_services as mpd

        monkeypatch.setattr(mpd, "MAX_IMPORT_ROWS", 50)
        header = "First Name,Last Name\n"
        rows = "".join(f"F{i},L{i}\n" for i in range(10))
        headers, data_rows = mpd.parse_csv((header + rows).encode("utf-8"))
        assert headers == ["First Name", "Last Name"]
        assert len(data_rows) == 10
