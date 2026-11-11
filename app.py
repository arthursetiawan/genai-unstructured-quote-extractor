"""Streamlit demo for unstructured quote extraction + catalog reconciliation."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from quote_extractor.catalog import load_catalog  # noqa: E402
from quote_extractor.extract import extract_quote  # noqa: E402
from quote_extractor.llm import resolve_mode  # noqa: E402
from reconcile import REVIEW_THRESHOLD, reconcile_lines  # noqa: E402

SAMPLES_DIR = ROOT / "data" / "samples"
SAMPLE_FILES = sorted(SAMPLES_DIR.glob("*.txt"))


@st.cache_resource
def _catalog():
    return load_catalog()


def _load_sample(name: str) -> str:
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


def main() -> None:
    st.set_page_config(
        page_title="GenAI Quote Extractor",
        page_icon="🧾",
        layout="wide",
    )
    st.title("GenAI Unstructured Quote Extractor")
    st.caption(
        "Extract automotive / freight invoice line items into Pydantic models, "
        "then reconcile against a 500-part OEM catalog with rapidfuzz."
    )

    mode = resolve_mode()
    st.sidebar.header("Runtime")
    st.sidebar.write(f"**LLM mode:** `{mode}`")
    st.sidebar.write(
        "Set `GEMINI_API_KEY` or `OPENAI_API_KEY` for live LLM extraction. "
        "Without keys, mock/offline mode is used automatically."
    )
    st.sidebar.write(f"**Review threshold:** {REVIEW_THRESHOLD:.2f}")
    catalog = _catalog()
    st.sidebar.write(f"**Catalog size:** {len(catalog)} parts")

    sample_names = [p.name for p in SAMPLE_FILES]
    default_idx = 0
    choice = st.selectbox("Preloaded sample invoice", sample_names, index=default_idx)
    use_custom = st.checkbox("Paste custom unstructured text instead", value=False)

    if use_custom:
        text = st.text_area("Invoice / quote text", height=280, placeholder="Paste OCR or email text…")
        source_name = "custom_paste"
    else:
        text = _load_sample(choice)
        source_name = choice
        st.text_area("Sample contents", value=text, height=280, disabled=True)

    col_a, col_b = st.columns(2)
    run = col_a.button("Extract + reconcile", type="primary")
    col_b.write("")

    if not run:
        st.info("Choose a preloaded invoice (or paste text) and click **Extract + reconcile**.")
        return

    if not text.strip():
        st.warning("No text to extract.")
        return

    with st.spinner("Extracting line items…"):
        quote = extract_quote(text, source_name=source_name)

    st.subheader("Extracted quote")
    st.json(quote.model_dump())

    results = reconcile_lines(quote.line_items, catalog)
    st.subheader("Reconciliation")
    if not results:
        st.warning("No line items extracted.")
        return

    rows = []
    for r in results:
        match = r.best_match
        rows.append(
            {
                "PartNumber": r.line_item.PartNumber,
                "Vendor": r.line_item.Vendor,
                "UnitCost": r.line_item.UnitCost,
                "MatchedPart": match.catalog_part_number if match else None,
                "Confidence": match.confidence if match else 0.0,
                "NeedsReview": r.needs_human_review,
                "FallbackLow": r.fallback_bounds.unit_cost_low if r.fallback_bounds else None,
                "FallbackHigh": r.fallback_bounds.unit_cost_high if r.fallback_bounds else None,
                "Reason": r.reason,
            }
        )
    st.dataframe(rows, use_container_width=True)

    review_count = sum(1 for r in results if r.needs_human_review)
    st.write(
        f"Matched {len(results) - review_count}/{len(results)} above threshold; "
        f"{review_count} flagged for human review."
    )


if __name__ == "__main__":
    main()
