"""
Behavioral coverage tests for apps.contacts.services.

Covers find_duplicates_for_contact match-merging (a contact matched by both
email and phone keeps the highest confidence and accumulates reasons) and the
merge_contacts guard rails (self-merge, already-merged survivor) plus the
_merge_journal_contacts decision-conflict branch where the survivor already
owns a decision and the loser's is deleted.

These run on SQLite; the PostgreSQL TrigramSimilarity name-matching path is
skipped via ImportError in the service and is not exercised here.
"""
import pytest

from apps.contacts.services import find_duplicates_for_contact, merge_contacts
from apps.contacts.tests.factories import ContactFactory
from apps.journals.models import Decision, Journal, JournalContact
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestFindDuplicatesMatchMerging:
    """find_duplicates_for_contact dedups multiple signals onto one match."""

    def test_email_and_phone_match_same_contact_merges_reasons(self):
        """A contact matched by BOTH email and phone yields one result with
        both reasons and 'high' confidence (the _add_match dedup branch)."""
        user = UserFactory()
        contact = ContactFactory(owner=user, email="dup@example.com", phone="555-100-2000")
        results = find_duplicates_for_contact(
            contact_data={"email": "dup@example.com", "phone": "555-100-2000"},
            owner_id=user.id,
        )
        # Single contact, not duplicated across results
        assert len(results) == 1
        match = results[0]
        assert match["contact"].id == contact.id
        assert match["confidence"] == "high"
        # Both signals contributed reasons
        assert "Exact email match" in match["reasons"]
        assert "Exact phone match" in match["reasons"]

    def test_email_match_only(self):
        user = UserFactory()
        contact = ContactFactory(owner=user, email="solo@example.com", phone="")
        results = find_duplicates_for_contact(
            contact_data={"email": "solo@example.com"},
            owner_id=user.id,
        )
        assert len(results) == 1
        assert results[0]["contact"].id == contact.id
        assert results[0]["reasons"] == ["Exact email match"]

    def test_phone_secondary_match(self):
        """A phone query matching the secondary phone column is detected."""
        user = UserFactory()
        contact = ContactFactory(
            owner=user, email="", phone="555-111-2222", phone_secondary="555-333-4444"
        )
        results = find_duplicates_for_contact(
            contact_data={"phone": "555-333-4444"},
            owner_id=user.id,
        )
        assert len(results) == 1
        assert results[0]["contact"].id == contact.id
        assert results[0]["confidence"] == "high"

    def test_excludes_self(self):
        """exclude_id removes the edited contact from its own duplicate set."""
        user = UserFactory()
        contact = ContactFactory(owner=user, email="self@example.com")
        results = find_duplicates_for_contact(
            contact_data={"email": "self@example.com"},
            owner_id=user.id,
            exclude_id=contact.id,
        )
        assert results == []

    def test_scoped_to_owner(self):
        """Duplicates from other owners are never returned."""
        owner = UserFactory()
        other = UserFactory()
        ContactFactory(owner=other, email="shared@example.com")
        results = find_duplicates_for_contact(
            contact_data={"email": "shared@example.com"},
            owner_id=owner.id,
        )
        assert results == []

    def test_no_input_returns_empty(self):
        user = UserFactory()
        ContactFactory(owner=user, email="x@example.com")
        results = find_duplicates_for_contact(contact_data={}, owner_id=user.id)
        assert results == []


@pytest.mark.django_db
class TestMergeContactsGuards:
    """merge_contacts raises on invalid merge requests."""

    def test_self_merge_raises_value_error(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        with pytest.raises(ValueError, match="itself"):
            merge_contacts(contact.id, contact.id, merged_by=user)

    def test_survivor_already_merged_raises(self):
        user = UserFactory()
        survivor = ContactFactory(owner=user, is_merged=True)
        loser = ContactFactory(owner=user)
        with pytest.raises(ValueError, match="Survivor contact has already been merged"):
            merge_contacts(survivor.id, loser.id, merged_by=user)

    def test_missing_contact_raises_does_not_exist(self):
        import uuid

        from apps.contacts.models import Contact

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        with pytest.raises(Contact.DoesNotExist):
            merge_contacts(survivor.id, uuid.uuid4(), merged_by=user)


@pytest.mark.django_db
class TestMergeJournalDecisionConflict:
    """_merge_journal_contacts: survivor already has a decision -> loser's deleted."""

    def test_loser_decision_deleted_when_survivor_has_one(self):
        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        survivor_jc = JournalContact.objects.create(journal=journal, contact=survivor)
        loser_jc = JournalContact.objects.create(journal=journal, contact=loser)

        survivor_decision = Decision.objects.create(
            journal_contact=survivor_jc, amount="100.00", cadence="monthly", status="active"
        )
        loser_decision = Decision.objects.create(
            journal_contact=loser_jc, amount="50.00", cadence="monthly", status="pending"
        )

        merge_contacts(survivor.id, loser.id, merged_by=user)

        # Conflict: both JCs share the journal AND survivor already has a decision,
        # so the loser's decision is deleted (not transferred) and loser JC removed.
        assert not Decision.objects.filter(pk=loser_decision.pk).exists()
        assert Decision.objects.filter(pk=survivor_decision.pk).exists()
        assert not JournalContact.objects.filter(pk=loser_jc.pk).exists()

    def test_loser_decision_transferred_when_survivor_has_none(self):
        """No survivor decision -> loser's decision is reassigned, not deleted."""
        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        survivor_jc = JournalContact.objects.create(journal=journal, contact=survivor)
        loser_jc = JournalContact.objects.create(journal=journal, contact=loser)
        loser_decision = Decision.objects.create(
            journal_contact=loser_jc, amount="75.00", cadence="annually", status="active"
        )

        merge_contacts(survivor.id, loser.id, merged_by=user)

        loser_decision.refresh_from_db()
        assert loser_decision.journal_contact_id == survivor_jc.id
