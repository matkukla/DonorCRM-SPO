"""
Shared gift aggregation utilities for DonorCRM.
Provides frequency multipliers and SQL aggregation helpers used by
dashboard services and goal services.
"""
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Sum, Value, When

from apps.gifts.models import RecurringGiftFrequency

# Frequency multipliers for SQL CASE/WHEN aggregation.
# Must match RecurringGift.monthly_equivalent property exactly.
FREQUENCY_MULTIPLIERS = {
    RecurringGiftFrequency.MONTHLY: Decimal('1'),
    RecurringGiftFrequency.QUARTERLY: Decimal('1') / Decimal('3'),
    RecurringGiftFrequency.SEMI_ANNUALLY: Decimal('1') / Decimal('6'),
    RecurringGiftFrequency.ANNUALLY: Decimal('1') / Decimal('12'),
    RecurringGiftFrequency.BIMONTHLY: Decimal('1') / Decimal('2'),
    RecurringGiftFrequency.BIWEEKLY: Decimal('26') / Decimal('12'),
    RecurringGiftFrequency.WEEKLY: Decimal('52') / Decimal('12'),
    RecurringGiftFrequency.IRREGULAR: Decimal('1'),
}


def _monthly_equivalent_aggregate(queryset):
    """
    Compute the total monthly equivalent of recurring gifts via SQL aggregation.

    Uses CASE/WHEN to apply the correct frequency multiplier per row,
    then SUM across all rows. Returns the total in dollars (Decimal).

    This replaces the O(N) Python loop pattern:
      sum(rg.monthly_equivalent for rg in queryset)
    """
    result = queryset.annotate(
        freq_multiplier=Case(
            *[
                When(frequency=freq, then=Value(mult))
                for freq, mult in FREQUENCY_MULTIPLIERS.items()
            ],
            default=Value(Decimal('1')),
            output_field=DecimalField(max_digits=20, decimal_places=10),
        ),
        monthly_cents=F('amount_cents') * F('freq_multiplier'),
    ).aggregate(total=Sum('monthly_cents'))

    total_cents = result['total'] or Decimal('0')
    return round(total_cents / Decimal('100'), 2)
