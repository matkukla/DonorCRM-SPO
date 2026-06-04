"""
Behavioral tests for apps.core.uploads.detect_upload_kind.

These cover magic-byte detection (XLSX/XLS), the permissive CSV heuristic,
the filename-assisted single-column CSV path, and the UNKNOWN fallbacks.
"""
from apps.core.uploads import UploadKind, detect_upload_kind


class TestDetectUploadKind:
    """Magic-byte + heuristic detection of uploaded file kinds."""

    def test_empty_content_is_unknown(self):
        """Empty bytes cannot be classified."""
        assert detect_upload_kind(b"", "anything.csv") is UploadKind.UNKNOWN

    def test_xlsx_zip_magic_detected(self):
        """PK\\x03\\x04 (ZIP/XLSX) magic bytes are detected regardless of name."""
        content = b"PK\x03\x04" + b"\x00" * 32
        assert detect_upload_kind(content, "report.csv") is UploadKind.XLSX

    def test_xlsx_empty_zip_magic_detected(self):
        """Empty-ZIP magic PK\\x05\\x06 also resolves to XLSX."""
        content = b"PK\x05\x06" + b"\x00" * 20
        assert detect_upload_kind(content, "empty.xlsx") is UploadKind.XLSX

    def test_xlsx_spanned_zip_magic_detected(self):
        """Spanned-ZIP magic PK\\x07\\x08 also resolves to XLSX."""
        content = b"PK\x07\x08" + b"\x00" * 20
        assert detect_upload_kind(content, "spanned.xlsx") is UploadKind.XLSX

    def test_xls_ole2_magic_detected(self):
        """The OLE2 compound-document signature resolves to legacy XLS."""
        content = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 16
        assert detect_upload_kind(content, "old.xls") is UploadKind.XLS

    def test_plain_csv_with_commas_detected(self):
        """ASCII text containing commas is treated as CSV."""
        content = b"name,email\nAlice,alice@example.com\n"
        assert detect_upload_kind(content, "contacts.csv") is UploadKind.CSV

    def test_csv_detected_via_newline_only(self):
        """Newline-delimited text (no commas) still trips the CSV heuristic."""
        content = b"line one\nline two\nline three\n"
        assert detect_upload_kind(content, "data.txt") is UploadKind.CSV

    def test_csv_handles_utf8_bom(self):
        """A UTF-8 BOM-prefixed CSV decodes cleanly and is detected as CSV."""
        content = "﻿name,amount\nBob,100\n".encode("utf-8")
        assert detect_upload_kind(content, "bom.csv") is UploadKind.CSV

    def test_binary_non_text_is_unknown(self):
        """Non-decodable binary content with no known magic is UNKNOWN."""
        # 0xFF 0xFE is not valid UTF-8 as a standalone leading sequence here.
        content = b"\xff\xfe\x00\x01\x02\x80\x81\x82" + b"\x90" * 32
        assert detect_upload_kind(content, "blob.bin") is UploadKind.UNKNOWN

    def test_single_column_csv_uses_filename_hint(self):
        """Text with no delimiter but a .csv name and real content is accepted as CSV."""
        # No comma/newline/semicolon/tab inside the first kilobyte -> heuristic
        # falls back to the filename hint.
        content = b"singlevalue"
        assert detect_upload_kind(content, "emails.csv") is UploadKind.CSV

    def test_delimiterless_text_without_csv_name_is_unknown(self):
        """Delimiterless text whose filename does not end in .csv stays UNKNOWN."""
        content = b"singlevalue"
        assert detect_upload_kind(content, "note.txt") is UploadKind.UNKNOWN

    def test_delimiterless_text_with_no_filename_is_unknown(self):
        """Without a filename hint, delimiterless text cannot be confirmed as CSV."""
        content = b"singlevalue"
        assert detect_upload_kind(content, None) is UploadKind.UNKNOWN

    def test_blank_content_with_csv_name_is_unknown(self):
        """Space-only content (no delimiters) fails the strip() check even with .csv.

        Note: tabs/newlines/semicolons would trip the delimiter heuristic, so this
        uses plain spaces to reach the filename-hint branch where strip() is empty.
        """
        content = b"      "
        assert detect_upload_kind(content, "blank.csv") is UploadKind.UNKNOWN

    def test_upload_kind_is_str_enum(self):
        """UploadKind members compare equal to their string values."""
        assert UploadKind.CSV == "csv"
        assert UploadKind.XLSX == "xlsx"
