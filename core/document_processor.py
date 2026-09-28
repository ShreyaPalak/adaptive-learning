"""
Extracts plain text from uploaded PDF/TXT documents.

Design notes:
- Never crashes on malformed input — always returns a DocumentResult with
  either usable text or a clear, user-facing error message.
- Never logs raw document content (see core.security.sanitize_for_log).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MIN_USABLE_CHARS = 200  # below this, generation quality would be poor


@dataclass
class DocumentResult:
    ok: bool
    text: str = ""
    page_count: int = 0
    char_count: int = 0
    error: str = ""
    warnings: list[str] = field(default_factory=list)


def extract_text(file_bytes: bytes, filename: str) -> DocumentResult:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    if lower.endswith(".txt"):
        return _extract_txt(file_bytes)
    return DocumentResult(ok=False, error="Unsupported file type.")


def _extract_pdf(file_bytes: bytes) -> DocumentResult:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except PdfReadError:
        return DocumentResult(ok=False, error="This PDF could not be read — it may be corrupted or encrypted.")
    except Exception:
        return DocumentResult(ok=False, error="This PDF could not be read — it may be corrupted or encrypted.")

    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")  # try empty password only; never guess/brute force
        except Exception:
            pass
        if reader.is_encrypted:
            return DocumentResult(ok=False, error="This PDF is password-protected. Please upload an unprotected file.")

    warnings: list[str] = []
    pages_text: list[str] = []
    blank_pages = 0

    for i, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if not page_text.strip():
            blank_pages += 1
        pages_text.append(page_text)

    full_text = "\n\n".join(pages_text).strip()

    if blank_pages > 0:
        warnings.append(
            f"{blank_pages} of {len(reader.pages)} page(s) had no extractable text "
            "(likely scanned images) and were skipped."
        )

    if len(full_text) < MIN_USABLE_CHARS:
        return DocumentResult(
            ok=False,
            text=full_text,
            page_count=len(reader.pages),
            char_count=len(full_text),
            error=(
                "Not enough readable text was found in this PDF to generate quality questions. "
                "It may be a scanned/image-only document — try a text-based PDF or a TXT file."
            ),
            warnings=warnings,
        )

    return DocumentResult(
        ok=True,
        text=full_text,
        page_count=len(reader.pages),
        char_count=len(full_text),
        warnings=warnings,
    )


def _extract_txt(file_bytes: bytes) -> DocumentResult:
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
        except Exception:
            return DocumentResult(ok=False, error="This text file could not be decoded.")

    text = text.strip()
    if len(text) < MIN_USABLE_CHARS:
        return DocumentResult(
            ok=False,
            text=text,
            char_count=len(text),
            error="This file doesn't have enough text to generate quality questions.",
        )

    return DocumentResult(ok=True, text=text, page_count=1, char_count=len(text))


def truncate_for_llm(text: str, max_chars: int = 12000) -> str:
    """Cap source material sent to the LLM (cost/latency control for the
    hackathon demo). Keeps the beginning, which usually carries the most
    structurally important content (intro/definitions)."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...document truncated for length...]"
