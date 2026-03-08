"""
TDD test scaffold for org-contact mapping behaviors.

These tests are intentionally written to FAIL against the current (unmodified) codebase.
They specify all behaviors that Wave 1 tasks must implement:

1. full_name returns organization_name when first/last are blank
2. ContactListSerializer includes 'organization_name' field
3. ContactCreateSerializer accepts blank first/last with non-blank organization_name
4. GET /contacts/ response items include 'organization_name'
5. GET /contacts/?search=<org> finds org contacts (list search_fields)
6. GET /contacts/search/?q=<org> finds org contacts (search Q filter)
7. CSV export Name column shows organization_name for org contacts
"""
import pytest
from rest_framework.test import APIClient

from apps.contacts.serializers import ContactCreateSerializer, ContactListSerializer
from apps.contacts.tests.factories import OrgContactFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestOrgContactFullName:
    def test_full_name_returns_org_name_when_names_blank(self):
        contact = OrgContactFactory()
        assert contact.full_name == contact.organization_name


@pytest.mark.django_db
class TestOrgContactSerializer:
    def test_contact_list_serializer_includes_org_name(self):
        contact = OrgContactFactory()
        data = ContactListSerializer(contact).data
        assert 'organization_name' in data
        assert data['organization_name'] == contact.organization_name

    def test_create_serializer_accepts_blank_names_with_org(self):
        serializer = ContactCreateSerializer(data={
            'first_name': '',
            'last_name': '',
            'organization_name': 'Acme Corp',
            'status': 'prospect',
        })
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestOrgContactAPIEndpoints:
    def setup_method(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.org_contact = OrgContactFactory(owner=self.user)

    def test_contact_list_api_includes_org_name(self):
        resp = self.client.get('/contacts/')
        assert resp.status_code == 200
        results = resp.json()['results']
        assert any(c['id'] == str(self.org_contact.id) for c in results)
        contact_data = next(c for c in results if c['id'] == str(self.org_contact.id))
        assert 'organization_name' in contact_data

    def test_list_endpoint_search_finds_org_by_name(self):
        query = self.org_contact.organization_name[:5]
        resp = self.client.get(f'/contacts/?search={query}')
        assert resp.status_code == 200
        ids = [c['id'] for c in resp.json()['results']]
        assert str(self.org_contact.id) in ids

    def test_search_endpoint_finds_org_by_name(self):
        query = self.org_contact.organization_name[:5]
        resp = self.client.get(f'/contacts/search/?q={query}')
        assert resp.status_code == 200
        ids = [c['id'] for c in resp.json()]
        assert str(self.org_contact.id) in ids


@pytest.mark.django_db
class TestOrgContactCSVExport:
    def setup_method(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.org_contact = OrgContactFactory(owner=self.user)

    def test_csv_export_uses_full_name_for_org(self):
        resp = self.client.get('/contacts/export/')
        assert resp.status_code == 200
        content = b''.join(resp.streaming_content).decode()
        lines = content.strip().split('\n')
        # Header row first, then data rows
        assert len(lines) >= 2
        # The org contact's name should appear in the CSV content
        assert self.org_contact.organization_name in content
