"""
Tests for User API views.
"""
import pytest
from rest_framework import status

from apps.users.models import UserRole
from apps.users.tests.factories import AdminUserFactory, UserFactory


@pytest.mark.django_db
class TestCurrentUserView:
    """Tests for current user endpoint."""

    def test_get_current_user(self, authenticated_client):
        """Test getting current user profile."""
        client, user = authenticated_client
        response = client.get('/api/v1/users/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['first_name'] == user.first_name

    def test_update_current_user(self, authenticated_client):
        """Test updating current user profile."""
        client, user = authenticated_client
        response = client.patch('/api/v1/users/me/', {
            'first_name': 'Updated',
            'phone': '555-1234'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'
        assert response.data['phone'] == '555-1234'

    def test_unauthenticated_denied(self, api_client):
        """Test unauthenticated access is denied."""
        response = api_client.get('/api/v1/users/me/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserListView:
    """Tests for user list endpoint (admin only)."""

    def test_admin_can_list_users(self, admin_client):
        """Test admin can list all users."""
        client, admin = admin_client
        UserFactory.create_batch(5)

        response = client.get('/api/v1/users/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 5

    def test_staff_cannot_list_users(self, authenticated_client):
        """Test staff cannot list users."""
        client, user = authenticated_client
        response = client.get('/api/v1/users/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_user(self, admin_client):
        """Test admin can create a new user."""
        client, admin = admin_client
        response = client.post('/api/v1/users/', {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'securePass123!',
            'password_confirm': 'securePass123!',
            'role': 'staff'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'newuser@example.com'


@pytest.mark.django_db
class TestPasswordChange:
    """Tests for password change endpoint."""

    def test_change_password(self, api_client, user_factory):
        """Test changing password with correct old password."""
        user = user_factory()
        user.set_password('oldpass123')
        user.save()
        api_client.force_authenticate(user=user)

        response = api_client.post('/api/v1/users/me/password/', {
            'old_password': 'oldpass123',
            'new_password': 'newSecurePass123!',
            'new_password_confirm': 'newSecurePass123!'
        })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password('newSecurePass123!')

    def test_change_password_wrong_old_password(self, authenticated_client):
        """Test changing password with wrong old password fails."""
        client, user = authenticated_client

        response = client.post('/api/v1/users/me/password/', {
            'old_password': 'wrongpassword',
            'new_password': 'newSecurePass123!',
            'new_password_confirm': 'newSecurePass123!'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_login(self, api_client, user_factory):
        """Test login with correct credentials."""
        user = user_factory(email='login@test.com')
        user.set_password('testpass123')
        user.save()

        response = api_client.post('/api/v1/auth/login/', {
            'email': 'login@test.com',
            'password': 'testpass123'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_wrong_password(self, api_client, user_factory):
        """Test login with wrong password fails."""
        user = user_factory(email='wrong@test.com')

        response = api_client.post('/api/v1/auth/login/', {
            'email': 'wrong@test.com',
            'password': 'wrongpassword'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self, api_client, user_factory):
        """Test refreshing access token."""
        user = user_factory(email='refresh@test.com')
        user.set_password('testpass123')
        user.save()

        # First login
        login_response = api_client.post('/api/v1/auth/login/', {
            'email': 'refresh@test.com',
            'password': 'testpass123'
        })
        refresh_token = login_response.data['refresh']

        # Refresh token
        response = api_client.post('/api/v1/auth/refresh/', {
            'refresh': refresh_token
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
