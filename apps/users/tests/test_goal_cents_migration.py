"""Regression guard for the 0010 goal-cents data migration.

Migration 0010 (`fix_dollar_values_to_cents`) converts goals stored as dollar floats
into integer cents by multiplying any value in 1..9999 by 100, on the assumption that
"no realistic missionary monthly goal is under $100/month (10000 cents)".

This test pins that boundary behavior so a future change is caught, and DOCUMENTS the
known limitation it implies (the reason this migration must never be re-applied):

  - A value already stored as cents in the 1..9999 window (e.g. a legitimate $50/month
    goal = 5000 cents) is indistinguishable from a dollar amount and would be wrongly
    multiplied to 500000 ($5,000). Re-running the migration therefore corrupts sub-$100
    goals — it is safe ONLY as the documented one-time conversion.
  - A value >= 10000 is left untouched (assumed already cents).

The migration's reverse is a no-op and it has already been applied in production, so the
practical protection is: never manually re-apply it, and catch any edit to its logic
here.
"""

import importlib

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()

_migration = importlib.import_module("apps.users.migrations.0010_fix_goal_cents_data")
fix_dollar_values_to_cents = _migration.fix_dollar_values_to_cents


class GoalCentsMigrationBoundaryTest(TestCase):
    """Boundary-value characterization of the 0010 conversion (1, 5000, 9999, 10000, 500000)."""

    def _user(self, email, goal_cents):
        u = User.objects.create_user(email=email, password="pw")
        u.monthly_support_goal_cents = goal_cents
        u.save(update_fields=["monthly_support_goal_cents"])
        return u

    def test_boundary_values(self):
        below = self._user("goal-1@test.com", 1)
        fifty_dollars = self._user("goal-5000@test.com", 5000)
        edge_in = self._user("goal-9999@test.com", 9999)
        edge_out = self._user("goal-10000@test.com", 10000)
        already_cents = self._user("goal-500000@test.com", 500000)
        zero = self._user("goal-0@test.com", 0)

        fix_dollar_values_to_cents(django_apps, None)

        for u in (below, fifty_dollars, edge_in, edge_out, already_cents, zero):
            u.refresh_from_db()

        # Values in 1..9999 are multiplied by 100 (treated as dollars).
        self.assertEqual(below.monthly_support_goal_cents, 100)
        self.assertEqual(fifty_dollars.monthly_support_goal_cents, 500000)  # known $50 corruption
        self.assertEqual(edge_in.monthly_support_goal_cents, 999900)
        # Values >= 10000 and 0 are left untouched.
        self.assertEqual(edge_out.monthly_support_goal_cents, 10000)
        self.assertEqual(already_cents.monthly_support_goal_cents, 500000)
        self.assertEqual(zero.monthly_support_goal_cents, 0)
