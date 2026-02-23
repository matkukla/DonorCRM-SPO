"""
Data migration: Copy Donation -> Gift and Pledge -> RecurringGift.

This migration has already been applied. The original forward functions
referenced the now-deleted 'donations' and 'pledges' apps. Since the
data has been migrated and those apps removed, the operations are now
no-ops to keep the migration graph valid.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gifts', '0002_alter_solicitor_user'),
    ]

    operations = [
        migrations.RunPython(
            migrations.RunPython.noop,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            migrations.RunPython.noop,
            migrations.RunPython.noop,
        ),
    ]
