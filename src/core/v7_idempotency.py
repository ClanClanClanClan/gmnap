"""
V7 Idempotency Checker - Ensures 0-byte idempotency per V7 specification.

V7 Requirement: Same input must produce bit-identical output on repeated processing.
"""

import copy
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class IdempotencyResult:
    """Result of idempotency check."""

    is_idempotent: bool
    hash_first: str
    hash_second: str
    differences: List[Dict[str, Any]]
    byte_difference: int
    processing_time_ms: int


class V7IdempotencyChecker:
    """
    V7 Idempotency Checker - Ensures 0-byte idempotency.

    Per V7 specification:
    - Same input must produce identical output (0-byte difference)
    - Processing must be deterministic
    - All transformations must be reproducible
    """

    def __init__(self):
        self.logger = logger

    def check_idempotency(
        self, entries: List[Dict[str, Any]], pipeline_func: callable
    ) -> IdempotencyResult:
        """
        Check if processing is idempotent (0-byte difference).

        Args:
            entries: Input entries to process
            pipeline_func: Pipeline processing function

        Returns:
            IdempotencyResult with verification details
        """
        start_time = datetime.now()

        # Deep copy to ensure independent processing
        entries_copy1 = copy.deepcopy(entries)
        entries_copy2 = copy.deepcopy(entries)

        # First processing pass
        processed_first = pipeline_func(entries_copy1)
        canonical_first = self._canonicalize_entries(processed_first)
        hash_first = self._compute_hash(canonical_first)

        # Second processing pass (must be identical)
        processed_second = pipeline_func(entries_copy2)
        canonical_second = self._canonicalize_entries(processed_second)
        hash_second = self._compute_hash(canonical_second)

        # Find differences if any
        differences = self._find_differences(canonical_first, canonical_second)

        # Calculate byte difference
        bytes_first = canonical_first.encode("utf-8")
        bytes_second = canonical_second.encode("utf-8")
        byte_difference = len(bytes_first) - len(bytes_second)
        if byte_difference == 0 and bytes_first != bytes_second:
            # Same length but different content
            byte_difference = sum(
                1 for a, b in zip(bytes_first, bytes_second) if a != b
            )

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return IdempotencyResult(
            is_idempotent=(hash_first == hash_second),
            hash_first=hash_first,
            hash_second=hash_second,
            differences=differences,
            byte_difference=abs(byte_difference),
            processing_time_ms=processing_time,
        )

    def _canonicalize_entries(self, entries: List[Dict[str, Any]]) -> str:
        """
        Create canonical representation of entries for hashing.

        Args:
            entries: Processed entries

        Returns:
            Canonical JSON string representation
        """
        # Remove non-deterministic fields
        canonical_entries = []

        for entry in entries:
            canonical_entry = copy.deepcopy(entry)

            # Remove fields that may vary between runs
            fields_to_remove = [
                "_timing",  # Processing timing metadata
                "_cache_hit",  # Cache hit information
                "_processing_id",  # Unique processing ID
                "_timestamp",  # Processing timestamp
            ]

            for field in fields_to_remove:
                canonical_entry.pop(field, None)

            # Sort dictionary keys for consistent ordering
            canonical_entry = self._sort_dict(canonical_entry)
            canonical_entries.append(canonical_entry)

        # Sort entries by GlobalID for consistent ordering
        canonical_entries.sort(key=lambda x: x.get("GlobalID", ""))

        # Create deterministic JSON representation
        return json.dumps(canonical_entries, sort_keys=True, separators=(",", ":"))

    def _sort_dict(self, d: Any) -> Any:
        """
        Recursively sort dictionary keys for deterministic output.

        Args:
            d: Dictionary or value to sort

        Returns:
            Sorted dictionary or original value
        """
        if isinstance(d, dict):
            return {k: self._sort_dict(v) for k, v in sorted(d.items())}
        elif isinstance(d, list):
            return [self._sort_dict(v) for v in d]
        else:
            return d

    def _compute_hash(self, canonical_str: str) -> str:
        """
        Compute SHA-256 hash of canonical representation.

        Args:
            canonical_str: Canonical JSON string

        Returns:
            Hex digest of SHA-256 hash
        """
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def _find_differences(
        self, canonical1: str, canonical2: str
    ) -> List[Dict[str, Any]]:
        """
        Find differences between two canonical representations.

        Args:
            canonical1: First canonical representation
            canonical2: Second canonical representation

        Returns:
            List of differences found
        """
        differences = []

        if canonical1 == canonical2:
            return differences

        try:
            data1 = json.loads(canonical1)
            data2 = json.loads(canonical2)

            # Check entry count
            if len(data1) != len(data2):
                differences.append(
                    {
                        "type": "count_mismatch",
                        "first": len(data1),
                        "second": len(data2),
                    }
                )

            # Compare entries by GlobalID
            entries1_by_id = {e.get("GlobalID", ""): e for e in data1}
            entries2_by_id = {e.get("GlobalID", ""): e for e in data2}

            # Check for missing entries
            missing_in_second = set(entries1_by_id.keys()) - set(entries2_by_id.keys())
            missing_in_first = set(entries2_by_id.keys()) - set(entries1_by_id.keys())

            if missing_in_second:
                differences.append(
                    {"type": "missing_in_second", "global_ids": list(missing_in_second)}
                )

            if missing_in_first:
                differences.append(
                    {"type": "missing_in_first", "global_ids": list(missing_in_first)}
                )

            # Compare common entries
            common_ids = set(entries1_by_id.keys()) & set(entries2_by_id.keys())
            for global_id in common_ids:
                entry1 = entries1_by_id[global_id]
                entry2 = entries2_by_id[global_id]

                if entry1 != entry2:
                    # Find field differences
                    field_diffs = self._compare_entries(entry1, entry2)
                    if field_diffs:
                        differences.append(
                            {
                                "type": "field_mismatch",
                                "global_id": global_id,
                                "fields": field_diffs,
                            }
                        )

        except json.JSONDecodeError as e:
            differences.append({"type": "json_error", "error": str(e)})

        return differences

    def _compare_entries(
        self, entry1: Dict[str, Any], entry2: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Compare two entries field by field.

        Args:
            entry1: First entry
            entry2: Second entry

        Returns:
            List of field differences
        """
        field_diffs = []

        all_keys = set(entry1.keys()) | set(entry2.keys())

        for key in all_keys:
            val1 = entry1.get(key)
            val2 = entry2.get(key)

            if val1 != val2:
                field_diffs.append({"field": key, "first": val1, "second": val2})

        return field_diffs

    def verify_pipeline_idempotency(self, pipeline) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify complete pipeline idempotency with test data.

        Args:
            pipeline: Pipeline instance to test

        Returns:
            Tuple of (is_idempotent, details)
        """
        # Test data covering various edge cases
        test_entries = [
            {
                "CanonicalLatin": "John Smith",
                "CanonicalNative": None,
                "DetectedRegion": "A1",
                "GlobalID": "TEST001",
            },
            {
                "CanonicalLatin": "Marie Curie",
                "CanonicalNative": "Maria Skłodowska",
                "DetectedRegion": "B2",
                "GlobalID": "TEST002",
            },
            {
                "CanonicalLatin": "Kim Min-jun",
                "CanonicalNative": "김민준",
                "DetectedRegion": "E4",
                "GlobalID": "TEST003",
            },
            {
                "CanonicalLatin": "José María de la Cruz-Sánchez",
                "CanonicalNative": None,
                "DetectedRegion": "G1",
                "GlobalID": "TEST004",
            },
            {
                "CanonicalLatin": "Test\tName",  # Tab character
                "CanonicalNative": None,
                "DetectedRegion": "A1",
                "GlobalID": "TEST005",
            },
        ]

        # Define pipeline processing function
        def process_batch(entries):
            processed = []
            for entry in entries:
                result = pipeline.process(copy.deepcopy(entry))
                processed.append(result)
            return processed

        # Check idempotency
        result = self.check_idempotency(test_entries, process_batch)

        # Prepare detailed report
        details = {
            "is_idempotent": result.is_idempotent,
            "hash_match": result.hash_first == result.hash_second,
            "byte_difference": result.byte_difference,
            "processing_time_ms": result.processing_time_ms,
            "test_entries_count": len(test_entries),
            "differences_found": len(result.differences),
            "hash_first": result.hash_first[:16] + "...",  # Truncated for readability
            "hash_second": result.hash_second[:16] + "...",
        }

        if result.differences:
            details["first_difference"] = result.differences[0]

        # Log results
        if result.is_idempotent:
            self.logger.info("✅ Pipeline is idempotent (0-byte difference)")
        else:
            self.logger.error(
                f"❌ Pipeline is NOT idempotent ({result.byte_difference} byte difference)"
            )
            self.logger.error(
                f"Differences found: {result.differences[:3]}"
            )  # First 3 differences

        return result.is_idempotent, details

    def check_single_entry_idempotency(
        self, entry: Dict[str, Any], processor_func: callable, iterations: int = 5
    ) -> bool:
        """
        Check if single entry processing is idempotent over multiple iterations.

        Args:
            entry: Entry to process
            processor_func: Processing function
            iterations: Number of iterations to test

        Returns:
            True if all iterations produce identical output
        """
        results = []

        for i in range(iterations):
            entry_copy = copy.deepcopy(entry)
            processed = processor_func(entry_copy)
            canonical = self._canonicalize_entries([processed])
            hash_val = self._compute_hash(canonical)
            results.append(hash_val)

        # All hashes should be identical
        is_idempotent = len(set(results)) == 1

        if not is_idempotent:
            self.logger.warning(
                f"Entry processing not idempotent: {len(set(results))} different outputs in {iterations} iterations"
            )

        return is_idempotent


def create_idempotency_report(
    checker: V7IdempotencyChecker,
    pipeline,
    test_entries: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Create comprehensive idempotency report for V7 compliance.

    Args:
        checker: V7IdempotencyChecker instance
        pipeline: Pipeline to test
        test_entries: Optional test entries (uses defaults if None)

    Returns:
        Comprehensive idempotency report
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "v7_requirement": "0-byte idempotency",
        "tests": {},
    }

    # Test pipeline idempotency
    is_idempotent, details = checker.verify_pipeline_idempotency(pipeline)
    report["tests"]["pipeline_idempotency"] = details

    # Test with custom entries if provided
    if test_entries:

        def process_batch(entries):
            return [pipeline.process(copy.deepcopy(e)) for e in entries]

        custom_result = checker.check_idempotency(test_entries, process_batch)
        report["tests"]["custom_entries"] = {
            "is_idempotent": custom_result.is_idempotent,
            "byte_difference": custom_result.byte_difference,
            "entry_count": len(test_entries),
        }

    # Overall compliance
    all_idempotent = all(
        test.get("is_idempotent", False) for test in report["tests"].values()
    )

    report["v7_compliant"] = all_idempotent
    report["summary"] = {
        "status": "✅ PASSED" if all_idempotent else "❌ FAILED",
        "requirement": "0-byte idempotency per V7 specification",
        "tests_run": len(report["tests"]),
        "tests_passed": sum(
            1 for t in report["tests"].values() if t.get("is_idempotent", False)
        ),
    }

    return report
