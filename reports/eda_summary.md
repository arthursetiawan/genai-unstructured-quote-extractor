# EDA summary — synthetic quote corpus

*Generated 2026-11-18 by `scripts/eda_corpus.py` (mock extraction, seed-42 catalog).*

## Corpus

| Samples | Total line items | Catalog size | Review threshold |
|---------|------------------|--------------|------------------|
| 3 | 10 | 500 | 0.40 |

## Per-sample breakdown

| Sample | Lines | Review queue | Mean confidence |
|--------|-------|--------------|-----------------|
| `invoice_dealer_parts.txt` | 4 | 0 | 0.7417 |
| `invoice_freight_ltl.txt` | 3 | 0 | 0.7915 |
| `invoice_noisy_ocr.txt` | 3 | 1 | 0.6514 |

## Field coverage (extracted rows)

Share of lines with a non-empty value (mock path).

| Field | Corpus-wide |
|-------|-------------|
| `PartNumber` | 100.0% |
| `Description` | 100.0% |
| `UnitCost` | 100.0% |
| `Vendor` | 100.0% |
| `CompetitorPrice (optional)` | 50.0% |

## Reconciliation confidence distribution

- **Mean confidence:** 0.7295
- **Median confidence:** 0.7605

| Bin | Count |
|-----|-------|
| < 0.40 (review) | 1 |
| 0.40 – 0.59 | 0 |
| 0.60 – 0.79 | 6 |
| ≥ 0.80 | 3 |

## Review queue

- **Lines flagged for human review:** 1 / 10 (10.0%)
- **Auto-reconcile rate (confidence ≥ 0.40):** 90.0%

Expected teaching case: `invoice_noisy_ocr.txt` line `ZZ-9999-0000` — unknown part, confidence below threshold.

## Regenerate

```bash
python scripts/eda_corpus.py
```
