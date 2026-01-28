"""
Views for Group management.
"""
from django.db.models import Count, Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOwnerOrAdmin
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
        # Admins see all groups, others see own + shared groups
        if user.role == 'admin':
            queryset = Group.objects.all()
        else:
            queryset = Group.objects.filter(
                Q(owner=user) | Q(owner__isnull=True)
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
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            queryset = Group.objects.all()
        else:
            queryset = Group.objects.filter(
                Q(owner=user) | Q(owner__isnull=True)
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
    permission_classes = [permissions.IsAuthenticated]

    def get_group(self, pk):
        user = self.request.user
        try:
            if user.role == 'admin':
                return Group.objects.get(pk=pk)
            return Group.objects.get(
                Q(pk=pk) & (Q(owner=user) | Q(owner__isnull=True))
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

        from apps.contacts.serializers import ContactListSerializer
        contacts = group.contacts.all()
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

        contact_ids = request.data.get('contact_ids', [])
        if not contact_ids:
            return Response(
                {'detail': 'No contact_ids provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.contacts.models import Contact
        contacts = Contact.objects.filter(id__in=contact_ids, owner=request.user)
        group.contacts.add(*contacts)

        return Response({'detail': f'Added {contacts.count()} contacts to group.'})

    def delete(self, request, pk):
        """Remove contacts from group."""
        group = self.get_group(pk)
        if not group:
            return Response(
                {'detail': 'Group not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        contact_ids = request.data.get('contact_ids', [])
        if not contact_ids:
            return Response(
                {'detail': 'No contact_ids provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.contacts.models import Contact
        contacts = Contact.objects.filter(id__in=contact_ids)
        group.contacts.remove(*contacts)

        return Response({'detail': f'Removed contacts from group.'})


class GroupContactEmailsView(APIView):
    """
    GET: Return all email addresses for contacts in a group.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        try:
            if user.role == 'admin':
                group = Group.objects.get(pk=pk)
            else:
                group = Group.objects.get(
                    Q(pk=pk) & (Q(owner=user) | Q(owner__isnull=True))
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
