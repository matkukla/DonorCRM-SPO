"""CSV formula-injection sanitizer hardening — security report #12.

The sanitizer prefixed values starting with = + - @, but a formula hidden behind
a leading tab/CR/LF/space (which spreadsheets strip before evaluating) slipped
through unchanged (CWE-1236). Each case fails if the hardening is reverted.
"""

import pytest

from apps.imports.services import sanitize_csv_value


@pytest.mark.parametrize(
    "payload",
    [
        '\t=HYPERLINK("http://evil","x")',
        "\r=cmd|'/c calc'!A1",
        "\n=1+1",
        " =1+1",
        "\t+1+1",
        "  -2+3",
        "\t@SUM(A1)",
        "=1+1",  # plain formula still caught
    ],
)
def test_dangerous_values_are_neutralized(payload):
    result = sanitize_csv_value(payload)
    assert result.startswith("'"), f"payload not neutralized: {payload!r} -> {result!r}"


@pytest.mark.parametrize("benign", ["John Smith", " hello world", "donor@example.com", "", "123"])
def test_benign_values_unchanged(benign):
    assert sanitize_csv_value(benign) == benign


def test_non_string_passthrough():
    assert sanitize_csv_value(1234) == 1234
    assert sanitize_csv_value(None) is None
