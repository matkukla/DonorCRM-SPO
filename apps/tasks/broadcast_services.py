"""
Service functions for broadcast task operations.

Handles target resolution, bulk copy creation, cascade edits, and cancellation.
All mutating operations are wrapped in database transactions for atomicity.
"""

from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from apps.tasks.models import BroadcastTask, Task, TaskStatus


def resolve_recipients(sender, target_type, specific_user_ids=None):
    """Resolve target specification to a concrete list of active users.

    Args:
        sender: User creating the broadcast.
        target_type: One of 'all_missionaries', 'all_supervisors', 'specific_users', 'my_team'.
        specific_user_ids: List of UUIDs when target_type is 'specific_users'.

    Returns:
        list[User]: Resolved recipient users.

    Raises:
        PermissionError: If sender role does not match target_type requirements.
    """
    from apps.users.models import User

    if target_type == "all_missionaries":
        if sender.role != "admin":
            raise PermissionError("Only admins can target all missionaries")
        return list(
            User.objects.filter(role__in=["missionary", "supervisor"], is_active=True).exclude(
                id=sender.id
            )
        )

    elif target_type == "all_supervisors":
        if sender.role != "admin":
            raise PermissionError("Only admins can target all supervisors")
        return list(User.objects.filter(role="supervisor", is_active=True))

    elif target_type == "my_team":
        if sender.role not in ("admin", "supervisor"):
            raise PermissionError("Only admins and supervisors can target their team")
        return list(sender.supervised_users.filter(is_active=True))

    elif target_type == "specific_users":
        if not specific_user_ids:
            return []
        users = User.objects.filter(id__in=specific_user_ids, is_active=True)
        # Server-side enforcement: supervisor can only target supervised users
        if sender.role == "supervisor":
            allowed_ids = set(
                sender.supervised_users.filter(is_active=True).values_list("id", flat=True)
            )
            users = users.filter(id__in=allowed_ids)
        return list(users)

    return []


@transaction.atomic
def create_broadcast(
    sender, title, description, task_type, priority, due_date, target_type, specific_user_ids=None
):
    """Create a broadcast and distribute task copies to all resolved recipients.

    Args:
        sender: User creating the broadcast.
        title: Task title.
        description: Task description.
        task_type: TaskType choice value.
        priority: TaskPriority choice value.
        due_date: Due date for the task.
        target_type: Target group specification.
        specific_user_ids: List of UUIDs for 'specific_users' target type.

    Returns:
        BroadcastTask: The created broadcast record.

    Raises:
        ValidationError: If no valid recipients are found.
    """
    recipients = resolve_recipients(sender, target_type, specific_user_ids)

    if not recipients:
        raise ValidationError("No valid recipients found")

    broadcast = BroadcastTask.objects.create(
        sender=sender,
        title=title,
        description=description,
        task_type=task_type,
        priority=priority,
        due_date=due_date,
        target_type=target_type,
        recipient_ids=[str(u.id) for u in recipients],
        recipient_count=len(recipients),
    )

    tasks = [
        Task(
            owner=recipient,
            broadcast=broadcast,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            due_date=due_date,
            status=TaskStatus.PENDING,
            contact=None,
            journal=None,
        )
        for recipient in recipients
    ]
    Task.objects.bulk_create(tasks)

    return broadcast


@transaction.atomic
def update_broadcast(
    broadcast, title=None, description=None, task_type=None, priority=None, due_date=None
):
    """Update broadcast fields and cascade changes to incomplete copies only.

    Completed and cancelled copies are untouched.

    Args:
        broadcast: BroadcastTask instance to update.
        title: New title (or None to skip).
        description: New description (or None to skip).
        task_type: New task type (or None to skip).
        priority: New priority (or None to skip).
        due_date: New due date (or None to skip).

    Returns:
        BroadcastTask: The updated broadcast record.
    """
    # Build update dicts from non-None params
    broadcast_update_fields = []
    task_update_fields = {}

    if title is not None:
        broadcast.title = title
        broadcast_update_fields.append("title")
        task_update_fields["title"] = title

    if description is not None:
        broadcast.description = description
        broadcast_update_fields.append("description")
        task_update_fields["description"] = description

    if task_type is not None:
        broadcast.task_type = task_type
        broadcast_update_fields.append("task_type")
        task_update_fields["task_type"] = task_type

    if priority is not None:
        broadcast.priority = priority
        broadcast_update_fields.append("priority")
        task_update_fields["priority"] = priority

    if due_date is not None:
        broadcast.due_date = due_date
        broadcast_update_fields.append("due_date")
        task_update_fields["due_date"] = due_date

    if broadcast_update_fields:
        broadcast_update_fields.append("updated_at")
        broadcast.save(update_fields=broadcast_update_fields)

    if task_update_fields:
        # Cascade to incomplete copies only
        Task.objects.filter(broadcast=broadcast).exclude(status=TaskStatus.COMPLETED).exclude(
            status=TaskStatus.CANCELLED
        ).update(**task_update_fields)

    return broadcast


@transaction.atomic
def cancel_broadcast(broadcast):
    """Cancel a broadcast by deleting incomplete copies and marking it cancelled.

    Completed copies are kept as historical records for missionaries.

    Args:
        broadcast: BroadcastTask instance to cancel.

    Returns:
        BroadcastTask: The updated broadcast record.
    """
    # Delete incomplete copies
    Task.objects.filter(broadcast=broadcast).exclude(status=TaskStatus.COMPLETED).delete()

    # Mark broadcast as cancelled
    broadcast.is_cancelled = True
    broadcast.cancelled_at = timezone.now()
    broadcast.save(update_fields=["is_cancelled", "cancelled_at", "updated_at"])

    return broadcast
