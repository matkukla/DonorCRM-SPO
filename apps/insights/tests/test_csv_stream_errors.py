"""
Tests that the CSV export `_safe_csv_stream` wrapper surfaces a sentinel
error row instead of silently truncating when the row generator raises
mid-stream.
"""
import csv
import io

from apps.insights.export_views import _safe_csv_stream


def test_safe_stream_yields_sentinel_on_exception():
    def rows(writer):
        yield writer.writerow(["header_a", "header_b"])
        yield writer.writerow(["row_1", "value"])
        raise RuntimeError("boom: data is bad")

    output = "".join(_safe_csv_stream(rows, export_name="unit_test"))

    parsed = list(csv.reader(io.StringIO(output)))
    # First two rows are the normal output; final row is the sentinel.
    assert parsed[0] == ["header_a", "header_b"]
    assert parsed[1] == ["row_1", "value"]
    assert parsed[-1][0] == "__ERROR__"
    # Generic message — must NOT contain the raw exception text (information leak).
    assert "boom: data is bad" not in parsed[-1][1]
    assert "incomplete" in parsed[-1][1].lower()


def test_safe_stream_clean_when_no_exception():
    def rows(writer):
        yield writer.writerow(["a"])
        yield writer.writerow(["b"])

    output = "".join(_safe_csv_stream(rows, export_name="unit_test"))
    parsed = list(csv.reader(io.StringIO(output)))
    assert parsed == [["a"], ["b"]]
