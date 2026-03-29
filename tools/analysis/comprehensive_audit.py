#!/usr/bin/env python3
"""
Comprehensive audit of GMNAP Phase 2 implementation.
Tests all components end-to-end and verifies claims.
"""

import sys
import tempfile
import yaml
import json
import threading
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
from src.core.config import GMNAPConfig
from src.regions.manager import RegionManager
from src.regions import *
from src.regions.d_groups import D1_HindiBelt
from src.utils.database import DatabaseManager, DatabaseConfig
from src.utils.cache import CacheManager
from src.core.globalid import GlobalIDGenerator


def audit_section(section_name):
    """Decorator to mark audit sections."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"\n{'='*60}")
            print(f"🔍 AUDITING: {section_name}")
            print(f"{'='*60}")
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                print(f"✅ {section_name} - PASSED ({duration:.2f}s)")
                return result
            except Exception as e:
                duration = time.time() - start_time
                print(f"❌ {section_name} - FAILED ({duration:.2f}s)")
                print(f"   Error: {str(e)}")
                raise

        return wrapper

    return decorator


class ComprehensiveAudit:
    """Main audit class."""

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.issues_found = []
        self.fixes_applied = []

    def log_issue(self, issue):
        """Log an issue found during audit."""
        self.issues_found.append(issue)
        print(f"⚠️  ISSUE: {issue}")

    def log_fix(self, fix):
        """Log a fix applied during audit."""
        self.fixes_applied.append(fix)
        print(f"🔧 FIX: {fix}")

    @audit_section("REGIONAL IMPLEMENTATION ACCURACY")
    def audit_regional_implementation(self):
        """Audit regional implementation accuracy."""
        print("Testing 7 critical regions...")

        # Test data for each region
        test_cases = [
            # A1 - Anglo-Sphere
            {
                "name": "Smith, John Michael",
                "country": "US",
                "expected_region": "A1",
                "test_type": "Anglo-Sphere",
            },
            # B1 - East Slavic
            {
                "name": "Иванов Иван Петрович",
                "country": "RU",
                "expected_region": "B1",
                "test_type": "East-Slavic",
            },
            # E1 - Chinese Mainland
            {
                "name": "王小明",
                "country": "CN",
                "expected_region": "E1",
                "test_type": "Chinese",
            },
            # C3 - Arabic Levant-Nile
            {
                "name": "محمد عبد الله",
                "country": "EG",
                "expected_region": "C3",
                "test_type": "Arabic",
            },
            # E3 - Japanese
            {
                "name": "田中太郎",
                "country": "JP",
                "expected_region": "E3",
                "test_type": "Japanese",
            },
            # G1 - Latin America
            {
                "name": "García López, José María",
                "country": "MX",
                "expected_region": "G1",
                "test_type": "Latin America",
            },
            # D1 - Hindi Belt
            {
                "name": "राम प्रकाश शर्मा",
                "country": "IN",
                "expected_region": "D1",
                "test_type": "Hindi Belt",
            },
        ]

        manager = RegionManager()
        regions = [
            A1_AngloSphere(),
            B1_EastSlavic(),
            C2_PersianTajik(),
            C3_ArabicLevantNile(),
            D1_HindiBelt(),
            E1_SinophoneMainland(),
            E3_Japan(),
            G1_LatinAmerica(),
        ]

        for region in regions:
            manager.register_region(region)

        correct_detections = 0
        total_tests = len(test_cases)

        for test_case in test_cases:
            entry = {
                "CanonicalNative": test_case["name"],
                "CanonicalLatin": test_case["name"],
                "CountryCodes": [test_case["country"]],
            }

            detection = manager.detect_region(entry)

            if detection.region_code == test_case["expected_region"]:
                correct_detections += 1
                print(
                    f"  ✅ {test_case['test_type']}: {test_case['name']} → {detection.region_code}"
                )
            else:
                self.log_issue(
                    f"{test_case['test_type']} detection failed: expected {test_case['expected_region']}, got {detection.region_code}"
                )

        accuracy = (correct_detections / total_tests) * 100
        print(
            f"\n📊 Region Detection Accuracy: {correct_detections}/{total_tests} = {accuracy:.1f}%"
        )

        if accuracy < 100:
            self.log_issue(
                f"Region detection accuracy is {accuracy:.1f}%, expected 100%"
            )

        return accuracy >= 100

    @audit_section("PIPELINE END-TO-END FUNCTIONALITY")
    def audit_pipeline_functionality(self):
        """Audit complete pipeline functionality."""
        print("Testing pipeline with real data...")

        # Create test input data
        input_dir = self.temp_dir / "input"
        input_dir.mkdir(parents=True)

        # Multi-regional test data
        test_entries = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "BirthYear": 1980,
                "CountryCodes": ["US"],
                "Confidence": 85,
            },
            "Иванов, Иван": {
                "GlobalID": "BCDEFGHIJKLMNOPQRSTUVW",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Ivanov, Ivan",
                "CanonicalNative": "Иванов, Иван",
                "BirthYear": 1975,
                "CountryCodes": ["RU"],
                "Confidence": 90,
            },
            "王小明": {
                "GlobalID": "CDEFGHIJKLMNOPQRSTUVWX",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Wang Xiaoming",
                "CanonicalNative": "王小明",
                "BirthYear": 1985,
                "CountryCodes": ["CN"],
                "Confidence": 88,
            },
        }

        # Write test data
        test_file = input_dir / "test_data.yaml"
        with open(test_file, "w", encoding="utf-8") as f:
            yaml.dump(test_entries, f, allow_unicode=True)

        # Configure pipeline
        config = GMNAPConfig()
        config.database.db_path = str(self.temp_dir / "test.db")
        config.cache.cache_dir = str(self.temp_dir / "cache")

        # Copy source_manifest.json to temp cache directory if it exists
        source_manifest_path = Path("cache/config/source_manifest.json")
        if source_manifest_path.exists():
            temp_config_dir = self.temp_dir / "cache" / "config"
            temp_config_dir.mkdir(parents=True, exist_ok=True)

            import shutil

            shutil.copy2(source_manifest_path, temp_config_dir / "source_manifest.json")
            print(f"  ✅ Copied source_manifest.json to temporary directory")

        # Run pipeline
        pipeline = GMNAPPipeline(config, PipelineMode.QUICK)

        try:
            result = pipeline.run(input_dir)

            # Verify results
            if result is None:
                self.log_issue("Pipeline returned None result")
                return False

            if not hasattr(result, "total_entries"):
                self.log_issue("Pipeline result missing total_entries")
                return False

            if result.total_entries != len(test_entries):
                self.log_issue(
                    f"Pipeline processed {result.total_entries} entries, expected {len(test_entries)}"
                )
                return False

            print(
                f"  ✅ Pipeline processed {result.total_entries} entries successfully"
            )
            return True

        except Exception as e:
            import traceback

            traceback_str = traceback.format_exc()
            self.log_issue(f"Pipeline execution failed: {str(e)}")
            print(f"Full traceback: {traceback_str}")
            return False

    @audit_section("DATABASE PERSISTENCE INTEGRITY")
    def audit_database_integrity(self):
        """Audit database operations and integrity."""
        print("Testing database persistence...")

        # Test database configuration
        db_path = self.temp_dir / "audit_test.db"
        config = DatabaseConfig(db_path=str(db_path))

        try:
            db = DatabaseManager(config)

            # Test data insertion - use correct format
            test_data = [
                {
                    "Test, Audit": {
                        "GlobalID": "TESTAUDIT12345678901234",
                        "CanonicalLatin": "Test, Audit",
                        "CanonicalNative": "Test, Audit",
                        "BirthYear": 1980,
                        "DeathYear": None,
                        "CountryCodes": ["US"],
                        "Confidence": 85.0,
                    }
                }
            ]

            db.insert_initial_stats(test_data)

            # Verify insertion
            stats = db.get_statistics()
            if not isinstance(stats, dict):
                self.log_issue(
                    f"Database get_statistics() returned {type(stats)}, expected dict"
                )
                return False

            if stats.get("total_entries", 0) != 1:
                self.log_issue(
                    f"Database has {stats.get('total_entries', 0)} entries, expected 1"
                )
                return False

            print(f"  ✅ Database operations working correctly")
            return True

        except Exception as e:
            self.log_issue(f"Database operations failed: {str(e)}")
            return False

    @audit_section("CACHE SYSTEM THREAD SAFETY")
    def audit_cache_thread_safety(self):
        """Audit cache system thread safety."""
        print("Testing cache thread safety...")

        cache_dir = self.temp_dir / "cache_test"
        cache = CacheManager(cache_dir=cache_dir, max_size_gb=0.1, max_days=1)

        def cache_worker(worker_id):
            """Worker that performs cache operations."""
            try:
                for i in range(10):
                    key = f"worker_{worker_id}_item_{i}"
                    data = {
                        "worker_id": worker_id,
                        "item_id": i,
                        "timestamp": time.time(),
                    }

                    # Write and read
                    cache.put("test_service", key, data)
                    read_data = cache.get("test_service", key)

                    if read_data != data:
                        return False
                return True
            except Exception:
                return False

        # Run concurrent workers
        num_workers = 5
        threads = []
        results = []

        for i in range(num_workers):
            thread = threading.Thread(
                target=lambda w=i: results.append(cache_worker(w))
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        successful = sum(1 for r in results if r)

        if successful != num_workers:
            self.log_issue(
                f"Cache thread safety failed: {successful}/{num_workers} workers successful"
            )
            return False

        print(
            f"  ✅ Cache thread safety verified: {successful}/{num_workers} workers successful"
        )
        return True

    @audit_section("GLOBALID GENERATION INTEGRITY")
    def audit_globalid_integrity(self):
        """Audit GlobalID generation integrity."""
        print("Testing GlobalID generation...")

        generator = GlobalIDGenerator()

        # Test basic generation
        test_entry = {"CanonicalNative": "Test, Person", "BirthYear": 1980}

        global_id = generator.generate(test_entry)

        if not global_id:
            self.log_issue("GlobalID generation returned None")
            return False

        if len(global_id) < 22:
            self.log_issue(f"GlobalID too short: {len(global_id)} characters")
            return False

        # Test deterministic behavior (same input should produce same output)
        duplicate_entry = test_entry.copy()
        global_id2 = generator.generate(duplicate_entry)

        if global_id != global_id2:
            self.log_issue(
                "GlobalID generation not deterministic - same input produces different output"
            )
            return False

        # Test actual collision handling with different entry
        different_entry = {"CanonicalNative": "Different, Person", "BirthYear": 1980}
        global_id3 = generator.generate(different_entry)

        if global_id == global_id3:
            self.log_issue("GlobalID collision occurred for different entries")
            return False

        print(f"  ✅ GlobalID generation working correctly")
        print(f"    Original: {global_id}")
        print(f"    Duplicate: {global_id2} (deterministic)")
        print(f"    Different: {global_id3} (unique)")
        return True

    @audit_section("REGIONAL PROCESSING ACCURACY")
    def audit_regional_processing(self):
        """Audit regional processing accuracy."""
        print("Testing regional processing...")

        # Test each region's processing
        regions_to_test = [
            (A1_AngloSphere(), "Dr. Smith Jr., John Michael", "Anglo-Sphere"),
            (B1_EastSlavic(), "Иванов Иван Петрович", "East-Slavic"),
            (E1_SinophoneMainland(), "王小明", "Chinese"),
            (C3_ArabicLevantNile(), "محمد عبد الله", "Arabic"),
            (E3_Japan(), "田中太郎", "Japanese"),
            (G1_LatinAmerica(), "García López, José María", "Latin America"),
        ]

        processing_success = 0
        total_regions = len(regions_to_test)

        for region, test_name, region_name in regions_to_test:
            try:
                entry = {
                    "CanonicalLatin": test_name,
                    "CanonicalNative": test_name,
                    "Variants": {"Observed": []},
                }

                # Test clean, augment, validate
                region.clean(entry)
                region.augment(entry)
                region.validate(entry)

                # Check if processing added expected data
                if "RegionalExtras" in entry:
                    processing_success += 1
                    print(f"  ✅ {region_name} processing successful")
                else:
                    self.log_issue(
                        f"{region_name} processing did not add RegionalExtras"
                    )

            except Exception as e:
                self.log_issue(f"{region_name} processing failed: {str(e)}")

        accuracy = (processing_success / total_regions) * 100
        print(
            f"\n📊 Regional Processing Accuracy: {processing_success}/{total_regions} = {accuracy:.1f}%"
        )

        return accuracy >= 100

    @audit_section("MEMORY AND PERFORMANCE")
    def audit_memory_performance(self):
        """Audit memory usage and performance."""
        print("Testing memory usage and performance...")

        import psutil
        import gc

        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Test with larger dataset
        generator = GlobalIDGenerator()

        start_time = time.time()

        for i in range(1000):
            entry = {
                "CanonicalNative": f"Test{i:04d}, Person",
                "BirthYear": 1980 + (i % 50),
            }
            global_id = generator.generate(entry)

            if not global_id:
                self.log_issue(f"GlobalID generation failed at iteration {i}")
                return False

        duration = time.time() - start_time
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory

        print(f"  📊 Generated 1000 GlobalIDs in {duration:.2f}s")
        print(
            f"  📊 Memory usage: {initial_memory:.1f}MB → {current_memory:.1f}MB (+{memory_increase:.1f}MB)"
        )

        # Performance threshold
        if duration > 5.0:  # 5 seconds for 1000 IDs
            self.log_issue(f"Performance too slow: {duration:.2f}s for 1000 GlobalIDs")
            return False

        # Memory threshold
        if memory_increase > 100:  # 100MB increase
            self.log_issue(f"Memory usage too high: +{memory_increase:.1f}MB")
            return False

        print(f"  ✅ Performance and memory usage within acceptable limits")
        return True

    def run_comprehensive_audit(self):
        """Run complete audit."""
        print("🔍 STARTING COMPREHENSIVE AUDIT")
        print(f"📁 Working directory: {self.temp_dir}")
        print(f"🕐 Start time: {datetime.now()}")

        audit_results = []

        # Run all audits
        audit_results.append(self.audit_regional_implementation())
        audit_results.append(self.audit_pipeline_functionality())
        audit_results.append(self.audit_database_integrity())
        audit_results.append(self.audit_cache_thread_safety())
        audit_results.append(self.audit_globalid_integrity())
        audit_results.append(self.audit_regional_processing())
        audit_results.append(self.audit_memory_performance())

        # Summary
        passed = sum(1 for r in audit_results if r)
        total = len(audit_results)

        print(f"\n{'='*60}")
        print(f"📊 AUDIT SUMMARY")
        print(f"{'='*60}")
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print(f"Issues Found: {len(self.issues_found)}")
        print(f"Fixes Applied: {len(self.fixes_applied)}")

        if self.issues_found:
            print(f"\n⚠️  ISSUES FOUND:")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"  {i}. {issue}")

        if self.fixes_applied:
            print(f"\n🔧 FIXES APPLIED:")
            for i, fix in enumerate(self.fixes_applied, 1):
                print(f"  {i}. {fix}")

        # Clean up
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        return passed == total, self.issues_found, self.fixes_applied


if __name__ == "__main__":
    audit = ComprehensiveAudit()
    success, issues, fixes = audit.run_comprehensive_audit()

    if success:
        print(f"\n🎉 AUDIT PASSED - All systems working correctly!")
        sys.exit(0)
    else:
        print(f"\n❌ AUDIT FAILED - {len(issues)} issues found")
        sys.exit(1)
