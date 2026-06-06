"""
Tests for legacy transaction import endpoint (returns 410 Gone).

The original SPO transaction import functions (parse_transactions_csv,
import_transactions, update_contact_stats_for_import) were removed in
Phase 30-02 and replaced by the RE Gift import pipeline. This test file
verifies the legacy endpoint returns 410 Gone.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient

import pytest

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user for testing."""
    return User.objects.create_user(email="admin@example.com", password="testpass", role="admin")


@pytest.fixture
def api_client():
    """Create API client for testing."""
    return APIClient()


@pytest.mark.django_db
class TestLegacyTransactionImportView:
    """Tests that legacy transaction import returns 410 Gone."""

    def test_legacy_import_returns_410(self, api_client, admin_user):
        """Legacy transaction import POST returns 410 Gone."""
        api_client.force_authenticate(user=admin_user)
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("test.csv", b"header\n", content_type="text/csv")
        response = api_client.post(
            reverse("imports:import-transactions"), {"file": file}, format="multipart"
        )
        assert response.status_code == 410

    def test_legacy_template_returns_410(self, api_client, admin_user):
        """Legacy transaction template GET returns 410 Gone."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse("imports:template-transactions"))
        assert response.status_code == 410
