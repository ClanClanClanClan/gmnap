"""
GMNAP v7.0 Pipeline Stage 5: Collision Detection and Analytics
Detects and analyzes name collisions across the processed dataset.
"""

import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.errors import CollisionAnalyticsError


class CollisionAnalyticsStage:
    """Stage 5: Collision detection and analytics"""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize collision analytics stage"""
        self.config_path = config_path or Path("./config")
        self.collision_stats = {}
        self.collision_data = {}

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze collisions in authority-enriched data

        Args:
            context: Pipeline execution context with enriched data

        Returns:
            Updated context with collision analytics
        """
        try:
            enriched_data = context.get("enriched_data", [])
            config = context.get("config", {})

            if not enriched_data:
                # No data to analyze, skip processing
                context["stage_5_completed"] = True
                context["collision_analysis_skipped"] = True
                context["collision_data"] = enriched_data
                return context

            # Initialize collision analytics
            collision_config = config.get("collision_analytics", {})
            collision_threshold = collision_config.get("similarity_threshold", 0.8)
            enable_cross_region = collision_config.get(
                "enable_cross_region_analysis", True
            )

            # Perform collision detection and analytics
            collision_results = self._analyze_collisions(
                enriched_data, collision_threshold, enable_cross_region
            )

            # Generate collision analytics
            analytics = self._generate_collision_analytics(collision_results)

            # Resolve or flag collisions
            resolved_data = self._resolve_collisions(
                enriched_data, collision_results, collision_config
            )

            # Update context
            context["collision_data"] = resolved_data
            context["collision_results"] = collision_results
            context["collision_analytics"] = analytics
            context["stage_5_completed"] = True

            return context

        except Exception as e:
            raise CollisionAnalyticsError(
                f"Stage 5 collision analytics failed: {str(e)}"
            )

    def _analyze_collisions(
        self, data: List[Dict[str, Any]], threshold: float, cross_region: bool
    ) -> Dict[str, Any]:
        """Analyze collisions in the dataset"""

        start_time = time.time()

        # Group records for collision analysis
        grouped_records = self._group_records_for_analysis(data)

        # Detect collisions within groups
        collisions = self._detect_collisions(grouped_records, threshold)

        # Cross-region collision analysis
        cross_region_collisions = {}
        if cross_region:
            cross_region_collisions = self._analyze_cross_region_collisions(
                data, threshold
            )

        # Authority source collision analysis
        authority_collisions = self._analyze_authority_collisions(data)

        # Calculate collision statistics
        collision_stats = self._calculate_collision_statistics(
            collisions, cross_region_collisions, authority_collisions
        )

        analysis_time = time.time() - start_time

        return {
            "within_region_collisions": collisions,
            "cross_region_collisions": cross_region_collisions,
            "authority_collisions": authority_collisions,
            "collision_statistics": collision_stats,
            "analysis_time": analysis_time,
            "total_records_analyzed": len(data),
            "collision_threshold": threshold,
        }

    def _group_records_for_analysis(
        self, data: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group records by region and other criteria for collision analysis"""

        grouped = defaultdict(list)

        for record in data:
            # Group by primary region
            regional_metadata = record.get("_regional_metadata", {})
            region = regional_metadata.get("assigned_region", "unknown")

            grouped[f"region_{region}"].append(record)

            # Also group by institution for cross-institutional analysis
            institution = record.get("Institution", "")
            if institution:
                grouped[f"institution_{hash(institution.lower())}"].append(record)

            # Group by research area for cross-field analysis
            research_area = record.get("ResearchArea", "")
            if research_area:
                grouped[f"research_{hash(research_area.lower())}"].append(record)

        return grouped

    def _detect_collisions(
        self, grouped_records: Dict[str, List[Dict[str, Any]]], threshold: float
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Detect collisions within grouped records"""

        collisions = {}

        for group_key, records in grouped_records.items():
            if len(records) < 2:
                continue

            group_collisions = []

            # Compare all pairs within the group
            for i in range(len(records)):
                for j in range(i + 1, len(records)):
                    record1 = records[i]
                    record2 = records[j]

                    similarity = self._calculate_record_similarity(record1, record2)

                    if similarity >= threshold:
                        collision = {
                            "record1_id": record1.get("GlobalID", f"record_{i}"),
                            "record2_id": record2.get("GlobalID", f"record_{j}"),
                            "similarity_score": similarity,
                            "collision_type": self._classify_collision_type(
                                record1, record2
                            ),
                            "collision_fields": self._identify_collision_fields(
                                record1, record2
                            ),
                            "collision_severity": self._assess_collision_severity(
                                record1, record2, similarity
                            ),
                            "resolution_strategy": self._suggest_resolution_strategy(
                                record1, record2, similarity
                            ),
                        }
                        group_collisions.append(collision)

            if group_collisions:
                collisions[group_key] = group_collisions

        return collisions

    def _calculate_record_similarity(
        self, record1: Dict[str, Any], record2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two records"""

        # Name similarity (primary factor)
        name1 = record1.get("CanonicalLatin", "").lower()
        name2 = record2.get("CanonicalLatin", "").lower()

        name_similarity = self._calculate_name_similarity(name1, name2)

        # Native name similarity (if available)
        native1 = record1.get("CanonicalNative", "").lower()
        native2 = record2.get("CanonicalNative", "").lower()

        native_similarity = 0.0
        if native1 and native2:
            native_similarity = self._calculate_name_similarity(native1, native2)

        # Contextual similarity
        context_similarity = self._calculate_context_similarity(record1, record2)

        # Authority ID overlap
        authority_overlap = self._calculate_authority_overlap(record1, record2)

        # Weighted final similarity
        weights = {"name": 0.4, "native": 0.2, "context": 0.2, "authority": 0.2}

        final_similarity = (
            weights["name"] * name_similarity
            + weights["native"] * native_similarity
            + weights["context"] * context_similarity
            + weights["authority"] * authority_overlap
        )

        return min(final_similarity, 1.0)

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        if not name1 or not name2:
            return 0.0

        # Exact match
        if name1 == name2:
            return 1.0

        # Token-based similarity (Jaccard)
        tokens1 = set(name1.split())
        tokens2 = set(name2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)

        jaccard_similarity = len(intersection) / len(union)

        # Edit distance similarity
        edit_distance_similarity = self._calculate_edit_distance_similarity(
            name1, name2
        )

        # Return the maximum of the two measures
        return max(jaccard_similarity, edit_distance_similarity)

    def _calculate_edit_distance_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity based on edit distance"""
        if not s1 or not s2:
            return 0.0

        # Simple Levenshtein distance implementation
        if len(s1) < len(s2):
            s1, s2 = s2, s1

        if len(s2) == 0:
            return 0.0

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        edit_distance = previous_row[-1]
        max_len = max(len(s1), len(s2))

        return 1.0 - (edit_distance / max_len)

    def _calculate_context_similarity(
        self, record1: Dict[str, Any], record2: Dict[str, Any]
    ) -> float:
        """Calculate contextual similarity between records"""

        context_fields = ["Institution", "Department", "ResearchArea", "Country"]
        matches = 0
        total_fields = 0

        for field in context_fields:
            value1 = record1.get(field, "").lower()
            value2 = record2.get(field, "").lower()

            if value1 and value2:
                total_fields += 1
                if value1 == value2:
                    matches += 1
                elif value1 in value2 or value2 in value1:
                    matches += 0.5

        return matches / total_fields if total_fields > 0 else 0.0

    def _calculate_authority_overlap(
        self, record1: Dict[str, Any], record2: Dict[str, Any]
    ) -> float:
        """Calculate overlap in authority source identifiers"""

        authority_fields = [
            "ORCID",
            "ScopusID",
            "ResearcherID",
            "ArXivID",
            "MathSciNetID",
        ]

        overlapping_ids = 0
        total_ids = 0

        for field in authority_fields:
            id1 = record1.get(field, "")
            id2 = record2.get(field, "")

            if id1 and id2:
                total_ids += 1
                if id1 == id2:
                    overlapping_ids += 1

        return overlapping_ids / total_ids if total_ids > 0 else 0.0

    def _classify_collision_type(
        self, record1: Dict[str, Any], record2: Dict[str, Any]
    ) -> str:
        """Classify the type of collision"""

        # Check if same person (high authority overlap)
        authority_overlap = self._calculate_authority_overlap(record1, record2)
        if authority_overlap > 0.5:
            return "same_person"

        # Check if different people with similar names
        name_similarity = self._calculate_name_similarity(
            record1.get("CanonicalLatin", "").lower(),
            record2.get("CanonicalLatin", "").lower(),
        )
        context_similarity = self._calculate_context_similarity(record1, record2)

        if name_similarity > 0.8 and context_similarity < 0.3:
            return "different_people_similar_names"
        elif name_similarity > 0.6 and context_similarity > 0.7:
            return "possible_same_person"
        else:
            return "ambiguous"

    def _identify_collision_fields(
        self, record1: Dict[str, Any], record2: Dict[str, Any]
    ) -> List[str]:
        """Identify which fields are involved in the collision"""

        collision_fields = []

        # Check name fields
        if (
            self._calculate_name_similarity(
                record1.get("CanonicalLatin", "").lower(),
                record2.get("CanonicalLatin", "").lower(),
            )
            > 0.7
        ):
            collision_fields.append("CanonicalLatin")

        # Check contextual fields
        context_fields = ["Institution", "Department", "ResearchArea"]
        for field in context_fields:
            value1 = record1.get(field, "").lower()
            value2 = record2.get(field, "").lower()
            if (
                value1
                and value2
                and (value1 == value2 or value1 in value2 or value2 in value1)
            ):
                collision_fields.append(field)

        return collision_fields

    def _assess_collision_severity(
        self, record1: Dict[str, Any], record2: Dict[str, Any], similarity: float
    ) -> str:
        """Assess the severity of the collision"""

        if similarity >= 0.95:
            return "critical"
        elif similarity >= 0.85:
            return "high"
        elif similarity >= 0.75:
            return "medium"
        else:
            return "low"

    def _suggest_resolution_strategy(
        self, record1: Dict[str, Any], record2: Dict[str, Any], similarity: float
    ) -> str:
        """Suggest a resolution strategy for the collision"""

        collision_type = self._classify_collision_type(record1, record2)

        if collision_type == "same_person":
            return "merge_records"
        elif collision_type == "different_people_similar_names":
            return "disambiguate"
        elif similarity >= 0.9:
            return "manual_review"
        else:
            return "flag_for_review"

    def _analyze_cross_region_collisions(
        self, data: List[Dict[str, Any]], threshold: float
    ) -> Dict[str, Any]:
        """Analyze collisions across different regions"""

        cross_region_collisions = []

        # Group by region
        by_region = defaultdict(list)
        for record in data:
            regional_metadata = record.get("_regional_metadata", {})
            region = regional_metadata.get("assigned_region", "unknown")
            by_region[region].append(record)

        # Compare across regions
        regions = list(by_region.keys())
        for i in range(len(regions)):
            for j in range(i + 1, len(regions)):
                region1, region2 = regions[i], regions[j]

                for record1 in by_region[region1]:
                    for record2 in by_region[region2]:
                        similarity = self._calculate_record_similarity(record1, record2)

                        if similarity >= threshold:
                            collision = {
                                "region1": region1,
                                "region2": region2,
                                "record1_id": record1.get("GlobalID", "unknown"),
                                "record2_id": record2.get("GlobalID", "unknown"),
                                "similarity_score": similarity,
                                "collision_type": self._classify_collision_type(
                                    record1, record2
                                ),
                            }
                            cross_region_collisions.append(collision)

        return {
            "collisions": cross_region_collisions,
            "total_cross_region_collisions": len(cross_region_collisions),
            "regions_involved": len(regions),
        }

    def _analyze_authority_collisions(
        self, data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze collisions in authority source data"""

        authority_collisions = {}
        authority_fields = [
            "ORCID",
            "ScopusID",
            "ResearcherID",
            "ArXivID",
            "MathSciNetID",
        ]

        for field in authority_fields:
            # Group by authority ID
            by_authority_id = defaultdict(list)

            for record in data:
                authority_id = record.get(field, "")
                if authority_id:
                    by_authority_id[authority_id].append(record)

            # Find collisions (multiple records with same authority ID)
            field_collisions = []
            for authority_id, records in by_authority_id.items():
                if len(records) > 1:
                    collision = {
                        "authority_id": authority_id,
                        "record_count": len(records),
                        "record_ids": [r.get("GlobalID", "unknown") for r in records],
                        "collision_severity": (
                            "critical" if len(records) > 3 else "medium"
                        ),
                    }
                    field_collisions.append(collision)

            if field_collisions:
                authority_collisions[field] = field_collisions

        return authority_collisions

    def _calculate_collision_statistics(
        self, collisions: Dict, cross_region: Dict, authority: Dict
    ) -> Dict[str, Any]:
        """Calculate comprehensive collision statistics"""

        total_collisions = sum(
            len(group_collisions) for group_collisions in collisions.values()
        )
        cross_region_count = cross_region.get("total_cross_region_collisions", 0)
        authority_count = sum(
            len(field_collisions) for field_collisions in authority.values()
        )

        # Collision severity distribution
        severity_counts = Counter()
        collision_types = Counter()

        for group_collisions in collisions.values():
            for collision in group_collisions:
                severity_counts[collision["collision_severity"]] += 1
                collision_types[collision["collision_type"]] += 1

        return {
            "total_within_region_collisions": total_collisions,
            "total_cross_region_collisions": cross_region_count,
            "total_authority_collisions": authority_count,
            "total_all_collisions": total_collisions
            + cross_region_count
            + authority_count,
            "severity_distribution": dict(severity_counts),
            "collision_type_distribution": dict(collision_types),
            "collision_rate": (
                total_collisions / max(1, len(collisions)) if collisions else 0
            ),
        }

    def _resolve_collisions(
        self,
        data: List[Dict[str, Any]],
        collision_results: Dict[str, Any],
        config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Apply collision resolution strategies to the data"""

        resolved_data = []
        collision_flags = set()

        # Collect all collision record IDs that need special handling
        for group_collisions in collision_results["within_region_collisions"].values():
            for collision in group_collisions:
                if collision["resolution_strategy"] in [
                    "merge_records",
                    "manual_review",
                ]:
                    collision_flags.add(collision["record1_id"])
                    collision_flags.add(collision["record2_id"])

        # Process records and apply collision metadata
        for record in data:
            record_id = record.get("GlobalID", "unknown")

            if record_id in collision_flags:
                # Add collision metadata
                record["_collision_metadata"] = {
                    "has_collisions": True,
                    "collision_status": "flagged_for_review",
                    "collision_timestamp": time.time(),
                }
            else:
                record["_collision_metadata"] = {
                    "has_collisions": False,
                    "collision_status": "no_collisions",
                    "collision_timestamp": time.time(),
                }

            resolved_data.append(record)

        return resolved_data

    def _generate_collision_analytics(
        self, collision_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive collision analytics"""

        analytics = {
            "summary": collision_results["collision_statistics"],
            "analysis_performance": {
                "analysis_time": collision_results["analysis_time"],
                "records_analyzed": collision_results["total_records_analyzed"],
                "records_per_second": collision_results["total_records_analyzed"]
                / max(collision_results["analysis_time"], 0.001),
            },
            "collision_details": {
                "within_region": {
                    "total_groups_with_collisions": len(
                        collision_results["within_region_collisions"]
                    ),
                    "collision_groups": list(
                        collision_results["within_region_collisions"].keys()
                    ),
                },
                "cross_region": {
                    "total_collisions": collision_results[
                        "cross_region_collisions"
                    ].get("total_cross_region_collisions", 0),
                    "regions_involved": collision_results[
                        "cross_region_collisions"
                    ].get("regions_involved", 0),
                },
                "authority_sources": {
                    "fields_with_collisions": list(
                        collision_results["authority_collisions"].keys()
                    ),
                    "total_authority_collisions": sum(
                        len(field_collisions)
                        for field_collisions in collision_results[
                            "authority_collisions"
                        ].values()
                    ),
                },
            },
            "resolution_recommendations": self._generate_resolution_recommendations(
                collision_results
            ),
        }

        return analytics

    def _generate_resolution_recommendations(
        self, collision_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for collision resolution"""

        recommendations = []

        # High-priority recommendations for critical collisions
        for group_key, group_collisions in collision_results[
            "within_region_collisions"
        ].items():
            critical_collisions = [
                c for c in group_collisions if c["collision_severity"] == "critical"
            ]

            if critical_collisions:
                recommendations.append(
                    {
                        "priority": "high",
                        "group": group_key,
                        "recommendation": f"Review {len(critical_collisions)} critical collisions in {group_key}",
                        "affected_records": len(critical_collisions) * 2,
                        "suggested_action": "immediate_manual_review",
                    }
                )

        # Authority source collision recommendations
        for field, field_collisions in collision_results[
            "authority_collisions"
        ].items():
            if field_collisions:
                recommendations.append(
                    {
                        "priority": "high",
                        "field": field,
                        "recommendation": f"Resolve {len(field_collisions)} authority ID collisions in {field}",
                        "affected_records": sum(
                            c["record_count"] for c in field_collisions
                        ),
                        "suggested_action": "verify_authority_data",
                    }
                )

        return recommendations

    def get_collision_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of collision detection performance"""

        if not self.collision_stats:
            return {"message": "No collision statistics available"}

        return {
            "collision_detection_performance": self.collision_stats,
            "most_collision_prone_groups": self._identify_collision_prone_groups(),
            "resolution_success_rate": self._calculate_resolution_success_rate(),
        }

    def _identify_collision_prone_groups(self) -> List[str]:
        """Identify groups with the highest collision rates"""
        # Implementation would analyze collision patterns
        return []

    def _calculate_resolution_success_rate(self) -> float:
        """Calculate the success rate of collision resolution"""
        # Implementation would track resolution outcomes
        return 0.0
