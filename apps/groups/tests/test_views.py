"""
Tests for Group API views.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.tests.factories import ContactFactory
from apps.groups.models import Group
from apps.groups.tests.factories import GroupFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestGroupListCreateView:
    """Tests for group list and create endpoints."""

    def test_list_groups_authenticated(self):
        """Test listing groups for authenticated user."""
        user = UserFactory(role='fundraiser')
        GroupFactory.create_batch(3, owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/groups/')

        assert response.status_code == status.HTTP_200_OK
        # Response is paginated
        assert response.data['count'] == 3
        # Check that results have contact_count annotated
        assert 'contact_count' in response.data['results'][0]

    def test_list_groups_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get('/api/v1/groups/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_group(self):
        """Test creating a group."""
        user = UserFactory(role='fundraiser')

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            'name': 'New Group',
            'description': 'A test group',
            'color': '#ff5733'
        }

        response = client.post('/api/v1/groups/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Group'
        assert response.data['color'] == '#ff5733'


@pytest.mark.django_db
class TestGroupDetailView:
    """Tests for group detail endpoint."""

    def test_get_group_detail(self):
        """Test getting group detail."""
        user = UserFactory(role='fundraiser')
        group = GroupFactory(owner=user, name='My Group')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f'/api/v1/groups/{group.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'My Group'

    def test_update_group(self):
        """Test updating a group."""
        user = UserFactory(role='fundraiser')
        group = GroupFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch(
            f'/api/v1/groups/{group.id}/',
            {'name': 'Updated Name'}
        )

        assert response.status_code == status.HTTP_200_OK
        group.refresh_from_db()
        assert group.name == 'Updated Name'

    def test_delete_group(self):
        """Test deleting a group."""
        user = UserFactory(role='fundraiser')
        group = GroupFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(f'/api/v1/groups/{group.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Group.objects.filter(id=group.id).exists()


@pytest.mark.django_db
class TestGroupContactsView:
    """Tests for group contacts management."""

    def test_list_contacts_in_group(self):
        """Test listing contacts in a group."""
        user = UserFactory(role='fundraiser')
        group = GroupFactory(owner=user)
        contact1 = ContactFactory(owner=user)
        contact2 = ContactFactory(owner=user)
        contact1.groups.add(group)
        contact2.groups.add(group)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f'/api/v1/groups/{group.id}/contacts/')

        assert response.status_code == status.HTTP_200_OK
        # Response is a list, not paginated
        assert len(response.data) == 2

    def test_add_contact_to_group(self):
        """Test adding a contact to a group via POST."""
        user = UserFactory(role='fundraiser')
        group = GroupFactory(owner=user)
        contact = ContactFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        # POST to /contacts/ endpoint adds contacts
        response = client.post(
            f'/api/v1/groups/{group.id}/contacts/',
            {'contact_ids': [str(contact.id)]},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert contact in group.contacts.all()

    def test_remove_contact_from_group(self):
        """Test removing a contact from a group via DELETE."""
        user = UserFactory(role='fundraiser')
        group = GroupFactory(owner=user)
        contact = ContactFactory(owner=user)
        contact.groups.add(group)

        client = APIClient()
        client.force_authenticate(user=user)

        # DELETE to /contacts/ endpoint removes contacts
        response = client.delete(
            f'/api/v1/groups/{group.id}/contacts/',
            {'contact_ids': [str(contact.id)]},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert contact not in group.contacts.all()
