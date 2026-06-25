"""
"Last Contacted" signal: the most recent real conversation with a contact.

Defined (ADR 0005) as the maximum of:
  - the completed_at of any completed Task of type Call or Meeting linked to the
    contact, and
  - the created_at of any JournalStageEvent of type call_logged or
    meeting_completed for the contact.

It excludes gift dates and all other task types — only a logged call or meeting
counts as "I talked to them." It may be null (never reached via a logged
call/meeting). It is computed on the fly as a query annotation, not
denormalized onto Contact.

The same 60-day default is shared with the import thank-you recency window
(ADR 0006) — keep them as one tunable constant.
"""

from datetime import timedelta

from django.db.models import DateTimeField, OuterRef, Subquery
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone

from apps.journals.models import JournalStageEvent, StageEventType
from apps.tasks.models import Task, TaskStatus, TaskType

# Days without a logged call/meeting before a donor counts as "not contacted
# recently." Shared with the import thank-you recency window (ADR 0006).
NOT_CONTACTED_RECENTLY_DAYS = 60

_CONTACT_TASK_TYPES = [TaskType.CALL, TaskType.MEETING]
_CONTACT_EVENT_TYPES = [StageEventType.CALL_LOGGED, StageEventType.MEETING_COMPLETED]


def annotate_last_contacted(queryset):
    """Annotate a Contact queryset with `last_contacted` (DateTimeField or null).

    `last_contacted` is the latest of the contact's last completed call/meeting
    task and last call/meeting journal event. Contacts never reached via either
    source get null.
    """
    last_task = (
        Task.objects.filter(
            contact_id=OuterRef("pk"),
            status=TaskStatus.COMPLETED,
            task_type__in=_CONTACT_TASK_TYPES,
            completed_at__isnull=False,
        )
        .order_by("-completed_at")
        .values("completed_at")[:1]
    )

    last_event = (
        JournalStageEvent.objects.filter(
            journal_contact__contact_id=OuterRef("pk"),
            event_type__in=_CONTACT_EVENT_TYPES,
        )
        .order_by("-created_at")
        .values("created_at")[:1]
    )

    last_task_at = Subquery(last_task, output_field=DateTimeField())
    last_event_at = Subquery(last_event, output_field=DateTimeField())

    # PostgreSQL's GREATEST ignores nulls, but SQLite (the test DB) maps Greatest
    # to MAX(...) which returns null if ANY arg is null. Coalescing each side to
    # the other makes the result correct on both: the non-null value when only
    # one source exists, the true max when both do, and null only when both are
    # null (the "never contacted" case).
    return queryset.annotate(
        last_contacted=Greatest(
            Coalesce(last_task_at, last_event_at),
            Coalesce(last_event_at, last_task_at),
            output_field=DateTimeField(),
        ),
    )


def not_contacted_recently_cutoff(days=NOT_CONTACTED_RECENTLY_DAYS, now=None):
    """The datetime before which a `last_contacted` value counts as stale."""
    now = now or timezone.now()
    return now - timedelta(days=days)


def latest_touch(contact):
    """Return the latest logged call/meeting for a single contact as a dict.

    {"at": datetime|None, "type": "call"|"meeting"|None} — drives the contact
    Overview "last touch" line (F7b). Type reflects whichever source produced
    the most recent touch; null when the contact has no logged call/meeting.
    """
    last_task = (
        Task.objects.filter(
            contact=contact,
            status=TaskStatus.COMPLETED,
            task_type__in=_CONTACT_TASK_TYPES,
            completed_at__isnull=False,
        )
        .order_by("-completed_at")
        .values("completed_at", "task_type")
        .first()
    )
    last_event = (
        JournalStageEvent.objects.filter(
            journal_contact__contact=contact,
            event_type__in=_CONTACT_EVENT_TYPES,
        )
        .order_by("-created_at")
        .values("created_at", "event_type")
        .first()
    )

    task_at = last_task["completed_at"] if last_task else None
    event_at = last_event["created_at"] if last_event else None

    if task_at is None and event_at is None:
        return {"at": None, "type": None}

    # Meeting events map to "meeting"; everything else logged here is a "call".
    if event_at is not None and (task_at is None or event_at >= task_at):
        kind = "meeting" if last_event["event_type"] == StageEventType.MEETING_COMPLETED else "call"
        return {"at": event_at, "type": kind}

    kind = "meeting" if last_task["task_type"] == TaskType.MEETING else "call"
    return {"at": task_at, "type": kind}


def not_contacted_recently(queryset, days=NOT_CONTACTED_RECENTLY_DAYS, now=None):
    """Filter+order a Contact queryset to "not contacted recently".

    Returns contacts whose `last_contacted` is older than `days`, plus
    never-contacted contacts (null), ordered never-contacted first then
    oldest-touch first. The queryset is annotated here, so callers pass a plain
    Contact queryset (already owner/status-scoped as they wish).
    """
    from django.db.models import F, Q

    cutoff = not_contacted_recently_cutoff(days=days, now=now)
    annotated = annotate_last_contacted(queryset)
    return annotated.filter(Q(last_contacted__lt=cutoff) | Q(last_contacted__isnull=True)).order_by(
        F("last_contacted").asc(nulls_first=True)
    )
