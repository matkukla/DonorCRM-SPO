"""
Views for Group management.
"""
from django.db.models import Count, Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contacts.models import Contact
from apps.contacts.serializers import ContactListSerializer
from apps.core.permissions import IsOwnerOrAdmin, IsStaffOrAbove, IsSupervisorWriteRestricted, get_visible_user_ids
from apps.groups.models import Group
from apps.groups.serializers import GroupCreateSerializer, GroupSerializer


class GroupListCreateView(generics.ListCreateAPIView):
    """
    GET: List groups (own groups + shared groups)
    POST: Create a new group (private to user)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        visible = get_visible_user_ids(user, request=self.request)
        queryset = Group.objects.filter(
            Q(owner_id__in=visible) | Q(owner__isnull=True)
        )
        return queryset.annotate(
            annotated_contact_count=Count('contacts')
        ).order_by('name')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return GroupCreateSerializer
        return GroupSerializer


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve group details
    PATCH/PUT: Update group
    DELETE: Delete group (if not system group)
    """
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin, IsSupervisorWriteRestricted]

    def get_queryset(self):
        user = self.request.user
        visible = get_visible_user_ids(user, request=self.request)
        queryset = Group.objects.filter(
            Q(owner_id__in=visible) | Q(owner__isnull=True)
        )
        return queryset.annotate(
            annotated_contact_count=Count('contacts')
        )

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        if group.is_system:
            return Response(
                {'detail': 'System groups cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class GroupContactsView(APIView):
    """
    GET: List contacts in a group
    POST: Add contacts to group
    DELETE: Remove contacts from group
    """

    def get_permissions(self):
        # IsStaffOrAbove blocks coaches on writes. Object-level scoping is
        # enforced inside get_group() since APIView doesn't auto-run
        # has_object_permission; IsOwnerOrAdmin would be a no-op here.
        if self.request.method not in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated(), IsStaffOrAbove()]
        return [permissions.IsAuthenticated()]

    def get_group(self, pk):
        user = self.request.user
        visible = get_visible_user_ids(user, request=self.request)
        try:
            return Group.objects.get(
                Q(pk=pk) & (Q(owner_id__in=visible) | Q(owner__isnull=True))
            )
        except Group.DoesNotExist:
            return None

    def get(self, request, pk):
        group = self.get_group(pk)
        if not group:
            return Response(
                {'detail': 'Group not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        contacts = group.contacts.filter(is_merged=False).select_related('owner')
        serializer = ContactListSerializer(contacts, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        """Add contacts to group."""
        group = self.get_group(pk)
        if not group:
            return Response(
                {'detail': 'Group not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if group.is_system:
            return Response(
                {'detail': 'Cannot modify membership of system groups.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contact_ids = request.data.get('contact_ids', [])
        if not contact_ids:
            return Response(
                {'detail': 'No contact_ids provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contacts = Contact.objects.filter(id__in=contact_ids, owner=request.user, is_merged=False)

        added_count = contacts.count()
        if added_count == 0:
            return Response(
                {'detail': 'None of the requested contacts were visible to you.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        group.contacts.add(*contacts)
        return Response({'detail': f'Added {added_count} contacts to group.'})

    def delete(self, request, pk):
        """Remove contacts from group."""
        group = self.get_group(pk)
        if not group:
            return Response(
                {'detail': 'Group not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if group.is_system:
            return Response(
                {'detail': 'Cannot modify membership of system groups.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contact_ids = request.data.get('contact_ids', [])
        if not contact_ids:
            return Response(
                {'detail': 'No contact_ids provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        visible = get_visible_user_ids(request.user, request=request)
        if visible is None:
            contacts = Contact.objects.filter(id__in=contact_ids)
        else:
            contacts = Contact.objects.filter(id__in=contact_ids, owner_id__in=visible)
        group.contacts.remove(*contacts)

        return Response({'detail': f'Removed contacts from group.'})


class GroupContactEmailsView(APIView):
    """
    GET: Return all email addresses for contacts in a group.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        visible = get_visible_user_ids(user, request=request)
        try:
            group = Group.objects.get(
                Q(pk=pk) & (Q(owner_id__in=visible) | Q(owner__isnull=True))
            )
        except Group.DoesNotExist:
            return Response(
                {'detail': 'Group not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        emails = list(
            group.contacts.exclude(email__isnull=True).exclude(email='')
            .values_list('email', flat=True)
            .order_by('email')
        )
        return Response({'emails': emails, 'count': len(emails)})
