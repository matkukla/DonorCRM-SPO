"""
URL patterns for user management endpoints.
"""
from django.urls import path

from apps.users.views import (
    CurrentUserView,
    PasswordChangeView,
    UserDetailView,
    UserListCreateView,
)

app_name = 'users'

urlpatterns = [
    path('', UserListCreateView.as_view(), name='user-list'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('me/password/', PasswordChangeView.as_view(), name='password-change'),
    path('<uuid:pk>/', UserDetailView.as_view(), name='user-detail'),
]
