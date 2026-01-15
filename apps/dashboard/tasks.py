"""
Celery tasks for dashboard/reporting.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def generate_weekly_summary():
    """
    Generate weekly summary for all active users.
    Run every Monday.
    """
    from apps.core.email import send_weekly_summary_email
    from apps.dashboard.services import get_dashboard_summary
    from apps.users.models import User

    active_users = User.objects.filter(is_active=True, email_notifications=True)
    summaries_sent = 0
    errors = 0

    for user in active_users:
        try:
            # Generate summary data
            summary = get_dashboard_summary(user)

            # Send email with summary
            if send_weekly_summary_email(user, summary):
                summaries_sent += 1
            else:
                errors += 1
                logger.warning(f'Failed to send weekly summary to {user.email}')
        except Exception as e:
            errors += 1
            logger.error(f'Error generating summary for {user.email}: {e}')

    return f'Sent {summaries_sent} weekly summaries ({errors} errors)'
