"""
Views for Donation management.
"""
from datetime import date, timedelta

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsContactOwnerOrReadAccess, IsFinanceOrAdmin
from apps.donations.models import Donation
from apps.donations.serializers import (
    DonationCreateSerializer,
    DonationSerializer,
    DonationSummarySerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=['donations'],
        summary='List donations',
        parameters=[
            OpenApiParameter(name='start_date', description='Filter by start date (YYYY-MM-DD)', type=str),
            OpenApiParameter(name='end_date', description='Filter by end date (YYYY-MM-DD)', type=str),
            OpenApiParameter(name='contact', description='Filter by contact ID', type=str),
        ]
    ),
    post=extend_schema(tags=['donations'], summary='Create donation')
)
class DonationListCreateView(generics.ListCreateAPIView):
    """
    GET: List donations
    POST: Create a new donation (admin/finance only)
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']
    filterset_fields = ['donation_type', 'payment_method', 'thanked']

    def get_permissions(self):
        # All authenticated users can create donations for their contacts
        # Finance/Admin can create for any contact
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        # Admin and Finance can see all donations
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Donation.objects.all()
        else:
            # Staffs see only donations to their contacts
            queryset = Donation.objects.filter(contact__owner=user)

        # Date range filter
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        # Contact filter
        contact_id = self.request.query_params.get('contact')
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)

        return queryset.select_related('contact', 'pledge')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DonationCreateSerializer
        return DonationSerializer


@extend_schema_view(
    get=extend_schema(tags=['donations'], summary='Get donation details'),
    put=extend_schema(tags=['donations'], summary='Update donation'),
    patch=extend_schema(tags=['donations'], summary='Partial update donation'),
    delete=extend_schema(tags=['donations'], summary='Delete donation')
)
class DonationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve donation details
    PATCH/PUT: Update donation (admin/finance only)
    DELETE: Delete donation (admin only)
    """
    serializer_class = DonationSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            from apps.core.permissions import IsAdmin
            return [permissions.IsAuthenticated(), IsAdmin()]
        if self.request.method in ['PATCH', 'PUT']:
            return [permissions.IsAuthenticated(), IsFinanceOrAdmin()]
        return [permissions.IsAuthenticated(), IsContactOwnerOrReadAccess()]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'finance', 'read_only']:
            return Donation.objects.all()
        return Donation.objects.filter(contact__owner=user)


class DonationThankView(APIView):
    """
    POST: Mark donation as thanked
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['donations'],
        summary='Mark donation as thanked',
        responses={200: {'type': 'object', 'properties': {'detail': {'type': 'string'}}}}
    )
    def post(self, request, pk):
        user = request.user
        try:
            if user.role == 'admin':
                donation = Donation.objects.get(pk=pk)
            else:
                donation = Donation.objects.get(pk=pk, contact__owner=user)
        except Donation.DoesNotExist:
            return Response(
                {'detail': 'Donation not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        donation.mark_thanked(user)

        # Update contact's thank-you status
        contact = donation.contact
        unthanked_count = contact.donations.filter(thanked=False).count()
        if unthanked_count == 0:
            contact.needs_thank_you = False
            contact.save(update_fields=['needs_thank_you'])

        return Response({'detail': 'Donation marked as thanked.'})


class DonationSummaryView(APIView):
    """
    GET: Get donation summary statistics
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['donations'],
        summary='Get donation summary statistics',
        parameters=[OpenApiParameter(name='days', description='Number of days to include (default: 30)', type=int)]
    )
    def get(self, request):
        user = request.user

        # Base queryset
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Donation.objects.all()
        else:
            queryset = Donation.objects.filter(contact__owner=user)

        # Date range
        days = int(request.query_params.get('days', 30))
        start_date = date.today() - timedelta(days=days)
        queryset = queryset.filter(date__gte=start_date)

        # Aggregate stats
        stats = queryset.aggregate(
            total_amount=Sum('amount'),
            donation_count=Count('id'),
            unique_donors=Count('contact', distinct=True),
            average_amount=Avg('amount')
        )

        return Response({
            'period': f'Last {days} days',
            'total_amount': stats['total_amount'] or 0,
            'donation_count': stats['donation_count'] or 0,
            'unique_donors': stats['unique_donors'] or 0,
            'average_amount': stats['average_amount'] or 0
        })


class DonationByMonthView(APIView):
    """
    GET: Get donations aggregated by month
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['donations'],
        summary='Get donations by month',
        parameters=[OpenApiParameter(name='months', description='Number of months to include (default: 12)', type=int)]
    )
    def get(self, request):
        user = request.user

        # Base queryset
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Donation.objects.all()
        else:
            queryset = Donation.objects.filter(contact__owner=user)

        # Number of months
        months = int(request.query_params.get('months', 12))
        start_date = date.today() - timedelta(days=months * 30)
        queryset = queryset.filter(date__gte=start_date)

        # Group by month
        monthly_data = queryset.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total_amount=Sum('amount'),
            donation_count=Count('id'),
            unique_donors=Count('contact', distinct=True)
        ).order_by('month')

        return Response(list(monthly_data))
