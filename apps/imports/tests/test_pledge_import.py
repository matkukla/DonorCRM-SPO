"""
Tests for legacy pledge import endpoint (returns 410 Gone).

The original SPO pledge import functions (parse_pledges_csv, import_pledges,
get_pledges_template) were removed in Phase 30-02 and replaced by the RE
Recurring Gift import pipeline. This test file verifies the legacy endpoint
returns 410 Gone.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user for testing."""
    return User.objects.create_user(
        email='admin@example.com',
        password='testpass',
        role='admin'
    )


@pytest.fixture
def api_client():
    """Create API client for testing."""
    return APIClient()


@pytest.mark.django_db
class TestLegacyPledgeImportView:
    """Tests that legacy pledge import returns 410 Gone."""

    def test_legacy_import_returns_410(self, api_client, admin_user):
        """Legacy pledge import POST returns 410 Gone."""
        api_client.force_authenticate(user=admin_user)
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile('test.csv', b'header\n', content_type='text/csv')
        response = api_client.post(
            reverse('imports:import-pledges'),
            {'file': file},
            format='multipart'
        )
        assert response.status_code == 410

    def test_legacy_template_returns_410(self, api_client, admin_user):
        """Legacy pledge template GET returns 410 Gone."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse('imports:template-pledges'))
        assert response.status_code == 410
