"""
URL patterns for import/export endpoints.
"""
from django.urls import path

from apps.imports.views import (
    ContactExportView,
    ContactImportView,
    ContactTemplateView,
    DonationExportView,
    DonationImportView,
    DonationTemplateView,
    FundImportView,
    FundTemplateView,
    ImportStatusView,
)

app_name = 'imports'

urlpatterns = [
    path('contacts/', ContactImportView.as_view(), name='import-contacts'),
    path('donations/', DonationImportView.as_view(), name='import-donations'),
    path('funds/', FundImportView.as_view(), name='import-funds'),
    path('export/contacts/', ContactExportView.as_view(), name='export-contacts'),
    path('export/donations/', DonationExportView.as_view(), name='export-donations'),
    path('templates/contacts/', ContactTemplateView.as_view(), name='template-contacts'),
    path('templates/donations/', DonationTemplateView.as_view(), name='template-donations'),
    path('templates/funds/', FundTemplateView.as_view(), name='template-funds'),
    path('status/<str:import_id>/', ImportStatusView.as_view(), name='import-status'),
]
