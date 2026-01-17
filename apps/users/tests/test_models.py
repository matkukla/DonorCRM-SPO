"""
Tests for User model.
"""
import pytest
from django.db import IntegrityError

from apps.users.models import User, UserRole
from apps.users.tests.factories import AdminUserFactory, UserFactory


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model."""

    def test_create_user(self):
        """Test creating a regular user."""
        user = UserFactory()
        assert user.id is not None
        assert user.email is not None
        assert user.role == UserRole.STAFF
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_admin_user(self):
        """Test creating an admin user."""
        user = AdminUserFactory()
        assert user.role == UserRole.ADMIN
        assert user.is_admin is True
        assert user.is_staff is True

    def test_full_name_property(self):
        """Test full_name property."""
        user = UserFactory(first_name='John', last_name='Doe')
        assert user.full_name == 'John Doe'

    def test_email_unique(self):
        """Test that email must be unique."""
        UserFactory(email='test@example.com')
        with pytest.raises(IntegrityError):
            UserFactory(email='test@example.com')

    def test_role_properties(self):
        """Test role checking properties."""
        staff = UserFactory(role=UserRole.STAFF)
        admin = UserFactory(role=UserRole.ADMIN)
        finance = UserFactory(role=UserRole.FINANCE)
        readonly = UserFactory(role=UserRole.READ_ONLY)

        assert staff.is_staff_role is True
        assert staff.is_admin is False

        assert admin.is_admin is True
        assert admin.is_staff_role is False

        assert finance.is_finance is True
        assert readonly.is_read_only is True

    def test_user_str(self):
        """Test string representation."""
        user = UserFactory(first_name='Jane', last_name='Smith', email='jane@example.com')
        assert str(user) == 'Jane Smith (jane@example.com)'


@pytest.mark.django_db
class TestUserManager:
    """Tests for User manager."""

    def test_create_user(self):
        """Test creating user via manager."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_superuser(self):
        """Test creating superuser via manager."""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == UserRole.ADMIN

    def test_create_user_without_email_raises(self):
        """Test that creating user without email raises error."""
        with pytest.raises(ValueError):
            User.objects.create_user(
                email='',
                password='testpass123',
                first_name='Test',
                last_name='User'
            )

    def test_get_by_natural_key_case_insensitive(self):
        """Test email lookup is case-insensitive."""
        UserFactory(email='Test@Example.com')
        user = User.objects.get_by_natural_key('test@example.com')
        assert user.email == 'Test@Example.com'
