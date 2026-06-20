"""Shared helpers for streaming CSV exports that fail loudly, not silently.

A ``StreamingHttpResponse`` has already sent the HTTP 200 + headers by the time the
row generator yields its first row, so an exception raised mid-stream cannot be turned
back into a 500 — the default behavior is a truncated-but-valid-looking CSV with no
error signal. ``safe_csv_stream`` wraps a row generator so a mid-stream failure instead
appends a clearly-labelled ``__ERROR__`` sentinel row to the download and logs the
traceback server-side. This gives the "complete-or-fail" contract the exporters need.
"""

import csv
import logging

logger = logging.getLogger(__name__)


class Echo:
    """Pseudo-buffer for csv.writer to write into a StreamingHttpResponse."""

    def write(self, value):
        return value


def safe_csv_stream(row_generator, *, export_name):
    """Wrap a CSV row generator so a mid-stream exception surfaces a sentinel row.

    ``row_generator`` is a callable taking a ``csv.writer`` and yielding the results of
    ``writer.writerow(...)``. On any exception the generator's partial output is kept,
    a ``__ERROR__`` line is appended so the consumer can detect the file is incomplete,
    and the full traceback is logged. The sentinel deliberately omits the exception
    message — raw exception text can leak SQL fragments, paths, or donor data.
    """
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    try:
        yield from row_generator(writer)
    except Exception:  # noqa: BLE001 — keep the stream alive to emit the sentinel
        logger.exception("CSV export %s failed mid-stream", export_name)
        yield writer.writerow(
            [
                "__ERROR__",
                "Export failed; this row is incomplete. Engineering has been notified.",
            ]
        )
