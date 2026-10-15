"""Command line entry point: `shoebox doctor | scan | report`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__, ledger, ollama
from .scan import LEDGER_NAME, run_scan, write_outputs

DEFAULT_MODEL = "gemma3:4b"


def _cmd_doctor(args: argparse.Namespace) -> int:
    print(f"Ollama host : {args.host}")
    print(f"Model       : {args.model}")
    try:
        installed = ollama.list_models(args.host)
    except ollama.OllamaError as exc:
        print(f"FAIL: {exc}")
        return 1
    if not ollama.has_model(installed, args.model):
        print(f"FAIL: model not installed. Run: ollama pull {args.model}")
        return 1
    print("OK: Ollama is reachable and the model is installed.")
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    src, out = Path(args.source), Path(args.out)
    if not src.is_dir():
        print(f"Source folder not found: {src}")
        return 2
    if not args.dry_run:
        code = _cmd_doctor(args)
        if code:
            return code
    result = run_scan(src, out, args.host, args.model, move=args.move, dry_run=args.dry_run)
    print(
        f"\nDone. added={len(result.added)} known={len(result.skipped_known)} "
        f"failed={len(result.failed)}"
    )
    if not args.dry_run:
        print(f"Open {out / 'summary.md'} and {out / 'ledger.csv'}")
    return 1 if result.failed else 0


def _cmd_report(args: argparse.Namespace) -> int:
    out = Path(args.out)
    receipts = ledger.load(out / LEDGER_NAME)
    if not receipts:
        print(f"No ledger found in {out}. Run `shoebox scan` first.")
        return 2
    write_outputs(out, receipts)
    print(f"Rebuilt {out / 'ledger.csv'} and {out / 'summary.md'} from {len(receipts)} documents.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shoebox", description="Sort receipts and invoices with a model that never leaves your laptop."
    )
    parser.add_argument("--version", action="version", version=f"shoebox {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_model_opts(p: argparse.ArgumentParser) -> None:
        p.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default {DEFAULT_MODEL})")
        p.add_argument("--host", default=ollama.default_host(), help="Ollama URL (default $OLLAMA_HOST or localhost)")

    p_doc = sub.add_parser("doctor", help="check Ollama and the model are ready")
    add_model_opts(p_doc)
    p_doc.set_defaults(func=_cmd_doctor)

    p_scan = sub.add_parser("scan", help="read a folder of receipts and sort them")
    p_scan.add_argument("source", help="folder with receipts (txt, pdf, png, jpg, webp)")
    p_scan.add_argument("--out", default="shoebox-out", help="output folder (default shoebox-out)")
    p_scan.add_argument("--move", action="store_true", help="move files instead of copying")
    p_scan.add_argument("--dry-run", action="store_true", help="list what would be read, change nothing")
    add_model_opts(p_scan)
    p_scan.set_defaults(func=_cmd_scan)

    p_rep = sub.add_parser("report", help="rebuild ledger.csv and summary.md from ledger.json")
    p_rep.add_argument("--out", default="shoebox-out")
    p_rep.set_defaults(func=_cmd_report)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
