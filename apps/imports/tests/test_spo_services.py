from django.test import TestCase


class TestReconcileMissionaries(TestCase):
    """Tests for reconcile_missionaries() service."""

    def test_exact_match(self):
        """Exact full name match links to existing User."""
        pass  # TODO: plan 02

    def test_normalized_match(self):
        """Punctuation-stripped lowercase match links to User."""
        pass  # TODO: plan 02

    def test_alias_match(self):
        """MissionaryAlias table lookup links source_name to User."""
        pass  # TODO: plan 02

    def test_alias_unresolved(self):
        """MissionaryAlias with user=None → flagged as unresolved, not created."""
        pass  # TODO: plan 02

    def test_auto_create_user(self):
        """No match → auto-create User with role=missionary, placeholder email."""
        pass  # TODO: plan 02

    def test_placeholder_email_collision(self):
        """Duplicate placeholder email gets numeric suffix (john.smith2@spo.org)."""
        pass  # TODO: plan 02

    def test_sha256_dedup(self):
        """Same file bytes → DUPLICATE status returned."""
        pass  # TODO: plan 02

    def test_force_bypasses_dedup(self):
        """--force flag bypasses SHA256 dedup."""
        pass  # TODO: plan 02

    def test_merge_only_existing_user(self):
        """Matched User: fill blank fields only, never overwrite existing values."""
        pass  # TODO: plan 02

    def test_tri_source_comparison_included_in_summary(self):
        """Summary JSON includes tri-source comparison categories."""
        pass  # TODO: plan 02

    def test_unresolved_stored_in_summary(self):
        """Unresolved names saved to ImportBatch.summary['unresolved_names']."""
        pass  # TODO: plan 02


class TestImportSpoGifts(TestCase):
    """Tests for import_spo_gifts() service."""

    def test_anonymous_contact_created_on_first_anonymous_gift(self):
        """First anonymous gift for missionary creates 'Anonymous Donor' contact."""
        pass  # TODO: plan 03

    def test_anonymous_contact_reused(self):
        """Second anonymous gift reuses the same anonymous contact."""
        pass  # TODO: plan 03

    def test_anonymous_contact_owner_is_missionary(self):
        """Anonymous contact owner=missionary for correct scope visibility."""
        pass  # TODO: plan 03

    def test_blank_constituent_id_treated_as_anonymous(self):
        """Blank Constituent ID is treated as anonymous even without 'Yes' flag."""
        pass  # TODO: plan 03

    def test_unresolved_solicitor_gift_skipped(self):
        """Gift referencing unresolved solicitor is skipped, counted in summary."""
        pass  # TODO: plan 03

    def test_gift_attributed_to_missionary(self):
        """Gift Solicitor Name maps to missionary User, GiftCredit created."""
        pass  # TODO: plan 03

    def test_prayer_extracted_from_gift_description(self):
        """Gift with prayer description column creates PrayerIntention."""
        pass  # TODO: plan 03

    def test_dedup_same_file(self):
        """Same file bytes returns DUPLICATE ImportBatch."""
        pass  # TODO: plan 03

    def test_type_label_row_skipped(self):
        """Leading SPO type-label row is skipped before DictReader."""
        pass  # TODO: plan 03


class TestIdempotency(TestCase):
    """Tests for SHA256 dedup and --force behavior across SPO services."""

    def test_reconcile_force_bypasses_dedup(self):
        """reconcile_missionaries with force=True reimports same file."""
        pass  # TODO: plan 03

    def test_gift_import_force_bypasses_dedup(self):
        """import_spo_gifts with force=True reimports same file."""
        pass  # TODO: plan 03
