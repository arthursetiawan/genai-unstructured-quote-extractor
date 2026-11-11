"""End-to-end extraction from unstructured invoice / quote text."""

from __future__ import annotations

from pathlib import Path

from quote_extractor.llm import LLMError, get_llm_client, mock_extract_from_text, parse_quote_payload
from quote_extractor.models import ExtractedQuote


def _read_document(path_or_text: str | Path) -> tuple[str, str]:
    if isinstance(path_or_text, Path) or (
        isinstance(path_or_text, str)
        and "\n" not in path_or_text
        and len(path_or_text) < 512
    ):
        path = Path(path_or_text)
        try:
            if path.exists() and path.is_file():
                # Simulated PDF invoices ship as .txt companions for offline demos.
                return path.name, path.read_text(encoding="utf-8")
        except OSError:
            pass
    return "inline", str(path_or_text)


def extract_quote(
    document: str | Path,
    *,
    mode: str | None = None,
    source_name: str | None = None,
) -> ExtractedQuote:
    """Extract structured line items from raw text or a sample invoice file.

    Uses Gemini 2.0 Flash / OpenAI when keys are present, otherwise mock mode.
    On LLM failure after retries, falls back to the deterministic mock extractor.
    """
    name, text = _read_document(document)
    resolved_name = source_name or name

    resolved_mode, client = get_llm_client(mode)
    prompt = (
        f"Document name: {resolved_name}\n\n"
        f"Extract all quote / invoice line items from the following text:\n\n{text}"
    )

    if resolved_mode == "mock":
        quote = mock_extract_from_text(text, source_name=resolved_name)
        return quote

    try:
        payload = client.complete_json(prompt)
        quote = parse_quote_payload(payload)
        if not quote.source_name or quote.source_name == "untitled":
            quote.source_name = resolved_name
        return quote
    except (LLMError, Exception):
        # Defensive offline fallback so Streamlit demos and CI never hard-fail.
        fallback = mock_extract_from_text(text, source_name=resolved_name)
        fallback.raw_notes = (
            (fallback.raw_notes or "")
            + f" | LLM mode={resolved_mode} failed; used mock fallback"
        ).strip(" |")
        return fallback
