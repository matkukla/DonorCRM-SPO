"""
Email service for DonorCRM notifications.
"""
import logging
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_email(
    subject: str,
    to_email: str,
    template_name: str,
    context: dict,
    from_email: Optional[str] = None
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
        text_content = render_to_string(f'emails/{template_name}.txt', context)

        # Try to render HTML version (optional)
        try:
            html_content = render_to_string(f'emails/{template_name}.html', context)
        except Exception:
            html_content = None

        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email]
        )

        if html_content:
            email.attach_alternative(html_content, 'text/html')

        email.send()
        logger.info(f'Email sent to {to_email}: {subject}')
        return True

    except Exception as e:
        logger.error(f'Failed to send email to {to_email}: {e}')
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
        'user': user,
        'summary': summary_data,
        'what_changed': summary_data.get('what_changed', {}),
        'needs_attention': summary_data.get('needs_attention', {}),
        'at_risk_count': summary_data.get('at_risk_count', 0),
        'thank_you_count': summary_data.get('thank_you_count', 0),
        'support_progress': summary_data.get('support_progress', {}),
    }

    return send_email(
        subject=f'DonorCRM Weekly Summary - {user.first_name}',
        to_email=user.email,
        template_name='weekly_summary',
        context=context
    )


def send_late_pledge_alert(user, pledge) -> bool:
    """
    Send alert email for late pledge.

    Args:
        user: User instance to notify
        pledge: Late pledge instance

    Returns:
        True if email sent successfully, False otherwise
    """
    context = {
        'user': user,
        'pledge': pledge,
        'contact': pledge.contact,
        'days_late': pledge.days_late,
    }

    return send_email(
        subject=f'Alert: Late Pledge from {pledge.contact.full_name}',
        to_email=user.email,
        template_name='late_pledge_alert',
        context=context
    )


def send_at_risk_donor_alert(user, contacts) -> bool:
    """
    Send alert email for at-risk donors.

    Args:
        user: User instance to notify
        contacts: List of at-risk contact instances

    Returns:
        True if email sent successfully, False otherwise
    """
    context = {
        'user': user,
        'contacts': contacts,
        'count': len(contacts),
    }

    return send_email(
        subject=f'Alert: {len(contacts)} At-Risk Donors Need Attention',
        to_email=user.email,
        template_name='at_risk_donors_alert',
        context=context
    )


def send_password_reset_email(user, reset_token: str, reset_url: str) -> bool:
    """
    Send password reset email.

    Args:
        user: User requesting password reset
        reset_token: Password reset token
        reset_url: Full URL for password reset

    Returns:
        True if email sent successfully, False otherwise
    """
    context = {
        'user': user,
        'reset_token': reset_token,
        'reset_url': reset_url,
    }

    return send_email(
        subject='DonorCRM Password Reset Request',
        to_email=user.email,
        template_name='password_reset',
        context=context
    )
