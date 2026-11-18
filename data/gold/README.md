# Synthetic gold labels

One JSON file per sample in `data/samples/`, listing **fictional** expected line items for offline extraction evaluation.

| Gold file | Sample text |
|-----------|-------------|
| `invoice_freight_ltl.json` | `invoice_freight_ltl.txt` |
| `invoice_dealer_parts.json` | `invoice_dealer_parts.txt` |
| `invoice_noisy_ocr.json` | `invoice_noisy_ocr.txt` |

Matching rule in `scripts/eval_extraction.py`: normalized part number + `UnitCost` within $0.05.

```bash
python scripts/eval_extraction.py
```