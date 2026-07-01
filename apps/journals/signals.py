"""
Signals for Journal event logging.
"""

import logging

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.journals.models import Decision, Journal, JournalStageEvent

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Journal)
def handle_journal_created(sender, instance, created, **kwargs):
    """Create event when journal is created."""
    if not created:
        return

    try:
        from apps.events.models import Event, EventSeverity, EventType

        Event.objects.create(
            user=instance.owner,
            event_type=EventType.JOURNAL_CREATED,
            title=f"Journal created: {instance.name}",
            message=f"Goal: ${instance.goal_amount}",
            severity=EventSeverity.INFO,
            metadata={"journal_id": str(instance.id), "goal_amount": str(instance.goal_amount)},
        )
    except Exception as e:
        logger.warning(f"Failed to create JOURNAL_CREATED event: {e}")


@receiver(post_save, sender=JournalStageEvent)
def handle_stage_event_created(sender, instance, created, **kwargs):
    """Create event when stage event is created."""
    if not created:
        return

    try:
        from apps.events.models import Event, EventSeverity, EventType

        journal = instance.journal_contact.journal

        Event.objects.create(
            user=journal.owner,
            event_type=EventType.JOURNAL_STAGE_EVENT,
            title=f"{instance.get_stage_display()}: {instance.get_event_type_display()}",
            message=instance.notes[:200] if instance.notes else "",
            severity=EventSeverity.INFO,
            metadata={
                "journal_id": str(journal.id),
                "stage": instance.stage,
                "event_type": instance.event_type,
                "journal_contact_id": str(instance.journal_contact_id),
            },
        )
    except Exception as e:
        logger.warning(f"Failed to create JOURNAL_STAGE_EVENT event: {e}")


@receiver(pre_delete, sender=Decision)
def discard_followup_on_decision_delete(sender, instance, **kwargs):
    """Delete the orphaned follow-up Task when its owning Decision is deleted.

    Mirror of the Task pre_delete handler in apps/tasks/signals.py. Covers every path
    that destroys a Decision — contact merge, JournalContact cascade, admin — so the
    auto-generated follow-up Task is never left dangling (issue #183). Uses pre_delete
    (not post_delete) because Decision.follow_up_task is on_delete=SET_NULL: after the
    delete the FK is already nulled. discard_followup() is a no-op for Decisions with
    no live follow-up Task.
    """
    from apps.journals.pledge_followup import discard_followup

    discard_followup(instance)
