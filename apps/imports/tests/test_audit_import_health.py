"""
Tests for the audit_import_health management command.

Covers all 5 sections, --verbose/--json flags, zero-solicitors edge case,
and HEALTHY vs NEEDS ATTENTION verdict logic.
"""
import json
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.contacts.models import Contact
from apps.gifts.models import (
    Gift,
    GiftCredit,
    RecurringGift,
    RecurringGiftCredit,
    RecurringGiftStatus,
    Solicitor,
)
from apps.imports.models import MissionaryAlias
from apps.users.models import UserRole
from apps.users.tests.factories import UserFactory


class AuditImportHealthZeroSolicitorsTest(TestCase):
    """Test zero solicitors edge case."""

    def test_zero_solicitors_exits_cleanly(self):
        """When no solicitors exist, print message and exit without sections."""
        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('No solicitors found', output)
        # Should not print any section headers
        self.assertNotIn('Section 1', output)
        self.assertNotIn('Section 2', output)
        self.assertNotIn('Section 3', output)
        self.assertNotIn('Section 4', output)
        self.assertNotIn('Section 5', output)


class AuditImportHealthSolicitorsTest(TestCase):
    """Test Section 1: Solicitor Linking."""

    def setUp(self):
        self.missionary = UserFactory(
            role=UserRole.MISSIONARY,
            first_name='John',
            last_name='Smith',
        )

    def test_section1_counts_linked_and_unlinked(self):
        """Counts total solicitors, linked and unlinked with percentages."""
        Solicitor.objects.create(normalized_name='Smith, John', user=self.missionary)
        Solicitor.objects.create(normalized_name='Doe, Jane', user=None)

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('Solicitor Linking', output)
        self.assertIn('Total: 2', output)
        self.assertIn('Linked: 1', output)
        self.assertIn('Unlinked: 1', output)
        self.assertIn('50.0%', output)

    def test_section1_near_miss_user_fullname(self):
        """Detects near-misses by comparing unlinked solicitor names to User full names."""
        # Unlinked solicitor with name very close to a User's full name
        Solicitor.objects.create(normalized_name='Smith, Jon', user=None)

        out = StringIO()
        call_command('audit_import_health', '--verbose', stdout=out)
        output = out.getvalue()
        self.assertIn('near-miss', output.lower())
        self.assertIn('John Smith', output)

    def test_section1_near_miss_alias(self):
        """Detects near-misses by comparing unlinked solicitor names to MissionaryAlias source_names."""
        MissionaryAlias.objects.create(source_name='Johnny Smith', user=self.missionary)
        Solicitor.objects.create(normalized_name='Johny Smith', user=None)

        out = StringIO()
        call_command('audit_import_health', '--verbose', stdout=out)
        output = out.getvalue()
        self.assertIn('near-miss', output.lower())


class AuditImportHealthContactOwnershipTest(TestCase):
    """Test Section 2: Contact Ownership."""

    def setUp(self):
        self.missionary = UserFactory(
            role=UserRole.MISSIONARY,
            first_name='Alice',
            last_name='Missionary',
        )
        self.admin = UserFactory(role=UserRole.ADMIN, first_name='Bob', last_name='Admin')
        # Need at least one solicitor so sections run
        self.solicitor = Solicitor.objects.create(
            normalized_name='Missionary, Alice',
            user=self.missionary,
        )

    def test_section2_counts_by_role(self):
        """Groups contacts by owner role."""
        Contact.objects.create(
            owner=self.missionary,
            first_name='Donor',
            last_name='One',
        )
        Contact.objects.create(
            owner=self.admin,
            first_name='Donor',
            last_name='Two',
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('Contact Ownership', output)
        self.assertIn('missionary', output.lower())

    def test_section2_detects_misattributions(self):
        """Detects contacts owned by admin/supervisor with gift credits to missionary solicitor."""
        # Contact owned by admin
        contact = Contact.objects.create(
            owner=self.admin,
            first_name='Misattributed',
            last_name='Donor',
        )
        # Gift on that contact with a credit pointing to missionary solicitor
        gift = Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date='2026-01-01',
        )
        GiftCredit.objects.create(
            gift=gift,
            solicitor=self.solicitor,
            amount_cents=10000,
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('misattribut', output.lower())


class AuditImportHealthGiftCreditTest(TestCase):
    """Test Section 3: Gift Credit Integrity."""

    def setUp(self):
        self.missionary = UserFactory(role=UserRole.MISSIONARY)
        self.solicitor = Solicitor.objects.create(
            normalized_name='Test, Sol',
            user=self.missionary,
        )
        self.contact = Contact.objects.create(
            owner=self.missionary,
            first_name='Donor',
            last_name='One',
        )

    def test_section3_counts_gifts_and_credits(self):
        """Counts total gifts and total gift credits."""
        gift = Gift.objects.create(
            donor_contact=self.contact,
            amount_cents=5000,
            gift_date='2026-01-01',
        )
        GiftCredit.objects.create(
            gift=gift,
            solicitor=self.solicitor,
            amount_cents=5000,
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('Gift Credit Integrity', output)
        self.assertIn('Total gifts: 1', output)
        self.assertIn('Total credits: 1', output)

    def test_section3_orphaned_gifts(self):
        """Detects orphaned gifts (no credits) and unlinked dollar value."""
        Gift.objects.create(
            donor_contact=self.contact,
            amount_cents=25000,
            gift_date='2026-01-15',
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('Orphaned gifts: 1', output)
        self.assertIn('250.00', output)


class AuditImportHealthRecurringTest(TestCase):
    """Test Section 4: Recurring Gift Credit Integrity."""

    def setUp(self):
        self.missionary = UserFactory(role=UserRole.MISSIONARY)
        self.solicitor = Solicitor.objects.create(
            normalized_name='Test, Sol',
            user=self.missionary,
        )
        self.contact = Contact.objects.create(
            owner=self.missionary,
            first_name='Donor',
            last_name='Rec',
        )

    def test_section4_counts_active_recurring(self):
        """Counts active recurring gifts and their credits."""
        rg = RecurringGift.objects.create(
            donor_contact=self.contact,
            amount_cents=10000,
            frequency='monthly',
            start_date='2026-01-01',
            status=RecurringGiftStatus.ACTIVE,
        )
        RecurringGiftCredit.objects.create(
            recurring_gift=rg,
            solicitor=self.solicitor,
            amount_cents=10000,
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('Recurring Gift Credit Integrity', output)
        self.assertIn('Active recurring gifts: 1', output)

    def test_section4_orphaned_recurring(self):
        """Detects orphaned active recurring gifts (no credits)."""
        RecurringGift.objects.create(
            donor_contact=self.contact,
            amount_cents=15000,
            frequency='monthly',
            start_date='2026-01-01',
            status=RecurringGiftStatus.ACTIVE,
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('Orphaned active recurring gifts: 1', output)
        self.assertIn('150.00', output)

    def test_section4_ignores_non_active(self):
        """Non-active recurring gifts are not counted."""
        RecurringGift.objects.create(
            donor_contact=self.contact,
            amount_cents=10000,
            frequency='monthly',
            start_date='2026-01-01',
            status=RecurringGiftStatus.CANCELLED,
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('Active recurring gifts: 0', output)


class AuditImportHealthDashboardImpactTest(TestCase):
    """Test Section 5: Dashboard Impact Estimate."""

    def setUp(self):
        self.missionary = UserFactory(
            role=UserRole.MISSIONARY,
            first_name='Test',
            last_name='Missionary',
        )
        self.solicitor = Solicitor.objects.create(
            normalized_name='Missionary, Test',
            user=self.missionary,
        )

    def test_section5_lists_missionaries(self):
        """Lists missionaries with their contact/gift counts."""
        contact = Contact.objects.create(
            owner=self.missionary,
            first_name='Donor',
            last_name='A',
        )
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date='2026-01-01',
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('Dashboard Impact', output)

    def test_section5_flags_missionary_with_credits_but_no_contacts(self):
        """Flags missionary with 0 contacts but gift credits via solicitor."""
        # No contacts owned by missionary, but solicitor has credits
        other_user = UserFactory(role=UserRole.ADMIN)
        contact = Contact.objects.create(
            owner=other_user,
            first_name='Donor',
            last_name='B',
        )
        gift = Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date='2026-01-01',
        )
        GiftCredit.objects.create(
            gift=gift,
            solicitor=self.solicitor,
            amount_cents=10000,
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        # Should have a flag/warning for this missionary
        self.assertIn('flag', output.lower())


class AuditImportHealthVerdictTest(TestCase):
    """Test verdict logic."""

    def test_healthy_verdict(self):
        """HEALTHY when all sections clean."""
        missionary = UserFactory(role=UserRole.MISSIONARY)
        solicitor = Solicitor.objects.create(
            normalized_name='Test, Sol',
            user=missionary,
        )
        contact = Contact.objects.create(
            owner=missionary,
            first_name='Donor',
            last_name='A',
        )
        gift = Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date='2026-01-01',
        )
        GiftCredit.objects.create(
            gift=gift,
            solicitor=solicitor,
            amount_cents=10000,
        )

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('HEALTHY', output)

    def test_needs_attention_verdict(self):
        """NEEDS ATTENTION with issue count when problems exist."""
        UserFactory(role=UserRole.MISSIONARY)
        Solicitor.objects.create(normalized_name='Unlinked, Sol', user=None)

        out = StringIO()
        call_command('audit_import_health', stdout=out)
        output = out.getvalue()
        self.assertIn('NEEDS ATTENTION', output)
        self.assertIn('issue', output.lower())


class AuditImportHealthVerboseTest(TestCase):
    """Test --verbose flag."""

    def test_verbose_shows_unlinked_solicitor_names(self):
        """--verbose lists each unlinked solicitor by name."""
        UserFactory(role=UserRole.MISSIONARY)
        Solicitor.objects.create(normalized_name='Doe, Jane', user=None)

        out = StringIO()
        call_command('audit_import_health', '--verbose', stdout=out)
        output = out.getvalue()
        self.assertIn('Doe, Jane', output)

    def test_verbose_shows_misattributed_contacts(self):
        """--verbose lists each misattributed contact."""
        missionary = UserFactory(role=UserRole.MISSIONARY)
        admin = UserFactory(role=UserRole.ADMIN)
        solicitor = Solicitor.objects.create(
            normalized_name='M, Test',
            user=missionary,
        )
        contact = Contact.objects.create(
            owner=admin,
            first_name='Donor',
            last_name='Misattr',
        )
        gift = Gift.objects.create(
            donor_contact=contact,
            amount_cents=5000,
            gift_date='2026-01-01',
        )
        GiftCredit.objects.create(
            gift=gift,
            solicitor=solicitor,
            amount_cents=5000,
        )

        out = StringIO()
        call_command('audit_import_health', '--verbose', stdout=out)
        output = out.getvalue()
        self.assertIn('Donor Misattr', output)


class AuditImportHealthJsonTest(TestCase):
    """Test --json flag."""

    def test_json_outputs_valid_json(self):
        """--json outputs valid JSON with all 5 sections."""
        missionary = UserFactory(role=UserRole.MISSIONARY)
        Solicitor.objects.create(
            normalized_name='Test, Sol',
            user=missionary,
        )

        out = StringIO()
        call_command('audit_import_health', '--json', stdout=out)
        output = out.getvalue()
        data = json.loads(output)
        self.assertIn('solicitor_linking', data)
        self.assertIn('contact_ownership', data)
        self.assertIn('gift_credit_integrity', data)
        self.assertIn('recurring_gift_credit_integrity', data)
        self.assertIn('dashboard_impact', data)
        self.assertIn('verdict', data)

    def test_json_no_styled_text(self):
        """--json does not include styled text output (section headers)."""
        missionary = UserFactory(role=UserRole.MISSIONARY)
        Solicitor.objects.create(
            normalized_name='Test, Sol',
            user=missionary,
        )

        out = StringIO()
        call_command('audit_import_health', '--json', stdout=out)
        output = out.getvalue()
        # Should not contain section header markers
        self.assertNotIn('===', output)
