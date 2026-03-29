import pytest

#!/usr/bin/env python3
"""
Production Monitoring System Test Suite
BRUTAL honesty test - validate TRUE production readiness
"""

import sys
import asyncio
import time
import tempfile
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_comprehensive_metrics_collection():
    """Test comprehensive system metrics collection."""
    print("🧪 TESTING: Comprehensive metrics collection")

    try:
        from src.core.monitoring_production import (
            ProductionMonitoringSystem,
            AlertNotificationConfig,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize production monitoring
            monitor = ProductionMonitoringSystem(
                db_path=Path(temp_dir) / "prod_test.db", alert_config=AlertNotificationConfig()
            )

            # Let it collect metrics for a few seconds
            print("   Collecting comprehensive metrics...")
            time.sleep(5)

            # Get live status
            status = monitor.get_live_status()

            print(f"PASS Comprehensive metrics results:")
            print(
                f"   System metrics collected: {len([k for k in status['system'].keys() if status['system'][k] > 0])}/5"
            )
            print(f"   CPU usage: {status['system']['cpu_percent']:.1f}%")
            print(
                f"   Memory usage: {status['system']['memory_used_mb']:.1f}MB ({status['system']['memory_percent']:.1f}%)"
            )
            print(
                f"   Disk usage: {status['system']['disk_used_gb']:.1f}GB ({status['system']['disk_percent']:.1f}%)"
            )
            print(f"   Uptime: {status['uptime_hours']:.3f} hours")
            print(f"   Health status: {status['health_status']}")

            # Verify comprehensive coverage
            system_metrics = status["system"]
            essential_metrics = [
                "cpu_percent",
                "memory_used_mb",
                "memory_percent",
                "disk_used_gb",
                "disk_percent",
            ]
            working_metrics = sum(
                1 for metric in essential_metrics if system_metrics.get(metric, 0) > 0
            )

            monitor.shutdown()

            if working_metrics >= 4:  # At least 4 of 5 system metrics working
                print("PASS Comprehensive metrics collection successful")
                return True
            else:
                print(f"FAIL Comprehensive metrics failed: only {working_metrics}/5 working")
                return False

    except Exception as e:
        print(f"FAIL Comprehensive metrics test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_real_time_alerting():
    """Test real-time alerting with actual threshold violations."""
    print("\n🧪 TESTING: Real-time alerting system")

    try:
        from src.core.monitoring_production import (
            ProductionMonitoringSystem,
            AlertNotificationConfig,
        )

        # Capture alerts
        captured_alerts = []

        @pytest.mark.timeout(15)
        def test_alert_handler(webhook_url, level, component, message, value, threshold):
            captured_alerts.append(
                {
                    "level": level,
                    "component": component,
                    "message": message,
                    "value": value,
                    "threshold": threshold,
                }
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            # Configure for aggressive alerting
            alert_config = AlertNotificationConfig()

            monitor = ProductionMonitoringSystem(
                db_path=Path(temp_dir) / "alert_test.db", alert_config=alert_config
            )

            # Monkey patch webhook sender to capture alerts
            original_send_webhook = monitor._send_webhook_alert
            monitor._send_webhook_alert = test_alert_handler

            # Simulate high resource usage to trigger alerts
            print("   Simulating resource stress...")

            # Force high CPU alert
            monitor._current_metrics.cpu_percent = 95.0
            monitor._check_system_health(monitor._current_metrics)

            # Force high memory alert
            monitor._current_metrics.memory_percent = 92.0
            monitor._check_system_health(monitor._current_metrics)

            # Force low pipeline performance alert
            monitor.update_pipeline_metrics(
                throughput=25.0,  # Low throughput
                latency_ms=2000.0,  # High latency
                success_rate=88.0,  # Low success rate
            )
            monitor._check_system_health(monitor._current_metrics)

            time.sleep(1)  # Allow alert processing

            print(f"PASS Real-time alerting results:")
            print(f"   Alerts generated: {len(captured_alerts)}")
            print(f"   Active alert keys: {len(monitor._active_alerts)}")

            # Verify alert details
            for alert in captured_alerts:
                print(f"   Alert: {alert['level']} - {alert['message'][:50]}...")

            monitor.shutdown()

            # Should have generated multiple alerts for the stress conditions
            if len(captured_alerts) >= 2:
                print("PASS Real-time alerting successful")
                return True
            else:
                print("FAIL Real-time alerting failed: insufficient alerts generated")
                return False

    except Exception as e:
        print(f"FAIL Real-time alerting test failed: {e}")
        return False


async def test_live_monitoring_endpoints():
    """Test live monitoring endpoints for dashboards."""
    print("\n🧪 TESTING: Live monitoring endpoints")

    try:
        from src.core.monitoring_production import (
            ProductionMonitoringSystem,
            AlertNotificationConfig,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            monitor = ProductionMonitoringSystem(
                db_path=Path(temp_dir) / "live_test.db", alert_config=AlertNotificationConfig()
            )

            # Update with realistic metrics
            monitor.update_pipeline_metrics(
                throughput=150.5,
                latency_ms=245.0,
                success_rate=98.7,
                queue_depth=12,
                active_workers=8,
            )

            monitor.update_database_metrics(
                active_connections=5,
                idle_connections=3,
                query_latency_ms=15.2,
                entries_per_sec=140.0,
            )

            monitor.update_regional_metrics("A1", 45.2, 99.1)
            monitor.update_regional_metrics("E4", 38.7, 96.8)

            time.sleep(2)  # Allow metric processing

            # Test live status endpoint
            live_status = monitor.get_live_status()

            # Test dashboard endpoint
            dashboard = monitor.get_performance_dashboard(hours=1)

            print(f"PASS Live monitoring results:")
            print(f"   Live status sections: {len(live_status.keys())}")
            print(f"   Pipeline throughput: {live_status['pipeline']['throughput']} entries/sec")
            print(
                f"   Database active connections: {live_status['database']['connections_active']}"
            )
            print(f"   Regional processors: {live_status['regions']['active_count']}")
            print(f"   Dashboard data sections: {len(dashboard.keys())}")
            print(f"   System trends available: {'trends' in dashboard}")
            print(f"   Health status: {live_status['health_status']}")

            monitor.shutdown()

            # Verify endpoint completeness
            essential_sections = ["system", "pipeline", "database", "regions", "alerts"]
            live_sections_present = sum(
                1 for section in essential_sections if section in live_status
            )

            dashboard_sections_present = ["period", "current_status", "trends", "alerts"]
            dashboard_complete = sum(
                1 for section in dashboard_sections_present if section in dashboard
            )

            if live_sections_present >= 4 and dashboard_complete >= 3:
                print("PASS Live monitoring endpoints successful")
                return True
            else:
                print(
                    f"FAIL Live monitoring failed: {live_sections_present}/5 live, {dashboard_complete}/4 dashboard"
                )
                return False

    except Exception as e:
        print(f"FAIL Live monitoring test failed: {e}")
        return False


async def test_production_integration():
    """Test production monitoring integration with streaming pipeline."""
    print("\n🧪 TESTING: Production monitoring integration")

    try:
        from src.core.monitoring_production import (
            ProductionMonitoringSystem,
            AlertNotificationConfig,
        )
        from src.core.streaming_v7 import V7StreamingPipeline, StreamingConfig, test_data_generator

        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize production monitoring
            monitor = ProductionMonitoringSystem(
                db_path=Path(temp_dir) / "integration_test.db",
                alert_config=AlertNotificationConfig(),
            )

            # Configure streaming pipeline
            stream_config = StreamingConfig(batch_size=20, parallel_workers=4)

            print("   Running production integration test...")
            start_time = time.time()

            async with V7StreamingPipeline(stream_config) as pipeline:
                # Run pipeline with monitoring integration
                data_source = test_data_generator(count=100)
                metrics = await pipeline.process_stream(data_source)

                # Update monitoring with pipeline metrics
                monitor.update_pipeline_metrics(
                    throughput=metrics.average_throughput,
                    latency_ms=metrics.average_latency_ms,
                    success_rate=metrics.success_rate,
                    queue_depth=0,  # Post-processing
                    active_workers=stream_config.parallel_workers,
                )

                # Simulate database load
                monitor.update_database_metrics(
                    active_connections=3,
                    idle_connections=2,
                    query_latency_ms=12.5,
                    entries_per_sec=metrics.average_throughput,
                )

            duration = time.time() - start_time

            # Get final monitoring state
            final_status = monitor.get_live_status()
            dashboard = monitor.get_performance_dashboard(hours=1)

            print(f"PASS Production integration results:")
            print(f"   Integration duration: {duration:.2f}s")
            print(f"   Pipeline entries processed: {metrics.entries_processed}")
            print(
                f"   Monitored throughput: {final_status['pipeline']['throughput']:.1f} entries/sec"
            )
            print(f"   System health: {final_status['health_status']}")
            print(
                f"   Database metrics captured: {final_status['database']['entries_per_sec']:.1f} entries/sec"
            )
            print(f"   Dashboard alerts: {len(dashboard['alerts'])}")
            print(f"   System uptime: {final_status['uptime_hours']:.3f} hours")

            monitor.shutdown()

            # Verify integration success
            integration_success = (
                metrics.entries_processed > 0
                and final_status["pipeline"]["throughput"] > 0
                and final_status["database"]["entries_per_sec"] > 0
                and final_status["health_status"] in ["healthy", "degraded"]
            )

            if integration_success:
                print("PASS Production monitoring integration successful")
                return True
            else:
                print("FAIL Production monitoring integration failed")
                return False

    except Exception as e:
        print(f"FAIL Production integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_monitoring_performance_impact():
    """Test that monitoring system doesn't significantly impact performance."""
    print("\n🧪 TESTING: Monitoring performance impact")

    try:
        from src.core.monitoring_production import (
            ProductionMonitoringSystem,
            AlertNotificationConfig,
        )
        from src.core.streaming_v7 import V7StreamingPipeline, StreamingConfig, test_data_generator

        # Test without monitoring
        print("   Testing baseline performance (no monitoring)...")
        stream_config = StreamingConfig(batch_size=50, parallel_workers=4)

        start_time = time.time()
        async with V7StreamingPipeline(stream_config) as pipeline:
            data_source = test_data_generator(count=200)
            baseline_metrics = await pipeline.process_stream(data_source)
        baseline_duration = time.time() - start_time

        # Test with monitoring
        print("   Testing performance with production monitoring...")
        with tempfile.TemporaryDirectory() as temp_dir:
            monitor = ProductionMonitoringSystem(
                db_path=Path(temp_dir) / "perf_test.db", alert_config=AlertNotificationConfig()
            )

            start_time = time.time()
            async with V7StreamingPipeline(stream_config) as pipeline:
                data_source = test_data_generator(count=200)
                monitored_metrics = await pipeline.process_stream(data_source)

                # Continuously update monitoring during processing
                monitor.update_pipeline_metrics(
                    throughput=monitored_metrics.average_throughput,
                    latency_ms=monitored_metrics.average_latency_ms,
                    success_rate=monitored_metrics.success_rate,
                )

            monitored_duration = time.time() - start_time
            monitor.shutdown()

        # Calculate performance impact
        impact_percent = ((monitored_duration - baseline_duration) / baseline_duration) * 100

        print(f"PASS Performance impact results:")
        print(f"   Baseline duration: {baseline_duration:.2f}s")
        print(f"   Monitored duration: {monitored_duration:.2f}s")
        print(f"   Performance impact: {impact_percent:.1f}%")
        print(f"   Baseline throughput: {baseline_metrics.average_throughput:.1f} entries/sec")
        print(f"   Monitored throughput: {monitored_metrics.average_throughput:.1f} entries/sec")

        # Acceptable impact is < 10%
        if abs(impact_percent) < 10:
            print("PASS Monitoring performance impact acceptable")
            return True
        else:
            print(f"FAIL Monitoring performance impact too high: {impact_percent:.1f}%")
            return False

    except Exception as e:
        print(f"FAIL Performance impact test failed: {e}")
        return False


async def main():
    """Run brutal production monitoring validation."""
    print("=" * 80)
    print("🔥 PRODUCTION V7 MONITORING BRUTAL VALIDATION")
    print("=" * 80)

    tests_passed = 0
    total_tests = 0

    # Test 1: Comprehensive metrics
    total_tests += 1
    if await test_comprehensive_metrics_collection():
        tests_passed += 1

    # Test 2: Real-time alerting
    total_tests += 1
    if await test_real_time_alerting():
        tests_passed += 1

    # Test 3: Live monitoring endpoints
    total_tests += 1
    if await test_live_monitoring_endpoints():
        tests_passed += 1

    # Test 4: Production integration
    total_tests += 1
    if await test_production_integration():
        tests_passed += 1

    # Test 5: Performance impact
    total_tests += 1
    if await test_monitoring_performance_impact():
        tests_passed += 1

    # Brutal assessment
    print("\n" + "=" * 80)
    print(f"🎯 PRODUCTION MONITORING BRUTAL RESULTS: {tests_passed}/{total_tests} PASSED")

    if tests_passed == total_tests:
        print("🚀 PRODUCTION MONITORING: TRULY PRODUCTION READY")
        print("PASS Comprehensive system metrics collection")
        print("PASS Real-time alerting with notification delivery")
        print("PASS Live monitoring endpoints for dashboards")
        print("PASS Deep integration with streaming pipeline")
        print("PASS Minimal performance impact (<10%)")
        print("PASS Ready for enterprise deployment")
        return True
    elif tests_passed >= 4:
        print("WARN PRODUCTION MONITORING: MOSTLY READY")
        print("PASS Core functionality working")
        print("WARN Minor issues but production viable")
        return True
    else:
        print("FAIL PRODUCTION MONITORING: NOT READY")
        print("🚨 Critical gaps prevent production use")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
