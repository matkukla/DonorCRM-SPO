"""
Celery tasks for journals.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def check_pledge_followups():
    """
    Check active pledges past their 10-day mark and create follow-up tasks for any
    that remain unfulfilled. Idempotent — safe to run repeatedly. Run daily.
    """
    from apps.journals.pledge_followup import run_pledge_followup_sweep

    count = run_pledge_followup_sweep()
    return f"Created {count} pledge follow-up tasks"
