from __future__ import annotations
from .spec_loader import load_specs

SPDX = {
    "CC0": "CC0-1.0",
    "CC-BY": "CC-BY-4.0",
    "Mixed": "Custom",
    "Subscription": "Proprietary",
    "Elsevier": "Proprietary",
    "DigitalScience": "Proprietary",
    "Commercial": "Proprietary",
    "Scraping": "Terms-of-Service",
}


def generate_attribution_text() -> str:
    try:
        specs = load_specs()
    except Exception:
        return "ATTRIBUTION - No spec file found.\n"
    lines = []
    lines.append("ATTRIBUTION - Third-party sources and licences\n")
    lines.append("This file is auto-generated based on specs_v7.yaml authority_sources.\n")
    sources = specs.get("authority_sources", []) or []
    for src in sources:
        name = src.get("service")
        licence = src.get("licence", "Unknown")
        spdx = SPDX.get(licence, licence)
        lines.append(f"- {name}: licence={licence} (SPDX: {spdx})")
    lines.append("- End -\n")
    return "\n".join(lines)
