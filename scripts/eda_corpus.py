#!/usr/bin/env python3
"""EDA over the synthetic sample corpus: field coverage, confidence, review-queue rate.

Writes reports/eda_summary.md (regenerate before publishing metrics).
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from quote_extractor.catalog import load_catalog  # noqa: E402
from quote_extractor.extract import extract_quote  # noqa: E402
from quote_extractor.models import LineItem  # noqa: E402
from reconcile import REVIEW_THRESHOLD, reconcile_lines  # noqa: E402

SAMPLES_DIR = ROOT / "data" / "samples"
DEFAULT_OUT = ROOT / "reports" / "eda_summary.md"
REQUIRED_FIELDS = ("PartNumber", "Description", "UnitCost", "Vendor")


def _field_coverage(items: list[LineItem]) -> dict[str, float]:
    if not items:
        return {f: 0.0 for f in REQUIRED_FIELDS}
    counts = {f: 0 for f in REQUIRED_FIELDS}
    for row in items:
        for field in REQUIRED_FIELDS:
            val = getattr(row, field)
            if val is not None and (not isinstance(val, str) or val.strip()):
                counts[field] += 1
        if row.CompetitorPrice is not None:
            counts.setdefault("CompetitorPrice", 0)
            counts["CompetitorPrice"] += 1
    base = len(items)
    out = {f: counts[f] / base for f in REQUIRED_FIELDS}
    out["CompetitorPrice (optional)"] = counts.get("CompetitorPrice", 0) / base
    return out


def _confidence_bins(values: list[float]) -> Counter[str]:
    bins = Counter()
    for v in values:
        if v < 0.40:
            bins["< 0.40 (review)"] += 1
        elif v < 0.60:
            bins["0.40 – 0.59"] += 1
        elif v < 0.80:
            bins["0.60 – 0.79"] += 1
        else:
            bins["≥ 0.80"] += 1
    return bins


def build_markdown() -> str:
    catalog = load_catalog()
    sample_paths = sorted(SAMPLES_DIR.glob("*.txt"))
    all_items: list[LineItem] = []
    all_confidences: list[float] = []
    per_sample: list[dict[str, object]] = []
    total_review = 0
    total_lines = 0

    for path in sample_paths:
        quote = extract_quote(path, mode="mock")
        results = reconcile_lines(quote.line_items, catalog)
        confidences = [
            r.best_match.confidence if r.best_match is not None else 0.0 for r in results
        ]
        review_n = sum(1 for r in results if r.needs_human_review)
        total_review += review_n
        total_lines += len(results)
        all_items.extend(quote.line_items)
        all_confidences.extend(confidences)
        coverage = _field_coverage(quote.line_items)
        per_sample.append(
            {
                "name": path.name,
                "lines": len(quote.line_items),
                "review": review_n,
                "coverage": coverage,
                "confidences": confidences,
            }
        )

    agg_coverage = _field_coverage(all_items)
    conf_bins = _confidence_bins(all_confidences)
    review_rate = (total_review / total_lines) if total_lines else 0.0
    mean_conf = statistics.mean(all_confidences) if all_confidences else 0.0
    med_conf = statistics.median(all_confidences) if all_confidences else 0.0

    lines: list[str] = [
        "# EDA summary — synthetic quote corpus",
        "",
        f"*Generated {date.today().isoformat()} by `scripts/eda_corpus.py` (mock extraction, seed-42 catalog).*",
        "",
        "## Corpus",
        "",
        f"| Samples | Total line items | Catalog size | Review threshold |",
        f"|---------|------------------|--------------|------------------|",
        f"| {len(sample_paths)} | {total_lines} | {len(catalog)} | {REVIEW_THRESHOLD:.2f} |",
        "",
        "## Per-sample breakdown",
        "",
        "| Sample | Lines | Review queue | Mean confidence |",
        "|--------|-------|--------------|-----------------|",
    ]
    for row in per_sample:
        confs = row["confidences"]
        m = statistics.mean(confs) if confs else 0.0
        lines.append(
            f"| `{row['name']}` | {row['lines']} | {row['review']} | {m:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Field coverage (extracted rows)",
            "",
            "Share of lines with a non-empty value (mock path).",
            "",
            "| Field | Corpus-wide |",
            "|-------|-------------|",
        ]
    )
    for field, rate in agg_coverage.items():
        lines.append(f"| `{field}` | {rate * 100:.1f}% |")

    lines.extend(
        [
            "",
            "## Reconciliation confidence distribution",
            "",
            f"- **Mean confidence:** {mean_conf:.4f}",
            f"- **Median confidence:** {med_conf:.4f}",
            "",
            "| Bin | Count |",
            "|-----|-------|",
        ]
    )
    for label in ("< 0.40 (review)", "0.40 – 0.59", "0.60 – 0.79", "≥ 0.80"):
        lines.append(f"| {label} | {conf_bins.get(label, 0)} |")

    auto_rate = 1.0 - review_rate
    lines.extend(
        [
            "",
            "## Review queue",
            "",
            f"- **Lines flagged for human review:** {total_review} / {total_lines} ({review_rate * 100:.1f}%)",
            f"- **Auto-reconcile rate (confidence ≥ {REVIEW_THRESHOLD:.2f}):** {auto_rate * 100:.1f}%",
            "",
            "Expected teaching case: `invoice_noisy_ocr.txt` line `ZZ-9999-0000` — unknown part, confidence below threshold.",
            "",
            "## Regenerate",
            "",
            "```bash",
            "python scripts/eda_corpus.py",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Markdown report path",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print report instead of writing file",
    )
    args = parser.parse_args()

    report = build_markdown()
    if args.stdout:
        print(report, end="")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())