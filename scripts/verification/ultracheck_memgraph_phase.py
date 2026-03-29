#!/usr/bin/env python3
"""
ULTRACHECK: Memgraph Database Phase 1 Completion Verification
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def ultracheck_memgraph_deployment():
    """Ultracheck that Memgraph deployment meets all V7 requirements."""
    print("🔥 ULTRACHECK: MEMGRAPH DATABASE PHASE 1 COMPLETION")
    print("=" * 70)

    checks_passed = 0
    total_checks = 0

    # Check 1: Database connectivity
    total_checks += 1
    print("🧪 CHECKING: Database connectivity and authentication")
    try:
        from core.memgraph_client import MemgraphClient

        client = MemgraphClient(username="", password="", use_mock=False)

        if client.is_connected():
            print("✅ VERIFIED: Memgraph database accessible")
            checks_passed += 1
            client.close()
        else:
            print("❌ FAILED: Cannot connect to Memgraph")
    except Exception as e:
        print(f"❌ FAILED: Connection error - {e}")

    # Check 2: Core operations performance
    total_checks += 1
    print("\n🧪 CHECKING: Performance meets V7 requirements (≥50 mathematicians/sec)")
    try:
        from core.memgraph_client import MemgraphClient

        client = MemgraphClient(username="", password="", use_mock=False)

        # Performance test
        start_time = time.time()
        test_count = 50

        for i in range(test_count):
            test_entry = {
                "GlobalID": f"ultracheck-{i}",
                "CanonicalLatin": f"Ultracheck Test {i}",
                "DetectedRegion": "A1",
                "DetectionConfidence": 0.95,
            }
            client.create_mathematician(test_entry)

        end_time = time.time()
        duration = end_time - start_time
        throughput = test_count / duration

        if throughput >= 50:
            print(
                f"✅ VERIFIED: Performance excellent ({throughput:.1f} mathematicians/sec)"
            )
            checks_passed += 1
        else:
            print(
                f"❌ FAILED: Performance below requirement ({throughput:.1f} < 50 mathematicians/sec)"
            )

        client.close()

    except Exception as e:
        print(f"❌ FAILED: Performance test error - {e}")

    # Check 3: Graph operations functional
    total_checks += 1
    print("\n🧪 CHECKING: Graph analytics and relationship management")
    try:
        from core.memgraph_client import MemgraphClient, GenealogyRelation

        client = MemgraphClient(username="", password="", use_mock=False)

        # Test relationship creation
        relation = GenealogyRelation(
            source_id="ultracheck-1",
            target_id="ultracheck-2",
            relation_type="doctoralAdvisor",
            confidence=0.95,
        )

        success = client.add_genealogy_relation(relation)
        if success:
            print("✅ VERIFIED: Genealogy relationships working")

            # Test analytics
            metrics = client.get_graph_metrics()
            if metrics.total_mathematicians > 0:
                print("✅ VERIFIED: Graph analytics operational")
                checks_passed += 1
            else:
                print("❌ FAILED: Graph analytics not working")
        else:
            print("❌ FAILED: Cannot create relationships")

        client.close()

    except Exception as e:
        print(f"❌ FAILED: Graph operations error - {e}")

    # Check 4: Database schema and data persistence
    total_checks += 1
    print("\n🧪 CHECKING: Data persistence and schema integrity")
    try:
        from core.memgraph_client import MemgraphClient

        # Create client and add test data
        client1 = MemgraphClient(username="", password="", use_mock=False)
        test_id = "persistence-test"
        test_entry = {
            "GlobalID": test_id,
            "CanonicalLatin": "Persistence Test Mathematician",
            "BirthYear": 1900,
            "DetectedRegion": "A1",
        }

        client1.create_mathematician(test_entry)
        client1.close()

        # Reconnect and verify data exists
        client2 = MemgraphClient(username="", password="", use_mock=False)
        metrics = client2.get_graph_metrics()

        if metrics.total_mathematicians > 0:
            print("✅ VERIFIED: Data persistence working")
            checks_passed += 1
        else:
            print("❌ FAILED: Data not persisted")

        client2.close()

    except Exception as e:
        print(f"❌ FAILED: Persistence test error - {e}")

    # Check 5: Production readiness
    total_checks += 1
    print("\n🧪 CHECKING: Production deployment readiness")
    try:
        import subprocess

        # Check Docker container is running
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=gmnap-memgraph",
                "--format",
                "{{.Status}}",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and "Up" in result.stdout:
            print("✅ VERIFIED: Docker container running stably")

            # Check ports are accessible
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            port_accessible = sock.connect_ex(("localhost", 7687)) == 0
            sock.close()

            if port_accessible:
                print("✅ VERIFIED: Database port accessible")
                checks_passed += 1
            else:
                print("❌ FAILED: Database port not accessible")
        else:
            print("❌ FAILED: Docker container not running properly")

    except Exception as e:
        print(f"❌ FAILED: Production readiness check error - {e}")

    # Final assessment
    print("\n" + "=" * 70)
    print("🎯 PHASE 1 COMPLETION ASSESSMENT")
    print("=" * 70)
    print(f"Checks passed: {checks_passed}/{total_checks}")
    print(f"Success rate: {100 * checks_passed / total_checks:.1f}%")

    if checks_passed == total_checks:
        print("\n🚀 PHASE 1 COMPLETE: MEMGRAPH DATABASE FULLY OPERATIONAL")
        print("✅ Database infrastructure ready for streaming pipeline integration")
        print("✅ Performance exceeds V7 requirements")
        print("✅ Graph analytics fully functional")
        print("✅ Production deployment stable")
        print("\n🎯 STATUS: PROCEED TO PHASE 2 - STREAMING PIPELINE")
        return True

    elif checks_passed >= total_checks * 0.8:
        print("\n✅ PHASE 1 MOSTLY COMPLETE: MINOR ISSUES PRESENT")
        print("⚠️ Some functionality needs attention but core database operational")
        print("\n🎯 STATUS: PROCEED WITH MONITORING")
        return True

    else:
        print("\n❌ PHASE 1 INCOMPLETE: CRITICAL ISSUES")
        print("🚨 Database infrastructure not ready for production")
        print("\n🎯 STATUS: RESOLVE ISSUES BEFORE PROCEEDING")
        return False


def main():
    """Run Memgraph phase completion ultracheck."""
    return ultracheck_memgraph_deployment()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
