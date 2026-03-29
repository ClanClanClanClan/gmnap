#!/usr/bin/env python3
"""
import pytest
from typing import List
from typing import Optional
from typing import Any
Generate comprehensive test report for GMNAP.
Analyzes test results, coverage, performance metrics, and generates HTML report.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import statistics


class TestReportGenerator:
    """Generate comprehensive test reports."""

    def __init__(self, output_dir: str = "test-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "coverage": {},
            "performance": {},
            "security": {},
            "quality": {},
        }

    def run_tests_with_reporting(self):
        """Run tests and collect reporting data."""
        print("Running comprehensive test suite...")

        # Run tests with XML output
        test_commands = [
            {
                "name": "unit_tests",
                "cmd": [
                    "python",
                    "-m",
                    "pytest",
                    "tests/unit/",
                    "-v",
                    "--junitxml=test-results-unit.xml",
                    "--cov=src",
                    "--cov-report=xml:coverage-unit.xml",
                ],
                "description": "Unit Tests",
            },
            {
                "name": "property_tests",
                "cmd": [
                    "python",
                    "-m",
                    "pytest",
                    "tests/property/",
                    "-v",
                    "--junitxml=test-results-property.xml",
                    "-m",
                    "property",
                ],
                "description": "Property-Based Tests",
            },
            {
                "name": "security_tests",
                "cmd": [
                    "python",
                    "-m",
                    "pytest",
                    "tests/security/",
                    "-v",
                    "--junitxml=test-results-security.xml",
                    "-m",
                    "security",
                ],
                "description": "Security Tests",
            },
            {
                "name": "memory_tests",
                "cmd": [
                    "python",
                    "-m",
                    "pytest",
                    "tests/memory/",
                    "-v",
                    "--junitxml=test-results-memory.xml",
                    "-m",
                    "memory",
                    "--tb=short",
                ],
                "description": "Memory & Performance Tests",
            },
        ]

        results = {}
        for test_config in test_commands:
            print(f"Running {test_config['description']}...")
            try:
                result = subprocess.run(
                    test_config["cmd"],
                    capture_output=True,
                    text=True,
                    timeout=1800,  # 30 minute timeout
                )
                results[test_config["name"]] = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": result.returncode == 0,
                }
                print(
                    f"  {test_config['description']}: {'PASSED' if result.returncode == 0 else 'FAILED'}"
                )
            except subprocess.TimeoutExpired:
                results[test_config["name"]] = {
                    "returncode": -1,
                    "stdout": "",
                    "stderr": "Test timed out",
                    "success": False,
                }
                print(f"  {test_config['description']}: TIMEOUT")
            except Exception as e:
                results[test_config["name"]] = {
                    "returncode": -2,
                    "stdout": "",
                    "stderr": str(e),
                    "success": False,
                }
                print(f"  {test_config['description']}: ERROR - {e}")

        return results

    def parse_junit_xml(self, xml_file: str) -> Dict[str, Any]:
        """Parse JUnit XML test results."""
        xml_path = Path(xml_file)
        if not xml_path.exists():
            return {"error": f"File not found: {xml_file}"}

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Handle different XML structures
            if root.tag == "testsuites":
                testsuite = root.find("testsuite")
            else:
                testsuite = root

            if testsuite is None:
                return {"error": "No testsuite found in XML"}

            stats = {
                "tests": int(testsuite.get("tests", 0)),
                "failures": int(testsuite.get("failures", 0)),
                "errors": int(testsuite.get("errors", 0)),
                "skipped": int(testsuite.get("skipped", 0)),
                "time": float(testsuite.get("time", 0)),
                "success_rate": 0,
            }

            # Calculate success rate
            total_run = stats["tests"] - stats["skipped"]
            if total_run > 0:
                passed = total_run - stats["failures"] - stats["errors"]
                stats["success_rate"] = (passed / total_run) * 100

            # Parse individual test cases
            testcases = []
            for testcase in testsuite.findall("testcase"):
                case = {
                    "name": testcase.get("name"),
                    "classname": testcase.get("classname"),
                    "time": float(testcase.get("time", 0)),
                    "status": "passed",
                }

                if testcase.find("failure") is not None:
                    case["status"] = "failed"
                    case["failure"] = testcase.find("failure").text
                elif testcase.find("error") is not None:
                    case["status"] = "error"
                    case["error"] = testcase.find("error").text
                elif testcase.find("skipped") is not None:
                    case["status"] = "skipped"

                testcases.append(case)

            stats["testcases"] = testcases
            return stats

        except ET.ParseError as e:
            return {"error": f"XML parse error: {e}"}
        except Exception as e:
            return {"error": f"Unexpected error: {e}"}

    def parse_coverage_xml(self, xml_file: str) -> Dict[str, Any]:
        """Parse coverage XML report."""
        xml_path = Path(xml_file)
        if not xml_path.exists():
            return {"error": f"Coverage file not found: {xml_file}"}

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Overall coverage
            coverage = {
                "line_rate": float(root.get("line-rate", 0)) * 100,
                "branch_rate": float(root.get("branch-rate", 0)) * 100,
                "lines_covered": int(root.get("lines-covered", 0)),
                "lines_valid": int(root.get("lines-valid", 0)),
                "branches_covered": int(root.get("branches-covered", 0)),
                "branches_valid": int(root.get("branches-valid", 0)),
                "packages": [],
            }

            # Per-package coverage
            packages = root.find("packages")
            if packages is not None:
                for package in packages.findall("package"):
                    pkg_data = {
                        "name": package.get("name"),
                        "line_rate": float(package.get("line-rate", 0)) * 100,
                        "branch_rate": float(package.get("branch-rate", 0)) * 100,
                        "classes": [],
                    }

                    classes = package.find("classes")
                    if classes is not None:
                        for cls in classes.findall("class"):
                            cls_data = {
                                "name": cls.get("name"),
                                "filename": cls.get("filename"),
                                "line_rate": float(cls.get("line-rate", 0)) * 100,
                                "branch_rate": float(cls.get("branch-rate", 0)) * 100,
                            }
                            pkg_data["classes"].append(cls_data)

                    coverage["packages"].append(pkg_data)

            return coverage

        except ET.ParseError as e:
            return {"error": f"Coverage XML parse error: {e}"}
        except Exception as e:
            return {"error": f"Unexpected coverage error: {e}"}

    def analyze_performance_data(self) -> Dict[str, Any]:
        """Analyze performance test data."""
        # Look for performance data in test outputs
        performance_data = {"benchmarks": [], "memory_usage": {}, "slowest_tests": []}

        # Parse memory test results for performance metrics
        memory_xml = self.parse_junit_xml("test-results-memory.xml")
        if "testcases" in memory_xml:
            test_times = [
                case["time"] for case in memory_xml["testcases"] if case["time"] > 0
            ]
            if test_times:
                performance_data["memory_usage"] = {
                    "avg_test_time": statistics.mean(test_times),
                    "max_test_time": max(test_times),
                    "min_test_time": min(test_times),
                    "total_time": sum(test_times),
                }

                # Identify slowest tests
                slowest = sorted(
                    memory_xml["testcases"], key=lambda x: x["time"], reverse=True
                )[:10]
                performance_data["slowest_tests"] = [
                    {"name": test["name"], "time": test["time"]}
                    for test in slowest
                    if test["time"] > 0
                ]

        return performance_data

    def run_security_analysis(self) -> Dict[str, Any]:
        """Run additional security analysis."""
        security_data = {
            "bandit_results": {},
            "safety_results": {},
            "dependency_scan": {},
        }

        # Run bandit if available
        try:
            result = subprocess.run(
                ["bandit", "-r", "src/", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0 or result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    security_data["bandit_results"] = {
                        "issues_count": len(bandit_data.get("results", [])),
                        "confidence_high": sum(
                            1
                            for r in bandit_data.get("results", [])
                            if r.get("issue_confidence") == "HIGH"
                        ),
                        "severity_high": sum(
                            1
                            for r in bandit_data.get("results", [])
                            if r.get("issue_severity") == "HIGH"
                        ),
                        "severity_medium": sum(
                            1
                            for r in bandit_data.get("results", [])
                            if r.get("issue_severity") == "MEDIUM"
                        ),
                    }
                except json.JSONDecodeError:
                    security_data["bandit_results"] = {
                        "error": "Failed to parse bandit output"
                    }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            security_data["bandit_results"] = {
                "error": "Bandit not available or timed out"
            }

        # Run safety check if available
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.stdout:
                try:
                    safety_data = json.loads(result.stdout)
                    security_data["safety_results"] = {
                        "vulnerabilities": len(safety_data),
                        "high_severity": sum(
                            1
                            for v in safety_data
                            if v.get("advisory", {}).get("severity") == "high"
                        ),
                    }
                except json.JSONDecodeError:
                    security_data["safety_results"] = {"vulnerabilities": 0}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            security_data["safety_results"] = {"error": "Safety not available"}

        return security_data

    def analyze_code_quality(self) -> Dict[str, Any]:
        """Analyze code quality metrics."""
        quality_data = {"complexity": {}, "style": {}, "documentation": {}}

        # Count lines of code
        try:
            src_files = list(Path("src").rglob("*.py"))
            test_files = list(Path("tests").rglob("*.py"))

            src_lines = 0
            test_lines = 0

            for file in src_files:
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        src_lines += len(f.readlines())
                except Exception:
                    pass

            for file in test_files:
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        test_lines += len(f.readlines())
                except Exception:
                    pass

            quality_data["complexity"] = {
                "src_files": len(src_files),
                "test_files": len(test_files),
                "src_lines": src_lines,
                "test_lines": test_lines,
                "test_ratio": test_lines / src_lines if src_lines > 0 else 0,
            }

        except Exception as e:
            quality_data["complexity"] = {"error": str(e)}

        return quality_data

    def generate_html_report(self) -> str:
        """Generate HTML test report."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GMNAP Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
        .metric.success { color: #27ae60; }
        .metric.warning { color: #f39c12; }
        .metric.danger { color: #e74c3c; }
        .progress { width: 100%; height: 20px; background-color: #ecf0f1; border-radius: 10px; overflow: hidden; }
        .progress-bar { height: 100%; transition: width 0.3s ease; }
        .progress-bar.success { background-color: #27ae60; }
        .progress-bar.warning { background-color: #f39c12; }
        .progress-bar.danger { background-color: #e74c3c; }
        .details { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #34495e; color: white; }
        .status-passed { color: #27ae60; font-weight: bold; }
        .status-failed { color: #e74c3c; font-weight: bold; }
        .status-error { color: #e67e22; font-weight: bold; }
        .status-skipped { color: #95a5a6; }
        .timestamp { color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 GMNAP Test Report</h1>
        <p class="timestamp">Generated: {timestamp}</p>
    </div>
    
    <div class="summary">
        <div class="card">
            <h3>📊 Test Summary</h3>
            <div class="metric {overall_status}">{total_tests}</div>
            <p>Total Tests</p>
            <div class="progress">
                <div class="progress-bar {overall_status}" style="width: {success_percentage}%"></div>
            </div>
            <p>{passed_tests} passed, {failed_tests} failed</p>
        </div>
        
        <div class="card">
            <h3>📈 Coverage</h3>
            <div class="metric {coverage_status}">{coverage_percentage}%</div>
            <p>Line Coverage</p>
            <div class="progress">
                <div class="progress-bar {coverage_status}" style="width: {coverage_percentage}%"></div>
            </div>
            <p>{lines_covered} of {lines_total} lines covered</p>
        </div>
        
        <div class="card">
            <h3>🔒 Security</h3>
            <div class="metric {security_status}">{security_issues}</div>
            <p>Security Issues</p>
            <p>{security_summary}</p>
        </div>
        
        <div class="card">
            <h3>⚡ Performance</h3>
            <div class="metric">{avg_test_time}s</div>
            <p>Average Test Time</p>
            <p>Total: {total_test_time}s</p>
        </div>
    </div>
    
    <div class="details">
        <h3>📋 Test Results Details</h3>
        {test_details_tables}
    </div>
    
    <div class="details">
        <h3>📊 Coverage Details</h3>
        {coverage_details}
    </div>
    
    <div class="details">
        <h3>🐌 Slowest Tests</h3>
        {slowest_tests_table}
    </div>
    
    <div class="details">
        <h3>🔍 Code Quality Metrics</h3>
        {quality_metrics}
    </div>
</body>
</html>
        """

        # Calculate summary metrics
        summary = self.report_data["summary"]
        total_tests = summary.get("total_tests", 0)
        passed_tests = summary.get("passed_tests", 0)
        failed_tests = summary.get("failed_tests", 0)

        success_percentage = (
            (passed_tests / total_tests * 100) if total_tests > 0 else 0
        )
        overall_status = (
            "success"
            if success_percentage >= 90
            else "warning" if success_percentage >= 70 else "danger"
        )

        coverage = self.report_data["coverage"]
        coverage_percentage = coverage.get("line_rate", 0)
        coverage_status = (
            "success"
            if coverage_percentage >= 80
            else "warning" if coverage_percentage >= 60 else "danger"
        )

        # Format the HTML
        html_content = html_template.format(
            timestamp=self.report_data["timestamp"],
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_percentage=success_percentage,
            overall_status=overall_status,
            coverage_percentage=f"{coverage_percentage:.1f}",
            coverage_status=coverage_status,
            lines_covered=coverage.get("lines_covered", 0),
            lines_total=coverage.get("lines_valid", 0),
            security_issues=self.report_data["security"].get("total_issues", 0),
            security_status=(
                "success"
                if self.report_data["security"].get("total_issues", 0) == 0
                else "danger"
            ),
            security_summary=self.report_data["security"].get(
                "summary", "No issues found"
            ),
            avg_test_time=f"{self.report_data['performance'].get('avg_test_time', 0):.2f}",
            total_test_time=f"{self.report_data['performance'].get('total_time', 0):.2f}",
            test_details_tables=self._generate_test_details_tables(),
            coverage_details=self._generate_coverage_details(),
            slowest_tests_table=self._generate_slowest_tests_table(),
            quality_metrics=self._generate_quality_metrics(),
        )

        return html_content

    def _generate_test_details_tables(self) -> str:
        """Generate test details tables."""
        tables = []

        for test_type, data in self.report_data["summary"].get("by_type", {}).items():
            if "testcases" in data:
                table = f"<h4>{test_type.replace('_', ' ').title()}</h4>"
                table += "<table><tr><th>Test Name</th><th>Class</th><th>Time (s)</th><th>Status</th></tr>"

                for case in data["testcases"][:50]:  # Limit to 50 tests per type
                    status_class = f"status-{case['status']}"
                    table += f"""
                    <tr>
                        <td>{case['name']}</td>
                        <td>{case.get('classname', '')}</td>
                        <td>{case['time']:.3f}</td>
                        <td class="{status_class}">{case['status'].upper()}</td>
                    </tr>
                    """

                table += "</table>"
                tables.append(table)

        return "".join(tables)

    def _generate_coverage_details(self) -> str:
        """Generate coverage details."""
        coverage = self.report_data["coverage"]
        if "packages" not in coverage:
            return "<p>No coverage details available.</p>"

        table = "<table><tr><th>Package</th><th>Line Coverage</th><th>Branch Coverage</th></tr>"

        for package in coverage["packages"]:
            table += f"""
            <tr>
                <td>{package['name']}</td>
                <td>{package['line_rate']:.1f}%</td>
                <td>{package['branch_rate']:.1f}%</td>
            </tr>
            """

        table += "</table>"
        return table

    def _generate_slowest_tests_table(self) -> str:
        """Generate slowest tests table."""
        slowest = self.report_data["performance"].get("slowest_tests", [])
        if not slowest:
            return "<p>No performance data available.</p>"

        table = "<table><tr><th>Test Name</th><th>Time (s)</th></tr>"

        for test in slowest:
            table += f"""
            <tr>
                <td>{test['name']}</td>
                <td>{test['time']:.3f}</td>
            </tr>
            """

        table += "</table>"
        return table

    def _generate_quality_metrics(self) -> str:
        """Generate quality metrics section."""
        quality = self.report_data["quality"]
        complexity = quality.get("complexity", {})

        if "error" in complexity:
            return f"<p>Error gathering quality metrics: {complexity['error']}</p>"

        return f"""
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Source Files</td><td>{complexity.get('src_files', 0)}</td></tr>
            <tr><td>Test Files</td><td>{complexity.get('test_files', 0)}</td></tr>
            <tr><td>Source Lines</td><td>{complexity.get('src_lines', 0)}</td></tr>
            <tr><td>Test Lines</td><td>{complexity.get('test_lines', 0)}</td></tr>
            <tr><td>Test/Source Ratio</td><td>{complexity.get('test_ratio', 0):.2f}</td></tr>
        </table>
        """

    def generate_report(self) -> str:
        """Generate complete test report."""
        print("Generating comprehensive test report...")

        # Run tests and collect data
        test_results = self.run_tests_with_reporting()

        # Parse test results
        test_files = {
            "unit_tests": "test-results-unit.xml",
            "property_tests": "test-results-property.xml",
            "security_tests": "test-results-security.xml",
            "memory_tests": "test-results-memory.xml",
        }

        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        by_type = {}

        for test_type, xml_file in test_files.items():
            data = self.parse_junit_xml(xml_file)
            if "error" not in data:
                by_type[test_type] = data
                total_tests += data["tests"]
                passed_tests += (
                    data["tests"] - data["failures"] - data["errors"] - data["skipped"]
                )
                failed_tests += data["failures"] + data["errors"]

        self.report_data["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (
                (passed_tests / total_tests * 100) if total_tests > 0 else 0
            ),
            "by_type": by_type,
        }

        # Parse coverage
        coverage_data = self.parse_coverage_xml("coverage-unit.xml")
        if "error" not in coverage_data:
            self.report_data["coverage"] = coverage_data

        # Analyze performance
        self.report_data["performance"] = self.analyze_performance_data()

        # Run security analysis
        self.report_data["security"] = self.run_security_analysis()

        # Analyze code quality
        self.report_data["quality"] = self.analyze_code_quality()

        # Generate HTML report
        html_content = self.generate_html_report()

        # Save report
        report_file = self.output_dir / "test-report.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Save JSON data
        json_file = self.output_dir / "test-data.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.report_data, f, indent=2)

        print(f"Test report generated: {report_file}")
        print(f"Test data saved: {json_file}")

        return str(report_file)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate GMNAP test report")
    parser.add_argument(
        "--output-dir", default="test-reports", help="Output directory for reports"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests, use existing results",
    )

    args = parser.parse_args()

    generator = TestReportGenerator(args.output_dir)

    if args.skip_tests:
        print("Skipping test execution, using existing results...")
        # Just generate report from existing files
        generator.report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {"total_tests": 0, "passed_tests": 0, "failed_tests": 0},
            "coverage": {},
            "performance": {},
            "security": {},
            "quality": {},
        }

    try:
        report_file = generator.generate_report()
        print(f"\nPASS Test report successfully generated: {report_file}")

        # Print summary
        summary = generator.report_data["summary"]
        if summary.get("total_tests", 0) > 0:
            print(f"\n📊 Summary:")
            print(f"   Total Tests: {summary['total_tests']}")
            print(f"   Passed: {summary['passed_tests']}")
            print(f"   Failed: {summary['failed_tests']}")
            print(f"   Success Rate: {summary.get('success_rate', 0):.1f}%")

            if summary["failed_tests"] > 0:
                print(
                    f"\nWARN  {summary['failed_tests']} tests failed. Please review the detailed report."
                )
                sys.exit(1)
            else:
                print(f"\n🎉 All tests passed!")

    except Exception as e:
        print(f"FAIL Error generating test report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
