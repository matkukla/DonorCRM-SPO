"""
Celery tasks for pledge management.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def check_late_pledges():
    """
    Check all active pledges for late payments.
    Run daily. Uses bulk_update for efficiency.
    """
    from apps.events.services import create_pledge_late_event
    from apps.pledges.models import Pledge, PledgeStatus

    active_pledges = Pledge.objects.filter(status=PledgeStatus.ACTIVE)
    total_count = active_pledges.count()

    logger.info(f'Checking {total_count} active pledges for late status')

    pledges_to_update = []
    newly_late_pledges = []

    for pledge in active_pledges.iterator():
        was_late = pledge.is_late
        pledge.check_late_status()

        # Track pledges that need updating
        if pledge.is_late != was_late or pledge.days_late != getattr(pledge, '_original_days_late', pledge.days_late):
            pledges_to_update.append(pledge)

            if pledge.is_late and not was_late:
                newly_late_pledges.append(pledge)

    # Bulk update all changed pledges
    if pledges_to_update:
        Pledge.objects.bulk_update(
            pledges_to_update,
            fields=['is_late', 'days_late'],
            batch_size=500
        )
        logger.info(f'Updated {len(pledges_to_update)} pledges')

    # Create events for newly late pledges
    for pledge in newly_late_pledges:
        create_pledge_late_event(pledge)

    logger.info(f'Checked {total_count} pledges, {len(newly_late_pledges)} newly late')

    return f'Checked {total_count} pledges, {len(newly_late_pledges)} newly late'
