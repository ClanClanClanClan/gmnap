#!/usr/bin/env python3
"""
Global Genealogy Harvester - Multi-Country Configuration-Driven System

Harvests thesis metadata from 50+ countries worldwide using configuration-driven
architecture. Supports tiered rollout (Tier 1 → Tier 2 → Tier 3).

Usage:
    # Harvest all enabled sources
    python3 scripts/genealogy/global_harvest.py

    # Harvest specific tier
    python3 scripts/genealogy/global_harvest.py --tier 1

    # Harvest specific countries
    python3 scripts/genealogy/global_harvest.py --countries FR,DE,UK

    # Test mode (10 records per source)
    python3 scripts/genealogy/global_harvest.py --test

Configuration:
    config/genealogy/sources.yaml - All source definitions
"""
import sys
import yaml
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.genealogy.connectors.oai_generic import GenericOaiConnector, OaiConfig, OaiConnectorFactory
from src.genealogy.connectors.wikidata_p184 import WikidataP184Connector, WikidataP184Config


@dataclass
class HarvestResult:
    """Result from harvesting a single source."""

    source_id: str
    country: str
    status: str  # success, failure, partial
    records_collected: int
    errors: List[Dict[str, Any]]
    duration_seconds: float
    output_file: str


class GlobalHarvester:
    """
    Configuration-driven global genealogy harvester.

    Orchestrates harvesting from multiple countries in parallel with
    automatic checkpointing and error recovery.
    """

    def __init__(
        self,
        config_file: Path = Path("config/genealogy/sources.yaml"),
        output_dir: Path = Path("data/genealogy/global"),
        checkpoint_every: int = 1000,
    ):
        self.config_file = config_file
        self.output_dir = output_dir
        self.checkpoint_every = checkpoint_every
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # Statistics
        self.results = []
        self.total_records = 0
        self.start_time = None

    def get_sources_by_tier(self, tier: int) -> Dict[str, Dict]:
        """Get all sources for a specific tier."""
        return {
            source_id: source_config
            for source_id, source_config in self.config.items()
            if isinstance(source_config, dict)
            and source_config.get("tier") == tier
            and source_config.get("enabled", False)
        }

    def get_sources_by_country(self, countries: List[str]) -> Dict[str, Dict]:
        """Get sources for specific countries (ISO codes)."""
        countries_upper = [c.upper() for c in countries]
        return {
            source_id: source_config
            for source_id, source_config in self.config.items()
            if isinstance(source_config, dict)
            and source_config.get("country", "").upper() in countries_upper
            and source_config.get("enabled", False)
        }

    def get_all_enabled_sources(self) -> Dict[str, Dict]:
        """Get all enabled sources."""
        return {
            source_id: source_config
            for source_id, source_config in self.config.items()
            if isinstance(source_config, dict) and source_config.get("enabled", False)
        }

    async def harvest_source(
        self, source_id: str, source_config: Dict[str, Any], max_records: int = None
    ) -> HarvestResult:
        """
        Harvest a single source.

        Args:
            source_id: Source identifier (e.g., 'fr_theses', 'uk_ethos')
            source_config: Configuration dict from YAML
            max_records: Maximum records to harvest (None = target_records from config)

        Returns:
            HarvestResult with statistics and status
        """
        start_time = datetime.now()
        source_name = source_config.get("name", source_id)
        country = source_config.get("country", "UNKNOWN")

        print(f"\n{'='*80}")
        print(f"HARVESTING: {source_name} ({country})")
        print(f"{'='*80}")

        connector_type = source_config.get("connector_type", "oai_pmh")

        # Create appropriate connector based on type
        try:
            if connector_type == "oai_pmh":
                connector = OaiConnectorFactory.from_yaml_config(source_config)
            elif connector_type == "sparql":
                # Wikidata P184 or other SPARQL endpoints
                config = WikidataP184Config(
                    endpoint=source_config.get("endpoint", "https://query.wikidata.org/sparql"),
                    rate_limit=source_config.get("rate_limit", 0.5),
                    timeout=source_config.get("timeout", 60),
                )
                connector = WikidataP184Connector(config)
            elif connector_type == "rest_api":
                print(f"⚠️  REST API connectors not yet implemented (needed for CN, KR)")
                return HarvestResult(
                    source_id=source_id,
                    country=country,
                    status="skipped",
                    records_collected=0,
                    errors=[{"type": "unsupported_connector", "connector_type": connector_type}],
                    duration_seconds=0,
                    output_file="",
                )
            else:
                print(f"⚠️  Unknown connector type '{connector_type}'")
                return HarvestResult(
                    source_id=source_id,
                    country=country,
                    status="skipped",
                    records_collected=0,
                    errors=[{"type": "unknown_connector", "connector_type": connector_type}],
                    duration_seconds=0,
                    output_file="",
                )
        except Exception as e:
            print(f"❌ Failed to create connector: {e}")
            return HarvestResult(
                source_id=source_id,
                country=country,
                status="failure",
                records_collected=0,
                errors=[{"type": "connector_creation_error", "error": str(e)}],
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                output_file="",
            )

        # Harvest records
        target_records = max_records or source_config.get("target_records", 1000)
        records = []
        checkpoint_count = 0

        # Get date range from config (if specified, OAI-PMH only)
        date_from = source_config.get("date_from")
        date_to = source_config.get("date_to")

        try:
            # SPARQL connectors (Wikidata) don't support date parameters
            if connector_type == "sparql":
                async for record in connector.records(max_records=target_records):
                    records.append(record)
                    if len(records) % 100 == 0:
                        print(f"  Progress: {len(records):,} records...")
                    if len(records) % self.checkpoint_every == 0:
                        checkpoint_file = (
                            self.output_dir / f"{source_id}_checkpoint_{checkpoint_count}.json"
                        )
                        self._save_checkpoint(records[-self.checkpoint_every :], checkpoint_file)
                        checkpoint_count += 1
            else:
                # OAI-PMH connectors support date range filtering
                async for record in connector.records(
                    date_from=date_from, date_to=date_to, max_records=target_records
                ):
                    records.append(record)
                    if len(records) % 100 == 0:
                        print(f"  Progress: {len(records):,} records...")
                    if len(records) % self.checkpoint_every == 0:
                        checkpoint_file = (
                            self.output_dir / f"{source_id}_checkpoint_{checkpoint_count}.json"
                        )
                        self._save_checkpoint(records[-self.checkpoint_every :], checkpoint_file)
                        checkpoint_count += 1

            # Save final output
            output_file = self.output_dir / f"{source_id}_harvest.json"
            self._save_records(records, output_file, source_config)

            duration = (datetime.now() - start_time).total_seconds()

            print(f"✅ {source_name}: {len(records):,} records ({duration:.1f}s)")

            return HarvestResult(
                source_id=source_id,
                country=country,
                status="success",
                records_collected=len(records),
                errors=connector.get_statistics()["error_details"],
                duration_seconds=duration,
                output_file=str(output_file),
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            print(f"❌ {source_name} failed: {e}")

            # Save partial results
            if records:
                output_file = self.output_dir / f"{source_id}_partial.json"
                self._save_records(records, output_file, source_config)
                print(f"💾 Saved {len(records):,} partial records: {output_file}")
            else:
                output_file = ""

            return HarvestResult(
                source_id=source_id,
                country=country,
                status="failure" if not records else "partial",
                records_collected=len(records),
                errors=[{"type": "harvest_error", "error": str(e)}],
                duration_seconds=duration,
                output_file=str(output_file),
            )

    def _save_checkpoint(self, records: List[Dict], checkpoint_file: Path):
        """Save checkpoint file."""
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    def _save_records(self, records: List[Dict], output_file: Path, source_config: Dict):
        """Save harvested records with metadata."""
        output = {
            "source": source_config.get("name"),
            "country": source_config.get("country"),
            "harvest_date": datetime.now().isoformat(),
            "count": len(records),
            "records": records,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    async def harvest_tier(self, tier: int, max_records_per_source: int = None):
        """
        Harvest all sources in a specific tier in parallel.

        Args:
            tier: Tier number (1, 2, or 3)
            max_records_per_source: Max records per source (for testing)
        """
        sources = self.get_sources_by_tier(tier)

        if not sources:
            print(f"⚠️  No enabled sources found for Tier {tier}")
            return

        print(f"\n{'='*80}")
        print(f"TIER {tier} HARVEST - {len(sources)} SOURCES")
        print(f"{'='*80}")
        for source_id, config in sources.items():
            print(f"  • {config.get('name')} ({config.get('country')})")
        print(f"{'='*80}\n")

        # Harvest all sources in parallel
        tasks = [
            self.harvest_source(source_id, source_config, max_records_per_source)
            for source_id, source_config in sources.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Harvest failed with exception: {result}")
                continue
            self.results.append(result)
            self.total_records += result.records_collected

    async def harvest_countries(self, countries: List[str], max_records_per_source: int = None):
        """Harvest specific countries."""
        sources = self.get_sources_by_country(countries)

        if not sources:
            print(f"⚠️  No enabled sources found for countries: {', '.join(countries)}")
            return

        print(f"\n{'='*80}")
        print(f"COUNTRY-SPECIFIC HARVEST - {len(sources)} SOURCES")
        print(f"{'='*80}\n")

        tasks = [
            self.harvest_source(source_id, source_config, max_records_per_source)
            for source_id, source_config in sources.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Harvest failed: {result}")
                continue
            self.results.append(result)
            self.total_records += result.records_collected

    async def harvest_all(self, max_records_per_source: int = None):
        """Harvest all enabled sources."""
        sources = self.get_all_enabled_sources()

        if not sources:
            print("⚠️  No enabled sources found")
            return

        print(f"\n{'='*80}")
        print(f"GLOBAL HARVEST - {len(sources)} ENABLED SOURCES")
        print(f"{'='*80}\n")

        # Group by tier for reporting
        by_tier = {}
        for source_id, config in sources.items():
            tier = config.get("tier", "unknown")
            if tier not in by_tier:
                by_tier[tier] = []
            by_tier[tier].append(config.get("name"))

        for tier in sorted(by_tier.keys()):
            print(f"Tier {tier} ({len(by_tier[tier])} sources):")
            for name in by_tier[tier][:5]:
                print(f"  • {name}")
            if len(by_tier[tier]) > 5:
                print(f"  • ... and {len(by_tier[tier]) - 5} more")
        print()

        tasks = [
            self.harvest_source(source_id, source_config, max_records_per_source)
            for source_id, source_config in sources.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Harvest failed: {result}")
                continue
            self.results.append(result)
            self.total_records += result.records_collected

    def print_summary(self):
        """Print harvest summary."""
        duration = (datetime.now() - self.start_time).total_seconds()

        print(f"\n{'='*80}")
        print("GLOBAL HARVEST COMPLETE")
        print(f"{'='*80}")

        successful = [r for r in self.results if r.status == "success"]
        failed = [r for r in self.results if r.status == "failure"]
        partial = [r for r in self.results if r.status == "partial"]

        print(f"\n📊 SUMMARY:")
        print(f"  Total sources attempted: {len(self.results)}")
        print(f"  ✅ Successful: {len(successful)}")
        print(f"  ⚠️  Partial: {len(partial)}")
        print(f"  ❌ Failed: {len(failed)}")
        print(f"  📦 Total records: {self.total_records:,}")
        print(f"  ⏱️  Duration: {duration:.1f}s ({duration/60:.1f} min)")

        if self.total_records > 0:
            print(f"  ⚡ Rate: {self.total_records/duration:.1f} records/second")

        # By country
        print(f"\n🌍 BY COUNTRY:")
        by_country = {}
        for result in self.results:
            country = result.country
            if country not in by_country:
                by_country[country] = 0
            by_country[country] += result.records_collected

        for country, count in sorted(by_country.items(), key=lambda x: -x[1]):
            print(f"  {country}: {count:,} records")

        # Save summary
        summary_file = self.output_dir / "harvest_summary.json"
        with open(summary_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": duration,
                    "total_records": self.total_records,
                    "sources_attempted": len(self.results),
                    "successful": len(successful),
                    "partial": len(partial),
                    "failed": len(failed),
                    "results": [asdict(r) for r in self.results],
                },
                f,
                indent=2,
            )

        print(f"\n📄 Summary report: {summary_file}")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"{'='*80}\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Global Genealogy Harvester - Multi-Country System"
    )
    parser.add_argument("--tier", type=int, choices=[0, 1, 2, 3], help="Harvest specific tier only")
    parser.add_argument(
        "--countries", type=str, help="Comma-separated list of country codes (e.g., FR,DE,UK)"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test mode: harvest only 10 records per source"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/genealogy/sources.yaml",
        help="Path to sources configuration file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/genealogy/global",
        help="Output directory for harvested data",
    )

    args = parser.parse_args()

    # Create harvester
    harvester = GlobalHarvester(config_file=Path(args.config), output_dir=Path(args.output_dir))

    harvester.start_time = datetime.now()
    max_records = 10 if args.test else None

    # Execute harvest based on arguments
    if args.tier is not None:
        await harvester.harvest_tier(args.tier, max_records)
    elif args.countries:
        countries = [c.strip() for c in args.countries.split(",")]
        await harvester.harvest_countries(countries, max_records)
    else:
        await harvester.harvest_all(max_records)

    # Print summary
    harvester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
