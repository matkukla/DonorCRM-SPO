"""
Shared late-donation calculation used by the Dashboard tile and the
/insights/late-donations page.

A recurring gift is "late" if more time has passed since the donor's last gift
than the expected interval for the gift's frequency, with a 50% grace period.

Grace period is intentionally hardcoded (locked 2026-05-01).
"""
from datetime import timedelta

from django.utils import timezone

from apps.gifts.models import RecurringGift, RecurringGiftFrequency, RecurringGiftStatus

# Frequency -> expected days between gifts. IRREGULAR is excluded — it has no
# meaningful interval.
FREQUENCY_DAYS = {
    RecurringGiftFrequency.WEEKLY: 7,
    RecurringGiftFrequency.BIWEEKLY: 14,
    RecurringGiftFrequency.MONTHLY: 30,
    RecurringGiftFrequency.BIMONTHLY: 60,
    RecurringGiftFrequency.QUARTERLY: 90,
    RecurringGiftFrequency.SEMI_ANNUALLY: 180,
    RecurringGiftFrequency.ANNUALLY: 365,
}

# Grace multiplier: late only if elapsed > interval * (1 + GRACE).
GRACE_MULTIPLIER = 1.5


def _is_late(rg, today):
    """Return (interval, reference_date, days_late) if `rg` is past the grace
    window, else None. `interval` and `reference_date` are returned for callers
    that need to construct the dict."""
    interval = FREQUENCY_DAYS.get(rg.frequency)
    if not interval:
        return None
    reference_date = rg.donor_contact.last_gift_date or rg.start_date
    threshold = timedelta(days=int(interval * GRACE_MULTIPLIER))
    if today - reference_date <= threshold:
        return None
    days_late = (today - reference_date).days - interval
    return interval, reference_date, days_late


def _scoped_qs(active_recurring_qs):
    return (
        active_recurring_qs.filter(status=RecurringGiftStatus.ACTIVE)
        .exclude(frequency=RecurringGiftFrequency.IRREGULAR)
        .select_related("donor_contact")
    )


def compute_late_donations(active_recurring_qs, today=None, limit=None):
    """Compute late donations from a base RecurringGift queryset.

    The queryset should already be scoped (owner / visible-users / etc.). This
    helper applies the ACTIVE status filter and excludes IRREGULAR.

    Args:
        active_recurring_qs: RecurringGift queryset (any pre-scoping the caller wants).
        today: optional reference date for testing.
        limit: optional max rows in the returned list.

    Returns:
        list[dict] with keys:
            id, contact_id, contact_name, amount, frequency, monthly_equivalent,
            last_gift_date, days_late, next_expected_date
    """
    today = today or timezone.localdate()

    late = []
    for rg in _scoped_qs(active_recurring_qs):
        result = _is_late(rg, today)
        if result is None:
            continue
        interval, reference_date, days_late = result
        contact = rg.donor_contact
        last_gift_date = contact.last_gift_date
        late.append(
            {
                "id": str(rg.id),
                "contact_id": str(contact.id),
                "contact_name": f"{contact.first_name} {contact.last_name}".strip(),
                "amount": float(rg.amount_dollars),
                "frequency": rg.frequency,
                "monthly_equivalent": float(rg.monthly_equivalent),
                "last_gift_date": last_gift_date.isoformat() if last_gift_date else None,
                "days_late": days_late,
                "next_expected_date": (reference_date + timedelta(days=interval)).isoformat(),
            }
        )

    late.sort(key=lambda x: x["days_late"], reverse=True)
    return late if limit is None else late[:limit]


def count_late_donations(active_recurring_qs, today=None):
    """Count late donations without allocating per-row dicts.

    Use when the caller only needs the total — e.g. the Dashboard summary's
    `late_donations_count` badge — so a tenant with thousands of late pledges
    doesn't OOM building a list that gets discarded.
    """
    today = today or timezone.localdate()
    return sum(1 for rg in _scoped_qs(active_recurring_qs) if _is_late(rg, today) is not None)


def base_recurring_for_owner(user):
    """Convenience: queryset of active recurring gifts owned by user."""
    return RecurringGift.objects.filter(donor_contact__owner=user)
