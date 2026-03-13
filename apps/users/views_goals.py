"""
API views for Goal tracking.
"""
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db import transaction

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
            try:
                value = int(data['monthly_support_goal_cents'])
            except (TypeError, ValueError):
                return Response({'error': 'monthly_support_goal_cents must be a non-negative integer'}, status=400)
            if value < 0:
                return Response({'error': 'monthly_support_goal_cents must be a non-negative integer'}, status=400)
            user.monthly_support_goal_cents = value
            update_fields.append('monthly_support_goal_cents')

        if 'goal_weeks' in data:
            try:
                value = int(data['goal_weeks'])
            except (TypeError, ValueError):
                return Response({'error': 'goal_weeks must be a positive integer'}, status=400)
            if value <= 0:
                return Response({'error': 'goal_weeks must be a positive integer'}, status=400)
            user.goal_weeks = value
            update_fields.append('goal_weeks')

        if update_fields != ['updated_at']:
            user.save(update_fields=update_fields)

        if 'journal_ids' in data:
            journal_ids = data['journal_ids']
            if not isinstance(journal_ids, list):
                return Response({'error': 'journal_ids must be a list'}, status=400)
            # Validate journals belong to the requesting user (no cross-user journal selection)
            try:
                valid_journals = list(Journal.objects.filter(id__in=journal_ids, owner=user))
            except Exception:
                return Response({'error': 'journal_ids contains invalid values'}, status=400)
            valid_journal_ids = {str(j.id) for j in valid_journals}
            submitted_ids = {str(jid) for jid in journal_ids}
            invalid_ids = submitted_ids - valid_journal_ids
            if invalid_ids:
                return Response({'error': f'Invalid or inaccessible journal_ids: {sorted(invalid_ids)}'}, status=400)
            # Replace-all semantics: delete then bulk create (atomic to prevent partial state)
            with transaction.atomic():
                GoalJournalSelection.objects.filter(user=user).delete()
                GoalJournalSelection.objects.bulk_create([
                    GoalJournalSelection(user=user, journal=j)
                    for j in valid_journals
                ])

        return Response(get_goal_progress(user))
