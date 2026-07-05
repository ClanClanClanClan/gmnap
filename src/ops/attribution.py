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
    specs = load_specs()
    lines = []
    lines.append("ATTRIBUTION — Third-party sources and licences\n")
    lines.append(
        "This file is auto-generated based on specs_v7.yaml authority_sources.\n"
    )
    sources = specs.get("authority_sources", []) or []
    for src in sources:
        name = src.get("service")
        licence = src.get("licence", "Unknown")
        # The spec's licence values (and this map's CC-BY key) historically
        # carry U+2011 NON-BREAKING HYPHEN; normalise so an ASCII "CC-BY"
        # in either place still resolves to its SPDX id.
        licence_key = str(licence).replace("\u2011", "-")
        spdx = SPDX.get(licence_key, SPDX.get(licence, licence))
        lines.append(f"- {name}: licence={licence} (SPDX: {spdx})")
    lines.append("— End —\n")
    return "\n".join(lines)
