"""Tests for apps.core.sentry_scrubbing — PII scrubbing in Sentry payloads."""
from __future__ import annotations

from apps.core import sentry_scrubbing


class TestEmailScrubbing:
    def test_plain_email_redacted(self):
        out = sentry_scrubbing._scrub_string("user alice@example.com submitted")
        assert "alice@example.com" not in out
        assert "[REDACTED]" in out

    def test_plus_address_redacted(self):
        out = sentry_scrubbing._scrub_string("alice+tag@sub.example.co.uk")
        assert "alice" not in out

    def test_no_email_unchanged(self):
        s = "no email here, just text"
        assert sentry_scrubbing._scrub_string(s) == s


class TestPhoneScrubbing:
    def test_us_dashes(self):
        assert "555-123-4567" not in sentry_scrubbing._scrub_string("call 555-123-4567")

    def test_us_parens(self):
        assert "(555)" not in sentry_scrubbing._scrub_string("ring (555) 123-4567")

    def test_us_plain(self):
        assert "5551234567" not in sentry_scrubbing._scrub_string("dial 5551234567 now")

    def test_ssn_lookalike_left_alone(self):
        # An SSN like 123-45-6789 shouldn't match the phone pattern.
        s = "ID 123-45-6789"
        assert sentry_scrubbing._scrub_string(s) == s


class TestNestedScrubbing:
    def test_dict_values_scrubbed(self):
        event = {
            "message": "user alice@example.com hit error",
            "tags": {"customer": "bob@example.com"},
            "extra": ["raw", "carol@example.org"],
        }
        scrubbed = sentry_scrubbing._scrub_value(event)
        assert "alice@example.com" not in scrubbed["message"]
        assert "bob@example.com" not in scrubbed["tags"]["customer"]
        assert "carol@example.org" not in scrubbed["extra"][1]

    def test_non_string_values_unchanged(self):
        event = {"count": 5, "ratio": 0.1, "ok": True}
        assert sentry_scrubbing._scrub_value(event) == event


class TestBeforeSendHook:
    def test_returns_event_dict(self):
        event = {"message": "user alice@example.com error"}
        out = sentry_scrubbing.before_send(event, {})
        assert "alice@example.com" not in out["message"]

    def test_breadcrumb_hook_scrubs(self):
        crumb = {"message": "logged email bob@example.com"}
        out = sentry_scrubbing.before_breadcrumb(crumb, {})
        assert "bob@example.com" not in out["message"]
