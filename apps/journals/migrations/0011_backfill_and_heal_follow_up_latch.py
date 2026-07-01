"""Backfill follow_up_task FK and heal orphaned follow-up latches.

For Decisions whose latch (follow_up_created_at) is set:
  - Backfill: if a matching live follow-up Task still exists, point follow_up_task
    at it.
  - Heal: otherwise the Task was deleted before the FK existed, so the latch is a
    permanent orphan (the bug this change fixes) — clear it so the sweep can re-arm.

Backfill runs before heal so a pledge that still has a live Task is never re-armed
(which would produce a duplicate follow-up on the next sweep). No-op on clean data.

See docs/adr/0010-follow-up-latch-resets-on-task-delete.md.
"""

from django.db import migrations

FOLLOW_UP_TITLE = "Donation still not received — follow up"


def backfill_and_heal(apps, schema_editor):
    Decision = apps.get_model("journals", "Decision")
    Task = apps.get_model("tasks", "Task")

    latched = Decision.objects.filter(follow_up_created_at__isnull=False).select_related(
        "journal_contact__contact"
    )
    for decision in latched.iterator():
        contact = decision.journal_contact.contact
        # A live follow-up Task = the auto-generated FOLLOW_UP for this contact that
        # has not been completed or cancelled. Historical follow-up Tasks carry no FK,
        # so match on contact + type + title, newest first.
        task = (
            Task.objects.filter(
                contact=contact,
                task_type="follow_up",
                title=FOLLOW_UP_TITLE,
            )
            .exclude(status__in=["completed", "cancelled"])
            .order_by("-created_at")
            .first()
        )
        if task is not None:
            decision.follow_up_task = task
            decision.save(update_fields=["follow_up_task"])
        else:
            decision.follow_up_created_at = None
            decision.save(update_fields=["follow_up_created_at"])


def noop_reverse(apps, schema_editor):
    # Irreversible: healed latches and backfilled FKs cannot be distinguished from
    # naturally-occurring state on reverse. Leaving data as-is is safe.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("journals", "0010_decision_follow_up_task"),
        ("tasks", "0004_broadcasttask"),
    ]

    operations = [
        migrations.RunPython(backfill_and_heal, noop_reverse),
    ]
