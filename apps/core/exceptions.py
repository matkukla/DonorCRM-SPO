"""
Custom exceptions for DonorCRM.
"""
from rest_framework.exceptions import APIException


class DuplicateRecordError(APIException):
    """Raised when attempting to create a duplicate record."""
    status_code = 409
    default_detail = 'A record with this identifier already exists.'
    default_code = 'duplicate_record'


class ImportValidationError(APIException):
    """Raised when CSV import validation fails."""
    status_code = 400
    default_detail = 'Import validation failed.'
    default_code = 'import_validation_error'
