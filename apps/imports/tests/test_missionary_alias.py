from django.db import IntegrityError
from django.test import TestCase

import pytest

from apps.imports.models import MissionaryAlias
from apps.users.models import User


class TestMissionaryAliasModel(TestCase):
    """Tests for MissionaryAlias model."""

    def _make_user(self, email="test@example.com", first="Test", last="User"):
        return User.objects.create_user(
            email=email,
            password="testpass123",
            first_name=first,
            last_name=last,
            role="missionary",
        )

    def test_source_name_unique(self):
        """source_name has unique constraint."""
        user = self._make_user()
        MissionaryAlias.objects.create(source_name="John Smith", user=user)
        with self.assertRaises(IntegrityError):
            MissionaryAlias.objects.create(source_name="John Smith", user=user)

    def test_null_user_means_unresolved(self):
        """user=None is distinct from 'never seen' — represents admin-flagged unresolved."""
        alias = MissionaryAlias.objects.create(source_name="Unknown Name", user=None)
        alias.refresh_from_db()
        self.assertIsNone(alias.user)
        # Verify it's stored intentionally with notes
        alias.notes = "Admin-flagged as unresolvable"
        alias.save()
        alias.refresh_from_db()
        self.assertEqual(alias.notes, "Admin-flagged as unresolvable")

    def test_str_representation(self):
        """__str__ shows source_name -> user."""
        user = self._make_user(email="john.smith@test.com", first="John", last="Smith")
        alias = MissionaryAlias.objects.create(source_name="J. Smith", user=user)
        self.assertIn("J. Smith", str(alias))
        self.assertIn("->", str(alias))

        # Also test with null user
        alias_null = MissionaryAlias.objects.create(source_name="Mystery Person", user=None)
        self.assertIn("Mystery Person", str(alias_null))
        self.assertIn("->", str(alias_null))
