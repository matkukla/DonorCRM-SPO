"""
Factories for Group model tests.
"""
import factory
from faker import Faker

from apps.groups.models import Group
from apps.users.tests.factories import UserFactory

fake = Faker()


class GroupFactory(factory.django.DjangoModelFactory):
    """Factory for creating Group instances."""

    class Meta:
        model = Group

    name = factory.LazyFunction(lambda: fake.word().title() + ' Group')
    description = factory.LazyFunction(fake.sentence)
    color = factory.LazyFunction(fake.hex_color)
    owner = factory.SubFactory(UserFactory)
    is_system = False


class SharedGroupFactory(GroupFactory):
    """Factory for organization-wide shared groups."""
    owner = None


class SystemGroupFactory(GroupFactory):
    """Factory for system-managed groups."""
    is_system = True
