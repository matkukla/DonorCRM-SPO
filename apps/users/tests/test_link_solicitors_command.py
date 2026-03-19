"""
Tests for the link_solicitors_and_reassign_owners management command.

Verifies that contact ownership is reassigned based on both GiftCredit
and RecurringGiftCredit records.
"""
from datetime import date

import pytest
from django.core.management import call_command

from apps.contacts.models import Contact
from apps.gifts.models import (
    Gift,
    GiftCredit,
    RecurringGift,
    RecurringGiftCredit,
    Solicitor,
)
from apps.users.tests.factories import AdminUserFactory, UserFactory


@pytest.fixture
def admin_user():
    return AdminUserFactory(email='cmd-admin@test.com')


@pytest.fixture
def missionary():
    return UserFactory(email='cmd-missionary@test.com', first_name='John', last_name='Doe')


@pytest.mark.django_db
class TestLinkSolicitorsCommand:
    """Test the link_solicitors_and_reassign_owners management command."""

    def test_reassigns_via_recurring_gift_credit_only(self, admin_user, missionary):
        """Contact with only RecurringGiftCredit (no GiftCredit) gets reassigned."""
        solicitor = Solicitor.objects.create(
            normalized_name='doe, john',
            external_solicitor_id='SOL-CMD-01',
            user=missionary,
        )
        contact = Contact.objects.create(
            owner=admin_user,
            external_constituent_id='C-CMD-01',
            first_name='Recurring',
            last_name='Only',
        )
        rg = RecurringGift.objects.create(
            external_gift_id='RG-CMD-01',
            donor_contact=contact,
            amount_cents=10000,
            frequency='monthly',
            start_date=date(2025, 1, 1),
            status='active',
        )
        RecurringGiftCredit.objects.create(
            recurring_gift=rg,
            solicitor=solicitor,
            amount_cents=10000,
        )

        call_command('link_solicitors_and_reassign_owners')

        contact.refresh_from_db()
        assert contact.owner == missionary, (
            f"Expected owner={missionary.email}, got {contact.owner.email}"
        )

    def test_reassigns_via_gift_credit_only(self, admin_user, missionary):
        """Contact with only GiftCredit (no RecurringGiftCredit) still works."""
        solicitor = Solicitor.objects.create(
            normalized_name='doe, john',
            external_solicitor_id='SOL-CMD-02',
            user=missionary,
        )
        contact = Contact.objects.create(
            owner=admin_user,
            external_constituent_id='C-CMD-02',
            first_name='Gift',
            last_name='Only',
        )
        gift = Gift.objects.create(
            external_gift_id='G-CMD-01',
            donor_contact=contact,
            amount_cents=50000,
            gift_date=date(2025, 6, 15),
        )
        GiftCredit.objects.create(
            gift=gift,
            solicitor=solicitor,
            amount_cents=50000,
        )

        call_command('link_solicitors_and_reassign_owners')

        contact.refresh_from_db()
        assert contact.owner == missionary

    def test_combined_credits_highest_total_wins(self, admin_user):
        """When two solicitors have credits, the one with highest combined total wins."""
        missionary_a = UserFactory(email='cmd-miss-a@test.com')
        missionary_b = UserFactory(email='cmd-miss-b@test.com')
        sol_a = Solicitor.objects.create(
            normalized_name='alpha, ann',
            external_solicitor_id='SOL-A',
            user=missionary_a,
        )
        sol_b = Solicitor.objects.create(
            normalized_name='beta, bob',
            external_solicitor_id='SOL-B',
            user=missionary_b,
        )
        contact = Contact.objects.create(
            owner=admin_user,
            external_constituent_id='C-CMD-03',
            first_name='Mixed',
            last_name='Credits',
        )
        # Sol A: GiftCredit $100
        gift = Gift.objects.create(
            external_gift_id='G-CMD-02',
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date(2025, 6, 15),
        )
        GiftCredit.objects.create(gift=gift, solicitor=sol_a, amount_cents=10000)

        # Sol B: RecurringGiftCredit $500 (higher total)
        rg = RecurringGift.objects.create(
            external_gift_id='RG-CMD-02',
            donor_contact=contact,
            amount_cents=50000,
            frequency='monthly',
            start_date=date(2025, 1, 1),
            status='active',
        )
        RecurringGiftCredit.objects.create(
            recurring_gift=rg, solicitor=sol_b, amount_cents=50000,
        )

        call_command('link_solicitors_and_reassign_owners')

        contact.refresh_from_db()
        assert contact.owner == missionary_b, (
            f"Expected owner={missionary_b.email} (highest total), "
            f"got {contact.owner.email}"
        )

    def test_skips_contact_with_no_credits(self, admin_user):
        """Contact with no GiftCredit or RecurringGiftCredit is skipped."""
        contact = Contact.objects.create(
            owner=admin_user,
            external_constituent_id='C-CMD-04',
            first_name='No',
            last_name='Credits',
        )

        call_command('link_solicitors_and_reassign_owners')

        contact.refresh_from_db()
        assert contact.owner == admin_user

    def test_dry_run_does_not_change_ownership(self, admin_user, missionary):
        """--dry-run previews changes without writing."""
        solicitor = Solicitor.objects.create(
            normalized_name='doe, john',
            external_solicitor_id='SOL-CMD-DRY',
            user=missionary,
        )
        contact = Contact.objects.create(
            owner=admin_user,
            external_constituent_id='C-CMD-DRY',
            first_name='Dry',
            last_name='Run',
        )
        rg = RecurringGift.objects.create(
            external_gift_id='RG-CMD-DRY',
            donor_contact=contact,
            amount_cents=10000,
            frequency='monthly',
            start_date=date(2025, 1, 1),
            status='active',
        )
        RecurringGiftCredit.objects.create(
            recurring_gift=rg, solicitor=solicitor, amount_cents=10000,
        )

        call_command('link_solicitors_and_reassign_owners', dry_run=True)

        contact.refresh_from_db()
        assert contact.owner == admin_user, "Dry run should not change ownership"
