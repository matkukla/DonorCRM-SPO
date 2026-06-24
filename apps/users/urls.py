"""
URL patterns for user management endpoints.
"""

from django.urls import path

from apps.users.views import (
    AdminPasswordResetView,
    CurrentUserView,
    PasswordChangeView,
    UserDetailView,
    UserListCreateView,
    UserReassignContactsView,
    ViewableUsersView,
)
from apps.users.views_assignments import AssignmentsView

app_name = "users"

urlpatterns = [
    path("", UserListCreateView.as_view(), name="user-list"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("me/password/", PasswordChangeView.as_view(), name="password-change"),
    path("admin/assignments/", AssignmentsView.as_view(), name="user-assignments"),
    path("viewable/", ViewableUsersView.as_view(), name="user-viewable"),
    path("<uuid:pk>/password/", AdminPasswordResetView.as_view(), name="admin-password-reset"),
    path(
        "<uuid:pk>/reassign-contacts/",
        UserReassignContactsView.as_view(),
        name="user-reassign-contacts",
    ),
    path("<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
]
