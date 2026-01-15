"""
Factories for User model tests.
"""
import factory
from faker import Faker

from apps.users.models import User, UserRole

fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    email = factory.LazyFunction(fake.email)
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)
    phone = factory.LazyFunction(lambda: fake.numerify('###-###-####'))
    role = UserRole.FUNDRAISER
    monthly_goal = factory.LazyFunction(lambda: fake.pydecimal(min_value=1000, max_value=10000, right_digits=2))
    is_active = True
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


class AdminUserFactory(UserFactory):
    """Factory for creating Admin users."""
    role = UserRole.ADMIN
    is_staff = True


class FinanceUserFactory(UserFactory):
    """Factory for creating Finance users."""
    role = UserRole.FINANCE


class ReadOnlyUserFactory(UserFactory):
    """Factory for creating Read-Only users."""
    role = UserRole.READ_ONLY
