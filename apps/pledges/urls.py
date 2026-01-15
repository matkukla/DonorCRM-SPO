"""
URL patterns for pledges endpoints.
"""
from django.urls import path

from apps.pledges.views import (
    LatePledgesView,
    PledgeCancelView,
    PledgeDetailView,
    PledgeListCreateView,
    PledgePauseView,
    PledgeResumeView,
    PledgeSummaryView,
)

app_name = 'pledges'

urlpatterns = [
    path('', PledgeListCreateView.as_view(), name='pledge-list'),
    path('late/', LatePledgesView.as_view(), name='pledge-late'),
    path('summary/', PledgeSummaryView.as_view(), name='pledge-summary'),
    path('<uuid:pk>/', PledgeDetailView.as_view(), name='pledge-detail'),
    path('<uuid:pk>/pause/', PledgePauseView.as_view(), name='pledge-pause'),
    path('<uuid:pk>/resume/', PledgeResumeView.as_view(), name='pledge-resume'),
    path('<uuid:pk>/cancel/', PledgeCancelView.as_view(), name='pledge-cancel'),
]
