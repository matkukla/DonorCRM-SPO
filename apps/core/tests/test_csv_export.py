"""Tests for the shared safe_csv_stream complete-or-fail helper."""

from apps.core.csv_export import safe_csv_stream


def _consume(stream):
    return "".join(stream)


def test_safe_csv_stream_emits_all_rows_on_success():
    def rows(writer):
        yield writer.writerow(["a", "b"])
        yield writer.writerow(["1", "2"])

    out = _consume(safe_csv_stream(rows, export_name="ok"))
    assert "a,b" in out
    assert "1,2" in out
    assert "__ERROR__" not in out


def test_safe_csv_stream_appends_sentinel_on_midstream_error():
    """A generator that raises after the header must NOT truncate silently."""

    def rows(writer):
        yield writer.writerow(["header1", "header2"])
        raise RuntimeError("boom in the middle")

    out = _consume(safe_csv_stream(rows, export_name="boom"))
    assert "header1,header2" in out  # partial output preserved
    assert "__ERROR__" in out  # loud failure signal present
    assert "boom in the middle" not in out  # raw exception text never written to file
