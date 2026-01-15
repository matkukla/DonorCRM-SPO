"""
Celery tasks for pledge management.
"""
from celery import shared_task


@shared_task
def check_late_pledges():
    """
    Check all active pledges for late payments.
    Run daily.
    """
    from apps.pledges.models import Pledge, PledgeStatus

    active_pledges = Pledge.objects.filter(status=PledgeStatus.ACTIVE)

    late_count = 0
    for pledge in active_pledges:
        was_late = pledge.is_late
        pledge.check_late_status()

        if pledge.is_late and not was_late:
            # Pledge just became late - create event
            late_count += 1
            pledge.save()

            # Create event notification
            from apps.events.services import create_pledge_late_event
            create_pledge_late_event(pledge)

    return f'Checked {active_pledges.count()} pledges, {late_count} newly late'
