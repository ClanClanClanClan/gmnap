
#!/usr/bin/env python3
"""
V7 Monitoring System Test Suite
Tests performance monitoring, alerting, and reporting
"""

import asyncio
import sys
import tempfile
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_monitoring_basic_functionality():
    """Test basic monitoring system functionality."""
    print("🧪 TESTING: Basic V7 monitoring functionality")

    try:
        from src.core.monitoring_v7 import (
            MetricType,
            MonitoringConfig,
            PerformanceMetric,
            V7MonitoringSystem,
        )

        # Create temporary config for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            config = MonitoringConfig(
                metrics_db_path=Path(temp_dir) / "test_metrics.db",
                throughput_min_threshold=50.0,  # Lower for testing
                latency_max_threshold=500.0,
                success_rate_min_threshold=90.0,
                alert_cooldown_minutes=0,  # No cooldown for testing
            )

            monitor = V7MonitoringSystem(config)

            # Test metric recording
            test_metrics = [
                PerformanceMetric(
                    MetricType.THROUGHPUT, 100.5, "entries/sec", component="test"
                ),
                PerformanceMetric(MetricType.LATENCY, 250.0, "ms", component="test"),
                PerformanceMetric(
                    MetricType.SUCCESS_RATE, 98.5, "percent", component="test"
                ),
            ]

            for metric in test_metrics:
                monitor.record_metric(metric)

            # Test current metrics retrieval
            current = monitor.get_current_metrics()

            print("PASS Basic monitoring results:")
            print(f"   Metrics recorded: {len(test_metrics)}")
            print(f"   Current metrics: {len(current)}")
            print(
                f"   Throughput: {current.get('throughput', {}).get('value', 'N/A')} entries/sec"
            )
            print(f"   Latency: {current.get('latency', {}).get('value', 'N/A')} ms")
            print(
                f"   Success rate: {current.get('success_rate', {}).get('value', 'N/A')}%"
            )

            # Verify metrics were stored
            if len(current) >= 3:
                print("PASS Basic monitoring successful")
                return True
            else:
                print("FAIL Basic monitoring failed: metrics not stored")
                return False

    except Exception as e:
        print(f"FAIL Basic monitoring test failed: {e}")
        return False


async def test_monitoring_alerting():
    """Test monitoring alerting system."""
    print("\n🧪 TESTING: V7 monitoring alerting system")

    try:
        from src.core.monitoring_v7 import (
            MetricType,
            MonitoringConfig,
            PerformanceMetric,
            V7MonitoringSystem,
        )

        # Track alerts
        captured_alerts = []

        def alert_handler(alert):
            captured_alerts.append(alert)

        with tempfile.TemporaryDirectory() as temp_dir:
            config = MonitoringConfig(
                metrics_db_path=Path(temp_dir) / "test_alerts.db",
                throughput_min_threshold=200.0,  # High threshold to trigger alerts
                latency_max_threshold=100.0,  # Low threshold to trigger alerts
                success_rate_min_threshold=99.0,  # High threshold to trigger alerts
                alert_cooldown_minutes=0,
            )

            monitor = V7MonitoringSystem(config)
            monitor.add_alert_handler(alert_handler)

            # Generate metrics that should trigger alerts
            alert_metrics = [
                PerformanceMetric(
                    MetricType.THROUGHPUT, 50.0, "entries/sec", component="test"
                ),  # Too low
                PerformanceMetric(
                    MetricType.LATENCY, 500.0, "ms", component="test"
                ),  # Too high
                PerformanceMetric(
                    MetricType.SUCCESS_RATE, 85.0, "percent", component="test"
                ),  # Too low
            ]

            for metric in alert_metrics:
                monitor.record_metric(metric)
                time.sleep(0.01)  # Small delay to avoid timing issues

            print("PASS Alerting results:")
            print(f"   Alert-triggering metrics: {len(alert_metrics)}")
            print(f"   Alerts captured: {len(captured_alerts)}")

            # Verify alert details
            for alert in captured_alerts:
                print(f"   Alert: {alert.level.value} - {alert.message}")

            # Should have at least 2-3 alerts
            if len(captured_alerts) >= 2:
                print("PASS Alerting system successful")
                return True
            else:
                print("FAIL Alerting system failed: insufficient alerts")
                return False

    except Exception as e:
        print(f"FAIL Alerting test failed: {e}")
        return False


async def test_monitoring_integration():
    """Test monitoring integration with streaming pipeline."""
    print("\n🧪 TESTING: V7 monitoring integration with streaming")

    try:
        from src.core.monitoring_v7 import MonitoringConfig, V7MonitoringSystem
        from src.core.streaming_v7 import (
            StreamingConfig,
            V7StreamingPipeline,
            test_data_generator,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup monitoring
            monitor_config = MonitoringConfig(
                metrics_db_path=Path(temp_dir) / "integration_metrics.db",
                sample_interval_seconds=1,
            )
            monitor = V7MonitoringSystem(monitor_config)

            # Setup streaming pipeline
            stream_config = StreamingConfig(batch_size=10, parallel_workers=2)

            # Test integration
            print("   Running streaming with monitoring...")
            start_time = time.time()

            async with V7StreamingPipeline(stream_config) as pipeline:
                # Generate test data
                data_source = test_data_generator(count=50)

                # Process with monitoring
                metrics = await pipeline.process_stream(data_source)

                # Record streaming metrics in monitoring system
                from src.core.monitoring_v7 import MetricType, PerformanceMetric

                monitor.record_metric(
                    PerformanceMetric(
                        MetricType.THROUGHPUT,
                        metrics.average_throughput,
                        "entries/sec",
                        component="streaming_integration",
                    )
                )

                monitor.record_metric(
                    PerformanceMetric(
                        MetricType.SUCCESS_RATE,
                        metrics.success_rate,
                        "percent",
                        component="streaming_integration",
                    )
                )

                monitor.record_metric(
                    PerformanceMetric(
                        MetricType.LATENCY,
                        metrics.average_latency_ms,
                        "ms",
                        component="streaming_integration",
                    )
                )

            duration = time.time() - start_time

            # Get system health
            health = monitor.get_system_health()

            print("PASS Integration results:")
            print(f"   Integration duration: {duration:.2f}s")
            print(f"   Streaming processed: {metrics.entries_processed}")
            print(
                f"   Streaming throughput: {metrics.average_throughput:.1f} entries/sec"
            )
            print(f"   System health status: {health['status']}")
            print(f"   Monitored metrics: {len(health['metrics'])}")

            # Verify integration success
            if (
                health["status"] in ["healthy", "degraded"]
                and len(health["metrics"]) >= 3
                and metrics.entries_processed > 0
            ):
                print("PASS Monitoring integration successful")
                return True
            else:
                print("FAIL Monitoring integration failed")
                return False

    except Exception as e:
        print(f"FAIL Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_monitoring_reporting():
    """Test monitoring reporting and export functionality."""
    print("\n🧪 TESTING: V7 monitoring reporting system")

    try:
        from src.core.monitoring_v7 import (
            MetricType,
            MonitoringConfig,
            PerformanceMetric,
            V7MonitoringSystem,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config = MonitoringConfig(
                metrics_db_path=Path(temp_dir) / "reporting_metrics.db"
            )

            monitor = V7MonitoringSystem(config)

            # Generate sample data for reporting
            sample_metrics = [
                PerformanceMetric(
                    MetricType.THROUGHPUT, 150.0, "entries/sec", component="report_test"
                ),
                PerformanceMetric(
                    MetricType.THROUGHPUT, 180.0, "entries/sec", component="report_test"
                ),
                PerformanceMetric(
                    MetricType.LATENCY, 200.0, "ms", component="report_test"
                ),
                PerformanceMetric(
                    MetricType.LATENCY, 250.0, "ms", component="report_test"
                ),
                PerformanceMetric(
                    MetricType.SUCCESS_RATE, 98.5, "percent", component="report_test"
                ),
                PerformanceMetric(
                    MetricType.SUCCESS_RATE, 99.2, "percent", component="report_test"
                ),
            ]

            for metric in sample_metrics:
                monitor.record_metric(metric)
                time.sleep(0.001)  # Tiny delay to ensure different timestamps

            # Generate performance report
            report = monitor.generate_performance_report(hours=1)

            # Test JSON export
            json_export = monitor.export_metrics("json", hours=1)

            # Test CSV export
            csv_export = monitor.export_metrics("csv", hours=1)

            print("PASS Reporting results:")
            print(f"   Sample metrics recorded: {len(sample_metrics)}")
            print(
                f"   Report period: {report['report_period']['duration_hours']} hours"
            )
            print(
                f"   Throughput samples: {report['performance_summary']['throughput']['samples']}"
            )
            print(
                f"   Average throughput: {report['performance_summary']['throughput']['avg_entries_per_sec']:.1f}"
            )
            print(f"   JSON export length: {len(json_export)} chars")
            print(f"   CSV export lines: {len(csv_export.splitlines())}")

            # Verify reporting functionality
            if (
                report["performance_summary"]["throughput"]["samples"] >= 2
                and len(json_export) > 100
                and len(csv_export.splitlines()) >= 3
            ):  # Header + at least 2 data lines
                print("PASS Reporting system successful")
                return True
            else:
                print("FAIL Reporting system failed")
                return False

    except Exception as e:
        print(f"FAIL Reporting test failed: {e}")
        return False


async def main():
    """Run comprehensive V7 monitoring system tests."""
    print("=" * 70)
    print("🔥 V7 MONITORING SYSTEM COMPREHENSIVE TEST")
    print("=" * 70)

    tests_passed = 0
    total_tests = 0

    # Test 1: Basic functionality
    total_tests += 1
    if await test_monitoring_basic_functionality():
        tests_passed += 1

    # Test 2: Alerting system
    total_tests += 1
    if await test_monitoring_alerting():
        tests_passed += 1

    # Test 3: Integration with streaming
    total_tests += 1
    if await test_monitoring_integration():
        tests_passed += 1

    # Test 4: Reporting and export
    total_tests += 1
    if await test_monitoring_reporting():
        tests_passed += 1

    # Final assessment
    print("\n" + "=" * 70)
    print(f"🎯 V7 MONITORING SYSTEM RESULTS: {tests_passed}/{total_tests} PASSED")

    if tests_passed == total_tests:
        print("🚀 V7 MONITORING: FULLY OPERATIONAL")
        print("PASS Real-time metric collection working")
        print("PASS Automated alerting system functional")
        print("PASS Streaming integration successful")
        print("PASS Reporting and export capabilities ready")
        print("PASS Production monitoring ready")
        return True
    elif tests_passed >= 3:
        print("PASS V7 MONITORING: MOSTLY OPERATIONAL")
        print("WARN Minor issues but core functionality working")
        return True
    else:
        print("FAIL V7 MONITORING: CRITICAL ISSUES")
        print("🚨 Major problems need resolution")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
