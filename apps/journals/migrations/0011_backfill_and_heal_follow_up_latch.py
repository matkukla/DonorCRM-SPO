"""Backfill follow_up_task FK and heal orphaned follow-up latches.

For Decisions whose latch (follow_up_created_at) is set:
  - Backfill: if a matching live follow-up Task still exists, point follow_up_task
    at it.
  - Heal: otherwise the Task was deleted before the FK existed, so the latch is a
    permanent orphan (the bug this change fixes) — clear it so the sweep can re-arm.

Backfill runs before heal so a pledge that still has a live Task is never re-armed
(which would produce a duplicate follow-up on the next sweep). No-op on clean data.

One-to-one pairing (issue #186): pre-FK follow-up Tasks carry no back-reference to the
Decision that spawned them, so the only distinguishing attribute is ``contact``. A
contact with more than one still-pending follow-up Task (from more than one latched
Decision) would otherwise have *every* Decision backfilled to the same newest Task,
breaking the one-Task-per-Decision invariant — and later deleting that shared Task
would clear both latches while leaving the other real Task referenced by nothing.
Instead, each Task is claimed by at most one Decision: latched Decisions and their
contact's candidate Tasks are paired oldest-to-oldest by ``created_at`` (a stable,
defensible temporal correlation given no better signal exists), and a claimed Task is
never reused. A Decision with no unclaimed candidate Task left is healed, exactly as if
its Task had been deleted.

See docs/adr/0010-follow-up-latch-resets-on-task-delete.md.
"""

from django.db import migrations

FOLLOW_UP_TITLE = "Donation still not received — follow up"


def backfill_and_heal(apps, schema_editor):
    Decision = apps.get_model("journals", "Decision")
    Task = apps.get_model("tasks", "Task")

    latched = (
        # Only journal_contact is needed (for its contact_id FK column) — no need to
        # join Contact itself, since candidate Tasks are queried by contact_id.
        Decision.objects.filter(follow_up_created_at__isnull=False).select_related(
            "journal_contact"
        )
        # Oldest Decision first so it claims the oldest candidate Task for its contact.
        .order_by("created_at")
    )

    # Candidate follow-up Tasks per contact, oldest first, so each contact's Decisions
    # claim distinct Tasks in the same order. A live follow-up Task = the auto-generated
    # FOLLOW_UP for a contact that has not been completed or cancelled. Historical
    # follow-up Tasks carry no FK, so match on contact + type + title.
    candidates_by_contact = {}
    claimed_task_ids = set()

    def next_unclaimed_task(contact_id):
        tasks = candidates_by_contact.get(contact_id)
        if tasks is None:
            tasks = list(
                Task.objects.filter(
                    contact_id=contact_id,
                    task_type="follow_up",
                    title=FOLLOW_UP_TITLE,
                )
                .exclude(status__in=["completed", "cancelled"])
                .order_by("created_at")
                .values_list("id", flat=True)
            )
            candidates_by_contact[contact_id] = tasks
        for task_id in tasks:
            if task_id not in claimed_task_ids:
                return task_id
        return None

    for decision in latched.iterator():
        contact_id = decision.journal_contact.contact_id
        task_id = next_unclaimed_task(contact_id)
        if task_id is not None:
            claimed_task_ids.add(task_id)
            decision.follow_up_task_id = task_id
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
