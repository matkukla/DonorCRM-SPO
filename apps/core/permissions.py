"""
Custom permission classes for role-based access control.

Access Control Matrix:
  admin       - Full access to all resources (all CRUD, all users' data)
  finance     - Read access to all resources; write access to own data only
  missionary  - Full CRUD on own resources only
  read_only   - Read access to own resources only (safe HTTP methods)
  supervisor  - Read/write own data + read supervised missionaries' data
  coach       - Read/write own data + read coached users' data (no financial data)

Owner scoping in views uses two patterns:
  - Multi-role check: role in ['admin', 'finance', 'read_only'] -> see all
  - Single-role check: role == 'admin' -> see all (admin-only endpoints)
Write operations are gated by IsStaffOrAbove (excludes read_only and coach).
"""
from rest_framework import permissions


def get_visible_user_ids(user):
    """Return set of user IDs whose data this user can see, or None for 'all'.

    - Admin/Finance/ReadOnly: returns None (sentinel for 'all users')
    - Supervisor: returns {own_id} union {supervised user IDs}
    - Coach: returns {own_id} union {coached user IDs}
    - Missionary: returns {own_id}
    """
    if user.role in ['admin', 'finance', 'read_only']:
        return None
    if user.role == 'supervisor':
        ids = set(
            user.supervised_users
            .filter(is_active=True)
            .values_list('id', flat=True)
        )
        ids.add(user.id)
        return ids
    if user.role == 'coach':
        ids = set(
            user.coached_users
            .filter(is_active=True)
            .values_list('id', flat=True)
        )
        ids.add(user.id)
        return ids
    return {user.id}


def is_financial_role(user):
    """Returns True if user can see financial data. Coach is excluded."""
    return user.role in ['admin', 'finance', 'read_only', 'supervisor', 'missionary']


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
    Permission class that allows Missionary, Finance, Supervisor, or Admin users.
    Excludes read-only and coach users from write operations.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Read-only users can only perform safe methods
        if request.user.role == 'read_only':
            return request.method in permissions.SAFE_METHODS

        return request.user.role in ['admin', 'finance', 'missionary', 'supervisor']


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


class IsSupervisorWriteRestricted(permissions.BasePermission):
    """
    Supervisor can read all visible data but only write to own data.
    Admin bypasses entirely. Staff can only write own data (enforced by queryset).
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.role == 'admin':
            return True
        # For write operations, object must belong to requesting user
        owner = getattr(obj, 'owner', None)
        if owner is None:
            # Try common relation patterns
            contact = getattr(obj, 'contact', None) or getattr(obj, 'donor_contact', None)
            if contact:
                owner = getattr(contact, 'owner', None)
        if owner is None:
            journal = getattr(obj, 'journal', None)
            if journal:
                owner = getattr(journal, 'owner', None)
        return owner == request.user if owner else True
