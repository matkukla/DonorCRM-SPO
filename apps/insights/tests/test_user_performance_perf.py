"""
Regression tests for the Subquery-based user performance pipeline.

Covers:
- Query-count budget for get_user_performance() — the Count(distinct=True)
  4-hop join blow-up from before phase 2B would push this well over budget.
- Query-count budget for get_user_drilldown() — now reuses the shared
  _annotate_user_performance() helper, so stat queries collapse into one.
- Output parity: metric values match what an independent per-user
  calculation yields, so the Subquery refactor did not silently change
  the conversion rate or decision counts exposed to the dashboard.
"""
from decimal import Decimal

from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.contacts.models import Contact
from apps.gifts.models import Gift
from apps.insights.services import get_user_drilldown, get_user_performance
from apps.journals.models import Decision, Journal, JournalContact
from apps.users.models import User


class UserPerformanceQueryBudgetTest(TestCase):
    """Assert phase 2B query budgets and metric parity."""

    # Budgets chosen with headroom over the steady-state plan:
    # get_user_performance fires ~8 Subqueries as one SELECT on User, so
    # 10 covers any auth/session side-queries the test client may add.
    # get_user_drilldown adds stalled-count + recent-journals on top of
    # the batched perf row, landing around 4-5 queries.
    PERFORMANCE_QUERY_BUDGET = 10
    DRILLDOWN_QUERY_BUDGET = 8

    def setUp(self):
        self.user = User.objects.create_user(
            email='perf@test.com',
            password='testpass123',
            role='missionary',
            first_name='Perf',
            last_name='Tester',
        )

        contacts = [
            Contact.objects.create(
                owner=self.user,
                first_name=f'C{i}',
                last_name='Test',
                email=f'c{i}@test.com',
                status='active',
            )
            for i in range(5)
        ]

        journal = Journal.objects.create(
            owner=self.user,
            name='Perf Journal',
            goal_amount=Decimal('10000.00'),
            is_archived=False,
        )

        # Put 4 contacts in a journal; mark 2 with decisions (50% conversion).
        journal_contacts = [
            JournalContact.objects.create(journal=journal, contact=c)
            for c in contacts[:4]
        ]
        for jc in journal_contacts[:2]:
            Decision.objects.create(
                journal_contact=jc,
                amount=Decimal('100.00'),
            )

        # Two gifts totaling $150.00.
        Gift.objects.create(
            donor_contact=contacts[0],
            amount_cents=10000,
            gift_date='2026-01-01',
        )
        Gift.objects.create(
            donor_contact=contacts[1],
            amount_cents=5000,
            gift_date='2026-01-02',
        )

    def test_get_user_performance_within_query_budget(self):
        with CaptureQueriesContext(connection) as ctx:
            result = get_user_performance()

        self.assertLessEqual(
            len(ctx.captured_queries),
            self.PERFORMANCE_QUERY_BUDGET,
            f'get_user_performance used {len(ctx.captured_queries)} queries, '
            f'budget is {self.PERFORMANCE_QUERY_BUDGET}',
        )

        rows = {row['email']: row for row in result['users']}
        row = rows['perf@test.com']
        self.assertEqual(row['total_contacts'], 5)
        self.assertEqual(row['active_journals'], 1)
        self.assertEqual(row['decisions_logged'], 2)
        self.assertEqual(row['conversion_rate'], 50.0)
        self.assertEqual(row['total_donations'], 150.0)
        self.assertEqual(row['donation_count'], 2)

    def test_get_user_drilldown_within_query_budget(self):
        with CaptureQueriesContext(connection) as ctx:
            result = get_user_drilldown(str(self.user.id))

        self.assertLessEqual(
            len(ctx.captured_queries),
            self.DRILLDOWN_QUERY_BUDGET,
            f'get_user_drilldown used {len(ctx.captured_queries)} queries, '
            f'budget is {self.DRILLDOWN_QUERY_BUDGET}',
        )

        stats = result['stats']
        self.assertEqual(stats['total_contacts'], 5)
        self.assertEqual(stats['active_journals'], 1)
        self.assertEqual(stats['decisions_logged'], 2)
        self.assertEqual(stats['conversion_rate'], 50.0)
        self.assertEqual(stats['total_donations'], 150.0)
        self.assertEqual(stats['donation_count'], 2)

    def test_drilldown_matches_performance_row(self):
        """Drilldown and table must report identical metrics for the same user."""
        perf_row = next(
            row for row in get_user_performance()['users']
            if row['email'] == 'perf@test.com'
        )
        drilldown = get_user_drilldown(str(self.user.id))['stats']

        for key in (
            'total_contacts',
            'active_journals',
            'decisions_logged',
            'conversion_rate',
            'total_donations',
            'donation_count',
        ):
            self.assertEqual(
                perf_row[key],
                drilldown[key],
                f'Mismatch on {key}: table={perf_row[key]} drilldown={drilldown[key]}',
            )

    def test_user_not_found_returns_detail(self):
        result = get_user_drilldown('00000000-0000-0000-0000-000000000000')
        self.assertEqual(result, {'detail': 'User not found'})
