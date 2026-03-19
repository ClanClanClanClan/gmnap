"""LLM-based ETD (Electronic Thesis & Dissertation) metadata extractor.

Stage 1b of the V7 pipeline. Uses Claude/GPT-4o-mini to extract structured
metadata from thesis PDFs. Includes cost metering (CHF 40/month cap) and
result caching.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import pdfplumber
except Exception:
    pdfplumber = None

# ── Cost metering ─────────────────────────────────────────────────────────

COST_FILE = pathlib.Path(os.getenv("GMNAP_COST_FILE", "cache/api_costs.json"))
LLM_CACHE_DIR = pathlib.Path(os.getenv("GMNAP_LLM_CACHE", "cache/llm"))


class CostMeter:
    """Track API spend against monthly cap (V7 spec: CHF 40/month for LLM)."""

    def __init__(self, monthly_cap_chf: float = 40.0):
        self.cap = monthly_cap_chf
        self.spent = self._load_month_spend()

    def _load_month_spend(self) -> float:
        if COST_FILE.exists():
            try:
                data = json.loads(COST_FILE.read_text())
                month_key = datetime.now().strftime("%Y-%m")
                return float(data.get(f"llm_{month_key}", 0.0))
            except Exception:
                pass
        return 0.0

    def add(self, chf: float) -> None:
        self.spent += chf
        if self.spent > self.cap:
            raise RuntimeError(
                f"LLM cost cap exceeded: CHF {self.spent:.2f} > {self.cap:.2f}"
            )
        self._persist(chf)

    def _persist(self, increment: float) -> None:
        COST_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if COST_FILE.exists():
            try:
                data = json.loads(COST_FILE.read_text())
            except Exception:
                pass
        month_key = f"llm_{datetime.now().strftime('%Y-%m')}"
        data[month_key] = data.get(month_key, 0.0) + increment
        COST_FILE.write_text(json.dumps(data, indent=2))


# ── PDF extraction ────────────────────────────────────────────────────────


def extract_from_pdf(pdf_path: str, max_pages: int = 400) -> str:
    """Extract text from PDF for LLM processing."""
    if not pdfplumber:
        logger.warning("pdfplumber not installed; returning empty text")
        return ""
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            if i >= max_pages:
                break
            text.append(page.extract_text() or "")
    return "\n".join(text)


# ── LLM cache ─────────────────────────────────────────────────────────────


def _cache_key(text: str) -> pathlib.Path:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return LLM_CACHE_DIR / f"etd_{h}.json"


def _cache_get(key: pathlib.Path) -> Optional[Dict]:
    if key.exists():
        try:
            return json.loads(key.read_text("utf-8"))
        except Exception:
            pass
    return None


def _cache_set(key: pathlib.Path, obj: Dict) -> None:
    key.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


# ── JSON schema validation ───────────────────────────────────────────────


ETD_SCHEMA = {
    "required": ["title", "authors", "advisors", "degree_date", "degree", "institution", "language"],
    "properties": {
        "title": {"type": "string"},
        "authors": {"type": "array"},
        "advisors": {"type": "array"},
        "degree_date": {"type": "string"},
        "degree": {"type": "string"},
        "institution": {"type": "string"},
        "language": {"type": "string"},
    },
}


def validate_llm_json(obj: Dict, schema: Optional[Dict] = None) -> Tuple[bool, List[str]]:
    """Validate LLM output against schema."""
    schema = schema or ETD_SCHEMA
    required = schema.get("required", [])
    errs = []
    for k in required:
        if k not in obj:
            errs.append(f"Missing key: {k}")
    return (len(errs) == 0), errs


# ── LLM call implementations ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are a metadata extractor for academic theses and dissertations.
Given the text of a thesis, extract the following fields as JSON:
- title: The thesis title
- authors: List of author names
- advisors: List of advisor/supervisor names
- degree_date: Date of degree (YYYY-MM format)
- degree: Type of degree (PhD, MSc, etc.)
- institution: Granting institution name
- language: ISO 639-1 language code (en, de, fr, etc.)

Return ONLY valid JSON, no markdown or explanation."""


def _estimate_cost_claude(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in CHF for Claude API call (Haiku pricing)."""
    # Claude Haiku: $0.25/1M input, $1.25/1M output (approx CHF equivalent)
    input_cost = (input_tokens / 1_000_000) * 0.25
    output_cost = (output_tokens / 1_000_000) * 1.25
    return input_cost + output_cost


def _estimate_cost_openai(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in CHF for GPT-4o-mini API call."""
    # GPT-4o-mini: $0.15/1M input, $0.60/1M output (approx CHF equivalent)
    input_cost = (input_tokens / 1_000_000) * 0.15
    output_cost = (output_tokens / 1_000_000) * 0.60
    return input_cost + output_cost


def call_llm_claude(text: str, meter: CostMeter) -> Dict:
    """Call Claude API (Haiku) for ETD extraction."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    # Truncate to ~100K chars to stay within context limits
    truncated = text[:100_000]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Extract metadata from this thesis:\n\n{truncated}"}],
    )

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = _estimate_cost_claude(input_tokens, output_tokens)
    meter.add(cost)

    content = response.content[0].text.strip()
    # Strip markdown fences if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
    return json.loads(content)


def call_llm_openai(text: str, meter: CostMeter) -> Dict:
    """Call OpenAI API (GPT-4o-mini) for ETD extraction."""
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package not installed. pip install openai")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = openai.OpenAI(api_key=api_key)

    truncated = text[:100_000]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract metadata from this thesis:\n\n{truncated}"},
        ],
        max_tokens=1024,
        temperature=0.0,
    )

    usage = response.usage
    cost = _estimate_cost_openai(usage.prompt_tokens, usage.completion_tokens)
    meter.add(cost)

    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
    return json.loads(content)


def call_llm_stub(text: str) -> Dict:
    """Deterministic placeholder when no API key is available."""
    return {
        "title": "Sample Thesis Title",
        "authors": ["Sample Author"],
        "advisors": ["Sample Advisor"],
        "degree_date": "2024-06",
        "degree": "PhD",
        "institution": "ETH Zurich",
        "language": "en",
    }


# ── Main entry point ─────────────────────────────────────────────────────


def run_llm_etd(pdf_path: str, specs: Optional[Dict] = None) -> Tuple[str, Dict]:
    """Extract ETD metadata from a PDF using LLM.

    Tries Claude (Haiku) first, then OpenAI (GPT-4o-mini), then falls
    back to a deterministic stub if no API keys are configured.

    Args:
        pdf_path: Path to the thesis PDF.
        specs: V7 spec dict (for llm_extract config).

    Returns:
        Tuple of (pdf_path, extracted_metadata_dict).
    """
    llm_spec = (specs or {}).get("llm_extract", {})
    max_pages = int(llm_spec.get("max_pdf_pages", 400))
    cap = float(llm_spec.get("cost_cap_chf_per_month", 40))
    schema = llm_spec.get("json_schema_inline", ETD_SCHEMA)

    meter = CostMeter(monthly_cap_chf=cap)
    text = extract_from_pdf(pdf_path, max_pages=max_pages)

    if not text.strip():
        logger.warning(f"No text extracted from {pdf_path}, using stub")
        return pdf_path, call_llm_stub("")

    # Check cache first
    ck = _cache_key(text)
    cached = _cache_get(ck)
    if cached:
        logger.info(f"LLM cache hit for {pdf_path}")
        return pdf_path, cached

    # Try real LLM providers, fall back to stub
    obj = None
    provider = "stub"

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            obj = call_llm_claude(text, meter)
            provider = "claude"
        except Exception as e:
            logger.warning(f"Claude API failed: {e}")

    if obj is None and os.getenv("OPENAI_API_KEY"):
        try:
            obj = call_llm_openai(text, meter)
            provider = "openai"
        except Exception as e:
            logger.warning(f"OpenAI API failed: {e}")

    if obj is None:
        logger.info("No LLM API keys configured, using stub extraction")
        obj = call_llm_stub(text)
        provider = "stub"

    # Validate
    ok, errs = validate_llm_json(obj, schema)
    if not ok:
        logger.warning(f"LLM output validation failed ({provider}): {errs}")
        # Fall back to stub on validation failure
        obj = call_llm_stub(text)
        provider = "stub"

    obj["_llm_provider"] = provider
    obj["_extraction_date"] = datetime.now().isoformat()

    # Cache successful extraction
    if provider != "stub":
        _cache_set(ck, obj)

    logger.info(f"ETD extraction via {provider} for {pdf_path}")
    return pdf_path, obj
