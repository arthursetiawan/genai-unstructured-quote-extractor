# Extraction metrics — synthetic gold labels

*Generated 2026-11-18 by `scripts/eval_extraction.py` (mode=`mock`, match on normalized part number + unit cost ± $0.05).*

## Micro-averaged (corpus)

| Precision | Recall | F1 | TP | FP | FN |
|-----------|--------|----|----|----|----|
| 1.0000 | 1.0000 | 1.0000 | 10 | 0 | 0 |

## Per-sample

| Sample | Gold lines | Predicted | TP | FP | FN | Precision | Recall |
|--------|------------|-----------|----|----|-----|-----------|--------|
| `invoice_dealer_parts.txt` | 4 | 4 | 4 | 0 | 0 | 1.0000 | 1.0000 |
| `invoice_freight_ltl.txt` | 3 | 3 | 3 | 0 | 0 | 1.0000 | 1.0000 |
| `invoice_noisy_ocr.txt` | 3 | 3 | 3 | 0 | 0 | 1.0000 | 1.0000 |

## Gold labels

Committed under `data/gold/*.json` — fictional line items aligned to `data/samples/*.txt`.

## Regenerate

```bash
python scripts/eval_extraction.py
```
