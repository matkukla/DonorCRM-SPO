"""
Custom exceptions for DonorCRM.
"""
import logging

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Catch Django ValidationErrors and unexpected exceptions to prevent
    internal details from leaking in API responses."""
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    logger.exception("Unhandled exception in API view")
    return Response(
        {"detail": "An unexpected error occurred."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class DuplicateRecordError(APIException):
    """Raised when attempting to create a duplicate record."""

    status_code = 409
    default_detail = "A record with this identifier already exists."
    default_code = "duplicate_record"


class ImportValidationError(APIException):
    """Raised when CSV import validation fails."""

    status_code = 400
    default_detail = "Import validation failed."
    default_code = "import_validation_error"
