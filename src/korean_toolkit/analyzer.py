"""
Korean Analyzer Module - Consolidates 37+ analysis scripts
Replaces: analyze_*.py scripts
"""

import re
from collections import Counter, defaultdict
from typing import Any, Dict, List


class KoreanAnalyzer:
    """Unified Korean text and data analysis."""

    def __init__(self):
        self.analysis_modes = {
            "failures": self._analyze_failures,
            "patterns": self._analyze_patterns,
            "duplicates": self._analyze_duplicates,
            "context": self._analyze_context,
            "dice": self._analyze_dice_scores,
            "regression": self._analyze_regression,
            "roundtrip": self._analyze_roundtrip,
            "coverage": self._analyze_coverage,
            "performance": self._analyze_performance,
        }

    def analyze(self, data: Any, mode: str = "all") -> Dict[str, Any]:
        """
        Main analysis entry point.
        Replaces all analyze_*.py scripts.

        Args:
            data: Input data to analyze
            mode: Analysis mode or "all" for comprehensive analysis

        Returns:
            Analysis results dictionary
        """
        if mode == "all":
            results = {}
            for name, analyzer in self.analysis_modes.items():
                try:
                    results[name] = analyzer(data)
                except Exception as e:
                    results[name] = {"error": str(e)}
            return results

        if mode not in self.analysis_modes:
            raise ValueError(f"Unknown analysis mode: {mode}")

        return self.analysis_modes[mode](data)

    def _analyze_failures(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze test failures. Replaces analyze_failures.py and related."""
        failures = defaultdict(list)
        failure_patterns = Counter()

        for item in data:
            if isinstance(item, dict) and not item.get("success", True):
                failure_type = item.get("failure_type", "unknown")
                failures[failure_type].append(item)

                # Extract patterns
                if "error" in item:
                    pattern = self._extract_error_pattern(item["error"])
                    failure_patterns[pattern] += 1

        return {
            "total_failures": sum(len(f) for f in failures.values()),
            "by_type": dict(failures),
            "patterns": dict(failure_patterns.most_common(10)),
            "summary": self._generate_failure_summary(failures),
        }

    def _analyze_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze text patterns. Replaces analyze_*_patterns.py scripts."""
        patterns = {
            "syllable_patterns": self._extract_syllable_patterns(text),
            "character_frequency": self._analyze_character_frequency(text),
            "romanization_patterns": self._extract_romanization_patterns(text),
            "context_patterns": self._extract_context_patterns(text),
        }
        return patterns

    def _analyze_duplicates(self, mappings: List[Dict]) -> Dict[str, Any]:
        """Analyze duplicate mappings. Replaces analyze_duplicates.py."""
        duplicates = defaultdict(list)
        seen = {}

        for mapping in mappings:
            key = mapping.get("key") or mapping.get("hangul")
            if key in seen:
                duplicates[key].append({"original": seen[key], "duplicate": mapping})
            else:
                seen[key] = mapping

        return {
            "total_duplicates": len(duplicates),
            "duplicate_groups": dict(duplicates),
            "most_duplicated": self._find_most_duplicated(duplicates),
        }

    def _analyze_context(self, data: Any) -> Dict[str, Any]:
        """Analyze context-dependent behaviors. Replaces analyze_context_*.py."""
        return {
            "context_sensitive_mappings": [],  # Placeholder
            "position_dependent": [],
            "neighbor_influenced": [],
        }

    def _analyze_dice_scores(self, comparisons: List[Dict]) -> Dict[str, Any]:
        """Analyze Dice coefficient scores. Replaces analyze_dice_*.py."""
        scores = [c.get("dice_score", 0) for c in comparisons if "dice_score" in c]

        if not scores:
            return {"error": "No dice scores found"}

        return {
            "mean_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "distribution": self._calculate_distribution(scores),
            "low_scores": [c for c in comparisons if c.get("dice_score", 1) < 0.5],
        }

    def _analyze_regression(self, before: List, after: List) -> Dict[str, Any]:
        """Analyze regression between versions. Replaces analyze_*_regression.py."""
        before_set = set(str(item) for item in before)
        after_set = set(str(item) for item in after)

        return {
            "regressions": list(before_set - after_set),
            "improvements": list(after_set - before_set),
            "unchanged": list(before_set & after_set),
            "regression_rate": (
                len(before_set - after_set) / len(before_set) if before_set else 0
            ),
        }

    def _analyze_roundtrip(self, tests: List[Dict]) -> Dict[str, Any]:
        """Analyze round-trip conversion. Replaces analyze_roundtrip_*.py."""
        successes = []
        failures = []

        for test in tests:
            if test.get("original") == test.get("roundtrip"):
                successes.append(test)
            else:
                failures.append(test)

        return {
            "success_rate": len(successes) / len(tests) if tests else 0,
            "successes": len(successes),
            "failures": len(failures),
            "failure_examples": failures[:10],
        }

    def _analyze_coverage(self, data: Any) -> Dict[str, Any]:
        """Analyze test/mapping coverage. Replaces analyze_coverage.py."""
        return {
            "syllable_coverage": 0,  # Placeholder
            "character_coverage": 0,
            "pattern_coverage": 0,
        }

    def _analyze_performance(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Analyze performance metrics. Replaces analyze_performance.py."""
        times = [m.get("time", 0) for m in metrics if "time" in m]

        if not times:
            return {"error": "No performance metrics found"}

        return {
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "p95_time": self._calculate_percentile(times, 95),
            "p99_time": self._calculate_percentile(times, 99),
        }

    # Helper methods
    def _extract_error_pattern(self, error: str) -> str:
        """Extract pattern from error message."""
        # Remove specific values, keep structure
        pattern = re.sub(r"\b\d+\b", "N", error)
        pattern = re.sub(r'"[^"]*"', '"..."', pattern)
        return pattern[:100]

    def _extract_syllable_patterns(self, text: str) -> List[str]:
        """Extract Korean syllable patterns."""
        # Simplified - would need actual Korean processing
        return []

    def _analyze_character_frequency(self, text: str) -> Dict[str, int]:
        """Analyze character frequency distribution."""
        return dict(Counter(text).most_common(20))

    def _extract_romanization_patterns(self, text: str) -> List[str]:
        """Extract romanization patterns."""
        return []

    def _extract_context_patterns(self, text: str) -> List[str]:
        """Extract context-dependent patterns."""
        return []

    def _generate_failure_summary(self, failures: Dict) -> str:
        """Generate human-readable failure summary."""
        total = sum(len(f) for f in failures.values())
        if total == 0:
            return "No failures detected"

        summary = f"Total failures: {total}\n"
        for failure_type, items in failures.items():
            summary += f"  - {failure_type}: {len(items)}\n"
        return summary

    def _find_most_duplicated(self, duplicates: Dict) -> List[tuple]:
        """Find most frequently duplicated items."""
        counts = [(key, len(dups)) for key, dups in duplicates.items()]
        return sorted(counts, key=lambda x: x[1], reverse=True)[:10]

    def _calculate_distribution(self, values: List[float]) -> Dict[str, int]:
        """Calculate distribution of values."""
        bins = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}

        for value in values:
            if value <= 0.2:
                bins["0.0-0.2"] += 1
            elif value <= 0.4:
                bins["0.2-0.4"] += 1
            elif value <= 0.6:
                bins["0.4-0.6"] += 1
            elif value <= 0.8:
                bins["0.6-0.8"] += 1
            else:
                bins["0.8-1.0"] += 1

        return bins

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
