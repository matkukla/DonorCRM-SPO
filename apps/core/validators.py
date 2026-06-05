"""
Custom password validators for DonorCRM.
"""
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class AlphanumericPasswordValidator:
    """
    Validate that the password contains at least one letter and one number.
    """

    def validate(self, password, user=None):
        if not re.search(r"[a-zA-Z]", password):
            raise ValidationError(
                _("Your password must contain at least one letter."),
                code="password_no_letter",
            )
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                _("Your password must contain at least one number."),
                code="password_no_number",
            )

    def get_help_text(self):
        return _("Your password must contain at least one letter and one number.")
