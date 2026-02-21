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
    EntityImportView,
    EntityTemplateView,
    FundImportView,
    FundListView,
    FundTemplateView,
    ImportRunErrorsCSVView,
    ImportStatusView,
    LatestImportRunsView,
    MPDImportView,
    MPDMyDataView,
    MPDOverviewView,
    MPDUploadHistoryView,
    PledgeImportView,
    PledgeTemplateView,
    RESolicitorImportView,
    TransactionImportView,
    TransactionTemplateView,
)

app_name = 'imports'

urlpatterns = [
    path('contacts/', ContactImportView.as_view(), name='import-contacts'),
    path('donations/', DonationImportView.as_view(), name='import-donations'),
    path('entities/', EntityImportView.as_view(), name='import-entities'),
    path('funds/', FundImportView.as_view(), name='import-funds'),
    path('funds/list/', FundListView.as_view(), name='fund-list'),
    path('mpd/', MPDImportView.as_view(), name='import-mpd'),
    path('mpd/overview/', MPDOverviewView.as_view(), name='mpd-overview'),
    path('mpd/me/', MPDMyDataView.as_view(), name='mpd-my-data'),
    path('mpd/uploads/', MPDUploadHistoryView.as_view(), name='mpd-upload-history'),
    path('re/solicitors/', RESolicitorImportView.as_view(), name='import-re-solicitors'),
    path('pledges/', PledgeImportView.as_view(), name='import-pledges'),
    path('transactions/', TransactionImportView.as_view(), name='import-transactions'),
    path('export/contacts/', ContactExportView.as_view(), name='export-contacts'),
    path('export/donations/', DonationExportView.as_view(), name='export-donations'),
    path('templates/contacts/', ContactTemplateView.as_view(), name='template-contacts'),
    path('templates/donations/', DonationTemplateView.as_view(), name='template-donations'),
    path('templates/entities/', EntityTemplateView.as_view(), name='template-entities'),
    path('templates/funds/', FundTemplateView.as_view(), name='template-funds'),
    path('templates/pledges/', PledgeTemplateView.as_view(), name='template-pledges'),
    path('templates/transactions/', TransactionTemplateView.as_view(), name='template-transactions'),
    path('runs/latest/', LatestImportRunsView.as_view(), name='latest-import-runs'),
    path('runs/<uuid:import_run_id>/errors/csv/', ImportRunErrorsCSVView.as_view(), name='import-run-errors-csv'),
    path('status/<str:import_id>/', ImportStatusView.as_view(), name='import-status'),
]
