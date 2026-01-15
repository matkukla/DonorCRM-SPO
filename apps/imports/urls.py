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
)

app_name = 'imports'

urlpatterns = [
    path('contacts/', ContactImportView.as_view(), name='import-contacts'),
    path('donations/', DonationImportView.as_view(), name='import-donations'),
    path('export/contacts/', ContactExportView.as_view(), name='export-contacts'),
    path('export/donations/', DonationExportView.as_view(), name='export-donations'),
    path('templates/contacts/', ContactTemplateView.as_view(), name='template-contacts'),
    path('templates/donations/', DonationTemplateView.as_view(), name='template-donations'),
]
