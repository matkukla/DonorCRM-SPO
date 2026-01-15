"""
Tests for Group model.
"""
import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.groups.models import Group
from apps.groups.tests.factories import GroupFactory, SharedGroupFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestGroupModel:
    """Tests for Group model methods and properties."""

    def test_group_str(self):
        """Test group string representation."""
        group = GroupFactory(name='Monthly Supporters')
        assert str(group) == 'Monthly Supporters'

    def test_contact_count_empty(self):
        """Test contact count for empty group."""
        group = GroupFactory()
        assert group.contact_count == 0

    def test_contact_count_with_contacts(self):
        """Test contact count with contacts."""
        user = UserFactory()
        group = GroupFactory(owner=user)
        contact1 = ContactFactory(owner=user)
        contact2 = ContactFactory(owner=user)
        contact1.groups.add(group)
        contact2.groups.add(group)

        assert group.contact_count == 2

    def test_is_shared_with_owner(self):
        """Test is_shared for group with owner."""
        group = GroupFactory()
        assert group.is_shared is False

    def test_is_shared_without_owner(self):
        """Test is_shared for organization-wide group."""
        group = SharedGroupFactory()
        assert group.is_shared is True

    def test_group_default_color(self):
        """Test group default color."""
        user = UserFactory()
        group = Group.objects.create(name='Test Group', owner=user)
        assert group.color == '#6366f1'

    def test_unique_name_per_owner(self):
        """Test unique name constraint per owner."""
        user = UserFactory()
        GroupFactory(name='Unique Name', owner=user)

        # Same name with same owner should fail
        with pytest.raises(Exception):  # IntegrityError
            GroupFactory(name='Unique Name', owner=user)

    def test_same_name_different_owners(self):
        """Test same name allowed for different owners."""
        user1 = UserFactory()
        user2 = UserFactory()

        group1 = GroupFactory(name='Same Name', owner=user1)
        group2 = GroupFactory(name='Same Name', owner=user2)

        assert group1.name == group2.name
        assert group1.owner != group2.owner
