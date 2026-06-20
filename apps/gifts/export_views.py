"""
CSV export views for Gift and RecurringGift with FilterSet-based filtering.
"""

from datetime import datetime

from django.http import HttpResponseForbidden, StreamingHttpResponse

from rest_framework import permissions
from rest_framework.views import APIView

from apps.core.csv_export import safe_csv_stream
from apps.core.permissions import get_visible_user_ids
from apps.gifts.filters import GiftFilterSet, RecurringGiftFilterSet
from apps.gifts.models import Gift, RecurringGift
from apps.imports.services import sanitize_csv_value


class GiftExportCSVView(APIView):
    """
    GET: Export gifts as filtered CSV file.
    Applies the same GiftFilterSet as the list endpoint.
    """

    permission_classes = [permissions.IsAuthenticated]
    # Rate-limit bulk exports so a stolen token cannot pull the donor base
    # repeatedly (issue #119). Matches the legacy imports/views.py exporters.
    throttle_scope = "export"

    def get(self, request):
        if request.user.role == "coach":
            return HttpResponseForbidden("Coaches cannot access financial exports")

        user = request.user

        # Same owner-scoping as GiftListCreateView. Cross-user access is
        # reached only via View As (X-View-As-User-Id -> get_visible_user_ids),
        # never a ?owner= query param.
        visible = get_visible_user_ids(user, request=request)
        queryset = Gift.objects.filter(donor_contact__owner_id__in=visible)

        # Apply FilterSet (same as list endpoint)
        filterset = GiftFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related("donor_contact", "fund")[:10000]

        filename = f"donations_{datetime.now().date().isoformat()}.csv"

        def generate_rows(writer):
            # Header
            yield writer.writerow(
                [
                    "Donor Name",
                    "Amount",
                    "Date",
                    "Payment Type",
                    "Fund",
                    "Description",
                ]
            )

            # Data rows
            for gift in filtered_qs:
                yield writer.writerow(
                    [
                        sanitize_csv_value(gift.donor_contact.full_name),
                        f"{gift.amount_dollars:.2f}",
                        gift.gift_date.isoformat(),
                        gift.get_payment_type_display() or "",
                        sanitize_csv_value(gift.fund.name if gift.fund else ""),
                        sanitize_csv_value(gift.description or ""),
                    ]
                )

        response = StreamingHttpResponse(
            safe_csv_stream(generate_rows, export_name="gifts"), content_type="text/csv"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class RecurringGiftExportCSVView(APIView):
    """
    GET: Export recurring gifts as filtered CSV file.
    Applies the same RecurringGiftFilterSet as the list endpoint.
    """

    permission_classes = [permissions.IsAuthenticated]
    # Rate-limit bulk exports so a stolen token cannot pull the donor base
    # repeatedly (issue #119). Matches the legacy imports/views.py exporters.
    throttle_scope = "export"

    def get(self, request):
        if request.user.role == "coach":
            return HttpResponseForbidden("Coaches cannot access financial exports")

        user = request.user

        # Same owner-scoping as RecurringGiftListCreateView. Cross-user access
        # is reached only via View As (X-View-As-User-Id -> get_visible_user_ids),
        # never a ?owner= query param.
        visible = get_visible_user_ids(user, request=request)
        queryset = RecurringGift.objects.filter(donor_contact__owner_id__in=visible)

        # Apply FilterSet (same as list endpoint)
        filterset = RecurringGiftFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related("donor_contact", "fund")[:10000]

        filename = f"pledges_{datetime.now().date().isoformat()}.csv"

        def generate_rows(writer):
            # Header
            yield writer.writerow(
                [
                    "Donor Name",
                    "Amount",
                    "Frequency",
                    "Status",
                    "Start Date",
                    "Fund",
                ]
            )

            # Data rows
            for rg in filtered_qs:
                yield writer.writerow(
                    [
                        sanitize_csv_value(rg.donor_contact.full_name),
                        f"{rg.amount_dollars:.2f}",
                        rg.frequency,
                        rg.status,
                        rg.start_date.isoformat(),
                        sanitize_csv_value(rg.fund.name if rg.fund else ""),
                    ]
                )

        response = StreamingHttpResponse(
            safe_csv_stream(generate_rows, export_name="recurring_gifts"),
            content_type="text/csv",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
