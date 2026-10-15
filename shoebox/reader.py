"""Ask the local model to read one document and return structured fields."""

from __future__ import annotations

import json
from typing import Optional

from . import ollama
from .extract import Document
from .schema import CATEGORIES, JSON_SCHEMA, Receipt

SYSTEM_PROMPT = (
    "You are a bookkeeping assistant for a freelancer. You read one receipt or invoice "
    "and extract its fields. Never invent values: if a field is not visible, use an empty "
    "string for text and 0 for numbers. Dates must be ISO format YYYY-MM-DD. "
    "`total` is the final amount paid or due, including tax. "
    "`currency` is a 3-letter ISO code such as USD, EUR, GBP, INR. "
    "`doc_type` is 'receipt' for proof of payment, 'invoice' for a bill, otherwise 'other'. "
    f"`category` must be one of: {', '.join(CATEGORIES)}."
)


def read_document(doc: Document, host: str, model: str, timeout: float = 300) -> Receipt:
    if doc.image_b64:
        user = "Extract the fields from the attached image of a receipt or invoice."
        images: Optional[list] = [doc.image_b64]
    else:
        user = "Extract the fields from this receipt or invoice text:\n\n" + (doc.text or "")
        images = None

    last_error: Optional[Exception] = None
    for _ in range(2):  # one retry if the model returns malformed JSON
        content = ollama.chat(
            host, model, SYSTEM_PROMPT, user, images=images, schema=JSON_SCHEMA, timeout=timeout
        )
        try:
            raw = json.loads(content)
            if not isinstance(raw, dict):
                raise ValueError("model JSON was not an object")
            return Receipt.from_model(raw, doc.path.name, doc.sha256)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
    raise ollama.OllamaError(f"Model returned unusable output for {doc.path.name}: {last_error}")
