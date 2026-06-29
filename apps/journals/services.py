"""Service functions for Journal goal/progress measurement.

Issue #167: the journal tab measures progress toward its (monthly) goal from
*actual gifts*, using the same canonical formula as the Goal tab — recurring
gifts at their monthly equivalent plus fiscal-year one-time gifts divided by 12.
The ÷12 is applied only in this measurement; the stored gift amount is never
changed. This deliberately reuses apps.core.support_math.compute_monthly_support
so there is a single source of truth for the cents math and rounding.
"""

from datetime import date

from django.db.models import Q

from apps.core.support_math import compute_monthly_support
from apps.journals.models import JournalContact


def get_journal_monthly_support(journal, today: date | None = None) -> dict:
    """Compute gift-based monthly support for a single journal.

    Scopes the canonical monthly-support formula to the contacts that belong to
    this journal (via the JournalContact through-table).

    Args:
        journal: the Journal to measure.
        today: optional reference date for the fiscal-year window (passed through
            to compute_monthly_support). Defaults to the current local date.

    Returns:
        dict with float dollar values:
            recurring_monthly         active recurring monthly equivalent
            one_time_monthly          FY one-time gift total / 12
            effective_monthly_support sum of the above
            active_pledge_count       count of active RecurringGifts in scope
    """
    contact_ids = list(
        JournalContact.objects.filter(journal=journal).values_list("contact_id", flat=True)
    )
    return compute_monthly_support(Q(donor_contact_id__in=contact_ids), today=today)
