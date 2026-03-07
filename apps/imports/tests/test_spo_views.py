from django.test import TestCase
from django.urls import reverse


class TestSPOMissionaryImportView(TestCase):
    """Tests for POST /api/imports/spo/missionaries/ view."""

    def test_requires_admin(self):
        pass  # TODO: plan 04

    def test_returns_batch_result(self):
        pass  # TODO: plan 04


class TestSPOGiftImportView(TestCase):
    """Tests for POST /api/imports/spo/gifts/ view."""

    def test_requires_admin(self):
        pass  # TODO: plan 04

    def test_returns_batch_result(self):
        pass  # TODO: plan 04


class TestSPOPrayerImportView(TestCase):
    """Tests for POST /api/imports/spo/prayers/ view."""

    def test_requires_admin(self):
        pass  # TODO: plan 04
