# Sample quote fixtures (synthetic)

All files here are **fictional** automotive / freight invoice text meant to simulate OCR from PDFs and dealer counter printouts. No employer or customer data.

| File | Format stress | Expected teaching moment |
|------|---------------|---------------------------|
| `invoice_freight_ltl.txt` | Labeled fields, mixed separators | Clean multi-line extraction + catalog match |
| `invoice_dealer_parts.txt` | Pipe-separated single-line rows | Table-style dealer quote parsing |
| `invoice_noisy_ocr.txt` | Typos, alternate field names, `ZZ-9999-0000` mystery part | Fuzzy reconcile + human-review flag (`confidence < 0.40`) |

## Regenerate catalog (optional)

```bash
python scripts/generate_catalog.py
```

The committed `data/oem_catalog_500.json` is deterministic (seed 42) so reconciliation scores stay stable in tests and demos.

## Offline smoke

```bash
python scripts/offline_smoke.py
# or
python scripts/offline_smoke.py --json
```

Runs mock extraction + full-catalog reconcile on every `.txt` file above — no API keys required.