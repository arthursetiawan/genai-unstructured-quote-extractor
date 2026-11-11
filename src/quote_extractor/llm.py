"""LLM providers for structured quote extraction with defensive retries."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from quote_extractor.models import ExtractedQuote, LineItem

load_dotenv()

SYSTEM_PROMPT = """You extract automotive and freight quote line items from unstructured text.
Return ONLY valid JSON matching this schema:
{
  "source_name": string,
  "vendor_hint": string|null,
  "currency": "USD",
  "line_items": [
    {
      "PartNumber": string,
      "Description": string,
      "UnitCost": number,
      "CompetitorPrice": number|null,
      "Vendor": string
    }
  ],
  "raw_notes": string|null
}
Do not invent parts that are not supported by the text. Normalize currency amounts to numbers.
"""


class LLMError(RuntimeError):
    """Raised when an LLM call fails after retries or returns unusable output."""


class LLMClient(Protocol):
    def complete_json(self, user_prompt: str) -> dict[str, Any]:
        ...


def _max_retries() -> int:
    try:
        return max(1, int(os.getenv("LLM_MAX_RETRIES", "3")))
    except ValueError:
        return 3


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_quote_payload(payload: dict[str, Any] | str) -> ExtractedQuote:
    if isinstance(payload, str):
        payload = json.loads(_strip_code_fence(payload))
    return ExtractedQuote.model_validate(payload)


class MockLLMClient:
    """Offline extractor used when no API key is configured."""

    def complete_json(self, user_prompt: str) -> dict[str, Any]:
        return mock_extract_from_text(user_prompt).model_dump()


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    def complete_json(self, user_prompt: str) -> dict[str, Any]:
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover
            raise LLMError("google-generativeai is not installed") from exc

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            self.model,
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        )

        @retry(
            reraise=True,
            stop=stop_after_attempt(_max_retries()),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type(Exception),
        )
        def _call() -> str:
            response = model.generate_content(user_prompt)
            text = getattr(response, "text", None)
            if not text:
                raise LLMError("Gemini returned empty response")
            return text

        try:
            return json.loads(_strip_code_fence(_call()))
        except json.JSONDecodeError as exc:
            raise LLMError(f"Gemini returned invalid JSON: {exc}") from exc


class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def complete_json(self, user_prompt: str) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMError("openai is not installed") from exc

        client = OpenAI(api_key=self.api_key)

        @retry(
            reraise=True,
            stop=stop_after_attempt(_max_retries()),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type(Exception),
        )
        def _call() -> dict[str, Any]:
            response = client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
            if not content:
                raise LLMError("OpenAI returned empty response")
            return json.loads(_strip_code_fence(content))

        try:
            return _call()
        except json.JSONDecodeError as exc:
            raise LLMError(f"OpenAI returned invalid JSON: {exc}") from exc


def resolve_mode(explicit: str | None = None) -> str:
    mode = (explicit or os.getenv("QUOTE_EXTRACTOR_MODE", "auto")).strip().lower()
    if mode not in {"auto", "mock", "gemini", "openai"}:
        raise ValueError(f"Unsupported QUOTE_EXTRACTOR_MODE: {mode}")
    if mode != "auto":
        return mode
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "mock"


def get_llm_client(mode: str | None = None) -> tuple[str, LLMClient]:
    resolved = resolve_mode(mode)
    if resolved == "mock":
        return resolved, MockLLMClient()
    if resolved == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY is required for gemini mode")
        return resolved, GeminiClient(key)
    if resolved == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise LLMError("OPENAI_API_KEY is required for openai mode")
        return resolved, OpenAIClient(key)
    raise LLMError(f"Unknown mode: {resolved}")


_MONEY = re.compile(
    r"(?P<label>unit(?:\s*cost)?|price|cost|competitor(?:\s*price)?)\s*[:=]?\s*\$?\s*(?P<amount>\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_PART = re.compile(
    r"(?:part(?:\s*#| number)?|pn|sku)\s*[:=]?\s*([A-Z0-9][A-Z0-9\-_/ ]{2,})",
    re.IGNORECASE,
)
_VENDOR = re.compile(r"(?:vendor|supplier|sold by)\s*[:=]?\s*([A-Za-z0-9 &\-./]+)", re.IGNORECASE)
_DESC = re.compile(r"(?:desc(?:ription)?|item)\s*[:=]?\s*(.+)$", re.IGNORECASE)


def _parse_pipe_line(line: str) -> LineItem | None:
    """Parse `PN | Description | $cost | Vendor [| competitor]` rows."""
    pipe_parts = [p.strip() for p in line.split("|")]
    if len(pipe_parts) < 3:
        return None
    maybe_part = pipe_parts[0]
    if not re.match(r"^[A-Z0-9][A-Z0-9\-_/]{2,}$", maybe_part, re.IGNORECASE):
        return None
    money = re.search(r"\$?\s*(\d+(?:\.\d{1,2})?)", pipe_parts[2])
    if not money:
        return None
    competitor = None
    if len(pipe_parts) >= 5:
        c_money = re.search(r"\$?\s*(\d+(?:\.\d{1,2})?)", pipe_parts[4])
        if c_money:
            competitor = float(c_money.group(1))
    vendor = pipe_parts[3] if len(pipe_parts) >= 4 else "Unknown"
    return LineItem(
        PartNumber=maybe_part,
        Description=pipe_parts[1],
        UnitCost=float(money.group(1)),
        CompetitorPrice=competitor,
        Vendor=vendor,
    )


def _normalize_part_number(raw: str) -> str:
    """Collapse OCR spacing like 'BRK 0007 4412' or 'FLT00128831' into catalog-ish form."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", raw).upper()
    m = re.match(r"^([A-Z]+)(\d{4,})(\d{4})$", cleaned)
    if m:
        return f"{m.group(1)}-{m.group(2)[-4:]}-{m.group(3)}"
    m2 = re.match(r"^([A-Z]+)(\d+)$", cleaned)
    if m2 and len(m2.group(2)) >= 8:
        digits = m2.group(2)
        return f"{m2.group(1)}-{digits[:4]}-{digits[4:8]}"
    return raw.strip().upper()


def mock_extract_from_text(text: str, source_name: str = "mock") -> ExtractedQuote:
    """Heuristic offline extractor for demos and tests without API keys."""
    blocks = re.split(r"\n\s*-{3,}\s*\n|\n\s*={3,}\s*\n|\n\s*\n+", text.strip())
    items: list[LineItem] = []
    vendor_hint: str | None = None

    for block in blocks:
        if not block.strip():
            continue
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]

        # Prefer pipe-table rows when present in the block.
        pipe_items = [_parse_pipe_line(ln) for ln in lines]
        pipe_items = [i for i in pipe_items if i is not None]
        if pipe_items:
            items.extend(pipe_items)
            vendor_hint = vendor_hint or pipe_items[0].Vendor
            continue

        joined = "\n".join(lines)
        part_match = _PART.search(joined)
        vendor_match = _VENDOR.search(joined)
        desc_match = _DESC.search(joined)

        amounts: dict[str, float] = {}
        for m in _MONEY.finditer(joined):
            key = m.group("label").lower()
            amount = float(m.group("amount"))
            if "competitor" in key:
                amounts["competitor"] = amount
            else:
                amounts["unit"] = amount

        # Compact labels: unitcost / competitorprice without separators.
        if "unit" not in amounts:
            compact = re.search(
                r"unit\s*cost\s*[:=]?\s*\$?\s*(\d+(?:\.\d{1,2})?)",
                joined,
                re.IGNORECASE,
            )
            if compact:
                amounts["unit"] = float(compact.group(1))
        if "competitor" not in amounts:
            compact_c = re.search(
                r"competitor\s*price\s*[:=]?\s*\$?\s*(\d+(?:\.\d{1,2})?)",
                joined,
                re.IGNORECASE,
            )
            if compact_c:
                amounts["competitor"] = float(compact_c.group(1))

        part_number: str | None = None
        if part_match:
            part_number = _normalize_part_number(part_match.group(1))
        else:
            loose_part = re.search(
                r"\b([A-Z]{2,5}[\s\-_]*\d{3,5}[\s\-_]*\d{3,5})\b",
                joined,
                re.IGNORECASE,
            )
            if loose_part:
                part_number = _normalize_part_number(loose_part.group(1))

        if not part_number or "unit" not in amounts:
            continue

        if vendor_match:
            vendor = vendor_match.group(1).strip()
        else:
            loose_vendor = re.search(
                r"vend(?:or|r)\s*[:=]?\s*([A-Za-z0-9 &\-./]+)",
                joined,
                re.IGNORECASE,
            )
            vendor = loose_vendor.group(1).strip() if loose_vendor else "Unknown"
        vendor_hint = vendor_hint or vendor

        if desc_match:
            description = desc_match.group(1).strip()
        else:
            loose_desc = re.search(
                r"desc(?:ryption|ription)?\s*[:=]?\s*(.+)$",
                joined,
                re.IGNORECASE | re.MULTILINE,
            )
            description = (
                loose_desc.group(1).strip()
                if loose_desc
                else next(
                    (
                        ln
                        for ln in lines
                        if "part" not in ln.lower() and "$" not in ln and "vendor" not in ln.lower()
                    ),
                    part_number,
                )
            )

        items.append(
            LineItem(
                PartNumber=part_number,
                Description=description,
                UnitCost=amounts["unit"],
                CompetitorPrice=amounts.get("competitor"),
                Vendor=vendor,
            )
        )

    return ExtractedQuote(
        source_name=source_name,
        vendor_hint=vendor_hint,
        currency="USD",
        line_items=items,
        raw_notes="mock heuristic extraction",
    )
