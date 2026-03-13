"""
API views for Goal tracking.
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.journals.models import Journal
from apps.users.goal_services import get_goal_progress
from apps.users.models import GoalJournalSelection


class GoalView(APIView):
    """
    GET  /api/v1/goals/me/  — Return current goal config and calculated effective monthly support.
    PATCH /api/v1/goals/me/ — Update goal amount, goal weeks, and/or journal selections.

    Always scoped to request.user — no cross-user access.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = get_goal_progress(request.user)
        return Response(data)

    def patch(self, request):
        user = request.user
        data = request.data
        update_fields = ['updated_at']

        if 'monthly_support_goal_cents' in data:
            user.monthly_support_goal_cents = int(data['monthly_support_goal_cents'])
            update_fields.append('monthly_support_goal_cents')

        if 'goal_weeks' in data:
            user.goal_weeks = int(data['goal_weeks'])
            update_fields.append('goal_weeks')

        if update_fields != ['updated_at']:
            user.save(update_fields=update_fields)

        if 'journal_ids' in data:
            # Validate journals belong to the requesting user (no cross-user journal selection)
            journal_ids = data['journal_ids']
            valid_journals = Journal.objects.filter(id__in=journal_ids, owner=user)
            # Replace-all semantics: delete then bulk create
            GoalJournalSelection.objects.filter(user=user).delete()
            GoalJournalSelection.objects.bulk_create([
                GoalJournalSelection(user=user, journal=j)
                for j in valid_journals
            ])

        return Response(get_goal_progress(user))
