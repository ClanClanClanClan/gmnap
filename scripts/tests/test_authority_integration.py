#!/usr/bin/env python3
"""
Test authority source integration for V7 compliance.
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_authority_sources():
    """Test that all authority sources are properly integrated."""

    print("=" * 60)
    print("TESTING AUTHORITY SOURCE INTEGRATION")
    print("=" * 60)

    # Test imports
    print("\n1. Testing imports...")
    sources_status = {}

    # Tier 0 sources
    try:
        from src.authorities.tier0.crossref import CrossrefFetcher

        sources_status["Crossref"] = "IMPORTED"
    except ImportError as e:
        sources_status["Crossref"] = f"FAILED: {e}"

    try:
        from src.authorities.tier0.orcid import ORCIDFetcher

        sources_status["ORCID"] = "IMPORTED"
    except ImportError as e:
        sources_status["ORCID"] = f"FAILED: {e}"

    try:
        from src.authorities.tier0.openalex import OpenAlexFetcher

        sources_status["OpenAlex"] = "IMPORTED"
    except ImportError as e:
        sources_status["OpenAlex"] = f"FAILED: {e}"

    try:
        from src.authorities.tier0.orcid_etd import ORCIDETDFetcher

        sources_status["ORCID_ETD"] = "IMPORTED"
    except ImportError as e:
        sources_status["ORCID_ETD"] = f"FAILED: {e}"

    try:
        from src.authorities.tier0.crossref_thesis import CrossrefThesisFetcher

        sources_status["Crossref_Thesis"] = "IMPORTED"
    except ImportError as e:
        sources_status["Crossref_Thesis"] = f"FAILED: {e}"

    # Tier 1 sources
    try:
        from src.authorities.tier1.arxiv import ArXivFetcher

        sources_status["arXiv"] = "IMPORTED"
    except ImportError as e:
        sources_status["arXiv"] = f"FAILED: {e}"

    try:
        from src.authorities.tier1.mathscinet import MathSciNetFetcher

        sources_status["MathSciNet"] = "IMPORTED"
    except ImportError as e:
        sources_status["MathSciNet"] = f"FAILED: {e}"

    try:
        from src.authorities.tier1.viaf import VIAFFetcher

        sources_status["VIAF"] = "IMPORTED"
    except ImportError as e:
        sources_status["VIAF"] = f"FAILED: {e}"

    try:
        from src.authorities.tier1.pubmed import PubMedFetcher

        sources_status["PubMed"] = "IMPORTED"
    except ImportError as e:
        sources_status["PubMed"] = f"FAILED: {e}"

    # Also check wikidata_p184
    try:
        from src.authorities.wikidata_p184 import WikidataP184Fetcher

        sources_status["Wikidata_P184"] = "IMPORTED"
    except ImportError as e:
        sources_status["Wikidata_P184"] = f"FAILED: {e}"

    # Print results
    working_count = 0
    for source, status in sources_status.items():
        if status == "IMPORTED":
            print(f"  ✅ {source}: {status}")
            working_count += 1
        else:
            print(f"  ❌ {source}: {status}")

    print(f"\nTotal: {working_count}/{len(sources_status)} sources imported successfully")

    # Test enricher integration
    print("\n2. Testing enricher integration...")
    try:
        from src.authorities.enricher import AuthorityEnricher

        enricher = AuthorityEnricher()

        # Count initialized fetchers
        total_fetchers = sum(len(f) for f in enricher.fetchers_by_tier.values())
        print(f"  Enricher initialized {total_fetchers} fetchers")

        for tier, fetchers in enricher.fetchers_by_tier.items():
            print(f"  {tier.name}: {len(fetchers)} fetchers")
    except Exception as e:
        print(f"  ❌ Enricher initialization failed: {e}")

    # Calculate V7 compliance for authority sources
    print("\n" + "=" * 60)
    print("V7 AUTHORITY SOURCE COMPLIANCE")
    print("=" * 60)

    v7_required = [
        "Crossref",
        "Crossref_Thesis",
        "ORCID",
        "ORCID_ETD",
        "Wikidata_P184",
        "OAI_University",
        "VIAF",
        "Scopus",
        "Web_of_Science",
        "PubMed",
        "arXiv",
        "MathSciNet",
        "zbMATH",
        "dblp",
        "IEEE_Xplore",
    ]

    implemented = []
    missing = []

    for source in v7_required:
        # Check various spellings
        found = False
        for check_name in [source, source.replace("_", ""), source.lower()]:
            if (
                check_name in sources_status
                or check_name.replace("arxiv", "arXiv") in sources_status
            ):
                found = True
                if (
                    sources_status.get(
                        check_name, sources_status.get(check_name.replace("arxiv", "arXiv"), "")
                    )
                    == "IMPORTED"
                ):
                    implemented.append(source)
                break

        if not found or source not in implemented:
            missing.append(source)

    print(f"Implemented: {len(implemented)}/15 ({len(implemented)/15*100:.1f}%)")
    print(f"Working sources: {', '.join(implemented)}")
    print(f"Missing sources: {', '.join(missing)}")

    # Calculate score impact
    authority_score = (len(implemented) / 15) * 10  # 10 points max for authorities
    print(f"\nAuthority component score: {authority_score:.1f}/10 points")

    return len(implemented)


if __name__ == "__main__":
    count = asyncio.run(test_authority_sources())
