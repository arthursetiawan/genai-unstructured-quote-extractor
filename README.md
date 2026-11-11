# GenAI Unstructured Quote Extractor

Applied GenAI pipeline that turns messy automotive / freight quote text (including simulated PDF invoice OCR) into structured **Pydantic v2** line items, then reconciles them against a **500-part mock OEM catalog** with **rapidfuzz**.

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
