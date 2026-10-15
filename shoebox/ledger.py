"""Persist the ledger and render the CSV + tax-time summary."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from .schema import Receipt

CSV_FIELDS = [
    "date", "vendor", "category", "doc_type", "total", "tax", "currency",
    "filename", "stored_as", "notes", "sha256",
]


def load(path: Path) -> List[Receipt]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Receipt.from_dict(item) for item in data]


def save(path: Path, receipts: List[Receipt]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.to_dict() for r in receipts]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, receipts: List[Receipt]) -> None:
    ordered = sorted(receipts, key=lambda r: (r.date or "9999", r.vendor))
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in ordered:
            writer.writerow(r.to_dict())


def _money(value: float, currency: str) -> str:
    return f"{value:,.2f} {currency or '??'}"


def render_summary(receipts: List[Receipt]) -> str:
    """Markdown report. Totals are kept per currency; nothing is converted."""
    spend = [r for r in receipts if r.total is not None]
    lines = ["# Shoebox summary", "", f"{len(receipts)} documents, {len(spend)} with a readable total.", ""]
    review = [r for r in receipts if r.total is None or not r.date]
    by_cur_cat: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_cur_month: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    tax_by_cur: Dict[str, float] = defaultdict(float)
    for r in spend:
        by_cur_cat[r.currency][r.category] += r.total
        by_cur_month[r.currency][r.date[:7] or "undated"] += r.total
        tax_by_cur[r.currency] += r.tax or 0.0

    for currency in sorted(by_cur_cat):
        label = currency or "unknown currency"
        total = sum(by_cur_cat[currency].values())
        lines += [f"## {label}: {_money(total, currency)}", "", "| Category | Total |", "|---|---:|"]
        for cat, amount in sorted(by_cur_cat[currency].items(), key=lambda kv: -kv[1]):
            lines.append(f"| {cat} | {_money(amount, currency)} |")
        lines += ["", "| Month | Total |", "|---|---:|"]
        for month, amount in sorted(by_cur_month[currency].items()):
            lines.append(f"| {month} | {_money(amount, currency)} |")
        lines += ["", f"Tax recorded: {_money(tax_by_cur[currency], currency)}", ""]

    if review:
        lines += ["## Needs a human look", "", "Missing a date or a total:", ""]
        for r in review:
            lines.append(f"- `{r.filename}` ({r.vendor})")
        lines.append("")
    lines.append("_Extracted by a local model. Check anything you will file with a tax office._")
    return "\n".join(lines) + "\n"


def write_summary(path: Path, receipts: List[Receipt]) -> None:
    path.write_text(render_summary(receipts), encoding="utf-8")
