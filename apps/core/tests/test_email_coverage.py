"""
Behavioral tests for apps.core.email send helpers.

The test settings use the locmem email backend, so real sends land in
django.core.mail.outbox. Failure paths are exercised with unittest.mock.
"""

from unittest import mock

from django.core import mail

import pytest

from apps.core.email import send_email, send_weekly_summary_email
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestSendEmail:
    """Tests for the generic send_email helper."""

    def test_sends_email_with_correct_recipient_and_subject(self):
        """A successful send delivers one message with the right to/subject/from."""
        result = send_email(
            subject="Hello There",
            to_email="recipient@example.com",
            template_name="weekly_summary",
            context={"user": UserFactory(), "summary": {}},
        )

        assert result is True
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.subject == "Hello There"
        assert message.to == ["recipient@example.com"]
        # Defaults to DEFAULT_FROM_EMAIL when from_email is not provided.
        assert message.from_email == "DonorCRM <noreply@donorcrm.app>"

    def test_uses_explicit_from_email_when_provided(self):
        """An explicit from_email overrides the configured default sender."""
        result = send_email(
            subject="Custom Sender",
            to_email="recipient@example.com",
            template_name="weekly_summary",
            context={"user": UserFactory(), "summary": {}},
            from_email="custom@example.com",
        )

        assert result is True
        assert mail.outbox[0].from_email == "custom@example.com"

    def test_attaches_html_alternative_when_template_exists(self):
        """weekly_summary has both .txt and .html, so an HTML alternative is attached."""
        send_email(
            subject="HTML Test",
            to_email="recipient@example.com",
            template_name="weekly_summary",
            context={"user": UserFactory(), "summary": {}},
        )

        message = mail.outbox[0]
        # The text body is the primary content; HTML is an attached alternative.
        assert message.body  # text content rendered
        assert len(message.alternatives) == 1
        _content, mimetype = message.alternatives[0]
        assert mimetype == "text/html"

    def test_no_html_alternative_when_html_template_missing(self):
        """password_reset ships only a .txt template — no HTML alternative attached."""
        send_email(
            subject="Text Only",
            to_email="recipient@example.com",
            template_name="password_reset",
            context={"reset_url": "https://example.com/reset", "user": UserFactory()},
        )

        assert len(mail.outbox) == 1
        assert mail.outbox[0].alternatives == []

    def test_returns_false_when_text_template_missing(self):
        """A missing text template makes render_to_string raise; send_email returns False."""
        result = send_email(
            subject="Broken",
            to_email="recipient@example.com",
            template_name="this_template_does_not_exist_xyz",
            context={},
        )

        assert result is False
        assert len(mail.outbox) == 0

    def test_returns_false_when_send_raises(self):
        """If the underlying email.send() raises, the helper swallows and returns False."""
        with mock.patch(
            "apps.core.email.EmailMultiAlternatives.send",
            side_effect=RuntimeError("SMTP down"),
        ):
            result = send_email(
                subject="Will Fail",
                to_email="recipient@example.com",
                template_name="weekly_summary",
                context={"user": UserFactory(), "summary": {}},
            )

        assert result is False
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestSendWeeklySummaryEmail:
    """Tests for the weekly summary convenience wrapper."""

    def test_builds_subject_and_recipient_from_user(self):
        """Subject embeds the user's first name; recipient is the user's email."""
        user = UserFactory(first_name="Grace", email="grace@example.com")
        summary = {
            "what_changed": {"new_gifts": 3},
            "needs_attention": {"overdue": 1},
            "at_risk_count": 2,
            "thank_you_count": 4,
            "support_progress": {"percent": 75},
        }

        result = send_weekly_summary_email(user, summary)

        assert result is True
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.subject == "DonorCRM Weekly Summary - Grace"
        assert message.to == ["grace@example.com"]

    def test_passes_summary_fields_into_send_email_context(self):
        """The wrapper maps summary_data fields into the template context dict."""
        user = UserFactory(first_name="Sam", email="sam@example.com")
        summary = {
            "what_changed": {"a": 1},
            "needs_attention": {"b": 2},
            "at_risk_count": 9,
            "thank_you_count": 7,
            "support_progress": {"percent": 50},
        }

        with mock.patch("apps.core.email.send_email", return_value=True) as send_mock:
            result = send_weekly_summary_email(user, summary)

        assert result is True
        send_mock.assert_called_once()
        kwargs = send_mock.call_args.kwargs
        assert kwargs["subject"] == "DonorCRM Weekly Summary - Sam"
        assert kwargs["to_email"] == "sam@example.com"
        assert kwargs["template_name"] == "weekly_summary"
        context = kwargs["context"]
        assert context["user"] is user
        assert context["at_risk_count"] == 9
        assert context["thank_you_count"] == 7
        assert context["what_changed"] == {"a": 1}
        assert context["needs_attention"] == {"b": 2}
        assert context["support_progress"] == {"percent": 50}

    def test_defaults_applied_for_missing_summary_keys(self):
        """Missing summary keys fall back to safe defaults (counts 0, dicts empty)."""
        user = UserFactory(first_name="Dana", email="dana@example.com")

        with mock.patch("apps.core.email.send_email", return_value=True) as send_mock:
            send_weekly_summary_email(user, {})

        context = send_mock.call_args.kwargs["context"]
        assert context["at_risk_count"] == 0
        assert context["thank_you_count"] == 0
        assert context["what_changed"] == {}
        assert context["needs_attention"] == {}
        assert context["support_progress"] == {}
