import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pypdf import PdfWriter
from core.document_processor import extract_text


def make_pdf_bytes(text_pages: list[str]) -> bytes:
    """Build a minimal real PDF using pypdf so we exercise real parsing.
    Note: pypdf's blank PdfWriter pages have no text layer, so this helper
    is only used for the "PDF with no extractable text" case; for the
    "valid text" case we fetch a tiny fixture PDF-like text scenario via TXT
    instead, since building a text-bearing PDF from scratch needs a real
    font/content stream which is out of scope for a unit test."""
    writer = PdfWriter()
    for _ in text_pages:
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_empty_pdf_bytes_handled_gracefully():
    result = extract_text(b"not a real pdf", "broken.pdf")
    assert result.ok is False
    assert result.error

def test_blank_page_pdf_reports_no_usable_text():
    pdf_bytes = make_pdf_bytes(["", ""])
    result = extract_text(pdf_bytes, "blank.pdf")
    assert result.ok is False  # blank pages -> not enough text

def test_txt_valid():
    text = ("Normalization is a database design technique. " * 30).encode("utf-8")
    result = extract_text(text, "notes.txt")
    assert result.ok is True
    assert result.char_count > 0

def test_txt_too_short():
    result = extract_text(b"short", "notes.txt")
    assert result.ok is False

def test_unsupported_extension():
    result = extract_text(b"data", "file.docx")
    assert result.ok is False


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
