"""Read an uploaded pitch deck PDF into the plain deck text the intake path
already expects.

Deliberately dumb: pypdf is pure-Python (same constraint that picked reportlab
for memo output — no system libs on Render's free tier), and the only cleanup is
removing artifacts that would otherwise become claim text. We do NOT summarize,
reflow, or infer anything here. Whatever the founder wrote is what lands in the
signals table; a scanned deck with no text layer is an explicit error, never a
silently-empty application.
"""
from __future__ import annotations

import io
import re

MAX_BYTES = 10 * 1024 * 1024
# Below this, the PDF is almost certainly image-only (a scanned or exported-as-
# image deck). Failing loudly beats ingesting three characters as a deck.
MIN_CHARS = 200

# Page furniture that survives extraction and would otherwise read as deck copy.
_ARTIFACT = re.compile(r"^(page\s*)?\d+\s*(/\s*\d+)?$|^confidential$", re.I)


class DeckPdfError(ValueError):
    """Extraction failed in a way the applicant can act on."""


def extract(data: bytes, filename: str = "deck.pdf") -> str:
    if len(data) > MAX_BYTES:
        raise DeckPdfError(
            f"{filename} is {len(data) // 1024 // 1024}MB — 10MB is the ceiling")
    if not data.startswith(b"%PDF-"):
        raise DeckPdfError(f"{filename} is not a PDF")

    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise DeckPdfError(f"{filename} is password-protected — send an unlocked copy")
        pages = [p.extract_text() or "" for p in reader.pages]
    except DeckPdfError:
        raise
    except Exception as e:
        raise DeckPdfError(f"could not read {filename}: {type(e).__name__}") from e

    text = "\n\n".join(t for t in (_clean(p) for p in pages) if t)
    if len(text) < MIN_CHARS:
        raise DeckPdfError(
            f"{filename} has no extractable text layer ({len(text)} chars) — it is "
            "probably a scanned or image-only deck. Paste the text instead.")
    return text


def _clean(page: str) -> str:
    """Drop page furniture and collapse the ragged whitespace slide extraction
    produces. Line order is preserved — downstream takes the deck's first
    non-blank line as the company descriptor for news search."""
    lines = []
    for raw in page.splitlines():
        line = " ".join(raw.split())
        if not line or _ARTIFACT.match(line):
            continue
        lines.append(line)
    return "\n".join(lines)
