"""Reconcile extracted quote line items against a mock OEM catalog using rapidfuzz."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from rapidfuzz import fuzz

from quote_extractor.catalog import CatalogPart, load_catalog
from quote_extractor.models import (
    FallbackBounds,
    LineItem,
    MatchCandidate,
    ReconciliationResult,
)

# Weighted scoring as specified.
PART_WEIGHT = 0.50
PRICE_WEIGHT = 0.40
VENDOR_WEIGHT = 0.10
REVIEW_THRESHOLD = 0.40

# Deterministic fallback band: ±15% of unit cost, with a $2 absolute floor.
FALLBACK_RELATIVE = 0.15
FALLBACK_ABS_MIN = 2.0


@dataclass(frozen=True)
class ScoreBreakdown:
    part_score: float
    price_score: float
    vendor_score: float

    @property
    def confidence(self) -> float:
        return (
            PART_WEIGHT * self.part_score
            + PRICE_WEIGHT * self.price_score
            + VENDOR_WEIGHT * self.vendor_score
        )


def part_token_score(extracted: str, catalog: str) -> float:
    """Token-aware part-number similarity in [0, 1]."""
    a = extracted.strip().upper()
    b = catalog.strip().upper()
    if not a or not b:
        return 0.0
    # Blend token set ratio and partial ratio for noisy OCR / transcription.
    token = fuzz.token_set_ratio(a, b) / 100.0
    partial = fuzz.partial_ratio(a, b) / 100.0
    return 0.6 * token + 0.4 * partial


def price_proximity_score(extracted: float, catalog: float) -> float:
    """Map absolute price gap to [0, 1]; exact match => 1.0."""
    if extracted < 0 or catalog < 0:
        return 0.0
    denom = max(abs(catalog), abs(extracted), 1.0)
    gap = abs(extracted - catalog) / denom
    # Linear decay to 0 at 100% relative gap.
    return max(0.0, 1.0 - gap)


def vendor_similarity_score(extracted: str, catalog: str) -> float:
    a = extracted.strip().lower()
    b = catalog.strip().lower()
    if not a or not b:
        return 0.0
    return fuzz.token_set_ratio(a, b) / 100.0


def score_pair(line: LineItem, part: CatalogPart) -> ScoreBreakdown:
    return ScoreBreakdown(
        part_score=part_token_score(line.PartNumber, part.part_number),
        price_score=price_proximity_score(line.UnitCost, part.unit_price),
        vendor_score=vendor_similarity_score(line.Vendor, part.vendor),
    )


def deterministic_fallback_bounds(unit_cost: float) -> FallbackBounds:
    """Deterministic review bounds when confidence is below threshold."""
    span = max(unit_cost * FALLBACK_RELATIVE, FALLBACK_ABS_MIN)
    low = max(0.0, round(unit_cost - span, 2))
    high = round(unit_cost + span, 2)
    return FallbackBounds(unit_cost_low=low, unit_cost_high=high)


def _to_candidate(part: CatalogPart, breakdown: ScoreBreakdown) -> MatchCandidate:
    return MatchCandidate(
        catalog_part_number=part.part_number,
        catalog_description=part.description,
        catalog_unit_price=part.unit_price,
        catalog_vendor=part.vendor,
        part_score=round(breakdown.part_score, 4),
        price_score=round(breakdown.price_score, 4),
        vendor_score=round(breakdown.vendor_score, 4),
        confidence=round(breakdown.confidence, 4),
    )


def reconcile_line(
    line: LineItem,
    catalog: Sequence[CatalogPart],
    *,
    review_threshold: float = REVIEW_THRESHOLD,
) -> ReconciliationResult:
    """Match one noisy extracted line against the OEM catalog."""
    if not catalog:
        bounds = deterministic_fallback_bounds(line.UnitCost)
        return ReconciliationResult(
            line_item=line,
            best_match=None,
            needs_human_review=True,
            fallback_bounds=bounds,
            reason="empty catalog; flagged for human review",
        )

    best_part: CatalogPart | None = None
    best_breakdown: ScoreBreakdown | None = None
    for part in catalog:
        breakdown = score_pair(line, part)
        if best_breakdown is None or breakdown.confidence > best_breakdown.confidence:
            best_part = part
            best_breakdown = breakdown

    assert best_part is not None and best_breakdown is not None
    candidate = _to_candidate(best_part, best_breakdown)

    if candidate.confidence < review_threshold:
        return ReconciliationResult(
            line_item=line,
            best_match=candidate,
            needs_human_review=True,
            fallback_bounds=deterministic_fallback_bounds(line.UnitCost),
            reason=(
                f"confidence {candidate.confidence:.4f} < {review_threshold:.2f}; "
                "flagged for human review with deterministic fallback bounds"
            ),
        )

    return ReconciliationResult(
        line_item=line,
        best_match=candidate,
        needs_human_review=False,
        fallback_bounds=None,
        reason=f"matched {candidate.catalog_part_number} @ confidence {candidate.confidence:.4f}",
    )


def reconcile_lines(
    lines: Iterable[LineItem],
    catalog: Sequence[CatalogPart] | None = None,
    *,
    review_threshold: float = REVIEW_THRESHOLD,
) -> list[ReconciliationResult]:
    parts = list(catalog) if catalog is not None else load_catalog()
    return [reconcile_line(line, parts, review_threshold=review_threshold) for line in lines]


def reconcile_quote_dict(
    line_items: list[dict],
    catalog_path: str | None = None,
) -> list[dict]:
    """Convenience helper for Streamlit / CLI: dict in, dict out."""
    catalog = load_catalog(catalog_path) if catalog_path else load_catalog()
    parsed = [LineItem.model_validate(row) for row in line_items]
    return [r.model_dump() for r in reconcile_lines(parsed, catalog)]


if __name__ == "__main__":
    demo = LineItem(
        PartNumber="BRK-0007-4412",
        Description="Brake pad set Front Bosch",
        UnitCost=64.5,
        CompetitorPrice=70.0,
        Vendor="Bosch",
    )
    result = reconcile_line(demo, load_catalog())
    print(result.model_dump_json(indent=2))
