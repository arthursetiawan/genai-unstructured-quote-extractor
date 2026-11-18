#!/usr/bin/env python3
"""Offline recruiter smoke: extract + reconcile every sample fixture (no API keys)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from quote_extractor.catalog import load_catalog  # noqa: E402
from quote_extractor.extract import extract_quote  # noqa: E402
from quote_extractor.llm import resolve_mode  # noqa: E402
from reconcile import reconcile_lines  # noqa: E402

SAMPLES_DIR = ROOT / "data" / "samples"


def _run_sample(path: Path, catalog) -> dict[str, object]:
    quote = extract_quote(path, mode="mock")
    results = reconcile_lines(quote.line_items, catalog)
    review_count = sum(1 for r in results if r.needs_human_review)
    return {
        "sample": path.name,
        "line_items": len(quote.line_items),
        "reconciled": len(results),
        "needs_human_review": review_count,
        "mode": "mock",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=SAMPLES_DIR,
        help="Directory of .txt invoice fixtures",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a table",
    )
    args = parser.parse_args()

    if resolve_mode() != "mock":
        print(
            "Warning: GEMINI_API_KEY or OPENAI_API_KEY is set; smoke still forces mode=mock.",
            file=sys.stderr,
        )

    sample_paths = sorted(args.samples_dir.glob("*.txt"))
    if not sample_paths:
        print(f"No .txt fixtures under {args.samples_dir}", file=sys.stderr)
        return 1

    catalog = load_catalog()
    rows = [_run_sample(p, catalog) for p in sample_paths]

    if args.json:
        print(json.dumps({"ok": True, "catalog_size": len(catalog), "samples": rows}, indent=2))
    else:
        print(f"Offline smoke (mock) — catalog={len(catalog)} parts\n")
        for row in rows:
            print(
                f"  {row['sample']}: "
                f"{row['line_items']} lines, "
                f"{row['needs_human_review']} flagged for review"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())