"""Decide where a receipt lives on disk and copy it there."""

from __future__ import annotations

import shutil
from pathlib import Path

from .schema import Receipt, slugify


def destination(receipt: Receipt, sorted_root: Path, ext: str) -> Path:
    month = receipt.date[:7] if receipt.date else "undated"
    amount = f"{receipt.total:.2f}" if receipt.total is not None else "unknown"
    name = f"{receipt.date or 'undated'}_{slugify(receipt.vendor)}_{amount}{ext.lower()}"
    return sorted_root / month / receipt.category / name


def unique(path: Path) -> Path:
    if not path.exists():
        return path
    for n in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Too many files named like {path.name}")


def place(src: Path, receipt: Receipt, sorted_root: Path, move: bool = False) -> Path:
    target = unique(destination(receipt, sorted_root, src.suffix))
    target.parent.mkdir(parents=True, exist_ok=True)
    if move:
        shutil.move(str(src), str(target))
    else:
        shutil.copy2(src, target)
    return target
