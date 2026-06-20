"""
Email recipient addresses must not be written raw to logs (issue #119).
"""

from unittest.mock import patch

from django.test import TestCase

from apps.core.email import _mask_email, send_email


class MaskEmailTests(TestCase):
    def test_masks_local_part_keeps_domain(self):
        self.assertEqual(_mask_email("jane.doe@example.com"), "j***@example.com")

    def test_handles_missing_at_and_empty(self):
        self.assertEqual(_mask_email("not-an-email"), "***")
        self.assertEqual(_mask_email(""), "***")


class SendEmailLoggingTests(TestCase):
    @patch("apps.core.email.render_to_string", return_value="body")
    def test_success_log_masks_recipient(self, _render):
        # render succeeds, locmem backend "sends" -> success/INFO path.
        with self.assertLogs("apps.core.email", level="INFO") as cm:
            ok = send_email(
                subject="Welcome",
                to_email="secret.donor@example.com",
                template_name="any",
                context={},
            )
        joined = "\n".join(cm.output)
        self.assertTrue(ok)
        self.assertNotIn("secret.donor@example.com", joined)
        self.assertIn("s***@example.com", joined)

    @patch("apps.core.email.render_to_string", return_value="body")
    def test_failure_log_masks_recipient_and_omits_exception_text(self, _render):
        # Force the send to raise with the raw recipient embedded in the message,
        # mimicking SMTPRecipientsRefused.
        with patch(
            "apps.core.email.EmailMultiAlternatives.send",
            side_effect=Exception("rejected: secret.donor@example.com"),
        ):
            with self.assertLogs("apps.core.email", level="ERROR") as cm:
                ok = send_email(
                    subject="Welcome",
                    to_email="secret.donor@example.com",
                    template_name="any",
                    context={},
                )
        joined = "\n".join(cm.output)
        self.assertFalse(ok)
        self.assertNotIn("secret.donor@example.com", joined)
        self.assertIn("s***@example.com", joined)
        # The raw exception text is not logged -- only its class name.
        self.assertIn("Exception", joined)
        self.assertNotIn("rejected:", joined)
