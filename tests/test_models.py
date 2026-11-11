"""Pydantic schema validation tests for quote line items."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from quote_extractor.models import ExtractedQuote, FallbackBounds, LineItem, MatchCandidate


def test_line_item_accepts_valid_payload():
    item = LineItem(
        PartNumber="BRK-0007-4412",
        Description="Brake pad set Front Bosch",
        UnitCost=64.5,
        CompetitorPrice=71.2,
        Vendor="Bosch",
    )
    assert item.PartNumber == "BRK-0007-4412"
    assert item.CompetitorPrice == 71.2


def test_line_item_strips_whitespace():
    item = LineItem(
        PartNumber="  FLT-0012-8831 ",
        Description="  Oil filter  ",
        UnitCost=12.0,
        Vendor="  Mann-Filter ",
    )
    assert item.PartNumber == "FLT-0012-8831"
    assert item.Description == "Oil filter"
    assert item.Vendor == "Mann-Filter"


def test_line_item_rejects_blank_part_number():
    with pytest.raises(ValidationError) as exc:
        LineItem(
            PartNumber="   ",
            Description="Oil filter",
            UnitCost=12.0,
            Vendor="Mann-Filter",
        )
    assert "PartNumber" in str(exc.value)


def test_line_item_rejects_negative_unit_cost():
    with pytest.raises(ValidationError) as exc:
        LineItem(
            PartNumber="WP-1",
            Description="Water pump",
            UnitCost=-1.0,
            Vendor="Gates",
        )
    assert "UnitCost" in str(exc.value)


def test_line_item_rejects_negative_competitor_price():
    with pytest.raises(ValidationError) as exc:
        LineItem(
            PartNumber="WP-1",
            Description="Water pump",
            UnitCost=10.0,
            CompetitorPrice=-0.01,
            Vendor="Gates",
        )
    assert "CompetitorPrice" in str(exc.value)


def test_line_item_rejects_missing_required_fields():
    with pytest.raises(ValidationError) as exc:
        LineItem.model_validate({"PartNumber": "X", "UnitCost": 1.0})
    err = str(exc.value)
    assert "Description" in err
    assert "Vendor" in err


def test_line_item_forbids_extra_fields():
    with pytest.raises(ValidationError) as exc:
        LineItem.model_validate(
            {
                "PartNumber": "X-1",
                "Description": "Thing",
                "UnitCost": 1.0,
                "Vendor": "Acme",
                "Surprise": True,
            }
        )
    assert "Surprise" in str(exc.value) or "extra" in str(exc.value).lower()


def test_extracted_quote_normalizes_currency():
    quote = ExtractedQuote(currency=" usd ", line_items=[])
    assert quote.currency == "USD"


def test_match_candidate_bounds():
    with pytest.raises(ValidationError):
        MatchCandidate(
            catalog_part_number="A",
            catalog_description="d",
            catalog_unit_price=1.0,
            catalog_vendor="v",
            part_score=1.2,
            price_score=0.5,
            vendor_score=0.5,
            confidence=0.5,
        )


def test_fallback_bounds_model():
    bounds = FallbackBounds(unit_cost_low=10.0, unit_cost_high=14.0)
    assert bounds.method.startswith("relative_band")
