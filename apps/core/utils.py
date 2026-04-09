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


def parse_date_params(request, *param_names):
    """Parse and validate YYYY-MM-DD date query parameters.

    Returns a dict mapping each param name to a datetime.date or None.
    Raises ValueError with a message suitable for a 400 response if
    any provided value is not in YYYY-MM-DD format.
    """
    from datetime import datetime

    result = {}
    for name in param_names:
        raw = request.query_params.get(name)
        if raw:
            try:
                result[name] = datetime.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f'Invalid {name} format. Use YYYY-MM-DD.')
        else:
            result[name] = None
    return result
