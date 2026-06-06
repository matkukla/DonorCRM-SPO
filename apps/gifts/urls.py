"""
URL patterns for gift endpoints.
"""

from django.urls import path

from apps.gifts.export_views import GiftExportCSVView, RecurringGiftExportCSVView
from apps.gifts.views import (
    GiftDetailView,
    GiftListCreateView,
    RecurringGiftDetailView,
    RecurringGiftListCreateView,
)

app_name = "gifts"

urlpatterns = [
    path("", GiftListCreateView.as_view(), name="gift-list"),
    path("export/csv/", GiftExportCSVView.as_view(), name="gift-export-csv"),
    path("<uuid:pk>/", GiftDetailView.as_view(), name="gift-detail"),
    path("recurring/", RecurringGiftListCreateView.as_view(), name="recurring-gift-list"),
    path(
        "recurring/export/csv/",
        RecurringGiftExportCSVView.as_view(),
        name="recurring-gift-export-csv",
    ),
    path("recurring/<uuid:pk>/", RecurringGiftDetailView.as_view(), name="recurring-gift-detail"),
]
