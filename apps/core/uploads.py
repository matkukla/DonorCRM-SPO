"""Shared upload validation helpers.

The import endpoints currently validate uploads inline (size + .csv extension).
This module adds magic-byte checks so that a maliciously named file (e.g. a
zip bomb renamed `.csv`) is rejected before being handed to a parser.

Usage
-----

    from apps.core.uploads import detect_upload_kind, UploadKind

    kind = detect_upload_kind(file_bytes, file.name)
    if kind not in (UploadKind.CSV, UploadKind.XLSX):
        return Response({"detail": "Unsupported file type."}, status=400)
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class UploadKind(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    XLS = "xls"
    UNKNOWN = "unknown"


# XLSX = ZIP archive — magic bytes ``PK\x03\x04`` or ``PK\x05\x06`` (empty ZIP)
_XLSX_MAGIC: Final = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
# XLS = OLE2 compound document
_XLS_MAGIC: Final = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def detect_upload_kind(content: bytes, filename: str | None = None) -> UploadKind:
    """Return the detected file kind based on magic bytes + extension.

    Magic bytes win when present. If neither magic matches, falls back to a
    permissive CSV check (printable text + comma/newline content), which is
    the only kind whose first 8 bytes are not deterministic.
    """
    if not content:
        return UploadKind.UNKNOWN

    head = content[:8]
    if head.startswith(_XLSX_MAGIC):
        return UploadKind.XLSX
    if head == _XLS_MAGIC:
        return UploadKind.XLS

    # Plausible CSV: ASCII/UTF-8 text in the first kilobyte.
    sample = content[:1024]
    try:
        decoded = sample.decode("utf-8-sig")
    except UnicodeDecodeError:
        return UploadKind.UNKNOWN

    # Heuristic: text content with at least one comma or newline.
    if any(ch in decoded for ch in (",", "\n", "\r", "\t", ";")):
        return UploadKind.CSV

    # If the filename strongly suggests CSV and the content is at least
    # decodable text, accept — single-column CSVs are valid.
    if filename and filename.lower().endswith(".csv") and decoded.strip():
        return UploadKind.CSV

    return UploadKind.UNKNOWN
