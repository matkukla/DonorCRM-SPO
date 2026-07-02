"""
Views for user management.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.contacts.models import Contact
from apps.core.audit import audit_event
from apps.core.permissions import IsAdmin
from apps.core.throttling import FailOpenSimpleRateThrottle
from apps.groups.models import Group
from apps.journals.models import Journal
from apps.tasks.models import Task
from apps.users.models import User
from apps.users.serializers import (
    AdminPasswordResetSerializer,
    CurrentUserSerializer,
    PasswordChangeSerializer,
    UserAdminUpdateSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ViewableUserSerializer,
)


class _PasswordBurstThrottle(FailOpenSimpleRateThrottle):
    """Per-IP burst limit on password mutations (rate from
    THROTTLE_RATES['password'])."""

    scope = "password"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class _PasswordHourThrottle(FailOpenSimpleRateThrottle):
    """Per-IP hourly cap layered on top of the burst throttle so a slow
    attacker pacing under the burst rate still hits a daily ceiling
    (rate from THROTTLE_RATES['password_hour'])."""

    scope = "password_hour"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class UserListCreateView(generics.ListCreateAPIView):
    """
    GET: List all users (admin only)
    POST: Create a new user (admin only)
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return (
            User.objects.all()
            .prefetch_related("supervised_users", "coached_users")
            .order_by("-date_joined")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve user details (admin only)
    PATCH/PUT: Update user (admin only)
    DELETE: Deactivate user (admin only)
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return User.objects.all().prefetch_related("supervised_users", "coached_users")

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return UserAdminUpdateSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        """Deactivate user instead of deleting, and revoke their tokens."""
        user = self.get_object()
        user.is_active = False
        user.save()
        # Revoke the deactivated user's outstanding refresh tokens so a
        # departed or compromised account cannot mint new access tokens via
        # /auth/refresh/ — matching the password-change/reset paths (CWE-613).
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserReassignContactsView(APIView):
    """POST: Reassign a departing user's contacts, journals, tasks, and groups.

    Offboarding control (admin only): when a missionary departs, move their
    donor relationships to a successor instead of stranding them on an inactive
    account.

    Contacts, Journals, Tasks, and private Groups each carry their own ``owner``
    FK — the field every view scopes by (``get_visible_user_ids``) — so all four
    must be reassigned together; moving only Contact.owner would leave the
    departing user's donor pipeline history (Journal), open follow-up tasks
    (Task), and private tags/segments (Group) invisible to the successor
    (issue #185).

    Excluded by design: Gifts and prayers have no owner FK and genuinely follow
    their contact. Broadcast task copies are recipient-owned distributions
    (issue #184), not donor history. Org-wide Groups (``owner=None``) belong to
    no one and stay shared. Funds and import runs are finance/audit metadata, not
    per-user caseload data.

    Group carries a ``unique_group_name_per_owner`` constraint, so a private
    group whose name already exists among the successor's groups is skipped
    (left on the departing user) rather than crashing the transaction on an
    IntegrityError.

    The reassignment runs in a single transaction. The new owner must exist, be
    active, and differ from the current owner. Audit-logged.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        from_user = get_object_or_404(User, pk=pk)
        new_owner_id = request.data.get("new_owner_id")
        if not new_owner_id:
            return Response(
                {"detail": "new_owner_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            to_user = User.objects.get(pk=new_owner_id)
        except (User.DoesNotExist, ValidationError, ValueError, TypeError):
            return Response(
                {"detail": "new_owner_id is not a valid user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if to_user.pk == from_user.pk:
            return Response(
                {"detail": "new_owner must differ from the current owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not to_user.is_active:
            return Response(
                {"detail": "new_owner must be an active user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            count = Contact.objects.filter(owner=from_user).update(owner=to_user)
            journals_count = Journal.objects.filter(owner=from_user).update(owner=to_user)
            # Broadcast copies are recipient-owned distributions (issue #184),
            # not donor history that follows the contact — leave them behind.
            tasks_count = Task.objects.filter(owner=from_user, broadcast__isnull=True).update(
                owner=to_user
            )
            # Private groups follow their owner too, but unique_group_name_per_owner
            # would raise IntegrityError (rolling back the whole reassignment) if
            # the successor already has a same-named group. Skip those collisions;
            # the group stays on the departing user rather than blocking offboarding.
            successor_group_names = set(
                Group.objects.filter(owner=to_user).values_list("name", flat=True)
            )
            groups_count = (
                Group.objects.filter(owner=from_user)
                .exclude(name__in=successor_group_names)
                .update(owner=to_user)
            )
        audit_event(
            "contacts.reassigned",
            actor_id=str(request.user.id),
            from_user_id=str(from_user.id),
            to_user_id=str(to_user.id),
            count=count,
            journals_count=journals_count,
            tasks_count=tasks_count,
            groups_count=groups_count,
        )
        return Response(
            {
                "detail": "Contacts reassigned.",
                "reassigned": count,
                "journals_reassigned": journals_count,
                "tasks_reassigned": tasks_count,
                "groups_reassigned": groups_count,
                "from": str(from_user.id),
                "to": str(to_user.id),
            }
        )


class CurrentUserView(APIView):
    """
    GET: Get current user's profile
    PATCH: Update current user's profile
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.gifts.models import RecurringGiftStatus

        # Annotate user with counts to avoid N+1 queries
        user = (
            User.objects.filter(pk=request.user.pk)
            .annotate(
                _contact_count=Count("contacts", distinct=True),
                _active_pledge_count=Count(
                    "contacts__recurring_gifts",
                    filter=Q(contacts__recurring_gifts__status=RecurringGiftStatus.ACTIVE),
                    distinct=True,
                ),
            )
            .first()
        )

        serializer = CurrentUserSerializer(user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CurrentUserSerializer(request.user).data)


class PasswordChangeView(APIView):
    """
    POST: Change current user's password
    """

    permission_classes = [permissions.IsAuthenticated]
    # Two-tier throttle: per-IP burst (THROTTLE_RATES['password']) plus an
    # hourly cap (THROTTLE_RATES['password_hour']) to slow an attacker pacing
    # under the burst rate.
    throttle_classes = [_PasswordBurstThrottle, _PasswordHourThrottle]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Blacklist all outstanding refresh tokens for this user
        for token in OutstandingToken.objects.filter(user=request.user):
            BlacklistedToken.objects.get_or_create(token=token)
        return Response({"detail": "Password changed successfully."})


class AdminPasswordResetView(APIView):
    """
    POST: Admin resets another user's password (no old password required).
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    throttle_classes = [_PasswordBurstThrottle, _PasswordHourThrottle]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        # Revoke the target user's outstanding refresh tokens so the reset
        # invalidates any stolen token, matching the self-service password
        # change path (PRD fix #13 / CWE-613).
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        return Response({"detail": "Password reset successfully."})


class ViewableUsersView(APIView):
    """
    GET /api/users/viewable/
    Returns list of users the authenticated user can impersonate via View As.

    - Admin: all active missionaries and supervisors
    - Supervisor: only missionaries in their supervised_users M2M
    - All other roles: 403 Forbidden
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role == "admin":
            qs = (
                User.objects.filter(role__in=["missionary", "supervisor"], is_active=True)
                .exclude(id=user.id)
                .order_by("last_name", "first_name")
            )
        elif user.role == "supervisor":
            qs = user.supervised_users.filter(role="missionary", is_active=True).order_by(
                "last_name", "first_name"
            )
        else:
            return Response({"detail": "You do not have permission to view this list."}, status=403)

        return Response(ViewableUserSerializer(qs, many=True).data)
