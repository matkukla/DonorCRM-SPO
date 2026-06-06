"""
Tests for custom password validators.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.validators import AlphanumericPasswordValidator


class AlphanumericPasswordValidatorTest(TestCase):
    def setUp(self):
        self.validator = AlphanumericPasswordValidator()

    def test_all_letter_password_raises_validation_error(self):
        """Password with only letters should fail (no number)."""
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("abcdefgh")
        self.assertEqual(ctx.exception.code, "password_no_number")

    def test_all_numeric_password_raises_validation_error(self):
        """Password with only numbers should fail (no letter)."""
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("12345678")
        self.assertEqual(ctx.exception.code, "password_no_letter")

    def test_mixed_alphanumeric_password_passes(self):
        """Password with both letters and numbers should pass."""
        # Should not raise
        self.validator.validate("abc12345")

    def test_password_with_special_chars_letters_numbers_passes(self):
        """Password with special characters, letters, and numbers should pass."""
        self.validator.validate("P@ssw0rd!#")

    def test_get_help_text(self):
        """get_help_text returns expected guidance string."""
        help_text = self.validator.get_help_text()
        self.assertEqual(
            help_text,
            "Your password must contain at least one letter and one number.",
        )
