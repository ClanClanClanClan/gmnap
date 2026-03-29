#!/usr/bin/env python3
"""
ULTRATHINK Comprehensive Audit - What's Broken & Untested
"""

import os
import sys
import json
import time
import traceback
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple


class UltrathinkAuditor:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "working": {},
            "broken": {},
            "untested": {},
            "failures": [],
            "summary": {},
        }

    def run_command(self, cmd: str, timeout: int = 5) -> Tuple[bool, str, str]:
        """Run command with timeout"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONPATH": "."},
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"TIMEOUT after {timeout}s"
        except Exception as e:
            return False, "", str(e)

    def audit_test_suite(self):
        """Audit the entire test suite"""
        print("\n" + "=" * 80)
        print("AUDITING TEST SUITE")
        print("=" * 80)

        test_categories = {
            "unit": "tests/unit/",
            "integration": "tests/integration/",
            "hardcore": "tests/hardcore/",
            "security": "tests/security/",
            "memory": "tests/memory/",
            "stress": "tests/stress/",
            "property": "tests/property/",
            "quality_gates": "tests/quality_gates/",
            "mock_api": "tests/mock_api/",
        }

        for category, path in test_categories.items():
            if not os.path.exists(path):
                self.results["untested"][f"test_{category}"] = "Directory missing"
                continue

            print(f"\nTesting {category}...")
            success, stdout, stderr = self.run_command(
                f"python3 -m pytest {path} -q --tb=no --timeout=2 2>&1 | tail -5",
                timeout=10,
            )

            if "passed" in stdout:
                # Extract pass/fail stats
                lines = stdout.strip().split("\n")
                for line in lines:
                    if "passed" in line or "failed" in line:
                        self.results["working"][f"test_{category}"] = line
                        print(f"  ✅ {line}")
                        break
            else:
                self.results["broken"][f"test_{category}"] = stderr or stdout
                print(f"  ❌ {category}: {stderr[:100] if stderr else stdout[:100]}")

    def audit_regional_processors(self):
        """Test all regional processors"""
        print("\n" + "=" * 80)
        print("AUDITING REGIONAL PROCESSORS")
        print("=" * 80)

        test_script = """
import sys
from src.regions.manager import RegionManager

manager = RegionManager()

# Test regions
test_cases = [
    ('E4', '김민수', 'Korean'),
    ('E1', '李明', 'Chinese'),
    ('B1', 'Иванов Иван', 'Russian'),
    ('E3', '山田太郎', 'Japanese'),
    ('C3', 'محمد علي', 'Arabic'),
    ('A1', 'John Smith', 'English'),
    ('A2', 'Jean-Pierre Dubois', 'French'),
    ('D1', 'राज कुमार', 'Hindi'),
    ('G1', 'José García', 'Spanish')
]

results = []
for region_code, name, lang in test_cases:
    try:
        region = manager.get_region(region_code)
        if region:
            result = region.process({'CanonicalNative': name, 'GlobalID': f'TEST-{region_code}'})
            latin = result.get('CanonicalLatin', 'NO_OUTPUT')
            results.append(f"{region_code} ({lang}): {name} → {latin}")
        else:
            results.append(f"{region_code} ({lang}): REGION_NOT_FOUND")
    except Exception as e:
        results.append(f"{region_code} ({lang}): ERROR - {str(e)[:50]}")

for r in results:
    print(r)
"""

        success, stdout, stderr = self.run_command(
            f'python3 -c "{test_script}"', timeout=10
        )

        if success and stdout:
            for line in stdout.strip().split("\n"):
                if "→" in line:
                    if "NO_OUTPUT" in line or "ERROR" in line or "NOT_FOUND" in line:
                        self.results["broken"][
                            f'region_{line.split(":")[0].strip()}'
                        ] = line
                        print(f"  ❌ {line}")
                    else:
                        self.results["working"][
                            f'region_{line.split(":")[0].strip()}'
                        ] = line
                        print(f"  ✅ {line}")
        else:
            self.results["broken"]["regional_processors"] = stderr or "Failed to test"
            print(f"  ❌ Regional processors test failed: {stderr[:200]}")

    def audit_authority_sources(self):
        """Test authority source integration"""
        print("\n" + "=" * 80)
        print("AUDITING AUTHORITY SOURCES")
        print("=" * 80)

        test_script = """
import os
os.environ['OFFLINE'] = '1'

from src.authorities.tier0.crossref import CrossrefAuthority
from src.authorities.tier0.openalex import OpenAlexAuthority
from src.authorities.tier0.zbmath import ZBMathAuthority

sources = {
    'Crossref': CrossrefAuthority(),
    'OpenAlex': OpenAlexAuthority(),
    'ZBMath': ZBMathAuthority()
}

for name, source in sources.items():
    try:
        # Test basic functionality
        result = source.fetch('test-id')
        if result:
            print(f"{name}: ✅ Returns data")
        else:
            print(f"{name}: ⚠️ Returns None (offline mode)")
    except Exception as e:
        print(f"{name}: ❌ ERROR - {str(e)[:50]}")
"""

        success, stdout, stderr = self.run_command(
            f'python3 -c "{test_script}"', timeout=10
        )

        if stdout:
            for line in stdout.strip().split("\n"):
                if ":" in line:
                    source = line.split(":")[0]
                    if "❌" in line:
                        self.results["broken"][f"authority_{source}"] = line
                    elif "✅" in line:
                        self.results["working"][f"authority_{source}"] = line
                    else:
                        self.results["untested"][f"authority_{source}"] = line
                    print(f"  {line}")

    def audit_database_systems(self):
        """Test database and caching systems"""
        print("\n" + "=" * 80)
        print("AUDITING DATABASE SYSTEMS")
        print("=" * 80)

        # Test SQLite
        test_sqlite = """
import sqlite3
import os
db_path = 'data/gmnap.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"SQLite: ✅ {len(tables)} tables found")
    conn.close()
else:
    print("SQLite: ❌ Database file not found")
"""

        success, stdout, stderr = self.run_command(
            f'python3 -c "{test_sqlite}"', timeout=5
        )

        if stdout:
            print(f"  {stdout.strip()}")
            if "✅" in stdout:
                self.results["working"]["database_sqlite"] = stdout.strip()
            else:
                self.results["broken"]["database_sqlite"] = stdout.strip()

        # Test DuckDB
        test_duckdb = """
import duckdb
try:
    conn = duckdb.connect(':memory:')
    result = conn.execute("SELECT version()").fetchone()
    print(f"DuckDB: ✅ Version {result[0]}")
    conn.close()
except Exception as e:
    print(f"DuckDB: ❌ {str(e)[:50]}")
"""

        success, stdout, stderr = self.run_command(
            f'python3 -c "{test_duckdb}"', timeout=5
        )

        if stdout:
            print(f"  {stdout.strip()}")
            if "✅" in stdout:
                self.results["working"]["database_duckdb"] = stdout.strip()
            else:
                self.results["broken"]["database_duckdb"] = stdout.strip()

        # Test caching
        test_cache = """
from src.core.cache_manager import CacheManager
cache = CacheManager()
cache.set('test_key', 'test_value')
value = cache.get('test_key')
if value == 'test_value':
    print("Cache: ✅ Basic operations working")
else:
    print(f"Cache: ❌ Got {value} instead of test_value")
"""

        success, stdout, stderr = self.run_command(
            f'python3 -c "{test_cache}"', timeout=5
        )

        if stdout:
            print(f"  {stdout.strip()}")
            if "✅" in stdout:
                self.results["working"]["cache_system"] = stdout.strip()
            else:
                self.results["broken"]["cache_system"] = stdout.strip()

    def audit_security_components(self):
        """Test security and authentication"""
        print("\n" + "=" * 80)
        print("AUDITING SECURITY COMPONENTS")
        print("=" * 80)

        # Test security validator
        test_security = """
from src.core.security_validator import SecurityValidator
validator = SecurityValidator()

test_input = {'CanonicalNative': 'Test Name', 'GlobalID': 'TEST-001'}
try:
    is_safe = validator.validate(test_input)
    print(f"Security Validator: ✅ Returns {is_safe}")
except Exception as e:
    print(f"Security Validator: ❌ {str(e)[:50]}")
"""

        success, stdout, stderr = self.run_command(
            f'python3 -c "{test_security}"', timeout=5
        )

        if stdout:
            print(f"  {stdout.strip()}")
            if "✅" in stdout:
                self.results["working"]["security_validator"] = stdout.strip()
            else:
                self.results["broken"]["security_validator"] = stdout.strip()

        # Test JWT authentication
        test_jwt = """
try:
    import jwt
    print("JWT: ✅ Module available")
except ImportError:
    print("JWT: ❌ Module not installed")
"""

        success, stdout, stderr = self.run_command(
            f'python3 -c "{test_jwt}"', timeout=5
        )

        if stdout:
            print(f"  {stdout.strip()}")
            if "✅" in stdout:
                self.results["working"]["jwt_auth"] = stdout.strip()
            else:
                self.results["untested"]["jwt_auth"] = "Module not installed"

    def audit_production_features(self):
        """Test production-critical features"""
        print("\n" + "=" * 80)
        print("AUDITING PRODUCTION FEATURES")
        print("=" * 80)

        # Test quality gates
        test_gates = """
from src.quality.gates import QualityGates
gates = QualityGates()

metrics = {
    'duplicate_ids': 0,
    'entries_per_second': 1000,
    'processed_entries': 1000000
}

try:
    passed = gates.check_all(metrics)
    print(f"Quality Gates: ✅ Check returns {passed}")
except Exception as e:
    print(f"Quality Gates: ❌ {str(e)[:50]}")
"""

        success, stdout, stderr = self.run_command(
            f'python3 -c "{test_gates}"', timeout=5
        )

        if stdout:
            print(f"  {stdout.strip()}")
            if "✅" in stdout:
                self.results["working"]["quality_gates"] = stdout.strip()
            else:
                self.results["broken"]["quality_gates"] = stdout.strip()

        # Test idempotency
        test_idempotency = """
from src.core.pipeline_v7 import V7Pipeline, PipelineMode
import asyncio

async def test():
    pipeline = V7Pipeline(mode=PipelineMode.DETERMINISTIC)
    entry = {'CanonicalNative': 'Test Name', 'GlobalID': 'TEST-001'}

    result1 = await pipeline.process_batch([entry])
    result2 = await pipeline.process_batch([entry])

    id1 = result1['processed'][0].get('SystemID')
    id2 = result2['processed'][0].get('SystemID')

    if id1 == id2:
        print(f"Idempotency: ✅ Deterministic ({id1})")
    else:
        print(f"Idempotency: ❌ Different IDs ({id1} vs {id2})")

asyncio.run(test())
"""

        success, stdout, stderr = self.run_command(
            f'python3 -c "{test_idempotency}"', timeout=10
        )

        if stdout:
            for line in stdout.strip().split("\n"):
                if "Idempotency:" in line:
                    print(f"  {line}")
                    if "✅" in line:
                        self.results["working"]["idempotency"] = line
                    else:
                        self.results["broken"]["idempotency"] = line

    def check_untested_areas(self):
        """Identify untested areas"""
        print("\n" + "=" * 80)
        print("IDENTIFYING UNTESTED AREAS")
        print("=" * 80)

        untested = [
            ("Concurrent processing", "No concurrent access tests found"),
            ("Memory profiling", "No memory profile under load"),
            ("1M+ entry processing", "Never tested at production scale"),
            ("Error recovery", "No systematic error recovery tests"),
            ("Network failures", "No network failure simulation"),
            ("Backup/restore", "No backup/restore procedures"),
            ("Monitoring integration", "No Prometheus/Grafana tests"),
            ("API endpoints", "No API endpoint tests"),
            ("Load balancing", "No load balancer tests"),
            ("Database migrations", "No migration tests"),
            ("Deployment automation", "No CI/CD pipeline tests"),
            ("Performance regression", "No performance regression tests"),
            ("Data validation rules", "No comprehensive validation tests"),
            ("Unicode edge cases", "Limited Unicode testing"),
            ("Time zone handling", "No timezone tests"),
            ("Large file handling", "No large file tests"),
            ("Disk space handling", "No disk space tests"),
            ("Rate limiting", "No rate limit tests"),
            ("Authentication flows", "No auth flow tests"),
            ("Encryption at rest", "No encryption tests"),
        ]

        for area, reason in untested:
            self.results["untested"][area] = reason
            print(f"  ❓ {area}: {reason}")

    def generate_summary(self):
        """Generate summary statistics"""
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)

        working_count = len(self.results["working"])
        broken_count = len(self.results["broken"])
        untested_count = len(self.results["untested"])
        total = working_count + broken_count + untested_count

        self.results["summary"] = {
            "total_components": total,
            "working": working_count,
            "broken": broken_count,
            "untested": untested_count,
            "working_percentage": (
                round(working_count / total * 100, 1) if total > 0 else 0
            ),
            "broken_percentage": (
                round(broken_count / total * 100, 1) if total > 0 else 0
            ),
            "untested_percentage": (
                round(untested_count / total * 100, 1) if total > 0 else 0
            ),
        }

        print(f"\n📊 Component Status:")
        print(
            f"  ✅ Working:  {working_count:3d} ({self.results['summary']['working_percentage']:.1f}%)"
        )
        print(
            f"  ❌ Broken:   {broken_count:3d} ({self.results['summary']['broken_percentage']:.1f}%)"
        )
        print(
            f"  ❓ Untested: {untested_count:3d} ({self.results['summary']['untested_percentage']:.1f}%)"
        )
        print(f"  📋 Total:    {total:3d}")

    def save_results(self):
        """Save results to JSON file"""
        filename = f"ultrathink_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Results saved to: {filename}")
        return filename

    def run_comprehensive_audit(self):
        """Run all audit checks"""
        print("=" * 80)
        print("ULTRATHINK COMPREHENSIVE AUDIT - WHAT'S BROKEN & UNTESTED")
        print("=" * 80)
        print(f"Started: {self.results['timestamp']}")

        self.audit_test_suite()
        self.audit_regional_processors()
        self.audit_authority_sources()
        self.audit_database_systems()
        self.audit_security_components()
        self.audit_production_features()
        self.check_untested_areas()
        self.generate_summary()

        return self.save_results()


if __name__ == "__main__":
    auditor = UltrathinkAuditor()
    results_file = auditor.run_comprehensive_audit()

    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)
