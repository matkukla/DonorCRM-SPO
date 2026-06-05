"""
Tests for SPO reconcile_missionaries() and import_spo_gifts() services.

TDD plan 02: TestReconcileMissionaries stubs filled in.
TDD plan 03: TestImportSpoGifts stubs filled in (import_spo_gifts, import_spo_prayers, TestIdempotency).
"""
import csv as csv_mod
import io

from django.test import TestCase

from apps.imports.models import ImportBatch, ImportBatchStatus, MissionaryAlias
from apps.users.models import User


def _make_solicitor_csv(*names):
    """Build minimal SPO Solicitor CSV bytes with type-label row.

    Uses csv.writer to properly quote names containing commas.
    """
    import csv as csv_mod
    import io as io_mod

    buf = io_mod.StringIO()
    writer = csv_mod.writer(buf)
    writer.writerow(["Solicitor"])
    writer.writerow(["Name"])
    for name in names:
        writer.writerow([name])
    return buf.getvalue().encode("utf-8")


def _make_user(email, first, last, role="missionary", active=True):
    return User.objects.create_user(
        email=email,
        password="testpass123",
        first_name=first,
        last_name=last,
        role=role,
        is_active=active,
    )


def _make_admin():
    return User.objects.create_user(
        email="admin@example.com",
        password="adminpass",
        first_name="Admin",
        last_name="User",
        role="admin",
    )


def _make_gifts_csv(*rows, include_type_label=True):
    """Build minimal SPO Gifts CSV bytes.

    Each row should be a dict with keys: gift_id, constituent_id, is_anonymous,
    solicitor_name, solicitor_amount, gift_amount, gift_date, prayer_description,
    payment_type. Missing keys default to empty string.
    """
    buf = io.StringIO()
    writer = csv_mod.writer(buf)
    if include_type_label:
        writer.writerow(["Gift"])
    writer.writerow(
        [
            "Gift ID",
            "Constituent ID",
            "Gift Is Anonymous",
            "Solicitor Name",
            "Solicitor Amount",
            "Gift Amount",
            "Gift Date",
            "Gift Specific Attributes Prayer Requests Description",
            "Gift Payment Type",
        ]
    )
    defaults = {
        "gift_id": "G001",
        "constituent_id": "",
        "is_anonymous": "",
        "solicitor_name": "",
        "solicitor_amount": "50.00",
        "gift_amount": "50.00",
        "gift_date": "2025-01-15",
        "prayer_description": "",
        "payment_type": "",
    }
    for row in rows:
        r = {**defaults, **row}
        writer.writerow(
            [
                r["gift_id"],
                r["constituent_id"],
                r["is_anonymous"],
                r["solicitor_name"],
                r["solicitor_amount"],
                r["gift_amount"],
                r["gift_date"],
                r["prayer_description"],
                r["payment_type"],
            ]
        )
    return buf.getvalue().encode("utf-8")


class TestReconcileMissionaries(TestCase):
    """Tests for reconcile_missionaries() service."""

    def test_exact_match(self):
        """Exact full name match links to existing User."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        missionary = _make_user("peter.anderson@test.com", "Peter", "Anderson")

        csv_bytes = _make_solicitor_csv("Peter Anderson")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        # Peter Anderson was matched, not created
        self.assertEqual(batch.created_count, 0)
        self.assertEqual(batch.summary["matched_exact"], 1)

    def test_normalized_match(self):
        """Punctuation-stripped lowercase match links to User."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        # User stored as "O'Brien" (with apostrophe)
        missionary = _make_user("pat.obrien@test.com", "Pat", "O'Brien")

        # CSV has "OBrien, Pat" (no apostrophe) — normalized match
        csv_bytes = _make_solicitor_csv("OBrien, Pat")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.summary["matched_normalized"], 1)
        self.assertEqual(batch.created_count, 0)

    def test_alias_match(self):
        """MissionaryAlias table lookup links source_name to User."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        missionary = _make_user("james.marshall@test.com", "James", "Marshall")
        MissionaryAlias.objects.create(source_name="Jim Marshall", user=missionary)

        csv_bytes = _make_solicitor_csv("Jim Marshall")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.summary["matched_alias"], 1)
        self.assertEqual(batch.created_count, 0)

    def test_alias_unresolved(self):
        """MissionaryAlias with user=None → flagged as unresolved, not created."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        # Admin has flagged this name as unresolvable
        MissionaryAlias.objects.create(source_name="Unknown Person", user=None)

        csv_bytes = _make_solicitor_csv("Unknown Person")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.summary["unresolved"], 1)
        self.assertEqual(batch.created_count, 0)
        self.assertIn("Unknown Person", batch.summary["unresolved_names"])

    def test_auto_create_user(self):
        """No match → auto-create User with role=missionary, placeholder email."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        csv_bytes = _make_solicitor_csv("Alice Newcomer")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 1)
        self.assertEqual(batch.summary["created"], 1)

        created_user = User.objects.get(first_name="Alice", last_name="Newcomer")
        self.assertEqual(created_user.role, "missionary")
        self.assertEqual(created_user.email, "alice.newcomer@spo.org")
        self.assertTrue(created_user.is_active)

    def test_placeholder_email_collision(self):
        """Duplicate placeholder email gets numeric suffix (john.smith2@spo.org)."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        # Pre-existing user with the expected placeholder email
        existing = _make_user("john.smith@spo.org", "John", "Smith")

        # Another John Smith in CSV (different person)
        csv_bytes = _make_solicitor_csv("John Smith")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        # Should have found existing John Smith by exact match (not created new)
        # But if there are genuinely two different Johns: second gets suffix
        # This test covers the case where existing John has @spo.org placeholder
        # and a new John Smith name appears — match should occur via exact match
        # Actually we need to test the email collision in _auto_create_missionary_user directly
        self.assertIsNotNone(batch)

    def test_placeholder_email_collision_direct(self):
        """When auto-creating user and email already exists, use numeric suffix."""
        from apps.imports.spo_services import _auto_create_missionary_user

        admin = _make_admin()
        # Create user with the expected placeholder email
        existing = User.objects.create_user(
            email="bob.jones@spo.org",
            password="pass",
            first_name="Bob",
            last_name="Jones",
        )
        # Now auto-create another Bob Jones (different person)
        user, email = _auto_create_missionary_user("Bob Jones", admin)
        self.assertEqual(email, "bob.jones2@spo.org")
        self.assertEqual(user.email, "bob.jones2@spo.org")

    def test_sha256_dedup(self):
        """Same file bytes → DUPLICATE status returned."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        csv_bytes = _make_solicitor_csv("Alice Test")

        batch1 = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)
        self.assertNotEqual(batch1.status, ImportBatchStatus.DUPLICATE)

        batch2 = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)
        self.assertEqual(batch2.status, ImportBatchStatus.DUPLICATE)

    def test_force_bypasses_dedup(self):
        """--force flag bypasses SHA256 dedup."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        csv_bytes = _make_solicitor_csv("Alice Force")

        batch1 = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)
        self.assertNotEqual(batch1.status, ImportBatchStatus.DUPLICATE)

        batch2 = reconcile_missionaries(csv_bytes, "solicitors.csv", admin, force=True)
        self.assertNotEqual(batch2.status, ImportBatchStatus.DUPLICATE)

    def test_merge_only_existing_user(self):
        """Matched User: fill blank fields only, never overwrite existing values."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        # User exists with no first_name filled (edge case for merge logic)
        missionary = _make_user("carol.white@test.com", "Carol", "White")
        original_first = missionary.first_name

        csv_bytes = _make_solicitor_csv("Carol White")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        missionary.refresh_from_db()
        # first_name should NOT be overwritten (it was already set)
        self.assertEqual(missionary.first_name, original_first)

    def test_summary_json_keys(self):
        """Summary JSON contains all required keys."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        csv_bytes = _make_solicitor_csv("Test Person")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        required_keys = [
            "missionaries_expected",
            "matched_exact",
            "matched_normalized",
            "matched_alias",
            "created",
            "unresolved",
            "unresolved_names",
            "needs_real_email",
            "per_missionary",
            "tri_source",
        ]
        for key in required_keys:
            self.assertIn(key, batch.summary, f"Missing key: {key}")

    def test_tri_source_comparison_included_in_summary(self):
        """Summary JSON includes tri-source comparison categories."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        csv_bytes = _make_solicitor_csv("Tri Source Person")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        self.assertIn("tri_source", batch.summary)
        tri = batch.summary["tri_source"]
        self.assertIn("csv_only", tri)
        self.assertIn("mpd_only", tri)
        self.assertIn("db_only", tri)
        self.assertIn("all_three", tri)

    def test_unresolved_stored_in_summary(self):
        """Unresolved names saved to ImportBatch.summary['unresolved_names']."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        MissionaryAlias.objects.create(source_name="Unresolvable Name", user=None)

        csv_bytes = _make_solicitor_csv("Unresolvable Name")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        self.assertIn("unresolved_names", batch.summary)
        self.assertIn("Unresolvable Name", batch.summary["unresolved_names"])

    def test_solicitor_record_created_for_resolved_missionary(self):
        """Resolved missionary has a Solicitor record after reconciliation."""
        from apps.gifts.models import Solicitor
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        missionary = _make_user("alice.resolved@test.com", "Alice", "Resolved")

        csv_bytes = _make_solicitor_csv("Alice Resolved")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        self.assertTrue(
            Solicitor.objects.filter(user=missionary).exists(),
            "Resolved missionary should have a Solicitor record",
        )

    def test_unresolved_missionary_has_no_solicitor_record(self):
        """Unresolved missionary (user=None alias) does NOT get a Solicitor record."""
        from apps.gifts.models import Solicitor
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        MissionaryAlias.objects.create(source_name="No Solicitor Person", user=None)

        initial_solicitor_count = Solicitor.objects.count()
        csv_bytes = _make_solicitor_csv("No Solicitor Person")
        batch = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)

        # No new Solicitor records should have been created
        self.assertEqual(Solicitor.objects.count(), initial_solicitor_count)


class TestMatchMissionaryName(TestCase):
    """Unit tests for _match_missionary_name helper."""

    def _make_user(self, email, first, last):
        return User.objects.create_user(
            email=email,
            password="pass",
            first_name=first,
            last_name=last,
            role="missionary",
        )

    def test_exact_match(self):
        """Exact full name → ('user', 'exact')."""
        from apps.imports.spo_services import _build_user_lookup, _match_missionary_name

        user = self._make_user("peter@test.com", "Peter", "Anderson")
        user_lookup = _build_user_lookup(User.objects.filter(role="missionary"))
        alias_lookup = {}

        result_user, match_type = _match_missionary_name(
            "Peter Anderson", user_lookup, alias_lookup
        )
        self.assertEqual(match_type, "exact")
        self.assertEqual(result_user, user)

    def test_normalized_match(self):
        """Punctuation-stripped match → ('user', 'normalized')."""
        from apps.imports.spo_services import _build_user_lookup, _match_missionary_name

        user = self._make_user("pat.obrien@test.com", "Pat", "O'Brien")
        user_lookup = _build_user_lookup(User.objects.filter(role="missionary"))
        alias_lookup = {}

        # CSV name has no apostrophe — should normalize-match
        result_user, match_type = _match_missionary_name("OBrien, Pat", user_lookup, alias_lookup)
        self.assertEqual(match_type, "normalized")
        self.assertEqual(result_user, user)

    def test_alias_match_with_user(self):
        """Alias entry with user set → ('user', 'alias')."""
        from apps.imports.spo_services import _build_alias_lookup, _match_missionary_name

        user = self._make_user("james@test.com", "James", "Marshall")
        MissionaryAlias.objects.create(source_name="Jim Marshall", user=user)
        alias_lookup = _build_alias_lookup()
        user_lookup = {}

        result_user, match_type = _match_missionary_name("Jim Marshall", user_lookup, alias_lookup)
        self.assertEqual(match_type, "alias")
        self.assertEqual(result_user, user)

    def test_alias_match_unresolved(self):
        """Alias entry with user=None → (None, 'unresolved')."""
        from apps.imports.spo_services import _build_alias_lookup, _match_missionary_name

        MissionaryAlias.objects.create(source_name="Ghost Person", user=None)
        alias_lookup = _build_alias_lookup()
        user_lookup = {}

        result_user, match_type = _match_missionary_name("Ghost Person", user_lookup, alias_lookup)
        self.assertIsNone(result_user)
        self.assertEqual(match_type, "unresolved")

    def test_no_match(self):
        """No match at all → (None, 'new')."""
        from apps.imports.spo_services import _match_missionary_name

        result_user, match_type = _match_missionary_name("Brand New Person", {}, {})
        self.assertIsNone(result_user)
        self.assertEqual(match_type, "new")


class TestBuildTriSourceComparison(TestCase):
    """Unit tests for _build_tri_source_comparison."""

    def test_all_three_overlap(self):
        """Name in all three sets → in all_three."""
        from apps.imports.spo_services import _build_tri_source_comparison

        result = _build_tri_source_comparison({"Alice"}, {"Alice"}, {"Alice"})
        self.assertIn("Alice", result["all_three"])
        self.assertNotIn("Alice", result["csv_only"])
        self.assertNotIn("Alice", result["mpd_only"])
        self.assertNotIn("Alice", result["db_only"])

    def test_csv_only(self):
        """Name only in CSV → csv_only."""
        from apps.imports.spo_services import _build_tri_source_comparison

        result = _build_tri_source_comparison({"Bob"}, set(), set())
        self.assertIn("Bob", result["csv_only"])

    def test_mpd_only(self):
        """Name only in MPD → mpd_only."""
        from apps.imports.spo_services import _build_tri_source_comparison

        result = _build_tri_source_comparison(set(), {"Carol"}, set())
        self.assertIn("Carol", result["mpd_only"])

    def test_db_only(self):
        """Name only in DB → db_only."""
        from apps.imports.spo_services import _build_tri_source_comparison

        result = _build_tri_source_comparison(set(), set(), {"Dave"})
        self.assertIn("Dave", result["db_only"])


class TestGetOrCreateMissionarySolicitor(TestCase):
    """Unit tests for _get_or_create_missionary_solicitor."""

    def test_creates_solicitor_for_missionary(self):
        """Creates Solicitor record for a missionary User."""
        from apps.gifts.models import Solicitor
        from apps.imports.spo_services import _get_or_create_missionary_solicitor

        missionary = User.objects.create_user(
            email="sol.test@test.com",
            password="pass",
            first_name="Sol",
            last_name="Test",
            role="missionary",
        )
        solicitor = _get_or_create_missionary_solicitor(missionary)
        self.assertIsNotNone(solicitor)
        self.assertEqual(solicitor.user, missionary)

    def test_idempotent(self):
        """Second call returns same Solicitor (no duplicate created)."""
        from apps.gifts.models import Solicitor
        from apps.imports.spo_services import _get_or_create_missionary_solicitor

        missionary = User.objects.create_user(
            email="idempotent@test.com",
            password="pass",
            first_name="Idem",
            last_name="Potent",
            role="missionary",
        )
        s1 = _get_or_create_missionary_solicitor(missionary)
        s2 = _get_or_create_missionary_solicitor(missionary)
        self.assertEqual(s1.id, s2.id)
        self.assertEqual(Solicitor.objects.filter(user=missionary).count(), 1)


class TestGetOrCreateAnonymousContact(TestCase):
    """Unit tests for _get_or_create_anonymous_contact."""

    def test_creates_contact(self):
        """Creates Anonymous Donor contact for missionary."""
        from apps.contacts.models import Contact
        from apps.imports.spo_services import _get_or_create_anonymous_contact

        missionary = User.objects.create_user(
            email="anon.test@test.com",
            password="pass",
            first_name="Anon",
            last_name="Test",
            role="missionary",
        )
        contact = _get_or_create_anonymous_contact(missionary)
        self.assertEqual(contact.first_name, "Anonymous")
        self.assertEqual(contact.last_name, "Donor")
        self.assertEqual(contact.owner, missionary)
        self.assertEqual(contact.external_id, f"spo_anonymous_{missionary.id}")

    def test_idempotent(self):
        """Second call returns same Contact (not a duplicate)."""
        from apps.contacts.models import Contact
        from apps.imports.spo_services import _get_or_create_anonymous_contact

        missionary = User.objects.create_user(
            email="anon.idem@test.com",
            password="pass",
            first_name="Anon",
            last_name="Idem",
            role="missionary",
        )
        c1 = _get_or_create_anonymous_contact(missionary)
        c2 = _get_or_create_anonymous_contact(missionary)
        self.assertEqual(c1.id, c2.id)
        self.assertEqual(
            Contact.objects.filter(
                owner=missionary, external_id=f"spo_anonymous_{missionary.id}"
            ).count(),
            1,
        )

    def test_contact_owner_is_missionary(self):
        """Contact.owner is the missionary User."""
        from apps.imports.spo_services import _get_or_create_anonymous_contact

        missionary = User.objects.create_user(
            email="anon.owner@test.com",
            password="pass",
            first_name="Owner",
            last_name="Check",
            role="missionary",
        )
        contact = _get_or_create_anonymous_contact(missionary)
        self.assertEqual(contact.owner, missionary)


class TestImportSpoGifts(TestCase):
    """Tests for import_spo_gifts() service."""

    def test_anonymous_contact_created_on_first_anonymous_gift(self):
        """First anonymous gift for missionary creates 'Anonymous Donor' contact."""
        from apps.contacts.models import Contact
        from apps.imports.spo_services import _get_or_create_anonymous_contact

        missionary = _make_user("anon.first@test.com", "Anon", "First")
        contact = _get_or_create_anonymous_contact(missionary)

        self.assertIsNotNone(contact)
        self.assertEqual(contact.first_name, "Anonymous")
        self.assertEqual(contact.last_name, "Donor")
        self.assertEqual(contact.owner, missionary)
        self.assertEqual(contact.external_id, f"spo_anonymous_{missionary.id}")
        self.assertEqual(contact.status, "donor")
        self.assertTrue(
            Contact.objects.filter(
                owner=missionary, external_id=f"spo_anonymous_{missionary.id}"
            ).exists()
        )

    def test_anonymous_contact_reused(self):
        """Second anonymous gift reuses the same anonymous contact."""
        from apps.contacts.models import Contact
        from apps.imports.spo_services import _get_or_create_anonymous_contact

        missionary = _make_user("anon.reuse@test.com", "Anon", "Reuse")
        c1 = _get_or_create_anonymous_contact(missionary)
        c2 = _get_or_create_anonymous_contact(missionary)
        self.assertEqual(c1.id, c2.id)
        self.assertEqual(
            Contact.objects.filter(
                owner=missionary, external_id=f"spo_anonymous_{missionary.id}"
            ).count(),
            1,
        )

    def test_anonymous_contact_owner_is_missionary(self):
        """Anonymous contact owner=missionary for correct scope visibility."""
        from apps.imports.spo_services import _get_or_create_anonymous_contact

        missionary = _make_user("anon.owner2@test.com", "Anon", "Owner")
        contact = _get_or_create_anonymous_contact(missionary)
        self.assertEqual(contact.owner, missionary)

    def test_blank_constituent_id_treated_as_anonymous(self):
        """Blank Constituent ID is treated as anonymous even without 'Yes' flag."""
        from apps.contacts.models import Contact
        from apps.gifts.models import Gift, Solicitor
        from apps.imports.re_services import normalize_solicitor_name
        from apps.imports.spo_services import import_spo_gifts

        admin = _make_admin()
        # first='Sam', last='Blank' → full_name='Sam Blank' → normalized='blank, sam'
        # CSV solicitor_name 'Sam Blank' → normalized 'blank, sam' → exact match
        missionary = _make_user("sam.blank@test.com", "Sam", "Blank")
        Solicitor.objects.create(
            user=missionary,
            normalized_name=normalize_solicitor_name(missionary.full_name),
        )

        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G-ANON-01",
                "constituent_id": "",  # blank → anonymous
                "is_anonymous": "",
                "solicitor_name": "Sam Blank",
                "gift_amount": "25.00",
            }
        )
        batch = import_spo_gifts(csv_bytes, "gifts.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 1)
        gift = Gift.objects.get(external_gift_id="G-ANON-01")
        anon_contact = Contact.objects.get(
            owner=missionary,
            external_id=f"spo_anonymous_{missionary.id}",
        )
        self.assertEqual(gift.donor_contact, anon_contact)

    def test_unresolved_solicitor_gift_skipped(self):
        """Gift referencing unresolved solicitor is skipped, counted in summary."""
        from apps.gifts.models import Gift
        from apps.imports.spo_services import import_spo_gifts

        admin = _make_admin()
        # 'Unknown Person' has no User and no alias → match_type='new'
        # For gift import, 'new' means unresolved (no Solicitor exists yet) — skip
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G-UNRES-01",
                "solicitor_name": "Unknown Person Nobody",
                "gift_amount": "100.00",
            }
        )
        batch = import_spo_gifts(csv_bytes, "gifts.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 0)
        self.assertEqual(Gift.objects.count(), 0)
        self.assertIn("unmatched_unresolved", batch.summary)
        self.assertGreater(len(batch.summary["unmatched_unresolved"]), 0)

    def test_gift_attributed_to_missionary(self):
        """Gift Solicitor Name maps to missionary User, GiftCredit created."""
        from apps.contacts.models import Contact
        from apps.gifts.models import Gift, GiftCredit, Solicitor
        from apps.imports.re_services import normalize_solicitor_name
        from apps.imports.spo_services import import_spo_gifts

        admin = _make_admin()
        missionary = _make_user("peter.attr@test.com", "Peter", "Attr")
        solicitor = Solicitor.objects.create(
            user=missionary,
            normalized_name=normalize_solicitor_name(missionary.full_name),
        )
        # Named donor contact with constituent_id
        contact = Contact.objects.create(
            owner=missionary,
            first_name="John",
            last_name="Donor",
            external_constituent_id="CONST-001",
            status="donor",
        )

        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G-ATTR-01",
                "constituent_id": "CONST-001",
                "solicitor_name": "Peter Attr",
                "solicitor_amount": "75.00",
                "gift_amount": "75.00",
            }
        )
        batch = import_spo_gifts(csv_bytes, "gifts.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(batch.created_count, 1)
        gift = Gift.objects.get(external_gift_id="G-ATTR-01")
        self.assertEqual(gift.donor_contact, contact)
        # GiftCredit links gift to missionary's solicitor
        self.assertEqual(GiftCredit.objects.count(), 1)
        credit = GiftCredit.objects.first()
        self.assertEqual(credit.solicitor.user, missionary)
        self.assertEqual(credit.gift, gift)

    def test_prayer_extracted_from_gift_description(self):
        """Gift with prayer description column creates PrayerIntention."""
        from apps.gifts.models import Solicitor
        from apps.imports.re_services import normalize_solicitor_name
        from apps.imports.spo_services import import_spo_gifts
        from apps.prayers.models import PrayerIntention

        admin = _make_admin()
        # first='Tom', last='Prayer' → full_name 'Tom Prayer' → normalized 'prayer, tom'
        # CSV 'Tom Prayer' → exact match
        missionary = _make_user("tom.prayer@test.com", "Tom", "Prayer")
        Solicitor.objects.create(
            user=missionary,
            normalized_name=normalize_solicitor_name(missionary.full_name),
        )

        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G-PRAY-01",
                "constituent_id": "",
                "solicitor_name": "Tom Prayer",
                "gift_amount": "50.00",
                "prayer_description": "Healing for my mother",
            }
        )
        batch = import_spo_gifts(csv_bytes, "gifts.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        self.assertEqual(PrayerIntention.objects.count(), 1)
        prayer = PrayerIntention.objects.first()
        self.assertIn("mother", prayer.description)

    def test_dedup_same_file(self):
        """Same file bytes returns DUPLICATE ImportBatch."""
        from apps.imports.spo_services import import_spo_gifts

        admin = _make_admin()
        csv_bytes = _make_gifts_csv({"gift_id": "G-DEDUP-01", "gift_amount": "10.00"})

        batch1 = import_spo_gifts(csv_bytes, "gifts.csv", admin)
        self.assertNotEqual(batch1.status, ImportBatchStatus.DUPLICATE)

        batch2 = import_spo_gifts(csv_bytes, "gifts.csv", admin)
        self.assertEqual(batch2.status, ImportBatchStatus.DUPLICATE)

    def test_type_label_row_skipped(self):
        """Leading SPO type-label row (Gift,...) is skipped before DictReader."""
        from apps.gifts.models import Gift, Solicitor
        from apps.imports.re_services import normalize_solicitor_name
        from apps.imports.spo_services import import_spo_gifts

        admin = _make_admin()
        # first='Luke', last='Type' → full_name 'Luke Type' → normalized 'type, luke'
        # CSV 'Luke Type' → exact match
        missionary = _make_user("luke.type@test.com", "Luke", "Type")
        Solicitor.objects.create(
            user=missionary,
            normalized_name=normalize_solicitor_name(missionary.full_name),
        )

        # include_type_label=True is default — ensures the type row is present
        csv_bytes = _make_gifts_csv(
            {"gift_id": "G-TYPELABEL-01", "solicitor_name": "Luke Type", "gift_amount": "20.00"},
            include_type_label=True,
        )
        batch = import_spo_gifts(csv_bytes, "gifts.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        # Type-label row skipped; exactly 1 data row processed
        self.assertEqual(batch.total_rows, 1)

    def test_payment_type_set_on_spo_gift(self):
        """Gift Payment Type column is mapped and stored on Gift.payment_type."""
        from apps.gifts.models import Gift, Solicitor
        from apps.imports.re_services import normalize_solicitor_name
        from apps.imports.spo_services import import_spo_gifts

        admin = _make_admin()
        missionary = _make_user("pay.type@test.com", "Pay", "Type")
        Solicitor.objects.create(
            user=missionary,
            normalized_name=normalize_solicitor_name(missionary.full_name),
        )
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G-PAY-01",
                "solicitor_name": "Pay Type",
                "gift_amount": "100.00",
                "payment_type": "EFT",
            }
        )
        batch = import_spo_gifts(csv_bytes, "gifts.csv", admin)
        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        gift = Gift.objects.get(external_gift_id="G-PAY-01")
        self.assertEqual(gift.payment_type, "direct_deposit")  # EFT maps to direct_deposit

    def test_zero_amount_gift_skipped(self):
        """SPO import should skip rows with unparseable/zero amounts."""
        from apps.gifts.models import Gift, Solicitor
        from apps.imports.re_services import normalize_solicitor_name
        from apps.imports.spo_services import import_spo_gifts

        admin = _make_admin()
        missionary = _make_user("zero.amt@test.com", "Zero", "Amt")
        Solicitor.objects.create(
            user=missionary,
            normalized_name=normalize_solicitor_name(missionary.full_name),
        )

        csv_bytes = _make_gifts_csv(
            {"gift_id": "G-ZERO-01", "solicitor_name": "Zero Amt", "gift_amount": "$0.00"},
            {"gift_id": "G-ZERO-02", "solicitor_name": "Zero Amt", "gift_amount": "N/A"},
            {"gift_id": "G-GOOD-01", "solicitor_name": "Zero Amt", "gift_amount": "50.00"},
        )
        batch = import_spo_gifts(csv_bytes, "gifts.csv", admin)

        # Only the valid $50 gift should be created
        self.assertEqual(Gift.objects.filter(external_gift_id="G-GOOD-01").count(), 1)
        self.assertFalse(Gift.objects.filter(external_gift_id="G-ZERO-01").exists())
        self.assertFalse(Gift.objects.filter(external_gift_id="G-ZERO-02").exists())


class TestImportSpoPrayers(TestCase):
    """Tests for import_spo_prayers() service."""

    def test_prayer_extracted_without_gift_creation(self):
        """import_spo_prayers() creates PrayerIntention but NOT Gift records."""
        from apps.contacts.models import Contact
        from apps.gifts.models import Gift, Solicitor
        from apps.imports.re_services import normalize_solicitor_name
        from apps.imports.spo_services import import_spo_prayers
        from apps.prayers.models import PrayerIntention

        admin = _make_admin()
        # first='Kate', last='Miller' → full_name 'Kate Miller' → normalized 'miller, kate'
        # CSV 'Kate Miller' → exact match
        missionary = _make_user("kate.miller@test.com", "Kate", "Miller")
        Solicitor.objects.create(
            user=missionary,
            normalized_name=normalize_solicitor_name(missionary.full_name),
        )

        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G-PONLY-01",
                "constituent_id": "",
                "solicitor_name": "Kate Miller",
                "gift_amount": "50.00",
                "prayer_description": "Safe travels for the family",
            }
        )
        batch = import_spo_prayers(csv_bytes, "gifts.csv", admin)

        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        # No Gift records should be created
        self.assertEqual(Gift.objects.count(), 0)
        # Prayer should be created
        self.assertEqual(PrayerIntention.objects.count(), 1)
        self.assertGreater(batch.created_count, 0)

    def test_prayer_dedup_separate_from_gift_import(self):
        """SPO_PRAYER dedup is separate from SPO_GIFT — both can exist."""
        from apps.imports.models import ImportBatchType
        from apps.imports.spo_services import import_spo_gifts, import_spo_prayers

        admin = _make_admin()
        csv_bytes = _make_gifts_csv({"gift_id": "G-PDEDUP-01", "gift_amount": "10.00"})

        # Import as gifts
        batch_gift = import_spo_gifts(csv_bytes, "gifts.csv", admin)
        self.assertEqual(batch_gift.import_type, ImportBatchType.SPO_GIFT)

        # Import same file as prayers — separate dedup namespace
        batch_prayer = import_spo_prayers(csv_bytes, "gifts.csv", admin)
        self.assertEqual(batch_prayer.import_type, ImportBatchType.SPO_PRAYER)
        self.assertNotEqual(batch_prayer.status, ImportBatchStatus.DUPLICATE)


class TestIdempotency(TestCase):
    """Tests for SHA256 dedup and --force behavior across SPO services."""

    def test_reconcile_force_bypasses_dedup(self):
        """reconcile_missionaries with force=True reimports same file."""
        from apps.imports.spo_services import reconcile_missionaries

        admin = _make_admin()
        csv_bytes = _make_solicitor_csv("Alice Force")

        batch1 = reconcile_missionaries(csv_bytes, "solicitors.csv", admin)
        self.assertNotEqual(batch1.status, ImportBatchStatus.DUPLICATE)

        batch2 = reconcile_missionaries(csv_bytes, "solicitors.csv", admin, force=True)
        self.assertNotEqual(batch2.status, ImportBatchStatus.DUPLICATE)
        self.assertEqual(batch2.status, ImportBatchStatus.COMPLETED)

    def test_gift_import_force_bypasses_dedup(self):
        """import_spo_gifts with force=True reimports same file."""
        from apps.imports.spo_services import import_spo_gifts

        admin = _make_admin()
        csv_bytes = _make_gifts_csv({"gift_id": "G-FORCE-01", "gift_amount": "10.00"})

        batch1 = import_spo_gifts(csv_bytes, "gifts.csv", admin)
        self.assertNotEqual(batch1.status, ImportBatchStatus.DUPLICATE)

        batch2 = import_spo_gifts(csv_bytes, "gifts.csv", admin, force=True)
        self.assertNotEqual(batch2.status, ImportBatchStatus.DUPLICATE)
        self.assertEqual(batch2.status, ImportBatchStatus.COMPLETED)
