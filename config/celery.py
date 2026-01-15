"""
Celery configuration for DonorCRM.
"""
import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('donorcrm')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Periodic tasks schedule
app.conf.beat_schedule = {
    'check-late-pledges-daily': {
        'task': 'apps.pledges.tasks.check_late_pledges',
        'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM UTC
        'options': {'expires': 3600},  # Expire after 1 hour
    },
    'detect-at-risk-donors-daily': {
        'task': 'apps.contacts.tasks.detect_at_risk_donors',
        'schedule': crontab(hour=7, minute=0),  # Daily at 7 AM UTC
        'options': {'expires': 3600},
    },
    'generate-weekly-summary': {
        'task': 'apps.dashboard.tasks.generate_weekly_summary',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),  # Mondays at 8 AM UTC
        'options': {'expires': 7200},
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
