"""
Email service for DonorCRM notifications.
"""

import logging
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    """Mask a recipient address for logging (issue #119).

    Keeps only the first local-part character and the domain
    ("jane.doe@example.com" -> "j***@example.com"), so logs stay debuggable
    without writing raw donor addresses to disk. The domain is retained because
    it is operationally useful and not personally identifying.
    """
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    first = local[0] if local else ""
    return f"{first}***@{domain}"


def send_email(
    subject: str, to_email: str, template_name: str, context: dict, from_email: Optional[str] = None
) -> bool:
    """
    Send an email using a template.

    Args:
        subject: Email subject line
        to_email: Recipient email address
        template_name: Base name of template (without extension)
        context: Context dict for template rendering
        from_email: Optional sender email (defaults to DEFAULT_FROM_EMAIL)

    Returns:
        True if email sent successfully, False otherwise
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    try:
        # Render text version
        text_content = render_to_string(f"emails/{template_name}.txt", context)

        # Try to render HTML version (optional)
        try:
            html_content = render_to_string(f"emails/{template_name}.html", context)
        except Exception:
            html_content = None

        # Create email
        email = EmailMultiAlternatives(
            subject=subject, body=text_content, from_email=from_email, to=[to_email]
        )

        if html_content:
            email.attach_alternative(html_content, "text/html")

        email.send()
        logger.info("Email sent to %s: %s", _mask_email(to_email), subject)
        return True

    except Exception as e:
        # Log the exception class, not str(e): SMTP errors (e.g.
        # SMTPRecipientsRefused) embed the raw recipient address.
        logger.error("Failed to send email to %s: %s", _mask_email(to_email), type(e).__name__)
        return False


def send_weekly_summary_email(user, summary_data: dict) -> bool:
    """
    Send weekly summary email to a user.

    Args:
        user: User instance to send email to
        summary_data: Dashboard summary data dict

    Returns:
        True if email sent successfully, False otherwise
    """
    context = {
        "user": user,
        "summary": summary_data,
        "what_changed": summary_data.get("what_changed", {}),
        "needs_attention": summary_data.get("needs_attention", {}),
        "at_risk_count": summary_data.get("at_risk_count", 0),
        "thank_you_count": summary_data.get("thank_you_count", 0),
        "support_progress": summary_data.get("support_progress", {}),
    }

    return send_email(
        subject=f"DonorCRM Weekly Summary - {user.first_name}",
        to_email=user.email,
        template_name="weekly_summary",
        context=context,
    )
