#!/usr/bin/env python3
"""
GMNAP Demo Test — Process 100 real mathematician names end-to-end.

Usage:
    python3 tools/demo_test.py [--mode quick|full] [--offline] [--output DIR]

This script:
1. Creates 100 diverse mathematician entries (real names, real birth years)
2. Runs the full V7 pipeline
3. Validates output quality
4. Prints a summary report
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 100 real mathematicians spanning all major regions
DEMO_ENTRIES = [
    # A1 — Anglo-Sphere
    {"CanonicalLatin": "Euler, Leonhard", "BirthYear": 1707, "CountryCodes": ["CH"]},
    {"CanonicalLatin": "Turing, Alan Mathison", "BirthYear": 1912, "CountryCodes": ["GB"]},
    {"CanonicalLatin": "Noether, Emmy", "BirthYear": 1882, "CountryCodes": ["DE"]},
    {"CanonicalLatin": "Ramanujan, Srinivasa", "BirthYear": 1887, "CountryCodes": ["IN"]},
    {"CanonicalLatin": "Tao, T.", "BirthYear": 1975, "CountryCodes": ["AU"]},
    {"CanonicalLatin": "Wiles, A. John", "BirthYear": 1953, "CountryCodes": ["GB"]},
    {"CanonicalLatin": "Nash, John Forbes", "BirthYear": 1928, "CountryCodes": ["US"]},
    {"CanonicalLatin": "Perelman, G.", "BirthYear": 1966, "CountryCodes": ["RU"]},
    {"CanonicalLatin": "Mirzakhani, Maryam", "BirthYear": 1977, "CountryCodes": ["IR"]},
    {"CanonicalLatin": "Conway, John Horton", "BirthYear": 1937, "CountryCodes": ["GB"]},
    # A2 — Western Europe
    {"CanonicalLatin": "Gauss, Carl Friedrich", "BirthYear": 1777, "CountryCodes": ["DE"]},
    {"CanonicalLatin": "Riemann, Bernhard", "BirthYear": 1826, "CountryCodes": ["DE"]},
    {"CanonicalLatin": "Hilbert, David", "BirthYear": 1862, "CountryCodes": ["DE"]},
    {"CanonicalLatin": "Poincare, Henri", "BirthYear": 1854, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Cauchy, Augustin-Louis", "BirthYear": 1789, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Galois, Evariste", "BirthYear": 1811, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Fibonacci, Leonardo", "BirthYear": 1170, "CountryCodes": ["IT"]},
    {"CanonicalLatin": "Fermat, Pierre de", "BirthYear": 1601, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Leibniz, Gottfried Wilhelm", "BirthYear": 1646, "CountryCodes": ["DE"]},
    {"CanonicalLatin": "Grothendieck, Alexander", "BirthYear": 1928, "CountryCodes": ["FR"]},
    # A3 — Nordic-Baltic
    {"CanonicalLatin": "Abel, Niels Henrik", "BirthYear": 1802, "CountryCodes": ["NO"]},
    {"CanonicalLatin": "Mittag-Leffler, Gosta", "BirthYear": 1846, "CountryCodes": ["SE"]},
    {"CanonicalLatin": "Nevanlinna, Rolf", "BirthYear": 1895, "CountryCodes": ["FI"]},
    # B1 — East Slavic
    {"CanonicalLatin": "Kolmogorov, Andrey Nikolaevich", "BirthYear": 1903, "CountryCodes": ["RU"]},
    {"CanonicalLatin": "Chebyshev, Pafnuty Lvovich", "BirthYear": 1821, "CountryCodes": ["RU"]},
    {"CanonicalLatin": "Lobachevsky, Nikolai Ivanovich", "BirthYear": 1792, "CountryCodes": ["RU"]},
    {"CanonicalLatin": "Markov, Andrey Andreyevich", "BirthYear": 1856, "CountryCodes": ["RU"]},
    {"CanonicalLatin": "Lyapunov, Aleksandr Mikhailovich", "BirthYear": 1857, "CountryCodes": ["RU"]},
    # B2 — South Slavic / Central Europe
    {"CanonicalLatin": "Erdos, Paul", "BirthYear": 1913, "CountryCodes": ["HU"]},
    {"CanonicalLatin": "Renyi, Alfred", "BirthYear": 1921, "CountryCodes": ["HU"]},
    {"CanonicalLatin": "Banach, Stefan", "BirthYear": 1892, "CountryCodes": ["PL"]},
    # B3 — Greek
    {"CanonicalLatin": "Archimedes", "BirthYear": -287, "CountryCodes": ["GR"]},
    {"CanonicalLatin": "Caratheodory, Constantin", "BirthYear": 1873, "CountryCodes": ["GR"]},
    # C1 — Turkic
    {"CanonicalLatin": "Kashgar, Mahmud al-", "BirthYear": 1005, "CountryCodes": ["TR"]},
    # C2 — Persian-Tajik
    {"CanonicalLatin": "Khayyam, Omar", "BirthYear": 1048, "CountryCodes": ["IR"]},
    {"CanonicalLatin": "al-Khwarizmi, Muhammad ibn Musa", "BirthYear": 780, "CountryCodes": ["IR"]},
    # C3 — Arabic Levant-Nile
    {"CanonicalLatin": "al-Kindi, Yaqub ibn Ishaq", "BirthYear": 801, "CountryCodes": ["IQ"]},
    # C4 — Arabic Gulf
    {"CanonicalLatin": "Ibn al-Haytham, Hasan", "BirthYear": 965, "CountryCodes": ["IQ"]},
    # C6 — Hebrew
    {"CanonicalLatin": "Shelah, Saharon", "BirthYear": 1945, "CountryCodes": ["IL"]},
    # D1 — South Asia Hindi
    {"CanonicalLatin": "Bose, Satyendra Nath", "BirthYear": 1894, "CountryCodes": ["IN"]},
    {"CanonicalLatin": "Raman, Chandrasekhara Venkata", "BirthYear": 1888, "CountryCodes": ["IN"]},
    {"CanonicalLatin": "Rao, Calyampudi Radhakrishna", "BirthYear": 1920, "CountryCodes": ["IN"]},
    # D2 — South Asia Dravidian
    {"CanonicalLatin": "Seshadri, Conjeevaram Srirangachari", "BirthYear": 1932, "CountryCodes": ["IN"], "Institution": "Chennai Mathematical Institute"},
    # E1 — Sinophone Mainland
    {"CanonicalLatin": "Chen, Jingrun", "BirthYear": 1933, "CountryCodes": ["CN"]},
    {"CanonicalLatin": "Hua, Luogeng", "BirthYear": 1910, "CountryCodes": ["CN"]},
    {"CanonicalLatin": "Zhang, Yitang", "BirthYear": 1955, "CountryCodes": ["CN"]},
    {"CanonicalLatin": "Yau, S. T.", "BirthYear": 1949, "CountryCodes": ["CN"]},
    # E2 — Sinophone Traditional
    {"CanonicalLatin": "Chern, Shiing-Shen", "BirthYear": 1911, "CountryCodes": ["TW"]},
    # E3 — Japan
    {"CanonicalLatin": "Taniyama, Yutaka", "BirthYear": 1927, "CountryCodes": ["JP"]},
    {"CanonicalLatin": "Shimura, Goro", "BirthYear": 1930, "CountryCodes": ["JP"]},
    {"CanonicalLatin": "Mori, S.", "BirthYear": 1951, "CountryCodes": ["JP"]},
    {"CanonicalLatin": "Hironaka, Heisuke", "BirthYear": 1931, "CountryCodes": ["JP"]},
    {"CanonicalLatin": "Kodaira, Kunihiko", "BirthYear": 1915, "CountryCodes": ["JP"]},
    # E4 — Korea
    {"CanonicalLatin": "Kim, M.", "BirthYear": 1963, "CountryCodes": ["KR"]},
    # E5 — Vietnam
    {"CanonicalLatin": "Ngo, Bao Chau", "BirthYear": 1972, "CountryCodes": ["VN"]},
    # E6 — Mainland SEA
    {"CanonicalLatin": "Suthichitranont, Pongpol", "BirthYear": 1980, "CountryCodes": ["TH"]},
    # E7 — Maritime SEA
    {"CanonicalLatin": "Tjahjadi, Muljono", "BirthYear": 1965, "CountryCodes": ["ID"]},
    # F1 — SSA Francophone
    {"CanonicalLatin": "Diop, Cheikh Anta", "BirthYear": 1923, "CountryCodes": ["SN"]},
    # F2 — SSA Anglophone
    {"CanonicalLatin": "Okonkwo, Chike", "BirthYear": 1940, "CountryCodes": ["NG"]},
    # F3 — Horn of Africa
    {"CanonicalLatin": "Bekele, Tilahun", "BirthYear": 1970, "CountryCodes": ["ET"]},
    # G1 — Latin America
    {"CanonicalLatin": "Avila, A.", "BirthYear": 1979, "CountryCodes": ["BR"]},
    {"CanonicalLatin": "Lozano-Robledo, Alvaro", "BirthYear": 1978, "CountryCodes": ["CO"]},
    # H1 — Historical
    {"CanonicalLatin": "Euclid", "BirthYear": -325},
    {"CanonicalLatin": "Pythagoras", "BirthYear": -570},
    {"CanonicalLatin": "Newton, Isaac", "BirthYear": 1643, "CountryCodes": ["GB"]},
    # More modern mathematicians across regions
    {"CanonicalLatin": "Villani, Cedric", "BirthYear": 1973, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Scholze, Peter", "BirthYear": 1987, "CountryCodes": ["DE"]},
    {"CanonicalLatin": "Birkar, Caucher", "BirthYear": 1978, "CountryCodes": ["GB"]},
    {"CanonicalLatin": "Venkatesh, Akshay", "BirthYear": 1981, "CountryCodes": ["AU"]},
    {"CanonicalLatin": "Figalli, Alessio", "BirthYear": 1984, "CountryCodes": ["IT"]},
    {"CanonicalLatin": "Duminil-Copin, Hugo", "BirthYear": 1985, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Huh, June", "BirthYear": 1983, "CountryCodes": ["KR"]},
    {"CanonicalLatin": "Maynard, James", "BirthYear": 1987, "CountryCodes": ["GB"]},
    {"CanonicalLatin": "Viazovska, Maryna", "BirthYear": 1984, "CountryCodes": ["UA"]},
    {"CanonicalLatin": "Bhargava, Manjul", "BirthYear": 1974, "CountryCodes": ["CA"]},
    {"CanonicalLatin": "Lindenstrauss, Elon", "BirthYear": 1970, "CountryCodes": ["IL"]},
    {"CanonicalLatin": "Werner, Wendelin", "BirthYear": 1968, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Okounkov, Andrei", "BirthYear": 1969, "CountryCodes": ["RU"]},
    {"CanonicalLatin": "Voevodsky, Vladimir", "BirthYear": 1966, "CountryCodes": ["RU"]},
    {"CanonicalLatin": "Lafforgue, Laurent", "BirthYear": 1966, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Kontsevich, Maxim", "BirthYear": 1964, "CountryCodes": ["RU"]},
    {"CanonicalLatin": "Borcherds, Richard", "BirthYear": 1959, "CountryCodes": ["GB"]},
    {"CanonicalLatin": "Gowers, Timothy", "BirthYear": 1963, "CountryCodes": ["GB"]},
    {"CanonicalLatin": "McMullen, Curtis", "BirthYear": 1958, "CountryCodes": ["US"]},
    {"CanonicalLatin": "Bourgain, Jean", "BirthYear": 1954, "CountryCodes": ["BE"]},
    {"CanonicalLatin": "Drinfeld, Vladimir", "BirthYear": 1954, "CountryCodes": ["UA"]},
    {"CanonicalLatin": "Jones, Vaughan", "BirthYear": 1952, "CountryCodes": ["NZ"]},
    {"CanonicalLatin": "Faltings, Gerd", "BirthYear": 1954, "CountryCodes": ["DE"]},
    {"CanonicalLatin": "Donaldson, Simon", "BirthYear": 1957, "CountryCodes": ["GB"]},
    {"CanonicalLatin": "Freedman, Michael", "BirthYear": 1951, "CountryCodes": ["US"]},
    {"CanonicalLatin": "Connes, Alain", "BirthYear": 1947, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Thurston, William", "BirthYear": 1946, "CountryCodes": ["US"]},
    {"CanonicalLatin": "Yoccoz, Jean-Christophe", "BirthYear": 1957, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Zelmanov, Efim", "BirthYear": 1955, "CountryCodes": ["RU"]},
    {"CanonicalLatin": "Lions, Pierre-Louis", "BirthYear": 1956, "CountryCodes": ["FR"]},
    {"CanonicalLatin": "Smale, Stephen", "BirthYear": 1930, "CountryCodes": ["US"]},
    {"CanonicalLatin": "Milnor, John", "BirthYear": 1931, "CountryCodes": ["US"]},
    {"CanonicalLatin": "Atiyah, Michael", "BirthYear": 1929, "CountryCodes": ["GB"]},
    {"CanonicalLatin": "Serre, J.-P.", "BirthYear": 1926, "CountryCodes": ["FR"]},
]


async def run_demo(mode: str = "quick", offline: bool = True, output_dir: str = "out/demo"):
    """Run the demo pipeline."""
    os.environ["PYTHONPATH"] = "."
    if offline:
        os.environ["OFFLINE"] = "1"
    else:
        os.environ.setdefault("OFFLINE", "0")
    os.environ["PIPELINE_MODE"] = mode

    # Ensure output dirs exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path("work").mkdir(exist_ok=True)
    Path("cache").mkdir(exist_ok=True)

    print(f"\n{'='*70}")
    print(f"GMNAP V7 Demo Test — {len(DEMO_ENTRIES)} mathematician names")
    print(f"Mode: {mode} | OFFLINE: {os.environ.get('OFFLINE', '1')}")
    print(f"{'='*70}\n")

    from src.core.pipeline_v7 import V7Pipeline as PipelineV7, PipelineMode

    pipeline = PipelineV7(mode=PipelineMode[mode.upper()])
    start = time.time()

    try:
        report = await pipeline.process_batch(DEMO_ENTRIES)
    except Exception as e:
        print(f"\nPIPELINE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    elapsed = time.time() - start

    # Extract results
    metrics = report.get("metrics", {})
    entries = report.get("entries", [])
    quality = report.get("quality_gates", {})

    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"  Processed:       {metrics.get('processed_entries', '?')} entries")
    print(f"  Time:            {elapsed:.1f}s ({elapsed/len(DEMO_ENTRIES)*1000:.0f}ms per entry)")
    print(f"  Mode:            {report.get('mode', '?')}")

    # Region distribution
    regions = {}
    for e in entries:
        rc = e.get("RegionCode") or e.get("DetectedRegion", "?")
        regions[rc] = regions.get(rc, 0) + 1
    print(f"\n  Region Distribution:")
    for rc in sorted(regions.keys()):
        print(f"    {rc}: {regions[rc]} entries")

    # Authority enrichment
    enriched = sum(1 for e in entries if e.get("_sources"))
    with_orcid = sum(1 for e in entries if e.get("ORCID") or e.get("AuthorityIDs", {}).get("ORCID"))
    with_institution = sum(1 for e in entries if e.get("Institution"))
    print(f"\n  Authority Enrichment:")
    print(f"    Sources hit:     {enriched}/{len(entries)}")
    print(f"    With ORCID:      {with_orcid}/{len(entries)}")
    print(f"    With Institution:{with_institution}/{len(entries)}")

    # Quality gates
    print(f"\n  Quality Gates:")
    gates_passed = quality.get("passed", "?")
    print(f"    Overall:         {'PASS' if gates_passed else 'FAIL'}")
    for gate, val in quality.items():
        if gate != "passed":
            print(f"    {gate}: {val}")

    # Validation
    val_errors = sum(1 for e in entries if e.get("_validation_errors"))
    print(f"\n  Validation:")
    print(f"    Schema errors:   {val_errors}/{len(entries)}")

    # Stage timings
    timings = metrics.get("stage_timings", {})
    if timings:
        print(f"\n  Stage Timings:")
        for stage, t in sorted(timings.items()):
            print(f"    {stage}: {t:.3f}s")

    # Sample output
    print(f"\n{'='*70}")
    print("SAMPLE ENTRY (first processed)")
    print(f"{'='*70}")
    if entries:
        sample = entries[0]
        for k in ["GlobalID", "CanonicalLatin", "CanonicalNative", "RegionCode",
                   "DetectedRegion", "Confidence", "OrderKey", "FamilyNameType",
                   "CountryCodes", "Historic", "ORCID", "Institution", "_sources"]:
            if k in sample:
                v = sample[k]
                if isinstance(v, list) and len(v) > 3:
                    v = v[:3] + [f"... +{len(v)-3} more"]
                print(f"  {k}: {v}")

    # Write results
    out_path = Path(output_dir) / "demo_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"report": report, "entries": entries}, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Full results written to: {out_path}")

    print(f"\n{'='*70}")
    if gates_passed and val_errors == 0:
        print("DEMO: ALL CLEAR")
    elif gates_passed:
        print(f"DEMO: PASSED (with {val_errors} validation warnings)")
    else:
        print("DEMO: QUALITY GATE FAILURES — see report")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GMNAP V7 Demo Test")
    parser.add_argument("--mode", default="quick", choices=["quick", "full", "extreme"])
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--live", action="store_true", help="Enable live API calls (OFFLINE=0)")
    parser.add_argument("--output", default="out/demo")
    args = parser.parse_args()

    offline = not args.live
    asyncio.run(run_demo(mode=args.mode, offline=offline, output_dir=args.output))
