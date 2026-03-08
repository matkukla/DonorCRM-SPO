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
        ).prefetch_related('supervisors', 'coaches').order_by('last_name', 'first_name')

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
                    'supervisor_ids': [str(s.id) for s in m.supervisors.all()],
                    'coach_ids': [str(c.id) for c in m.coaches.all()],
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
        warnings = []

        for item in assignments:
            missionary_id = item.get('missionary_id')
            supervisor_ids = item.get('supervisor_ids')  # list of uuid strs or null
            coach_ids = item.get('coach_ids')  # list of uuid strs or null
            additive = item.get('additive', False)

            try:
                missionary = User.objects.get(id=missionary_id, role='missionary')
            except User.DoesNotExist:
                errors.append({'missionary_id': missionary_id, 'error': 'Not found or not a missionary'})
                continue

            # Validate and assign supervisors
            if supervisor_ids is not None:
                valid_supervisors = list(
                    User.objects.filter(id__in=supervisor_ids, role='supervisor')
                )
                found_ids = {str(s.id) for s in valid_supervisors}
                invalid = [sid for sid in supervisor_ids if sid not in found_ids]
                if invalid:
                    errors.append({'missionary_id': missionary_id, 'error': f'Supervisor(s) not found or not supervisors: {invalid}'})
                    continue
                if additive:
                    missionary.supervisors.add(*valid_supervisors)
                else:
                    missionary.supervisors.set(valid_supervisors)

            # Validate and assign coaches
            if coach_ids is not None:
                valid_coaches = list(
                    User.objects.filter(id__in=coach_ids, role='coach')
                )
                found_ids = {str(c.id) for c in valid_coaches}
                invalid = [cid for cid in coach_ids if cid not in found_ids]
                if invalid:
                    errors.append({'missionary_id': missionary_id, 'error': f'Coach(es) not found or not coaches: {invalid}'})
                    continue
                if additive:
                    missionary.coaches.add(*valid_coaches)
                else:
                    missionary.coaches.set(valid_coaches)

            updated += 1
            # Soft warning: flag missionaries with 5+ supervisors
            if missionary.supervisors.count() >= 5:
                warnings.append({
                    'missionary_id': str(missionary.id),
                    'warning': 'Missionary has 5+ supervisors assigned',
                })

        return Response({'updated': updated, 'errors': errors, 'warnings': warnings})
