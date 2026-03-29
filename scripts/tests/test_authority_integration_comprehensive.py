#!/usr/bin/env python3
"""
ULTRATHINK Authority Sources Comprehensive Integration Test
Tests all authority sources thoroughly with real API calls
"""

import os
import sys
import json
import time
import asyncio
import traceback
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Enable online mode for testing
os.environ["OFFLINE"] = "0"

# Import authority sources
from src.authorities.manager import AuthoritySourceManager
from src.authorities.live_adapters import LiveAdapters


class AuthorityIntegrationTester:
    """Comprehensive authority source tester"""

    def __init__(self):
        self.results = {}
        self.live_adapters = LiveAdapters()

        # Test entries for different scenarios
        self.test_entries = [
            {
                "GlobalID": "TEST-001",
                "CanonicalNative": "A. Wiles",
                "CanonicalLatin": "A. Wiles",
                "Description": "Famous mathematician (Fermat's Last Theorem)",
            },
            {
                "GlobalID": "TEST-002",
                "CanonicalNative": "김민수",
                "CanonicalLatin": "Kim Min-su",
                "Description": "Korean name test",
            },
            {
                "GlobalID": "TEST-003",
                "CanonicalNative": "T. Tao",
                "CanonicalLatin": "T. Tao",
                "Description": "Fields medalist",
            },
            {
                "GlobalID": "TEST-004",
                "CanonicalNative": "Donald Knuth",
                "CanonicalLatin": "Donald Knuth",
                "Description": "Computer scientist",
            },
        ]

    def test_crossref(self) -> Dict[str, Any]:
        """Test Crossref API"""
        print("\n📚 Testing Crossref...")

        try:
            authority = CrossrefAuthority()
            results = []

            for entry in self.test_entries[:2]:  # Test first 2 entries
                name = entry["CanonicalLatin"]
                print(f"  Searching for: {name}")

                # Search for works
                works = authority.search_works(name, limit=3)

                if works:
                    results.append(
                        {
                            "name": name,
                            "works_found": len(works),
                            "first_work": (
                                {
                                    "title": (
                                        works[0].get("title", ["Unknown"])[0]
                                        if works[0].get("title")
                                        else "Unknown"
                                    ),
                                    "doi": works[0].get("DOI", "No DOI"),
                                    "year": works[0]
                                    .get("published-print", {})
                                    .get("date-parts", [[None]])[0][0],
                                }
                                if works
                                else None
                            ),
                        }
                    )
                    print(f"    ✅ Found {len(works)} works")
                else:
                    results.append({"name": name, "works_found": 0, "first_work": None})
                    print(f"    ⚠️ No works found")

                time.sleep(0.5)  # Rate limiting

            return {
                "status": "success",
                "api_working": len([r for r in results if r["works_found"] > 0]) > 0,
                "results": results,
            }

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            return {"status": "error", "api_working": False, "error": str(e)}

    def test_orcid(self) -> Dict[str, Any]:
        """Test ORCID API"""
        print("\n🆔 Testing ORCID...")

        try:
            authority = ORCIDAuthority()
            results = []

            for entry in self.test_entries[:2]:  # Test first 2 entries
                name = entry["CanonicalLatin"]
                print(f"  Searching for: {name}")

                # Search for ORCID
                orcid_results = authority.search(name)

                if orcid_results:
                    results.append(
                        {
                            "name": name,
                            "orcids_found": len(orcid_results),
                            "first_orcid": (
                                {
                                    "orcid": orcid_results[0]
                                    .get("orcid-identifier", {})
                                    .get("path"),
                                    "given_name": orcid_results[0]
                                    .get("person", {})
                                    .get("name", {})
                                    .get("given-names", {})
                                    .get("value"),
                                    "family_name": orcid_results[0]
                                    .get("person", {})
                                    .get("name", {})
                                    .get("family-name", {})
                                    .get("value"),
                                }
                                if orcid_results
                                else None
                            ),
                        }
                    )
                    print(f"    ✅ Found {len(orcid_results)} ORCID(s)")
                else:
                    results.append(
                        {"name": name, "orcids_found": 0, "first_orcid": None}
                    )
                    print(f"    ⚠️ No ORCID found")

                time.sleep(0.5)  # Rate limiting

            return {
                "status": "success",
                "api_working": len([r for r in results if r["orcids_found"] > 0]) > 0,
                "results": results,
            }

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            return {"status": "error", "api_working": False, "error": str(e)}

    def test_arxiv(self) -> Dict[str, Any]:
        """Test arXiv API"""
        print("\n📄 Testing arXiv...")

        try:
            authority = ArxivAuthority()
            results = []

            for entry in self.test_entries[:2]:  # Test first 2 entries
                name = entry["CanonicalLatin"]
                print(f"  Searching for: {name}")

                # Search for papers
                papers = authority.search_author(name, max_results=3)

                if papers:
                    results.append(
                        {
                            "name": name,
                            "papers_found": len(papers),
                            "first_paper": (
                                {
                                    "title": papers[0].get("title"),
                                    "arxiv_id": papers[0].get("id"),
                                    "categories": papers[0].get("categories"),
                                }
                                if papers
                                else None
                            ),
                        }
                    )
                    print(f"    ✅ Found {len(papers)} papers")
                else:
                    results.append(
                        {"name": name, "papers_found": 0, "first_paper": None}
                    )
                    print(f"    ⚠️ No papers found")

                time.sleep(0.5)  # Rate limiting

            return {
                "status": "success",
                "api_working": len([r for r in results if r["papers_found"] > 0]) > 0,
                "results": results,
            }

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            return {"status": "error", "api_working": False, "error": str(e)}

    def test_openalex(self) -> Dict[str, Any]:
        """Test OpenAlex API"""
        print("\n🔬 Testing OpenAlex...")

        try:
            authority = OpenAlexAuthority()
            results = []

            for entry in self.test_entries[:2]:  # Test first 2 entries
                name = entry["CanonicalLatin"]
                print(f"  Searching for: {name}")

                # Search for author
                authors = authority.search_author(name, limit=3)

                if authors:
                    results.append(
                        {
                            "name": name,
                            "authors_found": len(authors),
                            "first_author": (
                                {
                                    "id": authors[0].get("id"),
                                    "display_name": authors[0].get("display_name"),
                                    "works_count": authors[0].get("works_count"),
                                    "h_index": authors[0]
                                    .get("summary_stats", {})
                                    .get("h_index"),
                                }
                                if authors
                                else None
                            ),
                        }
                    )
                    print(f"    ✅ Found {len(authors)} author(s)")
                else:
                    results.append(
                        {"name": name, "authors_found": 0, "first_author": None}
                    )
                    print(f"    ⚠️ No authors found")

                time.sleep(0.5)  # Rate limiting

            return {
                "status": "success",
                "api_working": len([r for r in results if r["authors_found"] > 0]) > 0,
                "results": results,
            }

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            return {"status": "error", "api_working": False, "error": str(e)}

    def test_live_adapters(self) -> Dict[str, Any]:
        """Test the LiveAdapters integration layer"""
        print("\n🔌 Testing LiveAdapters integration...")

        try:
            # Test with a sample entry
            entry = self.test_entries[0].copy()

            # Get configured sources
            sources = self.live_adapters.get_configured_sources()
            print(f"  Configured sources: {sources}")

            # Enrich the entry
            enriched = self.live_adapters.enrich(entry)

            # Check what was added
            added_fields = [k for k in enriched.keys() if k not in entry]
            print(f"  Added fields: {added_fields}")

            # Check for authority data
            has_crossref = "CrossrefData" in enriched
            has_orcid = "ORCID" in enriched
            has_arxiv = "ArxivPapers" in enriched
            has_openalex = "OpenAlexID" in enriched

            return {
                "status": "success",
                "configured_sources": sources,
                "enrichment_working": len(added_fields) > 0,
                "sources_found": {
                    "crossref": has_crossref,
                    "orcid": has_orcid,
                    "arxiv": has_arxiv,
                    "openalex": has_openalex,
                },
                "added_fields": added_fields,
            }

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            return {"status": "error", "enrichment_working": False, "error": str(e)}

    def test_authority_manager(self) -> Dict[str, Any]:
        """Test the AuthorityManager"""
        print("\n📊 Testing AuthorityManager...")

        try:
            manager = AuthorityManager()

            # Get available sources
            sources = manager.get_available_sources()
            print(f"  Available sources: {sources}")

            # Test batch enrichment
            batch = self.test_entries[:2]
            enriched_batch = []

            for entry in batch:
                enriched = manager.enrich(entry.copy())
                enriched_batch.append(enriched)

                # Check enrichment
                added = len([k for k in enriched.keys() if k not in entry])
                print(f"  {entry['CanonicalLatin']}: {added} fields added")

            return {
                "status": "success",
                "available_sources": sources,
                "batch_enrichment_working": len(enriched_batch) == len(batch),
                "entries_enriched": len(enriched_batch),
            }

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            return {
                "status": "error",
                "batch_enrichment_working": False,
                "error": str(e),
            }

    def test_pipeline_integration(self) -> Dict[str, Any]:
        """Test authority enrichment in the V7 pipeline"""
        print("\n🔄 Testing Pipeline Integration...")

        try:
            from src.core.pipeline_v7 import V7Pipeline, PipelineMode

            # Create pipeline with authority enrichment
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)

            # Test batch with real names
            test_batch = [
                {
                    "GlobalID": "PIPE-001",
                    "CanonicalNative": "T. Tao",
                    "CanonicalLatin": "T. Tao",
                },
                {
                    "GlobalID": "PIPE-002",
                    "CanonicalNative": "A. Wiles",
                    "CanonicalLatin": "A. Wiles",
                },
            ]

            # Run pipeline
            result = asyncio.run(pipeline.process_batch(test_batch))

            # Check if authority enrichment happened
            processed = result.get("data", [])
            authority_fields_found = []

            for entry in processed:
                # Check for authority fields
                if "AuthoritySources" in entry:
                    authority_fields_found.append(entry["GlobalID"])
                    sources = entry.get("AuthoritySources", [])
                    print(f"  {entry['GlobalID']}: {len(sources)} authority sources")

            return {
                "status": "success",
                "pipeline_integration_working": len(authority_fields_found) > 0,
                "entries_with_authorities": len(authority_fields_found),
                "total_entries": len(processed),
            }

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            traceback.print_exc()
            return {
                "status": "error",
                "pipeline_integration_working": False,
                "error": str(e),
            }

    def run_all_tests(self):
        """Run all authority tests"""
        print("=" * 70)
        print("🚀 ULTRATHINK AUTHORITY SOURCES COMPREHENSIVE TEST")
        print("=" * 70)
        print(f"Time: {datetime.now()}")
        print(f"OFFLINE mode: {os.environ.get('OFFLINE', '1')}")
        print()

        # Test each authority source
        tests = [
            ("Crossref", self.test_crossref),
            ("ORCID", self.test_orcid),
            ("arXiv", self.test_arxiv),
            ("OpenAlex", self.test_openalex),
            ("LiveAdapters", self.test_live_adapters),
            ("AuthorityManager", self.test_authority_manager),
            ("Pipeline Integration", self.test_pipeline_integration),
        ]

        for test_name, test_func in tests:
            try:
                self.results[test_name] = test_func()
            except Exception as e:
                print(f"\n❌ Test '{test_name}' crashed: {e}")
                traceback.print_exc()
                self.results[test_name] = {
                    "status": "crash",
                    "api_working": False,
                    "error": str(e),
                }

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 AUTHORITY SOURCES TEST SUMMARY")
        print("=" * 70)

        working_sources = []
        failed_sources = []

        for source, result in self.results.items():
            if result["status"] == "success":
                if (
                    result.get("api_working")
                    or result.get("enrichment_working")
                    or result.get("batch_enrichment_working")
                    or result.get("pipeline_integration_working")
                ):
                    working_sources.append(source)
                    print(f"✅ {source}: WORKING")
                else:
                    failed_sources.append(source)
                    print(f"⚠️ {source}: No data retrieved")
            else:
                failed_sources.append(source)
                print(f"❌ {source}: {result.get('error', 'Unknown error')[:50]}")

        print(f"\n📈 Results:")
        print(f"  Working sources: {len(working_sources)}/{len(self.results)}")
        print(f"  Failed sources: {len(failed_sources)}/{len(self.results)}")

        if working_sources:
            print(f"\n✅ Working: {', '.join(working_sources)}")
        if failed_sources:
            print(f"❌ Failed: {', '.join(failed_sources)}")

        # Save detailed results
        report_file = (
            f"authority_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n📄 Detailed report saved to: {report_file}")

        # Overall verdict
        if len(working_sources) >= 4:
            print("\n🎉 AUTHORITY INTEGRATION: PASSED")
            print("At least 4 authority sources are working properly")
        else:
            print("\n⚠️ AUTHORITY INTEGRATION: NEEDS WORK")
            print(f"Only {len(working_sources)} sources working (need at least 4)")


if __name__ == "__main__":
    tester = AuthorityIntegrationTester()
    tester.run_all_tests()
