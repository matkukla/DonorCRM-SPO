"""
Assignments API for admin to manage missionary-supervisor-coach relationships.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.core.permissions import IsAdmin
from apps.users.models import User


class AssignmentsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        missionaries = User.objects.filter(
            role='missionary', is_active=True
        ).select_related('supervisor', 'coach').order_by('last_name', 'first_name')

        supervisors = User.objects.filter(
            role='supervisor', is_active=True
        ).order_by('last_name', 'first_name')

        coaches = User.objects.filter(
            role='coach', is_active=True
        ).order_by('last_name', 'first_name')

        def person(u):
            return {'id': str(u.id), 'first_name': u.first_name,
                    'last_name': u.last_name, 'email': u.email}

        return Response({
            'missionaries': [
                {
                    'id': str(m.id),
                    'email': m.email,
                    'full_name': m.full_name,
                    'supervisor_id': str(m.supervisor_id) if m.supervisor_id else None,
                    'coach_id': str(m.coach_id) if m.coach_id else None,
                }
                for m in missionaries
            ],
            'supervisors': [person(u) for u in supervisors],
            'coaches': [person(u) for u in coaches],
        })

    def patch(self, request):
        assignments = request.data.get('assignments', [])
        if not isinstance(assignments, list):
            return Response({'detail': 'assignments must be a list'}, status=400)

        updated = 0
        errors = []

        for item in assignments:
            missionary_id = item.get('missionary_id')
            supervisor_id = item.get('supervisor_id')  # uuid str or null
            coach_id = item.get('coach_id')  # uuid str or null

            try:
                missionary = User.objects.get(id=missionary_id, role='missionary')
            except User.DoesNotExist:
                errors.append({'missionary_id': missionary_id, 'error': 'Not found or not a missionary'})
                continue

            # Validate supervisor
            if supervisor_id is not None:
                try:
                    supervisor = User.objects.get(id=supervisor_id, role='supervisor')
                    missionary.supervisor = supervisor
                except User.DoesNotExist:
                    errors.append({'missionary_id': missionary_id, 'error': f'Supervisor {supervisor_id} not found or not a supervisor'})
                    continue
            else:
                missionary.supervisor = None

            # Validate coach
            if coach_id is not None:
                try:
                    coach = User.objects.get(id=coach_id, role='coach')
                    missionary.coach = coach
                except User.DoesNotExist:
                    errors.append({'missionary_id': missionary_id, 'error': f'Coach {coach_id} not found or not a coach'})
                    continue
            else:
                missionary.coach = None

            missionary.save(update_fields=['supervisor', 'coach'])
            updated += 1

        return Response({'updated': updated, 'errors': errors})
