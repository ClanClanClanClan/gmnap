from __future__ import annotations
from typing import Dict, Tuple, List

try:
    import pdfplumber  # optional
except Exception:
    pdfplumber = None


class CostMeter:
    def __init__(self, monthly_cap_chf: float = 40.0):
        self.cap = monthly_cap_chf
        self.spent = 0.0

    def add(self, chf: float):
        self.spent += chf
        if self.spent > self.cap:
            raise RuntimeError(f"LLM cost cap exceeded: {self.spent:.2f} CHF > {self.cap:.2f} CHF")


def validate_llm_json(obj: Dict, schema: Dict) -> Tuple[bool, List[str]]:
    required = schema.get("required", [])
    errs = []
    for k in required:
        if k not in obj:
            errs.append(f"Missing key: {k}")
    return (len(errs) == 0), errs


def extract_from_pdf(pdf_path: str, max_pages: int = 400) -> str:
    if not pdfplumber:
        return "OFFLINE: sample abstract text."
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            if i >= max_pages:
                break
            text.append(page.extract_text() or "")
    return "\n".join(text)


def call_llm_stub(text: str) -> Dict:
    # Deterministic placeholder; real system would call GPT-4o-mini
    return {
        "title": "Sample Thesis Title",
        "authors": ["Sample Author"],
        "advisors": ["Sample Advisor"],
        "degree_date": "2024-06",
        "degree": "PhD",
        "institution": "ETH Zürich",
        "language": "en",
    }


def run_llm_etd(pdf_path: str, specs: Dict) -> Tuple[str, Dict]:
    llm_spec = (specs or {}).get("llm_extract", {})
    max_pages = int(llm_spec.get("max_pdf_pages", 400))
    cap = float(llm_spec.get("cost_cap_chf_per_month", 40))
    schema = llm_spec.get("json_schema_inline", {})
    meter = CostMeter(monthly_cap_chf=cap)
    text = extract_from_pdf(pdf_path, max_pages=max_pages)
    meter.add(0.01)  # charge a cent offline
    obj = call_llm_stub(text)
    ok, errs = validate_llm_json(obj, schema)
    if not ok:
        raise RuntimeError("LLM JSON invalid: " + "; ".join(errs))
    return pdf_path, obj
