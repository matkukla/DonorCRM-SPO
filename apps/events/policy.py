"""Role-aware visibility policy for Event rows — single source of truth.

Both consumers of the Event table read through this module so the coach
financial boundary cannot be reopened by one of them drifting:

  - the dashboard "what changed" feed  (apps/dashboard/services.py)
  - the events API                     (apps/events/views.py)

Without a shared policy, a fix applied to one consumer (e.g. report_3 #1 in the
dashboard) leaves the other serving the same dollar figure — which is exactly
how a coach could read a coached user's journal goal via GET /api/v1/events/.

Scope — financial event types only:
    A coach has *authorized* read access to coached users' non-financial
    pipeline data: JournalStageEvent.notes is served unrestricted by
    JournalStageEventListCreateView, and AT_RISK alerts carry only a
    last_gift_date (already coach-visible). Only event types whose
    message/metadata embed an individual dollar figure are withheld, mirroring
    how the Decision* views gate financial records while stage events stay
    visible. JOURNAL_STAGE_EVENT is therefore intentionally NOT withheld.

    Any NEW event type that embeds an amount (e.g. a future PLEDGE_* signal
    carrying a pledge amount, or GIFT_LATE with an overdue figure) MUST be
    added to FINANCIAL_EVENT_TYPES below.
"""

from apps.events.models import EventType

# Event types whose message/metadata embed an individual dollar figure:
#   - DONATION_RECEIVED / FIRST_DONATION: message "$<amount> received"
#   - JOURNAL_CREATED:                    message "Goal: $<goal>" + metadata.goal_amount
FINANCIAL_EVENT_TYPES = (
    EventType.DONATION_RECEIVED,
    EventType.FIRST_DONATION,
    EventType.JOURNAL_CREATED,
)


def scope_events_for_requester(queryset, user):
    """Drop dollar-bearing events for non-financial requesters (coach).

    Financial roles (admin/supervisor/missionary) get ``queryset`` unchanged.
    A coach viewing a coached user's events gets the same rows minus the
    amount-bearing ones (CWE-200), matching the dashboard feed exactly.
    """
    from apps.core.permissions import is_financial_role

    if not is_financial_role(user):
        return queryset.exclude(event_type__in=FINANCIAL_EVENT_TYPES)
    return queryset
