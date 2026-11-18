# GenAI Unstructured Quote Extractor

Applied GenAI pipeline that turns messy automotive / freight quote text (including simulated PDF invoice OCR) into structured **Pydantic v2** line items, then reconciles them against a **500-part mock OEM catalog** with **rapidfuzz**.

## Charter

| | |
|---|---|
| **Product** | Messy quote / invoice text → structured JSON rows → fuzzy match against a synthetic OEM catalog. |
| **North star** | A recruiter clones the repo and runs **Streamlit** or the offline smoke script with **no API keys**; optional Gemini when keys are present. |
| **Primary demo** | [Portfolio mock UX](https://arthursetiawan.github.io/demos/genai-quote/) · runnable: `streamlit run app.py` |
| **Fixtures** | [`data/samples/`](./data/samples/README.md) — three synthetic OCR / dealer-quote stress cases |
| **Offline runbook** | [`docs/offline-runbook.md`](./docs/offline-runbook.md) — mock vs Gemini/OpenAI modes, CI, fallbacks |
| **Companion repos** | [Automotive dynamic pricing](https://github.com/arthursetiawan/automotive-dynamic-pricing-engine) (guardrailed ML pricing) · [Dealer-Counter AI](https://github.com/arthursetiawan/vehicle-negotiator-engine) (negotiation audit) |
| **Non-goals** | Employer IP, real customer quotes, inflated production metrics. |

**Program sprint iter 1:** Charter block, documented fixtures, offline smoke + CI. **Iter 2:** Problem brief, EDA + extraction metrics on synthetic gold, business outcome below.

## Business outcome

**Customer:** Parts pricing / procurement ops re-keying messy dealer and freight quotes.

**Before:** Multi-line PDFs and OCR faxes → manual typing into pricing tools → errors on garbled part numbers → no signal for which rows need an analyst.

**After (this repo, synthetic data):**

| Outcome | Evidence |
|---------|----------|
| Structured rows without API keys | Mock extractor + `pytest` / `scripts/offline_smoke.py` |
| **100%** line recall on gold corpus (mock) | [`reports/extraction_metrics.md`](./reports/extraction_metrics.md) |
| **90%** auto-reconcile; **10%** review queue | [`reports/eda_summary.md`](./reports/eda_summary.md) (`ZZ-9999-0000` demo) |
| Intake problem framing + KPIs | [`docs/problem.md`](./docs/problem.md) |

**North-star KPI:** cut manual quote-entry hours per 100 line items (target ≥ 80% reduction on representative intake). Portfolio hook: upload messy doc → validated lines in seconds.

## Features

- **Extraction** into `PartNumber`, `Description`, `UnitCost`, `CompetitorPrice`, `Vendor`
- **LLM backends**: Google **Gemini 2.0 Flash** (preferred) or **OpenAI** structured JSON, with **tenacity** retries
- **Mock / offline mode** when no API key is set (tests + Streamlit demos work offline)
- **`reconcile.py`**: weighted scoring — **50%** part token, **40%** price proximity, **10%** vendor similarity; confidence **&lt; 0.40** → human review + deterministic fallback bounds
- **Streamlit** UI (`app.py`) with preloaded sample invoices
- **Pytest** coverage for schema validation failures and fuzzy-match score boundaries

## Project layout

```text
app.py                      # Streamlit demo
reconcile.py                # rapidfuzz reconciliation entrypoint
docs/problem.md             # Customer, pain, success metrics (iter 2)
reports/                    # eda_summary.md, extraction_metrics.md (regenerate via scripts/)
scripts/eda_corpus.py       # Corpus EDA → reports/eda_summary.md
scripts/eval_extraction.py  # Gold-label precision/recall
data/gold/                  # Synthetic expected line items
src/quote_extractor/
  models.py                 # Pydantic v2 schemas
  llm.py                    # Gemini / OpenAI / mock clients + retries
  extract.py                # Document → ExtractedQuote
  catalog.py                # 500-part OEM catalog generator/loader
data/
  oem_catalog_500.json      # Generated mock catalog
  samples/                  # Preloaded invoice texts
scripts/generate_catalog.py
tests/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python scripts/generate_catalog.py
```

### Environment variables

Copy `.env.example` to `.env` and optionally set:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Prefer Gemini 2.0 Flash extraction |
| `OPENAI_API_KEY` | Fallback structured-output extraction |
| `QUOTE_EXTRACTOR_MODE` | `auto` (default), `mock`, `gemini`, or `openai` |
| `LLM_MAX_RETRIES` | Defensive retry count (default `3`) |

With no keys (or `QUOTE_EXTRACTOR_MODE=mock`), the deterministic heuristic extractor is used.

See [`docs/offline-runbook.md`](./docs/offline-runbook.md) for the full mock vs LLM matrix.

### Offline smoke (recruiters, no keys)

```bash
pip install -e .
python scripts/offline_smoke.py
```

Runs mock extraction + catalog reconciliation on every file in `data/samples/`.

## Run the Streamlit demo

```bash
streamlit run app.py
```

Pick a preloaded sample under `data/samples/` or paste custom OCR / email text, then click **Extract + reconcile**.

## Tests

```bash
pytest
# or with coverage:
pytest --cov=quote_extractor --cov=reconcile
```

## Reconciliation rules

For each extracted line item vs catalog row:

\[
confidence = 0.50\cdot part\_token + 0.40\cdot price\_proximity + 0.10\cdot vendor\_similarity
\]

- If `confidence < 0.40`, the row is **flagged for human review**.
- Fallback bounds are deterministic: \(\pm \max(15\% \cdot UnitCost,\ \$2)\).

## License

MIT
