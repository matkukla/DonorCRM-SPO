from django.test import TestCase


class TestReconcileMissionariesCommand(TestCase):
    """Integration tests for reconcile_missionaries management command."""

    def test_command_runs_successfully(self):
        """Command accepts file + --owner args, prints summary."""
        pass  # TODO: plan 04

    def test_force_flag_accepted(self):
        """--force flag accepted and passed to service."""
        pass  # TODO: plan 04

    def test_missing_owner_raises_error(self):
        """Missing --owner raises CommandError."""
        pass  # TODO: plan 04


class TestImportSpoGiftsCommand(TestCase):
    """Integration tests for import_spo_gifts management command."""

    def test_command_runs_successfully(self):
        pass  # TODO: plan 04

    def test_force_flag_accepted(self):
        pass  # TODO: plan 04


class TestImportSpoPrayersCommand(TestCase):
    """Integration tests for import_spo_prayers management command."""

    def test_command_runs_successfully(self):
        pass  # TODO: plan 04
