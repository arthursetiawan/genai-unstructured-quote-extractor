#!/usr/bin/env python3
"""Generate the 500-part mock OEM catalog into data/oem_catalog_500.json."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quote_extractor.catalog import generate_catalog, save_catalog  # noqa: E402


def main() -> None:
    out = ROOT / "data" / "oem_catalog_500.json"
    path = save_catalog(generate_catalog(seed=42, size=500), out)
    print(f"Wrote catalog: {path}")


if __name__ == "__main__":
    main()
