"""
Tests for SPO management commands: reconcile_missionaries, import_spo_gifts, import_spo_prayers.

TDD plan 04: Stubs filled in.
"""
import csv as csv_mod
import io
import os
import tempfile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.imports.models import ImportBatch, ImportBatchStatus
from apps.users.models import User

# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def _make_solicitor_csv(*names):
    """Build minimal SPO Solicitor CSV bytes with type-label row."""
    buf = io.StringIO()
    writer = csv_mod.writer(buf)
    writer.writerow(["Solicitor"])
    writer.writerow(["Name"])
    for name in names:
        writer.writerow([name])
    return buf.getvalue().encode("utf-8")


def _make_gifts_csv(*rows, include_type_label=True):
    """Build minimal SPO Gifts CSV bytes."""
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
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.get("gift_id", ""),
                row.get("constituent_id", ""),
                row.get("is_anonymous", "No"),
                row.get("solicitor_name", ""),
                row.get("solicitor_amount", ""),
                row.get("gift_amount", "0.00"),
                row.get("gift_date", "2024-01-01"),
                row.get("prayer_description", ""),
            ]
        )
    return buf.getvalue().encode("utf-8")


def _make_admin():
    return User.objects.create_user(
        email="admin@example.com",
        password="adminpass",
        first_name="Admin",
        last_name="User",
        role="admin",
    )


def _write_temp_csv(content_bytes):
    """Write bytes to a temp file. Caller must delete."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, content_bytes)
    os.close(fd)
    return path


# ---------------------------------------------------------------------------
# TestReconcileMissionariesCommand
# ---------------------------------------------------------------------------


class TestReconcileMissionariesCommand(TestCase):
    """Integration tests for reconcile_missionaries management command."""

    def setUp(self):
        self.admin = _make_admin()

    def test_command_runs_successfully(self):
        """Command accepts file + --owner args, creates ImportBatch, prints summary."""
        csv_bytes = _make_solicitor_csv("Peter Anderson")
        path = _write_temp_csv(csv_bytes)
        try:
            out = io.StringIO()
            call_command("reconcile_missionaries", path, owner=self.admin.email, stdout=out)
            self.assertTrue(ImportBatch.objects.exists())
        finally:
            os.unlink(path)

    def test_force_flag_accepted(self):
        """--force flag accepted and passed to service without CommandError."""
        csv_bytes = _make_solicitor_csv("Peter Anderson")
        path = _write_temp_csv(csv_bytes)
        try:
            out = io.StringIO()
            # Run twice; second run with --force should not raise
            call_command("reconcile_missionaries", path, owner=self.admin.email, stdout=out)
            call_command(
                "reconcile_missionaries", path, owner=self.admin.email, force=True, stdout=out
            )
            # Force creates a new batch (old one deleted)
            self.assertEqual(ImportBatch.objects.count(), 1)
        finally:
            os.unlink(path)

    def test_missing_owner_raises_error(self):
        """Missing --owner (unknown email) raises CommandError."""
        csv_bytes = _make_solicitor_csv("Peter Anderson")
        path = _write_temp_csv(csv_bytes)
        try:
            with self.assertRaises(CommandError):
                call_command("reconcile_missionaries", path, owner="nobody@example.com")
        finally:
            os.unlink(path)

    def test_zero_donation_flag_in_output(self):
        """_print_summary shows 'ZERO DONATIONS' for missionaries with gifts_imported==0."""
        from unittest.mock import MagicMock

        from apps.imports.management.commands.reconcile_missionaries import Command

        # Build a fake batch with a per_missionary entry where gifts_imported=0
        batch = MagicMock()
        batch.status = ImportBatchStatus.COMPLETED
        batch.filename = "test.csv"
        batch.created_count = 1
        batch.updated_count = 0
        batch.skipped_count = 0
        batch.error_count = 0
        batch.id = "test-batch-id"
        batch.summary = {
            "missionaries_expected": 2,
            "matched_exact": 1,
            "matched_normalized": 0,
            "matched_alias": 0,
            "created": 1,
            "unresolved": 0,
            "unresolved_names": [],
            "per_missionary": [
                {
                    "name": "Peter Anderson",
                    "match_type": "exact",
                    "action": "matched",
                    "gifts_imported": 12,
                },
                {
                    "name": "John Smith",
                    "match_type": "created",
                    "action": "created",
                    "gifts_imported": 0,
                },
            ],
        }

        cmd = Command()
        cmd.style = MagicMock()
        # Make style.WARNING return a recognizable string
        cmd.style.WARNING = lambda s: f"WARNING:{s}"
        cmd.style.SUCCESS = lambda s: f"SUCCESS:{s}"
        cmd.style.ERROR = lambda s: f"ERROR:{s}"

        out = io.StringIO()
        cmd._print_summary(batch, out)
        output = out.getvalue()

        self.assertIn("ZERO DONATIONS", output)
        self.assertNotIn(
            "ZERO DONATIONS",
            output.split("Peter Anderson")[0] if "Peter Anderson" in output else "",
        )
        # Ensure it's on the John Smith line
        lines = output.splitlines()
        john_lines = [l for l in lines if "John Smith" in l]
        self.assertTrue(
            any("ZERO DONATIONS" in l for l in john_lines),
            f"Expected 'ZERO DONATIONS' near 'John Smith' in output:\n{output}",
        )


# ---------------------------------------------------------------------------
# TestImportSpoGiftsCommand
# ---------------------------------------------------------------------------


class TestImportSpoGiftsCommand(TestCase):
    """Integration tests for import_spo_gifts management command."""

    def setUp(self):
        self.admin = _make_admin()
        # Create a missionary user so the solicitor name resolves
        self.missionary = User.objects.create_user(
            email="peter.anderson@spo.org",
            password="testpass",
            first_name="Peter",
            last_name="Anderson",
            role="missionary",
            is_active=True,
        )

    def test_command_runs_successfully(self):
        """Command accepts file + --owner args, creates ImportBatch."""
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G001",
                "solicitor_name": "Anderson, Peter",
                "gift_amount": "100.00",
                "gift_date": "2024-01-15",
                "is_anonymous": "Yes",
            }
        )
        path = _write_temp_csv(csv_bytes)
        try:
            out = io.StringIO()
            call_command("import_spo_gifts", path, owner=self.admin.email, stdout=out)
            self.assertTrue(ImportBatch.objects.exists())
        finally:
            os.unlink(path)

    def test_force_flag_accepted(self):
        """--force flag accepted without CommandError."""
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G002",
                "solicitor_name": "Anderson, Peter",
                "gift_amount": "50.00",
                "gift_date": "2024-02-01",
                "is_anonymous": "Yes",
            }
        )
        path = _write_temp_csv(csv_bytes)
        try:
            out = io.StringIO()
            call_command("import_spo_gifts", path, owner=self.admin.email, stdout=out)
            call_command("import_spo_gifts", path, owner=self.admin.email, force=True, stdout=out)
            self.assertEqual(ImportBatch.objects.count(), 1)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# TestImportSpoPrayersCommand
# ---------------------------------------------------------------------------


class TestImportSpoPrayersCommand(TestCase):
    """Integration tests for import_spo_prayers management command."""

    def setUp(self):
        self.admin = _make_admin()

    def test_command_runs_successfully(self):
        """Command accepts file + --owner args, creates ImportBatch."""
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G003",
                "solicitor_name": "Some Missionary",
                "gift_amount": "75.00",
                "gift_date": "2024-03-01",
                "is_anonymous": "Yes",
                "prayer_description": "",
            }
        )
        path = _write_temp_csv(csv_bytes)
        try:
            out = io.StringIO()
            call_command("import_spo_prayers", path, owner=self.admin.email, stdout=out)
            self.assertTrue(ImportBatch.objects.exists())
        finally:
            os.unlink(path)

    def test_force_flag_accepted(self):
        """--force flag accepted without CommandError."""
        csv_bytes = _make_gifts_csv(
            {
                "gift_id": "G004",
                "solicitor_name": "Some Missionary",
                "gift_amount": "25.00",
                "gift_date": "2024-04-01",
                "is_anonymous": "Yes",
            }
        )
        path = _write_temp_csv(csv_bytes)
        try:
            out = io.StringIO()
            call_command("import_spo_prayers", path, owner=self.admin.email, stdout=out)
            call_command("import_spo_prayers", path, owner=self.admin.email, force=True, stdout=out)
            self.assertEqual(ImportBatch.objects.count(), 1)
        finally:
            os.unlink(path)
