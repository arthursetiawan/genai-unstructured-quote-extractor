"""Pydantic v2 schemas for extracted quote line items and reconciliation."""

from __future__ import annotations

from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator


def _strip_upper(value: object) -> object:
    if isinstance(value, str):
        return value.strip().upper()
    return value


CurrencyCode = Annotated[str, BeforeValidator(_strip_upper)]


class LineItem(BaseModel):
    """A single extracted invoice / quote line item."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    PartNumber: str = Field(..., min_length=1, description="OEM or vendor part number")
    Description: str = Field(..., min_length=1, description="Human-readable part description")
    UnitCost: float = Field(..., ge=0, description="Quoted unit cost from the source document")
    CompetitorPrice: Optional[float] = Field(
        default=None,
        ge=0,
        description="Optional competitor / alternate market price",
    )
    Vendor: str = Field(..., min_length=1, description="Supplier or freight vendor name")

    @field_validator("PartNumber", "Description", "Vendor")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class ExtractedQuote(BaseModel):
    """Structured extraction result for one document."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(default="untitled")
    vendor_hint: Optional[str] = None
    currency: CurrencyCode = Field(default="USD", min_length=3, max_length=3)
    line_items: list[LineItem] = Field(default_factory=list)
    raw_notes: Optional[str] = None


class FallbackBounds(BaseModel):
    """Deterministic price bounds when fuzzy match confidence is too low."""

    model_config = ConfigDict(extra="forbid")

    unit_cost_low: float
    unit_cost_high: float
    method: str = "relative_band_15pct_or_min_abs_2"


class MatchCandidate(BaseModel):
    """A catalog match with weighted confidence components."""

    model_config = ConfigDict(extra="forbid")

    catalog_part_number: str
    catalog_description: str
    catalog_unit_price: float
    catalog_vendor: str
    part_score: float = Field(..., ge=0, le=1)
    price_score: float = Field(..., ge=0, le=1)
    vendor_score: float = Field(..., ge=0, le=1)
    confidence: float = Field(..., ge=0, le=1)


class ReconciliationResult(BaseModel):
    """Outcome of reconciling one extracted line against the OEM catalog."""

    model_config = ConfigDict(extra="forbid")

    line_item: LineItem
    best_match: Optional[MatchCandidate] = None
    needs_human_review: bool = False
    fallback_bounds: Optional[FallbackBounds] = None
    reason: str = ""
