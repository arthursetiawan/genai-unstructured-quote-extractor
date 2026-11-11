"""Mock OEM catalog of 500 automotive / freight parts."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "oem_catalog_500.json"
)

VENDORS = [
    "Bosch",
    "Denso",
    "ACDelco",
    "Motorcraft",
    "Gates",
    "NTK",
    "SKF",
    "Timken",
    "Dayco",
    "Mann-Filter",
    "Wix",
    "Mahle",
    "Valeo",
    "TRW",
    "Monroe",
    "Moog",
    "Fel-Pro",
    "NGK",
    "Continental",
    "Freightliner OEM",
]

CATEGORIES = [
    ("BRK", "Brake pad set", 28.0, 180.0),
    ("FLT", "Oil filter", 6.5, 45.0),
    ("ALT", "Alternator reman", 95.0, 420.0),
    ("STR", "Starter motor", 85.0, 380.0),
    ("RAD", "Radiator assembly", 110.0, 520.0),
    ("WP", "Water pump", 35.0, 210.0),
    ("TB", "Timing belt kit", 55.0, 260.0),
    ("SPK", "Spark plug iridium", 4.5, 28.0),
    ("SEN", "O2 sensor", 22.0, 140.0),
    ("HUB", "Wheel hub bearing", 40.0, 220.0),
    ("CV", "CV axle assembly", 65.0, 310.0),
    ("SHK", "Shock absorber", 30.0, 190.0),
    ("CTL", "Control arm", 45.0, 250.0),
    ("FPM", "Fuel pump module", 70.0, 340.0),
    ("TMO", "Thermostat housing", 12.0, 85.0),
    ("IGC", "Ignition coil", 18.0, 110.0),
    ("ABS", "ABS wheel sensor", 16.0, 95.0),
    ("FRT", "Freight pallet strap kit", 8.0, 55.0),
    ("LTL", "LTL dock seal gasket", 25.0, 160.0),
    ("AIR", "Cabin air filter", 7.0, 42.0),
]


class CatalogPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_number: str
    description: str
    unit_price: float = Field(..., ge=0)
    vendor: str
    category: str


def generate_catalog(seed: int = 42, size: int = 500) -> list[CatalogPart]:
    """Deterministically generate a mock OEM catalog."""
    rng = random.Random(seed)
    parts: list[CatalogPart] = []
    for idx in range(1, size + 1):
        code, label, lo, hi = CATEGORIES[idx % len(CATEGORIES)]
        vendor = VENDORS[idx % len(VENDORS)]
        price = round(rng.uniform(lo, hi), 2)
        suffix = rng.randint(1000, 9999)
        part_number = f"{code}-{idx:04d}-{suffix}"
        side = rng.choice(["LH", "RH", "Front", "Rear", "Universal"])
        description = f"{label} {side} {vendor}"
        parts.append(
            CatalogPart(
                part_number=part_number,
                description=description,
                unit_price=price,
                vendor=vendor,
                category=code,
            )
        )
    return parts


def save_catalog(parts: list[CatalogPart], path: Path | str = DEFAULT_CATALOG_PATH) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = [p.model_dump() for p in parts]
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def load_catalog(path: Path | str | None = None) -> list[CatalogPart]:
    catalog_path = Path(path) if path else DEFAULT_CATALOG_PATH
    if not catalog_path.exists():
        parts = generate_catalog()
        save_catalog(parts, catalog_path)
        return parts
    raw: list[dict[str, Any]] = json.loads(catalog_path.read_text(encoding="utf-8"))
    return [CatalogPart.model_validate(row) for row in raw]


def main() -> None:
    parts = generate_catalog()
    path = save_catalog(parts)
    print(f"Wrote {len(parts)} catalog parts to {path}")


if __name__ == "__main__":
    main()
