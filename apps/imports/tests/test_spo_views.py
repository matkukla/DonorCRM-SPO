"""
Tests for SPO import API views:
  POST /api/imports/spo/missionaries/
  POST /api/imports/spo/gifts/
  POST /api/imports/spo/prayers/

TDD plan 04: Stubs filled in.
"""
import csv as csv_mod
import io

from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from apps.users.models import User

# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def _make_solicitor_csv(*names):
    """Build minimal SPO Solicitor CSV bytes with type-label row."""
    buf = io.StringIO()
    writer = csv_mod.writer(buf)
    writer.writerow(["Solicitor"])
    writer.writerow(["Name"])
    for name in names:
        writer.writerow([name])
    return buf.getvalue().encode("utf-8")


def _make_gifts_csv(*rows):
    """Build minimal SPO Gifts CSV bytes."""
    buf = io.StringIO()
    writer = csv_mod.writer(buf)
    writer.writerow(["Gift"])
    writer.writerow(
        [
            "Gift ID",
            "Constituent ID",
            "Gift Is Anonymous",
            "Solicitor Name",
            "Solicitor Amount",
            "Gift Amount",
            "Gift Date",
            "Gift Specific Attributes Prayer Requests Description",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.get("gift_id", ""),
                row.get("constituent_id", ""),
                row.get("is_anonymous", "No"),
                row.get("solicitor_name", ""),
                row.get("solicitor_amount", ""),
                row.get("gift_amount", "0.00"),
                row.get("gift_date", "2024-01-01"),
                row.get("prayer_description", ""),
            ]
        )
    return buf.getvalue().encode("utf-8")


def _make_admin():
    return User.objects.create_user(
        email="admin@example.com",
        password="adminpass",
        first_name="Admin",
        last_name="User",
        role="admin",
    )


def _make_staff():
    return User.objects.create_user(
        email="staff@example.com",
        password="staffpass",
        first_name="Staff",
        last_name="User",
        role="missionary",
    )


# ---------------------------------------------------------------------------
# TestSPOMissionaryImportView
# ---------------------------------------------------------------------------


class TestSPOMissionaryImportView(TestCase):
    """Tests for POST /api/imports/spo/missionaries/ view."""

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin()
        self.url = reverse("imports:import-spo-missionaries")

    def test_requires_admin(self):
        """Non-admin user receives 403 Forbidden."""
        staff = _make_staff()
        self.client.force_authenticate(user=staff)
        csv_bytes = _make_solicitor_csv("Peter Anderson")
        file_obj = io.BytesIO(csv_bytes)
        file_obj.name = "solicitors.csv"
        response = self.client.post(self.url, {"file": file_obj}, format="multipart")
        self.assertEqual(response.status_code, 403)

    def test_returns_batch_result(self):
        """Admin upload returns 200 with ImportBatch JSON shape."""
        self.client.force_authenticate(user=self.admin)
        csv_bytes = _make_solicitor_csv("Peter Anderson")
        file_obj = io.BytesIO(csv_bytes)
        file_obj.name = "solicitors.csv"
        response = self.client.post(self.url, {"file": file_obj}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("batch_id", data)
        self.assertIn("status", data)
        self.assertIn("created_count", data)
        self.assertIn("is_duplicate", data)

    def test_no_file_returns_400(self):
        """Missing file in request returns 400."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        response = self.client.post(self.url, {})
        self.assertIn(response.status_code, [401, 403])


# ---------------------------------------------------------------------------
# TestSPOGiftImportView
# ---------------------------------------------------------------------------


class TestSPOGiftImportView(TestCase):
    """Tests for POST /api/imports/spo/gifts/ view."""

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin()
        self.url = reverse("imports:import-spo-gifts")

    def test_requires_admin(self):
        """Non-admin user receives 403 Forbidden."""
        staff = _make_staff()
        self.client.force_authenticate(user=staff)
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G001",
                "solicitor_name": "Some Person",
                "gift_amount": "10.00",
                "gift_date": "2024-01-01",
                "is_anonymous": "Yes",
            }
        )
        file_obj = io.BytesIO(csv_bytes)
        file_obj.name = "gifts.csv"
        response = self.client.post(self.url, {"file": file_obj}, format="multipart")
        self.assertEqual(response.status_code, 403)

    def test_returns_batch_result(self):
        """Admin upload returns 200 with ImportBatch JSON shape."""
        self.client.force_authenticate(user=self.admin)
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G001",
                "solicitor_name": "Some Person",
                "gift_amount": "10.00",
                "gift_date": "2024-01-01",
                "is_anonymous": "Yes",
            }
        )
        file_obj = io.BytesIO(csv_bytes)
        file_obj.name = "gifts.csv"
        response = self.client.post(self.url, {"file": file_obj}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("batch_id", data)
        self.assertIn("status", data)
        self.assertIn("created_count", data)


# ---------------------------------------------------------------------------
# TestSPOPrayerImportView
# ---------------------------------------------------------------------------


class TestSPOPrayerImportView(TestCase):
    """Tests for POST /api/imports/spo/prayers/ view."""

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin()
        self.url = reverse("imports:import-spo-prayers")

    def test_requires_admin(self):
        """Non-admin user receives 403 Forbidden."""
        staff = _make_staff()
        self.client.force_authenticate(user=staff)
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G002",
                "solicitor_name": "Someone",
                "gift_amount": "10.00",
                "gift_date": "2024-01-01",
                "is_anonymous": "Yes",
            }
        )
        file_obj = io.BytesIO(csv_bytes)
        file_obj.name = "prayers.csv"
        response = self.client.post(self.url, {"file": file_obj}, format="multipart")
        self.assertEqual(response.status_code, 403)

    def test_returns_batch_result(self):
        """Admin upload returns 200 with ImportBatch JSON shape."""
        self.client.force_authenticate(user=self.admin)
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G002",
                "solicitor_name": "Someone",
                "gift_amount": "10.00",
                "gift_date": "2024-01-01",
                "is_anonymous": "Yes",
            }
        )
        file_obj = io.BytesIO(csv_bytes)
        file_obj.name = "prayers.csv"
        response = self.client.post(self.url, {"file": file_obj}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("batch_id", data)
        self.assertIn("status", data)
        self.assertIn("created_count", data)
