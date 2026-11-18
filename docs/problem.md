# Problem brief — unstructured quote intake

## Customer

**Parts pricing and procurement ops** at regional automotive distributors and LTL freight shippers. Intake teams receive dealer counter printouts, emailed quotes, and faxed/OCR invoices with inconsistent layouts, typos, and mixed OEM vendors. They must enter structured rows (part number, cost, vendor) into pricing systems before margin rules and catalog reconciliation can run.

## Pain

| Symptom | Impact |
|---------|--------|
| Manual re-keying from PDF/OCR text | 5–15 minutes per multi-line quote; backlog grows at month-end |
| Field drift (`Part#` vs `SKU`, `Price` vs `Unit Cost`) | Wrong rows slip into ERP; downstream reconcile noise |
| Unknown or OCR-garbled part numbers | Analysts stall until someone opens the PDF again |
| No confidence signal | Everything treated as equally trustworthy |

**Hook (demo):** Upload a messy synthetic invoice → validated `LineItem` JSON in seconds → catalog reconcile flags low-confidence rows for human review instead of silent wrong matches.

## North-star KPI

**Manual quote-entry hours per 100 line items** — target **≥ 80% reduction** on representative intake (structured export + review queue only for exceptions).

## Success metrics (iter 2, synthetic corpus)

Measurable on the committed `data/samples/*.txt` fixtures and offline mock extractor (no API keys):

| Metric | Definition | Iter 2 target |
|--------|------------|---------------|
| **Extraction recall** | Gold line items recovered (part + unit cost) | ≥ 95% on corpus |
| **Extraction precision** | Predicted lines that match gold | ≥ 95% |
| **Field coverage** | Required fields present on extracted rows (`PartNumber`, `Description`, `UnitCost`, `Vendor`) | 100% on mock path |
| **Auto-reconcile rate** | Lines with reconcile confidence ≥ 0.40 (no human review) | ≥ 85% corpus-wide |
| **Review-queue precision** | Rows flagged for review that are truly ambiguous (e.g. `ZZ-9999-0000`) | Teachable in demo |

Artifacts that evidence these:

- [`reports/eda_summary.md`](../reports/eda_summary.md) — corpus EDA from `scripts/eda_corpus.py`
- [`reports/extraction_metrics.md`](../reports/extraction_metrics.md) — precision/recall vs `data/gold/`
- [`scripts/offline_smoke.py`](../scripts/offline_smoke.py) — recruiter one-command smoke

## Non-goals

- Real customer quotes, employer IP, or production volume claims
- Live LLM benchmarking in CI (optional local Gemini/OpenAI only)

## Data posture

All text fixtures and gold labels are **synthetic**. Catalog is a **500-part mock OEM** (`data/oem_catalog_500.json`, seed 42).