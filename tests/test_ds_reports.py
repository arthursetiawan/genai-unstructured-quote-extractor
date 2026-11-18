"""DS lifecycle iter 2: gold labels + report scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from quote_extractor.extract import extract_quote

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data" / "samples"
GOLD = ROOT / "data" / "gold"


def test_gold_labels_align_with_samples():
    for gold_path in sorted(GOLD.glob("*.json")):
        data = json.loads(gold_path.read_text(encoding="utf-8"))
        sample = SAMPLES / data["source"]
        assert sample.exists(), data["source"]
        quote = extract_quote(sample, mode="mock")
        assert len(quote.line_items) == len(data["line_items"])


def test_eval_extraction_perfect_on_mock_corpus():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "eval_extraction.py"), "--stdout"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    assert "1.0000 | 1.0000" in proc.stdout


def test_eda_corpus_runs():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "eda_corpus.py"), "--stdout"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    assert "Review queue" in proc.stdout
    assert "10" in proc.stdout  # total lines in corpus