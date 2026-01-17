"""
Custom permission classes for role-based access control.
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Permission class that only allows Admin users.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsFinanceOrAdmin(permissions.BasePermission):
    """
    Permission class that allows Finance or Admin users.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['admin', 'finance']
        )


class IsStaffOrAbove(permissions.BasePermission):
    """
    Permission class that allows Staff, Finance, or Admin users.
    Excludes read-only users from write operations.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Read-only users can only perform safe methods
        if request.user.role == 'read_only':
            return request.method in permissions.SAFE_METHODS

        return request.user.role in ['admin', 'finance', 'staff']


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object or admins.
    Assumes the model instance has an `owner` field.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Admin has full access
        if request.user.role == 'admin':
            return True

        # Check for 'owner' field on object
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        return False


class IsContactOwnerOrReadAccess(permissions.BasePermission):
    """
    Permission for contact-related objects.
    - Owner has full access
    - Admin has full access
    - Finance has read-only access
    - Read-only has read-only access
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        user = request.user

        # Admin has full access
        if user.role == 'admin':
            return True

        # Get the contact - either the object itself or via relation
        contact = None
        if hasattr(obj, 'owner') and obj.__class__.__name__ == 'Contact':
            contact = obj
        elif hasattr(obj, 'contact'):
            contact = obj.contact

        # Owner has full access to their contacts
        if contact and contact.owner == user:
            return True

        # Finance and read-only can only read
        if user.role in ['finance', 'read_only']:
            return request.method in permissions.SAFE_METHODS

        return False


class ReadOnlyOrAdmin(permissions.BasePermission):
    """
    Read-only access for most users, full access for Admin.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.role == 'admin':
            return True

        return request.method in permissions.SAFE_METHODS
