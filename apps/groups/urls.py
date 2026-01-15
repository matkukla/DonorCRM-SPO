"""
URL patterns for groups endpoints.
"""
from django.urls import path

from apps.groups.views import GroupContactsView, GroupDetailView, GroupListCreateView

app_name = 'groups'

urlpatterns = [
    path('', GroupListCreateView.as_view(), name='group-list'),
    path('<uuid:pk>/', GroupDetailView.as_view(), name='group-detail'),
    path('<uuid:pk>/contacts/', GroupContactsView.as_view(), name='group-contacts'),
]
