"""
Custom permission classes for feedback endpoints.
"""

from rest_framework import permissions


class IsAdminOrCreateOnly(permissions.BasePermission):
    """
    Allow any authenticated user to POST a feedback entry; restrict all other
    methods to admin users.
    """

    def has_permission(self, request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        if request.method == "POST":
            return True
        return request.user.role == "admin"
