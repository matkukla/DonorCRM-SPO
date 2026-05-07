"""
Custom permission classes for role-based access control.

Access Control Matrix:
  admin       - Full CRUD on own resources by default; cross-user access via View As only
  missionary  - Full CRUD on own resources only
  supervisor  - Full CRUD on own resources only; cross-user access via View As only
  coach       - Read/write own data + read coached users' data (no financial data)

Owner scoping in views uses get_visible_user_ids() as the central choke point.
Write operations are gated by IsStaffOrAbove (excludes coach from writes).
"""
from rest_framework import permissions


def get_visible_user_ids(user, request=None):
    """Return set of user IDs whose data this user can see.

    When request.view_as_user is set (View As mode), always returns
    {view_as_user.id} regardless of viewer role. This is the data scoping
    choke point for the View As feature (Phase 52+).

    Roles that see only their own data (return {user.id}):
      - admin, supervisor, missionary

    Roles that see own + coached users (return {user.id} ∪ coached_user_ids):
      - coach

    Note: Admin and supervisor cross-user access activates only via View As
    session (Phase 52+). Admin analytics endpoints (get_dashboard_overview,
    get_stalled_contacts, etc.) do NOT call this function and are unaffected.
    """
    # View As override: scope to the target user regardless of viewer role.
    if request is not None:
        view_as_user = getattr(request, "view_as_user", None)
        if view_as_user is not None:
            return {view_as_user.id}

    if user.role == "coach":
        ids = set(user.coached_users.filter(is_active=True).values_list("id", flat=True))
        ids.add(user.id)
        return ids
    return {user.id}


def is_financial_role(user):
    """Returns True if user can see financial data. Coach is excluded."""
    return user.role in ["admin", "supervisor", "missionary"]


class IsAdmin(permissions.BasePermission):
    """
    Permission class that only allows Admin users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsStaffOrAbove(permissions.BasePermission):
    """
    Permission class that allows Missionary, Supervisor, or Admin users.
    Excludes coach users from write operations.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Coach users can only perform safe methods
        if request.user.role == "coach":
            return request.method in permissions.SAFE_METHODS

        return request.user.role in ["admin", "missionary", "supervisor"]


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object or admins.
    Assumes the model instance has an `owner` field.

    A null `owner` is treated as private (deny) by default. Models that
    intentionally allow shared/public records must opt-in by declaring
    ``shared_when_unowned = True`` on the model class. This prevents a
    silent broadening of access if a future model gains a nullable owner
    field without a permission audit.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if request.user.role == "admin":
            return True

        if not hasattr(obj, "owner"):
            return False

        if obj.owner is None:
            return bool(getattr(obj.__class__, "shared_when_unowned", False))

        return obj.owner == request.user


class IsContactOwnerOrReadAccess(permissions.BasePermission):
    """
    Permission for contact-related objects.
    - Owner has full access
    - Admin has full access
    - Supervisor/coach with visibility can read
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        user = request.user

        # Admin has full access
        if user.role == "admin":
            return True

        # Get the contact - either the object itself or via relation
        contact = None
        if hasattr(obj, "owner") and obj.__class__.__name__ == "Contact":
            contact = obj
        elif hasattr(obj, "contact"):
            contact = obj.contact

        # Owner has full access to their contacts
        if contact and contact.owner == user:
            return True

        return False


class IsSupervisorWriteRestricted(permissions.BasePermission):
    """
    Supervisor can read all visible data but only write to own data.
    Admin bypasses entirely. Staff can only write own data (enforced by queryset).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.role == "admin":
            return True
        # For write operations, object must belong to requesting user
        owner = getattr(obj, "owner", None)
        if owner is None:
            # Try common relation patterns
            contact = getattr(obj, "contact", None) or getattr(obj, "donor_contact", None)
            if contact:
                owner = getattr(contact, "owner", None)
        if owner is None:
            journal = getattr(obj, "journal", None)
            if journal:
                owner = getattr(journal, "owner", None)
        if owner is None:
            journal_contact = getattr(obj, "journal_contact", None)
            if journal_contact:
                journal = getattr(journal_contact, "journal", None)
                if journal:
                    owner = getattr(journal, "owner", None)
        return owner == request.user if owner else False
