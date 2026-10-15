"""Receipt data model plus tolerant normalisation of model output."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

CATEGORIES = (
    "software",
    "hardware",
    "office",
    "travel",
    "meals",
    "marketing",
    "professional-services",
    "utilities",
    "education",
    "other",
)
DOC_TYPES = ("receipt", "invoice", "other")

# Passed to Ollama as `format` so the model must answer with this exact shape.
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor": {"type": "string"},
        "date": {"type": "string"},
        "total": {"type": "number"},
        "tax": {"type": "number"},
        "currency": {"type": "string"},
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "doc_type": {"type": "string", "enum": list(DOC_TYPES)},
        "notes": {"type": "string"},
    },
    "required": ["vendor", "date", "total", "currency", "category", "doc_type"],
}

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
)
_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY"}


@dataclass
class Receipt:
    sha256: str
    filename: str
    vendor: str = "unknown"
    date: str = ""
    total: Optional[float] = None
    tax: Optional[float] = None
    currency: str = ""
    category: str = "other"
    doc_type: str = "other"
    notes: str = ""
    stored_as: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Receipt":
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    @classmethod
    def from_model(cls, raw: dict, filename: str, sha256: str) -> "Receipt":
        category = str(raw.get("category", "")).strip().lower()
        doc_type = str(raw.get("doc_type", "")).strip().lower()
        return cls(
            sha256=sha256,
            filename=filename,
            vendor=str(raw.get("vendor") or "").strip() or "unknown",
            date=parse_date(raw.get("date")),
            total=parse_amount(raw.get("total")),
            tax=parse_amount(raw.get("tax")),
            currency=normalize_currency(raw.get("currency")),
            category=category if category in CATEGORIES else "other",
            doc_type=doc_type if doc_type in DOC_TYPES else "other",
            notes=str(raw.get("notes") or "").strip(),
        )


def parse_amount(value: Any) -> Optional[float]:
    """Turn '$1,234.50', '1.234,50 €' or 12.5 into a float, else None."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    cleaned = re.sub(r"[^\d,.\-]", "", str(value))
    if not re.search(r"\d", cleaned):
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        head, _, tail = cleaned.rpartition(",")
        if len(tail) == 2:
            cleaned = head.replace(",", "") + "." + tail
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def parse_date(value: Any) -> str:
    """Return an ISO date (YYYY-MM-DD) or an empty string."""
    text = str(value or "").strip()
    if not text:
        return ""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def normalize_currency(value: Any) -> str:
    text = str(value or "").strip()
    if text in _CURRENCY_SYMBOLS:
        return _CURRENCY_SYMBOLS[text]
    text = text.upper()
    return text if re.fullmatch(r"[A-Z]{3}", text) else ""


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit].strip("-")
    return slug or "unknown"
