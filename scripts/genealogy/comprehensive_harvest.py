#!/usr/bin/env python3
"""
Comprehensive Genealogy Data Harvest - Multi-Source Collection
==============================================================

Collects doctoral advisor relationships from multiple legal sources:
1. Wikidata P184 (doctoral advisor property)
2. French theses (theses.fr OAI-PMH)
3. German theses (OPUS repositories)
4. US theses (Crossref)
5. Brazilian theses (BDTD)

Target: 100,000+ advisor relationships from global sources
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.genealogy.wikidata_client import WikidataClient, P184_QUERY
from src.genealogy.connectors.fr_oai import FrThesesOAI
from src.genealogy.connectors.us_crossref import UsCrossrefAPI


class ComprehensiveGenealogyHarvester:
    """Multi-source genealogy data harvester."""

    def __init__(self, output_dir: Path = Path("data/genealogy/comprehensive")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize all connectors
        self.wikidata = WikidataClient(enabled=True)

        # French theses (theses.fr OAI-PMH)
        self.fr_theses = FrThesesOAI(
            base_url="http://www.theses.fr/oai/thesesfr/",
            rate_limit=1.0,
            set_spec="ddc:510",  # Mathematics Dewey classification
        )

        # US dissertations (Crossref)
        self.us_crossref = UsCrossrefAPI(
            mailto="gmnap@research.example.com", rate_limit=2.0
        )

        self.results = {
            "timestamp": datetime.now().isoformat(),
            "sources": {},
            "statistics": {},
            "errors": [],
        }

    async def harvest_wikidata_p184(self, limit: int = 10000) -> Dict[str, Any]:
        """
        Harvest doctoral advisor relationships from Wikidata P184 property.

        P184 = doctoral advisor property
        Wikidata has thousands of mathematician → advisor relationships
        """
        print("=" * 80)
        print("HARVESTING WIKIDATA P184 (Doctoral Advisors)")
        print("=" * 80)
        print(f"Target: {limit:,} relationships")
        print()

        relationships = []
        errors = []

        # Wikidata SPARQL query with pagination
        query_template = """
        SELECT DISTINCT ?student ?studentLabel ?advisor ?advisorLabel ?startTime ?instLabel ?degreeLabel
        WHERE {{
          {{
            ?student wdt:P106 wd:Q170790 .  # occupation: mathematician
            ?student wdt:P184 ?advisor .     # has doctoral advisor
          }} UNION {{
            ?student wdt:P106 wd:Q81096 .    # occupation: computer scientist
            ?student wdt:P184 ?advisor .
          }} UNION {{
            ?student wdt:P106 wd:Q593644 .   # occupation: statistician
            ?student wdt:P184 ?advisor .
          }}

          OPTIONAL {{
            ?student p:P184 ?stmt .
            ?stmt ps:P184 ?advisor .
            OPTIONAL {{ ?stmt pq:P580 ?startTime }}        # start time
            OPTIONAL {{ ?stmt pq:P512 ?degree }}           # academic degree
            OPTIONAL {{ ?stmt pq:P1027 ?inst }}            # conferred by institution
          }}

          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr,de,es". }}
        }}
        LIMIT {limit}
        OFFSET {offset}
        """

        # Fetch in batches of 1000
        batch_size = 1000
        offset = 0

        while offset < limit:
            current_batch = min(batch_size, limit - offset)
            query = query_template.format(limit=current_batch, offset=offset)

            print(f"  Fetching batch at offset {offset:,}...")

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(
                        "https://query.wikidata.org/sparql",
                        params={"query": query, "format": "json"},
                        headers={
                            "User-Agent": "GMNAP-Genealogy/1.0 (research purposes; https://github.com/gmnap)",
                            "Accept": "application/sparql-results+json",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                bindings = data.get("results", {}).get("bindings", [])

                if not bindings:
                    print(f"  No more results at offset {offset}")
                    break

                for binding in bindings:
                    student = binding.get("student", {}).get("value", "")
                    student_label = binding.get("studentLabel", {}).get("value", "")
                    advisor = binding.get("advisor", {}).get("value", "")
                    advisor_label = binding.get("advisorLabel", {}).get("value", "")
                    start_time = binding.get("startTime", {}).get("value")
                    institution = binding.get("instLabel", {}).get("value")
                    degree = binding.get("degreeLabel", {}).get("value")

                    if student and advisor and student_label and advisor_label:
                        relationships.append(
                            {
                                "student": student_label,
                                "student_wikidata": student,
                                "advisor": advisor_label,
                                "advisor_wikidata": advisor,
                                "start_time": start_time,
                                "institution": institution,
                                "degree": degree,
                                "source": "wikidata_p184",
                            }
                        )

                print(
                    f"  ✅ Collected {len(bindings)} relationships (total: {len(relationships):,})"
                )
                offset += current_batch

                # Rate limiting - Wikidata requests max 1 req/second
                await asyncio.sleep(1.0)

            except Exception as e:
                error_msg = f"Wikidata batch at offset {offset}: {str(e)}"
                print(f"  ⚠️  {error_msg}")
                errors.append(error_msg)
                break

        # Save checkpoint
        wikidata_file = self.output_dir / "wikidata_p184.json"
        with open(wikidata_file, "w") as f:
            json.dump(
                {
                    "source": "wikidata_p184",
                    "count": len(relationships),
                    "relationships": relationships,
                },
                f,
                indent=2,
            )

        print(f"\n✅ Wikidata P184: {len(relationships):,} relationships")
        print(f"   Saved to: {wikidata_file}")

        return {
            "count": len(relationships),
            "relationships": relationships,
            "errors": errors,
        }

    async def harvest_connector(
        self, connector, name: str, target: int = 5000, **kwargs
    ) -> Dict[str, Any]:
        """Harvest from a thesis connector using async iterator."""
        print("=" * 80)
        print(f"HARVESTING {name.upper()} THESES")
        print("=" * 80)
        print(f"Target: {target:,} records")
        print()

        records = []
        errors = []
        count = 0

        try:
            # Use async iterator from connector
            async for record in connector.records(**kwargs):
                records.append(record)
                count += 1

                # Progress reporting
                if count % 100 == 0:
                    print(f"  Progress: {count:,} records...")

                # Save checkpoint every 1000 records
                if count % 1000 == 0:
                    checkpoint_file = (
                        self.output_dir / f"{name}_checkpoint_{count}.json"
                    )
                    with open(checkpoint_file, "w") as f:
                        json.dump({"count": count, "records": records}, f, indent=2)
                    print(f"  ✅ Checkpoint: {count:,} records")

                # Stop at target
                if count >= target:
                    print(f"  Target reached: {count:,} records")
                    break

            # Save final results
            final_file = self.output_dir / f"{name}_harvest.json"
            with open(final_file, "w") as f:
                json.dump(
                    {"source": name, "count": len(records), "records": records},
                    f,
                    indent=2,
                )

            print(f"\n✅ {name.upper()}: {len(records):,} records")
            print(f"   Saved to: {final_file}")

        except Exception as e:
            error_msg = f"{name} harvest failed: {str(e)}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)

        return {"count": len(records), "records": records, "errors": errors}

    async def run_comprehensive_harvest(
        self, wikidata_limit: int = 10000, thesis_target: int = 5000
    ):
        """
        Run comprehensive harvest from all sources in parallel.

        Args:
            wikidata_limit: Max Wikidata P184 relationships to fetch
            thesis_target: Target number of thesis records per source
        """
        print("=" * 80)
        print("COMPREHENSIVE GENEALOGY HARVEST - MULTI-SOURCE COLLECTION")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Output directory: {self.output_dir}")
        print()
        print("SOURCES:")
        print(
            f"  1. Wikidata P184 (doctoral advisors): {wikidata_limit:,} relationships"
        )
        print(f"  2. French theses (theses.fr): {thesis_target:,} records")
        print(f"  3. US Crossref (dissertations): {thesis_target:,} records")
        print(f"\nEstimated total: {wikidata_limit + (thesis_target * 2):,}+ records")
        print("=" * 80)
        print()

        # Run all harvests in parallel for speed
        results = await asyncio.gather(
            self.harvest_wikidata_p184(limit=wikidata_limit),
            self.harvest_connector(self.fr_theses, "french", thesis_target),
            self.harvest_connector(
                self.us_crossref, "us_crossref", thesis_target, rows=100
            ),
            return_exceptions=True,
        )

        # Aggregate results
        total_records = 0
        total_relationships = 0
        all_errors = []

        source_names = ["wikidata_p184", "french", "us_crossref"]
        for i, (result, name) in enumerate(zip(results, source_names)):
            if isinstance(result, Exception):
                error_msg = f"{name}: {str(result)}"
                print(f"❌ {error_msg}")
                all_errors.append(error_msg)
                self.results["sources"][name] = {"error": error_msg}
            else:
                count = result.get("count", 0)
                errors = result.get("errors", [])

                if name == "wikidata_p184":
                    total_relationships += count
                else:
                    total_records += count

                self.results["sources"][name] = {"count": count, "errors": errors}
                all_errors.extend(errors)

        # Final statistics
        total_sources = len(source_names)
        self.results["statistics"] = {
            "total_thesis_records": total_records,
            "total_advisor_relationships": total_relationships,
            "total_combined": total_records + total_relationships,
            "sources_succeeded": len(
                [s for s in self.results["sources"].values() if "error" not in s]
            ),
            "sources_failed": len(
                [s for s in self.results["sources"].values() if "error" in s]
            ),
            "total_errors": len(all_errors),
        }
        self.results["errors"] = all_errors

        # Save summary report
        summary_file = self.output_dir / "harvest_summary.json"
        with open(summary_file, "w") as f:
            json.dump(self.results, f, indent=2)

        # Print final summary
        print("\n" + "=" * 80)
        print("COMPREHENSIVE HARVEST COMPLETE")
        print("=" * 80)
        print(f"\n📊 FINAL STATISTICS:")
        print(f"  Thesis records collected: {total_records:,}")
        print(f"  Advisor relationships: {total_relationships:,}")
        print(f"  Total combined: {total_records + total_relationships:,}")
        print(
            f"\n✅ Sources succeeded: {self.results['statistics']['sources_succeeded']}/{total_sources}"
        )
        print(
            f"❌ Sources failed: {self.results['statistics']['sources_failed']}/{total_sources}"
        )
        print(f"⚠️  Total errors: {len(all_errors)}")
        print(f"\n📁 Output directory: {self.output_dir}")
        print(f"📄 Summary report: {summary_file}")
        print("=" * 80)

        return self.results


async def main():
    """Run comprehensive harvest."""
    harvester = ComprehensiveGenealogyHarvester()

    # Comprehensive harvest:
    # - 10,000 Wikidata P184 relationships
    # - 5,000 records from each of 4 thesis sources
    # - Total target: 30,000+ records
    await harvester.run_comprehensive_harvest(wikidata_limit=10000, thesis_target=5000)


if __name__ == "__main__":
    asyncio.run(main())
