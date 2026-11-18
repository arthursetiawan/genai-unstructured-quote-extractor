#!/usr/bin/env python3
"""Precision/recall vs synthetic gold labels; writes reports/extraction_metrics.md."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from quote_extractor.extract import extract_quote  # noqa: E402
from quote_extractor.models import LineItem  # noqa: E402

GOLD_DIR = ROOT / "data" / "gold"
DEFAULT_OUT = ROOT / "reports" / "extraction_metrics.md"
COST_TOLERANCE = 0.05  # dollars


def _norm_part(part: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", part).upper()
    return cleaned


def _line_key(item: LineItem) -> str:
    return _norm_part(item.PartNumber)


def _cost_match(pred: float, gold: float) -> bool:
    return abs(pred - gold) <= COST_TOLERANCE


def _load_gold(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["line_items"]


def _match_line(pred: LineItem, gold_rows: list[dict]) -> dict | None:
    pk = _line_key(pred)
    for g in gold_rows:
        if _norm_part(g["PartNumber"]) != pk:
            continue
        if _cost_match(pred.UnitCost, float(g["UnitCost"])):
            return g
    return None


def _score_sample(sample_name: str, gold_path: Path, mode: str = "mock") -> dict[str, object]:
    sample_path = ROOT / "data" / "samples" / sample_name
    gold = _load_gold(gold_path)
    quote = extract_quote(sample_path, mode=mode)
    preds = quote.line_items

    matched_gold: set[int] = set()
    tp = 0
    for pred in preds:
        g = _match_line(pred, gold)
        if g is not None:
            idx = gold.index(g)
            if idx not in matched_gold:
                matched_gold.add(idx)
                tp += 1

    fp = len(preds) - tp
    fn = len(gold) - len(matched_gold)
    precision = tp / len(preds) if preds else (1.0 if not gold else 0.0)
    recall = tp / len(gold) if gold else 1.0
    return {
        "sample": sample_name,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "predicted": len(preds),
        "gold": len(gold),
    }


def build_markdown(mode: str = "mock") -> str:
    rows: list[dict[str, object]] = []
    for gold_path in sorted(GOLD_DIR.glob("*.json")):
        sample_name = gold_path.stem + ".txt"
        rows.append(_score_sample(sample_name, gold_path, mode=mode))

    total_tp = sum(int(r["tp"]) for r in rows)
    total_fp = sum(int(r["fp"]) for r in rows)
    total_fn = sum(int(r["fn"]) for r in rows)
    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 1.0
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 1.0
    f1 = (2 * micro_p * micro_r / (micro_p + micro_r)) if (micro_p + micro_r) else 0.0

    lines = [
        "# Extraction metrics — synthetic gold labels",
        "",
        f"*Generated {date.today().isoformat()} by `scripts/eval_extraction.py` "
        f"(mode=`{mode}`, match on normalized part number + unit cost ± ${COST_TOLERANCE}).*",
        "",
        "## Micro-averaged (corpus)",
        "",
        "| Precision | Recall | F1 | TP | FP | FN |",
        "|-----------|--------|----|----|----|----|",
        f"| {micro_p:.4f} | {micro_r:.4f} | {f1:.4f} | {total_tp} | {total_fp} | {total_fn} |",
        "",
        "## Per-sample",
        "",
        "| Sample | Gold lines | Predicted | TP | FP | FN | Precision | Recall |",
        "|--------|------------|-----------|----|----|-----|-----------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['sample']}` | {r['gold']} | {r['predicted']} | {r['tp']} | {r['fp']} | {r['fn']} | "
            f"{r['precision']:.4f} | {r['recall']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Gold labels",
            "",
            "Committed under `data/gold/*.json` — fictional line items aligned to `data/samples/*.txt`.",
            "",
            "## Regenerate",
            "",
            "```bash",
            "python scripts/eval_extraction.py",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", default="mock", help="Extraction mode (default mock)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()

    report = build_markdown(mode=args.mode)
    if args.stdout:
        print(report, end="")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())