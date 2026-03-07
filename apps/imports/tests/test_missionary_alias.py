from django.test import TestCase
from apps.imports.models import MissionaryAlias


class TestMissionaryAliasModel(TestCase):
    """Tests for MissionaryAlias model."""

    def test_source_name_unique(self):
        """source_name has unique constraint."""
        pass  # TODO: implement in plan 02

    def test_null_user_means_unresolved(self):
        """user=None is distinct from 'never seen' — represents admin-flagged unresolved."""
        pass  # TODO: implement in plan 02

    def test_str_representation(self):
        """__str__ shows source_name -> user."""
        pass  # TODO: implement in plan 02
