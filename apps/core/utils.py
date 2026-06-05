"""
Shared utility functions for the DonorCRM backend.
"""


def get_safe_int_param(request, key, default, min_val=1, max_val=1000):
    """Safely parse integer query parameter with bounds.

    Returns the default value if the parameter is missing, non-numeric,
    or cannot be parsed as an integer. Clamps the result between
    min_val and max_val.
    """
    try:
        value = int(request.query_params.get(key, default))
    except (ValueError, TypeError):
        return default
    return max(min_val, min(value, max_val))


def validate_date_params(request, param_names=("date_from", "date_to")):
    """Validate and parse date query params in YYYY-MM-DD format.

    Returns a tuple of (values_dict, error_response).
    - values_dict maps each param name to a ``date`` or ``None``.
    - error_response is a DRF ``Response`` if any param is invalid, else ``None``.

    Usage::

        dates, err = validate_date_params(request)
        if err:
            return err
        date_from, date_to = dates['date_from'], dates['date_to']
    """
    from datetime import datetime

    from rest_framework import status
    from rest_framework.response import Response

    values = {}
    for name in param_names:
        raw = request.query_params.get(name)
        if raw:
            try:
                values[name] = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                return values, Response(
                    {"detail": f"Invalid {name} format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            values[name] = None
    return values, None


def get_safe_year_param(request, key="year", default=None):
    """Safely parse a year query parameter.

    Returns None (or the given default) if the parameter is missing or
    non-numeric. Clamps the result between 2000 and 2100.
    """
    raw = request.query_params.get(key)
    if not raw:
        return default
    try:
        value = int(raw)
    except (ValueError, TypeError):
        return default
    return max(2000, min(value, 2100))
