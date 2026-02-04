"""
Tests for import views.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.imports.models import Fund, ImportRun, ImportType, ImportStatus
from apps.contacts.models import Contact

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        email='admin@example.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User',
        role='admin'
    )


@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.mark.django_db
class TestLatestImportRunsView:
    """Tests for LatestImportRunsView."""

    def test_latest_import_runs_returns_null_for_no_imports(self, api_client, admin_user):
        """With no imports, should return null for all types and zero counts."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('imports:latest-import-runs')

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['funds'] is None
        assert response.data['entities'] is None
        assert response.data['transactions'] is None
        assert response.data['pledges'] is None
        assert 'dependency_counts' in response.data
        assert response.data['dependency_counts']['funds_count'] == 0
        assert response.data['dependency_counts']['entities_with_external_id_count'] == 0

    def test_latest_import_runs_returns_latest_run(self, api_client, admin_user):
        """Should return the most recent import run for each type."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('imports:latest-import-runs')

        # Create two fund import runs (older and newer)
        older_run = ImportRun.objects.create(
            type=ImportType.FUNDS,
            status=ImportStatus.COMPLETED,
            filename='funds_old.csv',
            uploaded_by=admin_user,
            created_count=5,
            updated_count=2,
            error_count=0
        )

        # Create newer run
        newer_run = ImportRun.objects.create(
            type=ImportType.FUNDS,
            status=ImportStatus.COMPLETED,
            filename='funds_new.csv',
            uploaded_by=admin_user,
            created_count=10,
            updated_count=3,
            error_count=1
        )

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['funds'] is not None
        # Should return the newer run
        assert response.data['funds']['id'] == str(newer_run.id)
        assert response.data['funds']['status'] == ImportStatus.COMPLETED
        assert response.data['funds']['created_count'] == 10
        assert response.data['funds']['updated_count'] == 3
        assert response.data['funds']['error_count'] == 1
        # Other types should still be null
        assert response.data['entities'] is None
        assert response.data['transactions'] is None
        assert response.data['pledges'] is None

    def test_latest_import_runs_requires_admin(self, api_client, test_user):
        """Non-admin users should receive 403 Forbidden."""
        api_client.force_authenticate(user=test_user)
        url = reverse('imports:latest-import-runs')

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_latest_import_runs_includes_dependency_counts(self, api_client, admin_user, test_user):
        """Should return accurate counts for funds and entities with external_id."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('imports:latest-import-runs')

        # Create some Funds
        Fund.objects.create(external_id='FUND001', name='Fund 1', status='active')
        Fund.objects.create(external_id='FUND002', name='Fund 2', status='active')
        Fund.objects.create(external_id='FUND003', name='Fund 3', status='inactive')

        # Create some Contacts with and without external_id
        Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            owner=test_user,
            external_id='EXT001'
        )
        Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            owner=test_user,
            external_id='EXT002'
        )
        # Contacts without external_id (should not be counted)
        Contact.objects.create(
            first_name='Bob',
            last_name='Jones',
            email='bob@example.com',
            owner=test_user,
            external_id=''
        )
        Contact.objects.create(
            first_name='Alice',
            last_name='Brown',
            email='alice@example.com',
            owner=test_user,
            external_id=''
        )

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['dependency_counts']['funds_count'] == 3
        assert response.data['dependency_counts']['entities_with_external_id_count'] == 2
