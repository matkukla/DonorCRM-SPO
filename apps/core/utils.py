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


def get_safe_year_param(request, key='year', default=None):
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
