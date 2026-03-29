#!/usr/bin/env python3
"""
genealogy/harvest_fr_full.py
Production-scale harvester for French mathematics theses.
Collects 10,000+ records from STAR repository for genealogy pilot.
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.genealogy.connectors.fr_oai import FrThesesOAI, parse_dc


class FrHarvester:
    def __init__(
        self,
        output_dir: str = "data/genealogy/fr_harvest",
        target_records: int = 10000,
        rate_limit: float = 1.0,
        checkpoint_interval: int = 1000,
    ):
        """
        Initialize production FR harvester.

        Args:
            output_dir: Directory to save harvested records
            target_records: Number of records to collect
            rate_limit: Requests per second
            checkpoint_interval: Save checkpoint every N records
        """
        self.output_dir = Path(output_dir)
        self.target_records = target_records
        self.checkpoint_interval = checkpoint_interval

        self.harvester = FrThesesOAI(
            base_url="https://staroai.theses.fr/OAIHandler",
            set_spec="ddc:510",  # Mathematics
            rate_limit=rate_limit,
        )

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = {
            "start_time": None,
            "end_time": None,
            "total_records": 0,
            "records_with_creators": 0,
            "records_with_advisors": 0,
            "total_creators": 0,
            "total_advisors": 0,
            "date_range": {"min": None, "max": None},
        }

    async def harvest(self, resume_from: int = 0) -> List[Dict[str, Any]]:
        """
        Harvest mathematics theses from FR repository.

        Args:
            resume_from: Resume from checkpoint (record number)

        Returns:
            List of harvested records
        """
        print("=" * 80)
        print("FR MATHEMATICS THESIS HARVESTER - PRODUCTION RUN")
        print("=" * 80)
        print()
        print(f"Target: {self.target_records:,} records")
        print(f"Output: {self.output_dir}")
        print(f"Checkpoint interval: {self.checkpoint_interval:,} records")
        print(f"Rate limit: {self.harvester.sleep:.1f}s per request")
        if resume_from > 0:
            print(f"Resuming from: {resume_from:,}")
        print()
        print("-" * 80)

        records = []
        self.stats["start_time"] = datetime.now().isoformat()

        try:
            count = 0
            async for record in self.harvester.records():
                count += 1

                # Skip if resuming
                if count <= resume_from:
                    continue

                # Parse metadata
                parsed = parse_dc(record["raw"])
                records.append(parsed)

                # Update statistics
                self._update_stats(parsed)

                # Progress indicator
                if count % 100 == 0:
                    elapsed = (
                        datetime.now() - datetime.fromisoformat(self.stats["start_time"])
                    ).total_seconds()
                    rate = count / elapsed if elapsed > 0 else 0
                    eta_seconds = (self.target_records - count) / rate if rate > 0 else 0
                    eta_minutes = eta_seconds / 60
                    print(
                        f"  [{count:,}/{self.target_records:,}] "
                        f"Harvested {count:,} records "
                        f"({rate:.1f} rec/s, ETA {eta_minutes:.1f} min)"
                    )

                # Checkpoint
                if count % self.checkpoint_interval == 0:
                    self._save_checkpoint(records, count)

                # Stop at target
                if count >= self.target_records:
                    break

            self.stats["end_time"] = datetime.now().isoformat()
            self.stats["total_records"] = len(records)

            # Final save
            self._save_final(records)

            # Print summary
            self._print_summary()

            return records

        except KeyboardInterrupt:
            print()
            print("=" * 80)
            print("HARVEST INTERRUPTED - Saving checkpoint...")
            print("=" * 80)
            self._save_checkpoint(records, len(records))
            raise

        except Exception as e:
            print()
            print("=" * 80)
            print(f"ERROR: {type(e).__name__}: {str(e)}")
            print("=" * 80)
            self._save_checkpoint(records, len(records))
            raise

    def _update_stats(self, record: Dict[str, Any]):
        """Update harvest statistics."""
        if record.get("creators"):
            self.stats["records_with_creators"] += 1
            self.stats["total_creators"] += len(record["creators"])

        if record.get("advisors_text"):
            self.stats["records_with_advisors"] += 1
            self.stats["total_advisors"] += len(record["advisors_text"])

        # Track date range
        date = record.get("date")
        if date:
            year = date[:4] if len(date) >= 4 else None
            if year:
                if (
                    self.stats["date_range"]["min"] is None
                    or year < self.stats["date_range"]["min"]
                ):
                    self.stats["date_range"]["min"] = year
                if (
                    self.stats["date_range"]["max"] is None
                    or year > self.stats["date_range"]["max"]
                ):
                    self.stats["date_range"]["max"] = year

    def _save_checkpoint(self, records: List[Dict], count: int):
        """Save checkpoint file."""
        checkpoint_file = self.output_dir / f"checkpoint_{count}.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metadata": {
                        "checkpoint_count": count,
                        "timestamp": datetime.now().isoformat(),
                        "stats": self.stats,
                    },
                    "records": records,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"  ✅ Checkpoint saved: {checkpoint_file} ({count:,} records)")

    def _save_final(self, records: List[Dict]):
        """Save final harvest file."""
        final_file = self.output_dir / "fr_harvest_full.json"
        with open(final_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metadata": {
                        "harvest_date": datetime.now().isoformat(),
                        "target_records": self.target_records,
                        "actual_records": len(records),
                        "stats": self.stats,
                    },
                    "records": records,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print()
        print(f"✅ Final harvest saved: {final_file}")

        # Also save compact version (without raw XML)
        compact_file = self.output_dir / "fr_harvest_compact.json"
        compact_records = [{k: v for k, v in r.items() if k != "_raw_dc"} for r in records]
        with open(compact_file, "w", encoding="utf-8") as f:
            json.dump(
                {"metadata": self.stats, "records": compact_records},
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"✅ Compact version saved: {compact_file}")

    def _print_summary(self):
        """Print harvest summary."""
        print()
        print("=" * 80)
        print("HARVEST COMPLETE")
        print("=" * 80)
        print()

        start = datetime.fromisoformat(self.stats["start_time"])
        end = datetime.fromisoformat(self.stats["end_time"])
        duration = (end - start).total_seconds()
        duration_min = duration / 60

        print(f"📊 STATISTICS:")
        print(f"  Total records: {self.stats['total_records']:,}")
        print(
            f"  Records with creators: {self.stats['records_with_creators']:,} "
            f"({self.stats['records_with_creators']/self.stats['total_records']*100:.1f}%)"
        )
        print(
            f"  Records with advisors: {self.stats['records_with_advisors']:,} "
            f"({self.stats['records_with_advisors']/self.stats['total_records']*100:.1f}%)"
        )
        print(f"  Total creators: {self.stats['total_creators']:,}")
        print(f"  Total advisors: {self.stats['total_advisors']:,}")
        print(
            f"  Date range: {self.stats['date_range']['min']} - {self.stats['date_range']['max']}"
        )
        print()

        print(f"⏱️  PERFORMANCE:")
        print(f"  Duration: {duration_min:.1f} minutes ({duration:.0f} seconds)")
        print(f"  Rate: {self.stats['total_records']/duration:.1f} records/second")
        print()

        # Estimate edges
        avg_advisors = (
            self.stats["total_advisors"] / self.stats["records_with_advisors"]
            if self.stats["records_with_advisors"] > 0
            else 0
        )
        estimated_edges = self.stats["records_with_advisors"] * avg_advisors
        print(f"🔗 EDGE ESTIMATION:")
        print(f"  Average advisors per thesis: {avg_advisors:.2f}")
        print(f"  Estimated DOCTORAL_ADVISOR edges: {estimated_edges:,.0f}")
        print()

        print("=" * 80)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Harvest French mathematics theses")
    parser.add_argument(
        "--target", type=int, default=10000, help="Number of records to harvest (default: 10000)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/genealogy/fr_harvest",
        help="Output directory (default: data/genealogy/fr_harvest)",
    )
    parser.add_argument(
        "--rate-limit", type=float, default=1.0, help="Requests per second (default: 1.0)"
    )
    parser.add_argument(
        "--resume", type=int, default=0, help="Resume from checkpoint (record number)"
    )

    args = parser.parse_args()

    harvester = FrHarvester(
        output_dir=args.output, target_records=args.target, rate_limit=args.rate_limit
    )

    await harvester.harvest(resume_from=args.resume)


if __name__ == "__main__":
    asyncio.run(main())
