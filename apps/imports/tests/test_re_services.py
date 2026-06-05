"""
Tests for RE import pipeline services.

Covers all 4 RE import functions with minimal CSV inputs:
- import_re_constituents
- import_re_solicitors
- import_re_gifts
- import_re_recurring_gifts

Plus SHA256 dedup and malformed CSV handling.
"""
from datetime import date

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import Gift, RecurringGift, Solicitor
from apps.imports.models import ImportBatch, ImportBatchStatus, ImportBatchType
from apps.imports.re_services import (
    import_re_constituents,
    import_re_gifts,
    import_re_recurring_gifts,
    import_re_solicitors,
)
from apps.users.tests.factories import AdminUserFactory, UserFactory


def _to_bytes(csv_str: str) -> bytes:
    """Convert a CSV string to bytes for import functions."""
    return csv_str.encode("utf-8")


@pytest.fixture
def admin_user():
    return AdminUserFactory(email="import-admin@test.com")


@pytest.fixture
def staff_user():
    return UserFactory(email="import-staff@test.com")


# ---------------------------------------------------------------------------
# import_re_solicitors tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestImportRESolicitors:
    """Test RE solicitor CSV import."""

    def test_import_solicitors_basic(self, admin_user):
        csv_data = _to_bytes(
            "Solicitor_Name,Solicitor_ID\n" '"Doe, John",SOL001\n' '"Smith, Jane",SOL002\n'
        )
        batch = import_re_solicitors(csv_data, "solicitors.csv", admin_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 2
        assert Solicitor.objects.filter(external_solicitor_id="SOL001").exists()
        assert Solicitor.objects.filter(external_solicitor_id="SOL002").exists()

    def test_import_solicitors_dedup_within_file(self, admin_user):
        csv_data = _to_bytes(
            "Solicitor_Name,Solicitor_ID\n" '"Doe, John",SOL001\n' '"Doe, John",SOL001\n'
        )
        batch = import_re_solicitors(csv_data, "solicitors.csv", admin_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 1
        assert batch.skipped_count == 1

    def test_import_solicitors_missing_name_header(self, admin_user):
        csv_data = _to_bytes("Some_Column,Another_Column\n" "foo,bar\n")
        batch = import_re_solicitors(csv_data, "bad.csv", admin_user)
        assert batch.status == ImportBatchStatus.FAILED

    def test_import_solicitors_empty_name_row(self, admin_user):
        """Rows with empty solicitor name are recorded as errors."""
        csv_data = _to_bytes("Solicitor_Name\n" "  \n" '"Smith, Jane"\n')
        batch = import_re_solicitors(csv_data, "solicitors.csv", admin_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 1
        # The whitespace-only row is counted as a row with missing name
        assert batch.total_rows == 2
        assert batch.error_count == 1


# ---------------------------------------------------------------------------
# import_re_constituents tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestImportREConstituents:
    """Test RE constituent CSV import."""

    def test_import_constituents_basic(self, admin_user, staff_user):
        csv_data = _to_bytes(
            "CnBio_ID,CnBio_First_Name,CnBio_Last_Name,CnAdrPrf_Email\n"
            "C001,Alice,Johnson,alice@example.com\n"
            "C002,Bob,Williams,bob@example.com\n"
        )
        batch = import_re_constituents(csv_data, "constituents.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 2
        assert Contact.objects.filter(external_constituent_id="C001", owner=staff_user).exists()
        assert Contact.objects.filter(external_constituent_id="C002", owner=staff_user).exists()

    def test_import_constituents_merge_existing(self, admin_user, staff_user):
        # Create existing contact with constituent ID
        Contact.objects.create(
            owner=staff_user,
            external_constituent_id="C001",
            first_name="Alice",
            last_name="Johnson",
            email="",  # blank -- will be filled
        )
        csv_data = _to_bytes(
            "CnBio_ID,CnBio_First_Name,CnBio_Last_Name,CnAdrPrf_Email\n"
            "C001,Alice,Johnson,alice@example.com\n"
        )
        batch = import_re_constituents(csv_data, "constituents.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.updated_count == 1
        assert batch.created_count == 0
        contact = Contact.objects.get(external_constituent_id="C001")
        assert contact.email == "alice@example.com"

    def test_import_constituents_missing_name_headers(self, admin_user, staff_user):
        csv_data = _to_bytes("Random_Column\n" "value\n")
        batch = import_re_constituents(csv_data, "bad.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.FAILED

    def test_import_constituents_row_with_no_name(self, admin_user, staff_user):
        csv_data = _to_bytes(
            "CnBio_ID,CnBio_First_Name,CnBio_Last_Name\n" "C001,,\n" "C002,Alice,Johnson\n"
        )
        batch = import_re_constituents(csv_data, "constituents.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 1
        assert batch.error_count == 1


# ---------------------------------------------------------------------------
# import_re_gifts tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestImportREGifts:
    """Test RE gift CSV import with multi-row grouping."""

    @pytest.fixture
    def setup_contact(self, staff_user):
        return Contact.objects.create(
            owner=staff_user,
            external_constituent_id="C001",
            first_name="Alice",
            last_name="Donor",
        )

    def test_import_gifts_basic(self, admin_user, staff_user, setup_contact):
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,GF_Amount,GF_Date\n"
            "G001,C001,100.00,2025-06-15\n"
            "G002,C001,250.00,2025-07-20\n"
        )
        batch = import_re_gifts(csv_data, "gifts.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 2
        assert Gift.objects.filter(external_gift_id="G001").exists()
        assert Gift.objects.filter(external_gift_id="G002").exists()

    def test_import_gifts_multi_row_grouping(self, admin_user, staff_user, setup_contact):
        # Create two solicitors for split-credit rows
        # normalize_solicitor_name("Doe, John") -> "doe, john"
        # normalize_solicitor_name("Smith, Jane") -> "smith, jane"
        Solicitor.objects.create(
            normalized_name="doe, john",
            external_solicitor_id="SOL001",
        )
        Solicitor.objects.create(
            normalized_name="smith, jane",
            external_solicitor_id="SOL002",
        )
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,GF_Amount,GF_Date,Solicitor_Name,Credit_Amount\n"
            'G001,C001,500.00,2025-06-15,"Doe, John",250.00\n'
            'G001,C001,500.00,2025-06-15,"Smith, Jane",250.00\n'
        )
        batch = import_re_gifts(csv_data, "gifts.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 1
        gift = Gift.objects.get(external_gift_id="G001")
        assert gift.amount_cents == 50000
        # Two different solicitors = two GiftCredit rows
        assert gift.credits.count() == 2

    def test_import_gifts_missing_constituent(self, admin_user, staff_user, setup_contact):
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,GF_Amount,GF_Date\n" "G001,C999,100.00,2025-06-15\n"
        )
        batch = import_re_gifts(csv_data, "gifts.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 0
        assert batch.error_count >= 1

    def test_import_gifts_missing_required_headers(self, admin_user, staff_user):
        csv_data = _to_bytes("Random_Header\n" "value\n")
        batch = import_re_gifts(csv_data, "bad.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.FAILED

    def test_import_gifts_invalid_amount(self, admin_user, staff_user, setup_contact):
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,GF_Amount,GF_Date\n" "G001,C001,not_a_number,2025-06-15\n"
        )
        batch = import_re_gifts(csv_data, "gifts.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 0
        assert batch.error_count >= 1


# ---------------------------------------------------------------------------
# import_re_recurring_gifts tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestImportRERecurringGifts:
    """Test RE recurring gift CSV import."""

    @pytest.fixture
    def setup_contact(self, staff_user):
        return Contact.objects.create(
            owner=staff_user,
            external_constituent_id="C001",
            first_name="Alice",
            last_name="Donor",
        )

    def test_import_recurring_gifts_basic(self, admin_user, staff_user, setup_contact):
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,Amount,Frequency,Start_Date,Status\n"
            "RG001,C001,200.00,Monthly,2025-01-01,Active\n"
            "RG002,C001,300.00,Quarterly,2025-03-01,Active\n"
        )
        batch = import_re_recurring_gifts(csv_data, "recurring.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 2
        rg1 = RecurringGift.objects.get(external_gift_id="RG001")
        assert rg1.amount_cents == 20000
        assert rg1.frequency == "monthly"
        rg2 = RecurringGift.objects.get(external_gift_id="RG002")
        assert rg2.frequency == "quarterly"

    def test_import_recurring_gifts_empty_frequency_defaults_monthly(
        self,
        admin_user,
        staff_user,
        setup_contact,
    ):
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,Amount,Frequency,Start_Date,Status\n"
            "RG001,C001,100.00,,2025-01-01,Active\n"
        )
        batch = import_re_recurring_gifts(csv_data, "recurring.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 1
        rg = RecurringGift.objects.get(external_gift_id="RG001")
        assert rg.frequency == "monthly"

    def test_import_recurring_gifts_empty_status_defaults_active(
        self,
        admin_user,
        staff_user,
        setup_contact,
    ):
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,Amount,Frequency,Start_Date,Status\n"
            "RG001,C001,100.00,Monthly,2025-01-01,\n"
        )
        batch = import_re_recurring_gifts(csv_data, "recurring.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 1
        rg = RecurringGift.objects.get(external_gift_id="RG001")
        assert rg.status == "active"

    def test_import_recurring_gifts_unknown_frequency_skips(
        self,
        admin_user,
        staff_user,
        setup_contact,
    ):
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,Amount,Frequency,Start_Date,Status\n"
            "RG001,C001,100.00,FortnightlyWeird,2025-01-01,Active\n"
        )
        batch = import_re_recurring_gifts(csv_data, "recurring.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 0
        assert batch.error_count >= 1

    def test_import_recurring_gifts_missing_headers(self, admin_user, staff_user):
        csv_data = _to_bytes("Bad_Header\n" "value\n")
        batch = import_re_recurring_gifts(csv_data, "bad.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.FAILED


# ---------------------------------------------------------------------------
# SHA256 dedup tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSHA256Dedup:
    """Test SHA256 dedup prevents reprocessing same file."""

    def test_solicitor_dedup_second_import_returns_duplicate(self, admin_user):
        csv_data = _to_bytes("Solicitor_Name\n" '"Doe, John"\n')
        batch1 = import_re_solicitors(csv_data, "solicitors.csv", admin_user)
        assert batch1.status == ImportBatchStatus.COMPLETED
        assert batch1.created_count == 1

        batch2 = import_re_solicitors(csv_data, "solicitors.csv", admin_user)
        assert batch2.status == ImportBatchStatus.DUPLICATE
        assert batch2.id == batch1.id  # Same batch returned

    def test_constituent_dedup_second_import_returns_duplicate(self, admin_user):
        staff_user = UserFactory(email="dedup-staff@test.com")
        csv_data = _to_bytes("CnBio_First_Name,CnBio_Last_Name\n" "Alice,Johnson\n")
        batch1 = import_re_constituents(csv_data, "constituents.csv", admin_user, staff_user)
        assert batch1.status == ImportBatchStatus.COMPLETED

        batch2 = import_re_constituents(csv_data, "constituents.csv", admin_user, staff_user)
        assert batch2.status == ImportBatchStatus.DUPLICATE
        assert batch2.id == batch1.id

    def test_gift_dedup_second_import_returns_duplicate(self, admin_user, staff_user):
        Contact.objects.create(
            owner=staff_user,
            external_constituent_id="C001",
            first_name="Test",
            last_name="Donor",
        )
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,GF_Amount,GF_Date\n" "G001,C001,100.00,2025-01-01\n"
        )
        batch1 = import_re_gifts(csv_data, "gifts.csv", admin_user, staff_user)
        assert batch1.status == ImportBatchStatus.COMPLETED

        batch2 = import_re_gifts(csv_data, "gifts.csv", admin_user, staff_user)
        assert batch2.status == ImportBatchStatus.DUPLICATE
        assert batch2.id == batch1.id


# ---------------------------------------------------------------------------
# Malformed CSV handling tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMalformedCSVHandling:
    """Test graceful error handling for bad CSV input."""

    def test_empty_csv_solicitors(self, admin_user):
        csv_data = _to_bytes("")
        batch = import_re_solicitors(csv_data, "empty.csv", admin_user)
        assert batch.status == ImportBatchStatus.FAILED

    def test_empty_csv_constituents(self, admin_user, staff_user):
        csv_data = _to_bytes("")
        batch = import_re_constituents(csv_data, "empty.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.FAILED

    def test_binary_garbage_solicitors(self, admin_user):
        csv_data = bytes(range(256))
        batch = import_re_solicitors(csv_data, "garbage.csv", admin_user)
        # Should not raise -- returns a batch with FAILED status or misparse
        assert batch is not None
        assert isinstance(batch, ImportBatch)

    def test_csv_with_null_bytes(self, admin_user):
        csv_data = b'Solicitor_Name\x00\n"Doe, John"\x00\n'
        batch = import_re_solicitors(csv_data, "nulls.csv", admin_user)
        # Null bytes are stripped by decode_csv_bytes, import should succeed
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 1


# ---------------------------------------------------------------------------
# Recurring gift prayer extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestImportRERecurringGiftsPrayers:
    """Test prayer extraction from recurring gift import."""

    @pytest.fixture
    def setup_contact(self, staff_user):
        return Contact.objects.create(
            owner=staff_user,
            external_constituent_id="C-PRAY-01",
            first_name="Prayer",
            last_name="Donor",
        )

    def test_prayer_extracted_from_recurring_gift(self, admin_user, staff_user, setup_contact):
        """Recurring gift with prayer_description creates PrayerIntention."""
        from apps.prayers.models import PrayerIntention

        csv_data = _to_bytes(
            "Recurring Gift\n"
            "Gift ID,Constituent ID,Amount,Frequency,Gift Date,Status,"
            "Gift Specific Attributes Prayer Requests Description\n"
            "RG-PRAY-01,C-PRAY-01,100.00,Monthly,2025-01-01,Active,Healing for family\n"
        )
        batch = import_re_recurring_gifts(csv_data, "recurring.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert PrayerIntention.objects.count() == 1
        prayer = PrayerIntention.objects.first()
        assert "Healing" in prayer.description
        assert prayer.contact == setup_contact
        # No gift M2M link — recurring gifts have no associated Gift record
        assert prayer.gifts.count() == 0

    def test_no_prayer_when_description_empty(self, admin_user, staff_user, setup_contact):
        """Recurring gift with empty prayer description creates no PrayerIntention."""
        from apps.prayers.models import PrayerIntention

        csv_data = _to_bytes(
            "Recurring Gift\n"
            "Gift ID,Constituent ID,Amount,Frequency,Gift Date,Status,"
            "Gift Specific Attributes Prayer Requests Description\n"
            "RG-NOPRAY-01,C-PRAY-01,100.00,Monthly,2025-01-01,Active,\n"
        )
        batch = import_re_recurring_gifts(csv_data, "recurring.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert PrayerIntention.objects.count() == 0

    def test_prayer_dedup_across_recurring_gifts(self, admin_user, staff_user, setup_contact):
        """Two recurring gifts with identical prayer text create one PrayerIntention."""
        from apps.prayers.models import PrayerIntention

        csv_data = _to_bytes(
            "Recurring Gift\n"
            "Gift ID,Constituent ID,Amount,Frequency,Gift Date,Status,"
            "Gift Specific Attributes Prayer Requests Description\n"
            "RG-DEDUP-01,C-PRAY-01,100.00,Monthly,2025-01-01,Active,Same prayer text\n"
            "RG-DEDUP-02,C-PRAY-01,200.00,Monthly,2025-02-01,Active,Same prayer text\n"
        )
        batch = import_re_recurring_gifts(csv_data, "recurring.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert PrayerIntention.objects.count() == 1


# ---------------------------------------------------------------------------
# Owner reassignment tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestImportREGiftsOwnerReassignment:
    """Test that import_re_gifts reassigns contact owner to the matched solicitor's user."""

    @pytest.fixture
    def admin1(self):
        return AdminUserFactory(email="admin1@test.com")

    @pytest.fixture
    def admin2(self):
        return AdminUserFactory(email="admin2@test.com")

    @pytest.fixture
    def missionary(self):
        return UserFactory(email="missionary@test.com")

    def test_reassigns_owner_when_imported_by_different_admin(
        self,
        admin1,
        admin2,
        missionary,
    ):
        """Contact owned by admin1 should be reassigned to missionary when gifts
        are imported by admin2 (cross-admin scenario from production Render bug)."""
        contact = Contact.objects.create(
            owner=admin1,
            external_constituent_id="C-REOWN-01",
            first_name="Cross",
            last_name="Admin",
        )
        solicitor = Solicitor.objects.create(
            normalized_name="doe, john",
            external_solicitor_id="SOL-REOWN-01",
            user=missionary,
        )
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,GF_Amount,GF_Date,Solicitor_Name,Credit_Amount\n"
            'G-REOWN-01,C-REOWN-01,100.00,2025-06-15,"Doe, John",100.00\n'
        )
        batch = import_re_gifts(csv_data, "gifts_reown.csv", admin2, admin2)
        assert batch.status == ImportBatchStatus.COMPLETED
        contact.refresh_from_db()
        assert contact.owner == missionary, f"Expected owner={missionary}, got {contact.owner}"

    def test_does_not_reassign_if_already_owned_by_missionary(
        self,
        admin1,
        missionary,
    ):
        """Contact already owned by a missionary (has Solicitor record) should NOT
        be reassigned to a different missionary."""
        # Create a Solicitor record for missionary (they are already a missionary)
        Solicitor.objects.create(
            normalized_name="existing, missionary",
            external_solicitor_id="SOL-EXIST-01",
            user=missionary,
        )
        contact = Contact.objects.create(
            owner=missionary,
            external_constituent_id="C-EXIST-01",
            first_name="Existing",
            last_name="Missionary",
        )
        # A different solicitor will try to claim the contact
        other_missionary = UserFactory(email="other-missionary@test.com")
        Solicitor.objects.create(
            normalized_name="other, solicitor",
            external_solicitor_id="SOL-OTHER-01",
            user=other_missionary,
        )
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,GF_Amount,GF_Date,Solicitor_Name,Credit_Amount\n"
            'G-EXIST-01,C-EXIST-01,200.00,2025-07-01,"Other, Solicitor",200.00\n'
        )
        batch = import_re_gifts(csv_data, "gifts_exist.csv", admin1, admin1)
        assert batch.status == ImportBatchStatus.COMPLETED
        contact.refresh_from_db()
        # Owner should remain the original missionary, not be changed to other_missionary
        assert (
            contact.owner == missionary
        ), f"Expected owner to remain {missionary}, got {contact.owner}"

    def test_no_reassign_if_no_solicitor_match(self, admin1):
        """If no solicitor credit in CSV, contact owner is unchanged."""
        contact = Contact.objects.create(
            owner=admin1,
            external_constituent_id="C-NOSOL-01",
            first_name="No",
            last_name="Solicitor",
        )
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,GF_Amount,GF_Date\n" "G-NOSOL-01,C-NOSOL-01,50.00,2025-08-01\n"
        )
        batch = import_re_gifts(csv_data, "gifts_nosol.csv", admin1, admin1)
        assert batch.status == ImportBatchStatus.COMPLETED
        contact.refresh_from_db()
        assert contact.owner == admin1, f"Expected owner to remain {admin1}, got {contact.owner}"


# ---------------------------------------------------------------------------
# Recurring gift owner reassignment tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestImportRERecurringGiftsOwnerReassignment:
    """Test that import_re_recurring_gifts reassigns contact owner
    to the matched solicitor's user (mirrors gift import behavior)."""

    @pytest.fixture
    def admin1(self):
        return AdminUserFactory(email="rg-admin1@test.com")

    @pytest.fixture
    def missionary(self):
        return UserFactory(email="rg-missionary@test.com")

    def test_recurring_gift_reassigns_contact_owner_from_admin(
        self,
        admin1,
        missionary,
    ):
        """Contact owned by admin should be reassigned to missionary when
        recurring gifts are imported with a solicitor linked to that missionary."""
        contact = Contact.objects.create(
            owner=admin1,
            external_constituent_id="C-RGREOWN-01",
            first_name="Recurring",
            last_name="Donor",
        )
        Solicitor.objects.create(
            normalized_name="doe, john",
            external_solicitor_id="SOL-RGREOWN-01",
            user=missionary,
        )
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,Amount,Frequency,Start_Date,Status,"
            "Solicitor_Name,Credit_Amount\n"
            "RG-REOWN-01,C-RGREOWN-01,200.00,Monthly,2025-01-01,Active,"
            '"Doe, John",200.00\n'
        )
        batch = import_re_recurring_gifts(csv_data, "rg_reown.csv", admin1, admin1)
        assert batch.status == ImportBatchStatus.COMPLETED
        contact.refresh_from_db()
        assert contact.owner == missionary, f"Expected owner={missionary}, got {contact.owner}"

    def test_recurring_gift_no_reassign_if_already_missionary(
        self,
        admin1,
        missionary,
    ):
        """Contact already owned by a missionary should NOT be reassigned."""
        Solicitor.objects.create(
            normalized_name="existing, missionary",
            external_solicitor_id="SOL-RGEXIST-01",
            user=missionary,
        )
        contact = Contact.objects.create(
            owner=missionary,
            external_constituent_id="C-RGEXIST-01",
            first_name="Already",
            last_name="Missionary",
        )
        other_missionary = UserFactory(email="rg-other@test.com")
        Solicitor.objects.create(
            normalized_name="other, solicitor",
            external_solicitor_id="SOL-RGOTHER-01",
            user=other_missionary,
        )
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,Amount,Frequency,Start_Date,Status,"
            "Solicitor_Name,Credit_Amount\n"
            "RG-EXIST-01,C-RGEXIST-01,150.00,Monthly,2025-01-01,Active,"
            '"Other, Solicitor",150.00\n'
        )
        batch = import_re_recurring_gifts(csv_data, "rg_exist.csv", admin1, admin1)
        assert batch.status == ImportBatchStatus.COMPLETED
        contact.refresh_from_db()
        assert (
            contact.owner == missionary
        ), f"Expected owner to remain {missionary}, got {contact.owner}"

    def test_recurring_gift_no_reassign_if_solicitor_unlinked(self, admin1):
        """If solicitor has no linked user, contact stays with admin."""
        contact = Contact.objects.create(
            owner=admin1,
            external_constituent_id="C-RGUNLINK-01",
            first_name="Unlinked",
            last_name="Solicitor",
        )
        Solicitor.objects.create(
            normalized_name="doe, john",
            external_solicitor_id="SOL-RGUNLINK-01",
            user=None,  # Not linked to any user
        )
        csv_data = _to_bytes(
            "Gift_ID,Constituent_ID,Amount,Frequency,Start_Date,Status,"
            "Solicitor_Name,Credit_Amount\n"
            "RG-UNLINK-01,C-RGUNLINK-01,100.00,Monthly,2025-01-01,Active,"
            '"Doe, John",100.00\n'
        )
        batch = import_re_recurring_gifts(csv_data, "rg_unlink.csv", admin1, admin1)
        assert batch.status == ImportBatchStatus.COMPLETED
        contact.refresh_from_db()
        assert contact.owner == admin1, f"Expected owner to remain {admin1}, got {contact.owner}"


# ---------------------------------------------------------------------------
# Constituent import skip details tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConstituentSkipDetails:
    """Test that skipped_details are included in constituent import summary."""

    def test_skip_fully_populated_includes_details(self, admin_user, staff_user):
        """When all fields are already populated, skip details include reason and match_type."""
        Contact.objects.create(
            owner=staff_user,
            external_constituent_id="C-SKIP-01",
            first_name="Alice",
            last_name="Johnson",
            email="alice@example.com",
            phone="555-0001",
            street_address="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="90210",
            country="US",
        )
        csv_data = _to_bytes(
            "Constituent_ID,First_Name,Last_Name,Email,Phone,"
            "Address,City,State,ZIP,Country\n"
            "C-SKIP-01,Alice,Johnson,alice@example.com,555-0001,"
            "123 Main St,Anytown,CA,90210,US\n"
        )
        batch = import_re_constituents(csv_data, "skip.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.skipped_count == 1
        assert batch.created_count == 0
        details = batch.summary["skipped_details"]
        assert len(details) == 1
        assert details[0]["reason"] == "all_fields_populated"
        assert details[0]["match_type"] == "constituent_id"
        assert details[0]["contact_name"] == "Alice Johnson"
        assert details[0]["constituent_id"] == "C-SKIP-01"

    def test_merge_partial_no_skip_details(self, admin_user, staff_user):
        """When merge fills blank fields, no skip details are recorded."""
        Contact.objects.create(
            owner=staff_user,
            external_constituent_id="C-MERGE-01",
            first_name="Bob",
            last_name="Williams",
            email="",  # blank -- will be filled
        )
        csv_data = _to_bytes(
            "Constituent_ID,First_Name,Last_Name,Email\n"
            "C-MERGE-01,Bob,Williams,bob@example.com\n"
        )
        batch = import_re_constituents(csv_data, "merge.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.updated_count == 1
        assert batch.skipped_count == 0
        assert batch.summary["skipped_details"] == []

    def test_no_skips_empty_details(self, admin_user, staff_user):
        """Fresh import with no pre-existing contacts has empty skipped_details."""
        csv_data = _to_bytes(
            "Constituent_ID,First_Name,Last_Name,Email\n"
            "C-NEW-01,Charlie,Brown,charlie@example.com\n"
        )
        batch = import_re_constituents(csv_data, "fresh.csv", admin_user, staff_user)
        assert batch.status == ImportBatchStatus.COMPLETED
        assert batch.created_count == 1
        assert batch.skipped_count == 0
        assert batch.summary["skipped_details"] == []
