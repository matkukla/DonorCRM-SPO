"""Signal handlers for the tasks app."""

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from apps.tasks.models import Task


@receiver(pre_delete, sender=Task)
def release_followup_on_task_delete(sender, instance, **kwargs):
    """Re-arm the pledge follow-up sweep when a follow-up Task is deleted.

    Uses pre_delete (not post_delete) because Decision.follow_up_task is
    on_delete=SET_NULL, which nulls the FK before post_delete fires — mirroring the
    RecurringGift handler in apps/gifts/signals.py. release_followup() is a no-op for
    Tasks that are not a pledge follow-up.
    """
    from apps.journals.pledge_followup import release_followup

    release_followup(instance)
