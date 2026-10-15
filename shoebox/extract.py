"""Turn a file on disk into something a model can read: text or a base64 image."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

TEXT_EXTS = {".txt", ".md", ".eml", ".csv", ".html", ".htm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
PDF_EXTS = {".pdf"}
SUPPORTED_EXTS = TEXT_EXTS | IMAGE_EXTS | PDF_EXTS

MAX_TEXT_CHARS = 8000


class ExtractError(RuntimeError):
    pass


@dataclass
class Document:
    path: Path
    sha256: str
    text: Optional[str] = None
    image_b64: Optional[str] = None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader  # optional dependency
    except ImportError as exc:
        raise ExtractError(
            "PDF support needs pypdf: pip install 'shoebox[pdf]' (or pip install pypdf)"
        ) from exc
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    if not text.strip():
        raise ExtractError("PDF has no text layer (scanned?). Export it as an image instead.")
    return text


def load(path: Path) -> Document:
    ext = path.suffix.lower()
    doc = Document(path=path, sha256=file_sha256(path))
    if ext in IMAGE_EXTS:
        doc.image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    elif ext in PDF_EXTS:
        doc.text = _pdf_text(path)[:MAX_TEXT_CHARS]
    elif ext in TEXT_EXTS:
        doc.text = path.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT_CHARS]
    else:
        raise ExtractError(f"Unsupported file type: {ext or '(none)'}")
    return doc
