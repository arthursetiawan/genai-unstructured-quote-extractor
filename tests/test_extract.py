"""Extraction + mock LLM tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from quote_extractor.catalog import generate_catalog, load_catalog
from quote_extractor.extract import extract_quote
from quote_extractor.llm import mock_extract_from_text, resolve_mode
from reconcile import reconcile_lines

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def test_resolve_mode_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("QUOTE_EXTRACTOR_MODE", "auto")
    assert resolve_mode() == "mock"


def test_mock_extract_labeled_invoice():
    text = (SAMPLES / "invoice_freight_ltl.txt").read_text(encoding="utf-8")
    quote = mock_extract_from_text(text, source_name="invoice_freight_ltl.txt")
    assert len(quote.line_items) >= 3
    parts = {i.PartNumber for i in quote.line_items}
    assert "BRK-0007-4412" in parts
    assert all(i.UnitCost >= 0 for i in quote.line_items)


def test_mock_extract_pipe_table():
    text = (SAMPLES / "invoice_dealer_parts.txt").read_text(encoding="utf-8")
    quote = mock_extract_from_text(text, source_name="invoice_dealer_parts.txt")
    assert len(quote.line_items) >= 4
    assert quote.line_items[0].Vendor


def test_extract_quote_mock_mode_from_file():
    path = SAMPLES / "invoice_freight_ltl.txt"
    quote = extract_quote(path, mode="mock")
    assert quote.source_name == path.name
    assert len(quote.line_items) >= 2


def test_catalog_has_500_parts(tmp_path):
    parts = generate_catalog(seed=42, size=500)
    assert len(parts) == 500
    assert len({p.part_number for p in parts}) == 500


def test_end_to_end_extract_and_reconcile():
    text = (SAMPLES / "invoice_noisy_ocr.txt").read_text(encoding="utf-8")
    quote = extract_quote(text, mode="mock", source_name="noisy")
    catalog = generate_catalog(seed=42, size=500)
    results = reconcile_lines(quote.line_items, catalog)
    assert results
    # Mystery part should require human review.
    mystery = [r for r in results if r.line_item.PartNumber.upper().startswith("ZZ-")]
    if mystery:
        assert mystery[0].needs_human_review is True
        assert mystery[0].fallback_bounds is not None


def test_load_catalog_creates_default(tmp_path, monkeypatch):
    target = tmp_path / "oem_catalog_500.json"
    monkeypatch.setattr(
        "quote_extractor.catalog.DEFAULT_CATALOG_PATH",
        target,
        raising=False,
    )
    # Call with explicit missing path via generate+save path through load_catalog(path)
    parts = load_catalog(target)
    assert len(parts) == 500
    assert target.exists()
