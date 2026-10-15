"""The scan pipeline: walk a folder, read each new document, sort it, update the ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List

from . import ledger
from .extract import SUPPORTED_EXTS, ExtractError, file_sha256, load
from .ollama import OllamaError
from .reader import read_document
from .sorter import place

LEDGER_NAME = "ledger.json"


@dataclass
class ScanResult:
    added: List[str] = field(default_factory=list)
    skipped_known: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)


def find_files(src: Path, out: Path) -> List[Path]:
    out = out.resolve()
    found = []
    for path in sorted(src.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if out in path.resolve().parents:
            continue
        if path.suffix.lower() in SUPPORTED_EXTS:
            found.append(path)
    return found


def run_scan(
    src: Path,
    out: Path,
    host: str,
    model: str,
    move: bool = False,
    dry_run: bool = False,
    log: Callable[[str], None] = print,
) -> ScanResult:
    ledger_path = out / LEDGER_NAME
    receipts = ledger.load(ledger_path)
    known = {r.sha256 for r in receipts}
    result = ScanResult()

    files = find_files(src, out)
    log(f"Found {len(files)} candidate files in {src}")
    for path in files:
        digest = file_sha256(path)
        if digest in known:
            result.skipped_known.append(path.name)
            log(f"  skip   {path.name} (already in ledger)")
            continue
        if dry_run:
            log(f"  would read {path.name}")
            continue
        try:
            doc = load(path)
            receipt = read_document(doc, host, model)
        except (ExtractError, OllamaError) as exc:
            result.failed.append(path.name)
            log(f"  FAIL   {path.name}: {exc}")
            continue
        target = place(path, receipt, out / "sorted", move=move)
        receipt.stored_as = str(target.relative_to(out))
        receipts.append(receipt)
        known.add(digest)
        result.added.append(path.name)
        total = f"{receipt.total:.2f} {receipt.currency}" if receipt.total is not None else "?"
        log(f"  ok     {path.name} -> {receipt.category} / {receipt.vendor} / {total}")
        ledger.save(ledger_path, receipts)  # save as we go so a crash loses nothing

    if not dry_run:
        write_outputs(out, receipts)
    return result


def write_outputs(out: Path, receipts: List[ledger.Receipt]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    ledger.save(out / LEDGER_NAME, receipts)
    ledger.write_csv(out / "ledger.csv", receipts)
    ledger.write_summary(out / "summary.md", receipts)
