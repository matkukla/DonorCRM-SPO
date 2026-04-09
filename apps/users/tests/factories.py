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
    role = UserRole.MISSIONARY
    monthly_support_goal_cents = factory.LazyFunction(lambda: fake.random_int(min=100000, max=1000000))
    goal_weeks = 52
    is_active = True
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


class AdminUserFactory(UserFactory):
    """Factory for creating Admin users."""
    role = UserRole.ADMIN
    is_staff = True


class SupervisorUserFactory(UserFactory):
    """Factory for creating Supervisor users."""
    role = UserRole.SUPERVISOR
    email = factory.Sequence(lambda n: f"supervisor{n}@example.com")


class CoachUserFactory(UserFactory):
    """Factory for creating Coach users."""
    role = UserRole.COACH
    email = factory.Sequence(lambda n: f"coach{n}@example.com")
