"""
Views for user management.
"""
from django.db.models import Count, Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.core.permissions import IsAdmin
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


class UserListCreateView(generics.ListCreateAPIView):
    """
    GET: List all users (admin only)
    POST: Create a new user (admin only)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return User.objects.all().prefetch_related('supervised_users', 'coached_users').order_by('-date_joined')

    def get_serializer_class(self):
        if self.request.method == 'POST':
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
        return User.objects.all().prefetch_related('supervised_users', 'coached_users')

    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return UserAdminUpdateSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        """Deactivate user instead of deleting."""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    """
    GET: Get current user's profile
    PATCH: Update current user's profile
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.gifts.models import RecurringGiftStatus

        # Annotate user with counts to avoid N+1 queries
        user = User.objects.filter(pk=request.user.pk).annotate(
            _contact_count=Count('contacts', distinct=True),
            _active_pledge_count=Count(
                'contacts__recurring_gifts',
                filter=Q(contacts__recurring_gifts__status=RecurringGiftStatus.ACTIVE),
                distinct=True
            )
        ).first()

        serializer = CurrentUserSerializer(user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CurrentUserSerializer(request.user).data)


class PasswordChangeView(APIView):
    """
    POST: Change current user's password
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Blacklist all outstanding refresh tokens for this user
        for token in OutstandingToken.objects.filter(user=request.user):
            BlacklistedToken.objects.get_or_create(token=token)
        return Response({'detail': 'Password changed successfully.'})


class AdminPasswordResetView(APIView):
    """
    POST: Admin resets another user's password (no old password required).
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        # Blacklist all outstanding refresh tokens for the target user
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        return Response({'detail': 'Password reset successfully.'})


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

        if user.role == 'admin':
            qs = User.objects.filter(
                role__in=['missionary', 'supervisor'],
                is_active=True
            ).exclude(id=user.id).order_by('last_name', 'first_name')
        elif user.role == 'supervisor':
            qs = user.supervised_users.filter(
                role='missionary',
                is_active=True
            ).order_by('last_name', 'first_name')
        else:
            return Response(
                {'detail': 'You do not have permission to view this list.'},
                status=403
            )

        return Response(ViewableUserSerializer(qs, many=True).data)
