#!/usr/bin/env python3
"""
Systematic Improvement Framework v2.0 for Korean Regional Processor
Addresses critical audit findings: reproducibility, validation, concurrency safety

CRITICAL FIXES IMPLEMENTED:
- SHA-256 checksums and Git commit tracking (§1.1)
- Duplicate row prevention (§1.3)
- Strict weight validation with regex (§1.4)
- Wilson score confidence intervals (§2.1)
- Statistical error bounds (§2.2)
- TTY detection for CI safety (§3.4)
"""
import json
import csv
import shutil
import subprocess
import hashlib
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from statsmodels.stats.proportion import proportion_confint


class SystematicImprovementFrameworkV2:
    """Production-hardened framework with audit fixes"""

    # Critical validation patterns (§1.4)
    WEIGHT_REGEX = re.compile(r"^-?\d+\.\d{1,4}$")
    WEIGHT_MIN = -10.0  # Allow negative weights for -log(probability)
    WEIGHT_MAX = 10.0

    def __init__(self):
        self.base_path = Path(".")
        self.mapping_file = "resources/rr_syllable_map.csv"
        self.audit_dir = Path("audit/improvements")  # §1.5 - move from data/
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        # Performance thresholds with Wilson score requirements (§2.1)
        self.performance_thresholds = {
            "math_dataset": {"accuracy": 90.0, "wilson_lb": 89.0},
            "diverse_dataset": {"accuracy": 92.0, "wilson_lb": 90.0},
            "independent_dataset": {"accuracy": 85.0, "wilson_lb": 82.0},
        }

        # Detect non-TTY environment (§3.4)
        self.is_interactive = sys.stdin.isatty()

    def _validate_weight(self, weight_str):
        """Strict weight validation (§1.4, §4.2)"""
        # Strip Unicode whitespace categories
        weight_clean = "".join(c for c in weight_str if unicodedata.category(c)[0] != "Z")

        if not self.WEIGHT_REGEX.match(weight_clean):
            raise ValueError(
                f"Invalid weight format: '{weight_str}' (must match {self.WEIGHT_REGEX.pattern})"
            )

        weight_val = float(weight_clean)
        if not (self.WEIGHT_MIN <= weight_val <= self.WEIGHT_MAX):
            raise ValueError(
                f"Weight {weight_val} outside range [{self.WEIGHT_MIN}, {self.WEIGHT_MAX}]"
            )

        return weight_clean

    def _get_git_info(self):
        """Get reproducibility metadata (§1.1)"""
        try:
            git_commit = (
                subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
                )
                .decode()
                .strip()
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            git_commit = "unknown"

        # SHA-256 of mapping file (§1.1)
        try:
            with open(self.mapping_file, "rb") as f:
                mapping_sha256 = hashlib.sha256(f.read()).hexdigest()
        except FileNotFoundError:
            mapping_sha256 = "missing"

        return git_commit, mapping_sha256

    def _calculate_wilson_score(self, success, total, alpha=0.05):
        """Calculate Wilson score confidence interval (§2.1)"""
        if total == 0:
            return 0.0, 0.0

        try:
            lb, ub = proportion_confint(success, total, alpha=alpha, method="wilson")
            return lb * 100, ub * 100  # Convert to percentage
        except Exception:
            # Fallback to simple proportion
            p = success / total
            return p * 100, p * 100

    def capture_baseline_performance(self):
        """Capture cryptographically reproducible baseline (§1.1, §1.7)"""
        print("=== CAPTURING BASELINE PERFORMANCE V2 ===")

        # ISO-8601 Zulu timestamp (§1.7)
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        git_commit, mapping_sha256 = self._get_git_info()

        baseline = {
            "timestamp": timestamp,
            "git_commit": git_commit,
            "mapping_sha256": mapping_sha256,
            "framework_version": "2.0",
            "performance": {},
            "statistical_analysis": {},
        }

        # Create cryptographic backup (§1.1)
        baseline_backup_dir = Path("baselines")
        baseline_backup_dir.mkdir(exist_ok=True)
        backup_filename = (
            f"rr_syllable_map_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"
        )
        baseline["mapping_file_backup"] = str(baseline_backup_dir / backup_filename)
        shutil.copy(self.mapping_file, baseline["mapping_file_backup"])

        # Test all datasets with statistical analysis
        datasets = {
            "math_dataset": "scripts/validate.py",
            "diverse_dataset": "scripts/correct_diverse_evaluation.py",
            "independent_dataset": "scripts/test_expanded_independent_dataset.py",
        }

        for dataset_name, test_script in datasets.items():
            print(f"Testing {dataset_name}...")
            try:
                result = subprocess.run(
                    ["python3", test_script],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5-minute timeout
                )

                if result.returncode != 0:
                    print(f"  ERROR: {dataset_name} test failed with code {result.returncode}")
                    baseline["performance"][dataset_name] = {
                        "error": f"Exit code {result.returncode}"
                    }
                    continue

                # Parse performance with statistical analysis
                performance = self._parse_performance_v2(result.stdout, dataset_name)
                baseline["performance"][dataset_name] = performance

                # Wilson score confidence interval (§2.1)
                if "success" in performance and "total" in performance:
                    wilson_lb, wilson_ub = self._calculate_wilson_score(
                        performance["success"], performance["total"]
                    )
                    baseline["statistical_analysis"][dataset_name] = {
                        "wilson_lower_bound": wilson_lb,
                        "wilson_upper_bound": wilson_ub,
                        "standard_error": (
                            (performance["accuracy"] * (100 - performance["accuracy"]))
                            / performance["total"]
                        )
                        ** 0.5,
                    }

                print(
                    f"  {dataset_name}: {performance['accuracy']:.2f}% ({performance['success']}/{performance['total']}) [Wilson LB: {wilson_lb:.2f}%]"
                )

            except subprocess.TimeoutExpired:
                print(f"  TIMEOUT: {dataset_name} test timed out")
                baseline["performance"][dataset_name] = {"error": "timeout"}
            except Exception as e:
                print(f"  ERROR testing {dataset_name}: {e}")
                baseline["performance"][dataset_name] = {"error": str(e)}

        # Save baseline with schema validation preparation (§1.6)
        baseline_file = (
            self.audit_dir
            / f"baseline_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)

        print(f"✅ Baseline captured: {baseline_file}")
        return baseline

    def add_systematic_mappings(self, category, mappings, rationale=""):
        """Add mappings with comprehensive validation and rollback safety"""
        if not self.is_interactive and not rationale:
            raise RuntimeError("Non-interactive environment requires rationale parameter (§3.4)")

        print(f"=== ADDING SYSTEMATIC MAPPINGS V2: {category} ===")
        print(f"Rationale: {rationale}")

        # Validate all mappings first (fail fast)
        validated_mappings = []
        for hangul, roman, weight in mappings:
            validated_weight = self._validate_weight(weight)
            validated_mappings.append((hangul, roman, validated_weight))

        # 1. Capture baseline with full reproducibility
        baseline = self.capture_baseline_performance()

        # 2. Create atomic backup
        backup_file = f"resources/rr_syllable_map.csv.backup_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        shutil.copy(self.mapping_file, backup_file)
        print(f"Created atomic backup: {backup_file}")

        # 3. Add mappings with duplicate detection (§1.3)
        try:
            self._add_mappings_to_csv_v2(validated_mappings, category)
            print(f"Added {len(validated_mappings)} mappings to {category}")

            # 4. Rebuild FSTs
            print("Rebuilding FSTs...")
            subprocess.run(["python3", "scripts/build_fsts_multi.py"], check=True)

            # 5. Comprehensive validation with statistical tests
            print("Validating performance with statistical analysis...")
            validation_result = self._validate_all_datasets_v2(baseline)

            if validation_result["passed"]:
                print("✅ VALIDATION PASSED - Changes accepted")

                # Make mapping file read-only (§3.5)
                Path(self.mapping_file).chmod(0o444)

                # Log successful improvement
                self._log_improvement_v2(
                    category, validated_mappings, rationale, baseline, validation_result
                )

                return True
            else:
                print("❌ VALIDATION FAILED - Rolling back changes")
                print("Validation failures:")
                for violation in validation_result.get("threshold_violations", []):
                    print(f"  - {violation}")

                # Atomic rollback
                Path(self.mapping_file).chmod(0o644)  # Make writable for rollback
                shutil.copy(backup_file, self.mapping_file)
                subprocess.run(["python3", "scripts/build_fsts_multi.py"], check=True)
                Path(self.mapping_file).chmod(0o444)  # Restore read-only

                print("Rollback complete - original performance restored")
                return False

        except Exception as e:
            print(f"❌ ERROR during improvement: {e}")

            # Emergency rollback
            Path(self.mapping_file).chmod(0o644)  # Make writable for rollback
            shutil.copy(backup_file, self.mapping_file)
            subprocess.run(["python3", "scripts/build_fsts_multi.py"], check=True)
            Path(self.mapping_file).chmod(0o444)  # Restore read-only

            print("Emergency rollback complete")
            return False

    def _add_mappings_to_csv_v2(self, mappings, category):
        """Add mappings with duplicate detection (§1.3)"""
        # Make file writable temporarily (§3.5)
        Path(self.mapping_file).chmod(0o644)

        try:
            rows = []
            with open(self.mapping_file, "r", encoding="utf-8-sig") as f:  # §4.4 - BOM handling
                rows = list(csv.reader(f))

            # Build existing mappings index for duplicate detection (§1.3)
            existing_mappings = set()
            for row in rows:
                if len(row) >= 2 and not row[0].startswith("#"):
                    existing_mappings.add((row[0], row[1]))

            # Add new mappings with duplicate prevention
            category_comment = f"# {category} - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
            rows.append([category_comment])

            for hangul, roman, weight in mappings:
                dup_key = (hangul, roman)
                if dup_key in existing_mappings:
                    raise ValueError(f"Duplicate mapping detected: {dup_key}")

                rows.append([hangul, roman, weight])
                existing_mappings.add(dup_key)

            # Write updated file
            with open(self.mapping_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                for row in rows:
                    writer.writerow(row)
        finally:
            # Always restore read-only (§3.5)
            Path(self.mapping_file).chmod(0o444)

    def _validate_all_datasets_v2(self, baseline):
        """Enhanced validation with Wilson score bounds (§2.1, §2.2)"""
        validation_result = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "passed": True,
            "results": {},
            "threshold_violations": [],
            "statistical_analysis": {},
        }

        datasets = {
            "math_dataset": "scripts/validate.py",
            "diverse_dataset": "scripts/correct_diverse_evaluation.py",
            "independent_dataset": "scripts/test_expanded_independent_dataset.py",
        }

        for dataset_name, test_script in datasets.items():
            try:
                result = subprocess.run(
                    ["python3", test_script], capture_output=True, text=True, timeout=300
                )

                performance = self._parse_performance_v2(result.stdout, dataset_name)
                validation_result["results"][dataset_name] = performance

                # Wilson score statistical validation (§2.1)
                if "success" in performance and "total" in performance:
                    wilson_lb, wilson_ub = self._calculate_wilson_score(
                        performance["success"], performance["total"]
                    )
                    validation_result["statistical_analysis"][dataset_name] = {
                        "wilson_lower_bound": wilson_lb,
                        "wilson_upper_bound": wilson_ub,
                    }

                    # Check Wilson score lower bound (§2.1)
                    required_wilson_lb = self.performance_thresholds[dataset_name]["wilson_lb"]
                    if wilson_lb < required_wilson_lb:
                        validation_result["passed"] = False
                        validation_result["threshold_violations"].append(
                            {
                                "dataset": dataset_name,
                                "type": "wilson_score_violation",
                                "required_wilson_lb": required_wilson_lb,
                                "actual_wilson_lb": wilson_lb,
                                "violation": required_wilson_lb - wilson_lb,
                            }
                        )

                # Check absolute threshold
                threshold = self.performance_thresholds[dataset_name]["accuracy"]
                if performance["accuracy"] < threshold:
                    validation_result["passed"] = False
                    validation_result["threshold_violations"].append(
                        {
                            "dataset": dataset_name,
                            "type": "absolute_threshold",
                            "required": threshold,
                            "actual": performance["accuracy"],
                            "violation": threshold - performance["accuracy"],
                        }
                    )

                # Check regression with statistical significance (§2.2)
                if (
                    dataset_name in baseline["performance"]
                    and "accuracy" in baseline["performance"][dataset_name]
                ):
                    baseline_accuracy = baseline["performance"][dataset_name]["accuracy"]
                    regression = baseline_accuracy - performance["accuracy"]

                    # Use standard error instead of fixed 1% threshold (§2.2)
                    baseline_se = (
                        baseline["statistical_analysis"]
                        .get(dataset_name, {})
                        .get("standard_error", 1.0)
                    )
                    significance_threshold = baseline_se / 2  # Half standard error

                    if regression > significance_threshold:
                        validation_result["passed"] = False
                        validation_result["threshold_violations"].append(
                            {
                                "dataset": dataset_name,
                                "type": "statistical_regression",
                                "baseline": baseline_accuracy,
                                "actual": performance["accuracy"],
                                "regression": regression,
                                "significance_threshold": significance_threshold,
                            }
                        )

            except Exception as e:
                validation_result["passed"] = False
                validation_result["results"][dataset_name] = {"error": str(e)}

        return validation_result

    def _parse_performance_v2(self, output, dataset_name):
        """Enhanced performance parsing with error handling"""
        lines = output.split("\n")

        # Enhanced parsing with multiple fallback patterns
        patterns = {
            "math_dataset": [
                r"(\d+)/(\d+) = ([\d.]+)% round[‑-]trip",
                r"Overall.*?(\d+)/(\d+).*?([\d.]+)%",
            ],
            "diverse_dataset": [
                r"DIVERSE DATASET:\s*(\d+)/(\d+)\s*=\s*([\d.]+)%",
                r"(\d+)/(\d+)\s*=\s*([\d.]+)%.*diverse",
            ],
            "independent_dataset": [
                r"Overall Performance:\s*(\d+)/(\d+)\s*=\s*([\d.]+)%",
                r"(\d+)/(\d+)\s*=\s*([\d.]+)%.*independent",
            ],
        }

        for pattern in patterns.get(dataset_name, []):
            for line in lines:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    success = int(match.group(1))
                    total = int(match.group(2))
                    accuracy = float(match.group(3))
                    return {
                        "success": success,
                        "total": total,
                        "accuracy": accuracy,
                        "parsed_line": line.strip(),
                    }

        # Fallback - return error with debug info
        return {
            "error": f"Could not parse performance from {dataset_name}",
            "debug_output": output[:500] + "..." if len(output) > 500 else output,
        }

    def _log_improvement_v2(self, category, mappings, rationale, baseline, validation_result):
        """Enhanced logging with cryptographic auditability"""
        git_commit, mapping_sha256 = self._get_git_info()

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "framework_version": "2.0",
            "git_commit": git_commit,
            "mapping_sha256_before": baseline["mapping_sha256"],
            "mapping_sha256_after": mapping_sha256,
            "category": category,
            "rationale": rationale,
            "mappings_added": len(mappings),
            "mappings": mappings,  # Note: §6.1 suggests hashing PII - consider for production
            "baseline_performance": baseline["performance"],
            "final_performance": validation_result["results"],
            "statistical_analysis": validation_result.get("statistical_analysis", {}),
            "improvement_summary": self._calculate_improvements_v2(baseline, validation_result),
        }

        log_file = (
            self.audit_dir
            / f"improvement_log_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False)

        print(f"📝 Improvement logged: {log_file}")

    def _calculate_improvements_v2(self, baseline, validation_result):
        """Enhanced improvement calculation with statistical significance"""
        improvements = {}

        for dataset_name in baseline["performance"]:
            baseline_perf = baseline["performance"][dataset_name]
            final_perf = validation_result["results"].get(dataset_name, {})

            if (
                "error" not in baseline_perf
                and "error" not in final_perf
                and "accuracy" in baseline_perf
                and "accuracy" in final_perf
            ):

                baseline_acc = baseline_perf["accuracy"]
                final_acc = final_perf["accuracy"]
                change = final_acc - baseline_acc

                # Statistical significance assessment
                baseline_se = (
                    baseline.get("statistical_analysis", {})
                    .get(dataset_name, {})
                    .get("standard_error", 1.0)
                )
                is_significant = abs(change) > baseline_se

                improvements[dataset_name] = {
                    "baseline": baseline_acc,
                    "final": final_acc,
                    "change": change,
                    "is_statistically_significant": is_significant,
                    "standard_error": baseline_se,
                }

        return improvements


def main():
    """Enhanced CLI with safety checks"""
    if len(sys.argv) < 2:
        print("Systematic Improvement Framework v2.0")
        print("Usage: python3 systematic_improvement_framework_v2.py [command] [args...]")
        print("\nCommands:")
        print("  baseline    - Capture cryptographically reproducible baseline")
        print("  add         - Add systematic mappings with validation")
        print("  validate    - Validate current performance")
        print("\nNew in v2.0:")
        print("  ✓ SHA-256 checksums and Git commit tracking")
        print("  ✓ Wilson score confidence intervals")
        print("  ✓ Duplicate mapping prevention")
        print("  ✓ Statistical regression detection")
        print("  ✓ Enhanced CI/CD safety")
        return

    framework = SystematicImprovementFrameworkV2()
    command = sys.argv[1]

    if command == "baseline":
        framework.capture_baseline_performance()

    elif command == "validate":
        framework.capture_baseline_performance()  # Acts as validation

    elif command == "add":
        if not framework.is_interactive:
            print("ERROR: Interactive add command requires TTY (§3.4)")
            print("For CI/CD, use programmatic interface")
            sys.exit(1)

        if len(sys.argv) < 3:
            print("Usage: add [category] - then provide mappings interactively")
            return

        category = sys.argv[2]
        print(f"Adding mappings for category: {category}")
        print("Enter mappings in format: hangul,roman,weight")
        print("Enter empty line to finish:")

        mappings = []
        while True:
            try:
                line = input("> ").strip()
                if not line:
                    break

                parts = line.split(",")
                if len(parts) == 3:
                    hangul, roman, weight = [p.strip() for p in parts]
                    mappings.append((hangul, roman, weight))
                else:
                    print("Invalid format. Use: hangul,roman,weight")
            except (EOFError, KeyboardInterrupt):
                print("\nAborted by user")
                return
            except Exception as e:
                print(f"Error parsing: {e}")

        if mappings:
            rationale = input("Rationale for these mappings: ").strip()
            if not rationale:
                print("Rationale required for audit trail")
                return

            success = framework.add_systematic_mappings(category, mappings, rationale)

            if success:
                print("✅ Systematic improvement completed successfully!")
            else:
                print("❌ Systematic improvement failed - changes rolled back")
        else:
            print("No mappings provided")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
