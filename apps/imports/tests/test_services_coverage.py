"""
Behavioral coverage tests for apps/imports/services.py.

Targets currently-uncovered helpers and validation branches:
- sanitize_csv_value formula-injection prefixing
- _validate_email empty-allowed branch
- _parse_amount / _parse_date helpers (every error path)
- parse_contacts_csv length-limit and email-format/duplicate branches
- parse_funds_csv / parse_entities_csv empty-header (no fieldnames) branch

Each test asserts real, observable behavior: the sanitized value, the parsed
Decimal/date, or the specific validation error string returned.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.contacts.models import Contact
from apps.contacts.tests.factories import ContactFactory
from apps.imports.services import (
    _parse_amount,
    _parse_date,
    _validate_email,
    parse_contacts_csv,
    parse_entities_csv,
    parse_funds_csv,
    sanitize_csv_value,
)
from apps.users.tests.factories import UserFactory


class TestSanitizeCsvValue:
    """CSV formula-injection prevention."""

    @pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
    def test_formula_prefix_is_quoted(self, prefix):
        dangerous = f"{prefix}cmd|'/c calc'!A1"
        result = sanitize_csv_value(dangerous)
        assert result == "'" + dangerous

    def test_plain_value_unchanged(self):
        assert sanitize_csv_value("John Smith") == "John Smith"

    def test_non_string_passthrough(self):
        # Non-string inputs (e.g. int) must not be mangled.
        assert sanitize_csv_value(1234) == 1234

    def test_empty_and_none_passthrough(self):
        assert sanitize_csv_value("") == ""
        assert sanitize_csv_value(None) is None


class TestValidateEmail:
    """Email format validation, including the empty-allowed branch."""

    def test_empty_email_allowed(self):
        assert _validate_email("") is True

    def test_valid_email(self):
        assert _validate_email("a@b.com") is True

    def test_invalid_email(self):
        assert _validate_email("not-an-email") is False


class TestParseAmountHelper:
    """services._parse_amount returns (Decimal, error)."""

    def test_empty_required(self):
        amount, err = _parse_amount("")
        assert amount is None
        assert err == "Amount is required"

    def test_valid_with_currency_and_commas(self):
        amount, err = _parse_amount("$1,234.56")
        assert err is None
        assert amount == Decimal("1234.56")

    def test_negative_rejected(self):
        amount, err = _parse_amount("-5.00")
        assert amount is None
        assert err == "Amount cannot be negative"

    def test_zero_rejected(self):
        amount, err = _parse_amount("0")
        assert amount is None
        assert "greater than zero" in err

    def test_exceeds_maximum(self):
        amount, err = _parse_amount("10000000.00")
        assert amount is None
        assert "exceeds maximum" in err

    def test_invalid_format(self):
        amount, err = _parse_amount("abc")
        assert amount is None
        assert "Invalid amount format" in err


class TestParseDateHelper:
    """services._parse_date returns (date, error)."""

    def test_empty_required(self):
        parsed, err = _parse_date("")
        assert parsed is None
        assert err == "Date is required"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("2026-02-01", date(2026, 2, 1)),
            ("02/01/2026", date(2026, 2, 1)),
        ],
    )
    def test_valid_formats(self, raw, expected):
        parsed, err = _parse_date(raw)
        assert err is None
        assert parsed == expected

    def test_invalid_format(self):
        parsed, err = _parse_date("31/31/2026")
        assert parsed is None
        assert "Invalid date format" in err


@pytest.mark.django_db
class TestParseContactsValidationBranches:
    """parse_contacts_csv length-limit, email format, and duplicate branches."""

    def test_first_name_too_long(self):
        user = UserFactory()
        long_name = "x" * 151
        csv_content = f"first_name,last_name\n{long_name},Smith"
        valid, errors = parse_contacts_csv(csv_content, user)
        assert len(valid) == 0
        assert len(errors) == 1
        assert any("maximum length of 150" in e for e in errors[0]["errors"])

    def test_invalid_email_format(self):
        user = UserFactory()
        csv_content = "first_name,last_name,email\nJohn,Smith,bogus-email"
        valid, errors = parse_contacts_csv(csv_content, user)
        assert len(valid) == 0
        assert any("Invalid email format" in e for e in errors[0]["errors"])

    def test_duplicate_email_within_file(self):
        user = UserFactory()
        csv_content = (
            "first_name,last_name,email\n" "John,Smith,dup@example.com\n" "Jane,Doe,dup@example.com"
        )
        valid, errors = parse_contacts_csv(csv_content, user)
        # First row valid, second flagged as in-file duplicate.
        assert len(valid) == 1
        assert any("Duplicate email in file" in e for e in errors[0]["errors"])

    def test_phone_too_long(self):
        user = UserFactory()
        long_phone = "1" * 21
        csv_content = f"first_name,last_name,phone\nJohn,Smith,{long_phone}"
        valid, errors = parse_contacts_csv(csv_content, user)
        assert len(valid) == 0
        assert any("Phone number exceeds maximum length" in e for e in errors[0]["errors"])

    def test_postal_code_too_long(self):
        user = UserFactory()
        long_zip = "0" * 21
        csv_content = f"first_name,last_name,postal_code\nJohn,Smith,{long_zip}"
        valid, errors = parse_contacts_csv(csv_content, user)
        assert len(valid) == 0
        assert any("Postal code exceeds maximum length" in e for e in errors[0]["errors"])

    def test_existing_email_in_account_flagged(self):
        user = UserFactory()
        ContactFactory(owner=user, email="taken@example.com")
        csv_content = "first_name,last_name,email\nJohn,Smith,taken@example.com"
        valid, errors = parse_contacts_csv(csv_content, user)
        assert len(valid) == 0
        assert any("already exists in your account" in e for e in errors[0]["errors"])


@pytest.mark.django_db
class TestParseFundsHeaderBranches:
    """parse_funds_csv header / empty-file branches."""

    def test_empty_file_no_headers(self):
        # An empty string yields DictReader.fieldnames is None.
        valid, errors = parse_funds_csv("")
        assert len(valid) == 0
        assert errors[0]["errors"] == ["CSV file is empty or has no headers"]

    def test_missing_required_column(self):
        valid, errors = parse_funds_csv("fund_id\nF-1")
        assert len(valid) == 0
        assert "Missing required column" in errors[0]["errors"][0]


@pytest.mark.django_db
class TestParseEntitiesHeaderBranches:
    """parse_entities_csv header / empty-file branches."""

    def test_empty_file_no_headers(self):
        user = UserFactory()
        valid, errors = parse_entities_csv("", user)
        assert len(valid) == 0
        assert errors[0]["errors"] == ["CSV file is empty or has no headers"]

    def test_missing_required_column(self):
        user = UserFactory()
        valid, errors = parse_entities_csv("entity_id\nE-1", user)
        assert len(valid) == 0
        assert "Missing required column" in errors[0]["errors"][0]

    def test_single_word_name_splits_to_first_name_only(self):
        # Exercises the single-word name branch (last_name empty).
        user = UserFactory()
        valid, errors = parse_entities_csv("entity_id,name\nE-2,Cher", user)
        assert len(errors) == 0
        assert valid[0]["first_name"] == "Cher"
        assert valid[0]["last_name"] == ""


@pytest.mark.django_db
class TestImportContactsWritesOwner:
    """import_contacts persists records under the given owner (sanity behavior)."""

    def test_created_contact_belongs_to_owner(self):
        from apps.imports.services import import_contacts

        user = UserFactory()
        records = [
            {
                "first_name": "Pat",
                "last_name": "Lee",
                "email": "pat@example.com",
                "phone": "",
                "street_address": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "country": "USA",
                "notes": "",
            }
        ]
        count, contacts = import_contacts(records, user)
        assert count == 1
        assert Contact.objects.filter(owner=user, first_name="Pat").exists()
