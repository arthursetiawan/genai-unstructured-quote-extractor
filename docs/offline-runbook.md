# Offline and LLM extraction runbook

Recruiters and CI should be able to run the full **extract → validate → reconcile** path without cloud credentials. Live Gemini / OpenAI extraction is optional.

## Mode resolution

`QUOTE_EXTRACTOR_MODE` controls the backend (`auto` default):

| Mode | When used |
|------|-----------|
| `mock` | Forced heuristic parser (offline) |
| `gemini` | Requires `GEMINI_API_KEY` (Gemini 2.0 Flash JSON) |
| `openai` | Requires `OPENAI_API_KEY` (structured JSON) |
| `auto` | Gemini if key present, else OpenAI, else **mock** |

Install LLM extras only when you need live calls:

```bash
pip install -e ".[llm]"
cp .env.example .env   # add GEMINI_API_KEY and/or OPENAI_API_KEY
```

## Offline paths (no keys)

### Tests

```bash
pip install -e ".[dev]"
pytest
```

### Fixture smoke (all samples)

```bash
python scripts/offline_smoke.py
```

### Streamlit

```bash
streamlit run app.py
```

Sidebar shows resolved `LLM mode`; without keys it reads `mock`. Preloaded samples live under `data/samples/`.

### Python API

```python
from pathlib import Path
from quote_extractor.extract import extract_quote
from quote_extractor.catalog import load_catalog
from reconcile import reconcile_lines

quote = extract_quote(Path("data/samples/invoice_freight_ltl.txt"), mode="mock")
results = reconcile_lines(quote.line_items, load_catalog())
```

On LLM failure (network, bad JSON, quota), `extract_quote` **falls back to mock** so demos never hard-fail.

## Live Gemini path

1. Set `GEMINI_API_KEY` in `.env` (or environment).
2. `QUOTE_EXTRACTOR_MODE=auto` or `gemini`.
3. Paste the same noisy OCR sample; compare mock vs model output in Streamlit.

## Primary marketing demo

Static UX mock (no Streamlit host required): https://arthursetiawan.github.io/demos/genai-quote/

This repo is the **runnable** counterpart — synthetic data only, resume-honest stack (Pydantic, rapidfuzz, optional Gemini/OpenAI).