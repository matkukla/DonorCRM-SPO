"""Cross-user generic-import dedup scoping — security report #10/#11.

Generic contact/donation import dedup keyed only on (import_type, sha256_hash),
so a second user uploading byte-identical content collided with the first user's
batch and no record was created for the second owner (CWE-639). Dedup is now
scoped per uploader for generic import types.

Each test fails if the per-uploader scoping is reverted (project rule #1).
"""

from django.test import TestCase

from apps.contacts.models import Contact
from apps.gifts.models import Gift
from apps.imports.generic_services import import_generic_contacts, import_generic_donations
from apps.imports.models import ImportBatchStatus
from apps.users.models import User, UserRole

CONTACT_CSV = (
    "first_name,last_name,email,phone\n" "John,Smith,john@example.com,555-1234\n"
).encode("utf-8")

DONATION_CSV = ("email,amount,date\n" "john@example.com,100.00,2026-01-15\n").encode("utf-8")


def _make_user(email):
    return User.objects.create_user(
        email=email,
        password="testpass123",
        first_name="T",
        last_name="User",
        role=UserRole.MISSIONARY,
    )


class CrossUserContactDedupTests(TestCase):
    def setUp(self):
        self.user_a = _make_user("a-import@test.com")
        self.user_b = _make_user("b-import@test.com")

    def test_second_user_identical_csv_is_not_marked_duplicate(self):
        batch_a = import_generic_contacts(
            CONTACT_CSV, "contacts.csv", self.user_a, self.user_a, match_by="email"
        )
        batch_b = import_generic_contacts(
            CONTACT_CSV, "contacts.csv", self.user_b, self.user_b, match_by="email"
        )

        assert batch_a.status == ImportBatchStatus.COMPLETED
        # The cross-user upload must NOT be suppressed as a duplicate.
        assert batch_b.status == ImportBatchStatus.COMPLETED
        assert batch_b.id != batch_a.id
        assert batch_b.created_count == 1
        # Each owner gets their own contact.
        assert Contact.objects.filter(owner=self.user_b).count() == 1

    def test_same_user_identical_csv_still_dedups(self):
        first = import_generic_contacts(
            CONTACT_CSV, "contacts.csv", self.user_a, self.user_a, match_by="email"
        )
        second = import_generic_contacts(
            CONTACT_CSV, "contacts.csv", self.user_a, self.user_a, match_by="email"
        )
        # Same uploader re-uploading identical bytes is still caught.
        assert second.id == first.id
        assert second.status == ImportBatchStatus.DUPLICATE


class CrossUserDonationDedupTests(TestCase):
    def setUp(self):
        self.user_a = _make_user("a-don@test.com")
        self.user_b = _make_user("b-don@test.com")
        # Each user owns a contact matching the donation CSV email.
        for owner in (self.user_a, self.user_b):
            Contact.objects.create(
                owner=owner,
                first_name="John",
                last_name="Smith",
                email="john@example.com",
                status="donor",
            )

    def test_second_user_identical_donation_csv_creates_gift(self):
        batch_a = import_generic_donations(
            DONATION_CSV, "don.csv", self.user_a, self.user_a, match_by="email"
        )
        batch_b = import_generic_donations(
            DONATION_CSV, "don.csv", self.user_b, self.user_b, match_by="email"
        )

        assert batch_a.status == ImportBatchStatus.COMPLETED
        assert batch_b.status == ImportBatchStatus.COMPLETED
        assert batch_b.id != batch_a.id
        # The second owner's gift was actually created (not suppressed).
        assert Gift.objects.filter(donor_contact__owner=self.user_b).count() == 1
