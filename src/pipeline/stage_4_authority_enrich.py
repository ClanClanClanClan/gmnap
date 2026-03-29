"""
GMNAP v7.0 Pipeline Stage 4: Authority Enrichment
Enriches name records with data from tiered authority sources.
"""

from typing import Dict, Any, List, Optional
from ..authorities.base import AuthoritySource
from ..core.errors import AuthorityEnrichmentError
from ..core.rate_limiter import RateLimiter
from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)


class AuthorityEnrichStage:
    """Stage 4: Authority source enrichment and validation"""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize authority enrichment stage"""
        self.config_path = config_path or Path("./config")
        self.authority_sources = {}
        self.rate_limiters = {}
        self.enrichment_stats = {}
        self.cache = {}

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich processed records with authority source data

        Args:
            context: Pipeline execution context with processed data

        Returns:
            Updated context with authority-enriched data
        """
        try:
            processed_data = context.get("processed_data", [])
            config = context.get("config", {})

            # Initialize authority sources based on configuration
            authority_config = config.get("authorities", {})
            runtime_profile = config.get("pipeline", {}).get("runtime_profile", "quick")

            self._initialize_authority_sources(authority_config, runtime_profile)

            # Filter records that need authority enrichment
            records_for_enrichment = self._filter_records_for_enrichment(processed_data)

            if not records_for_enrichment:
                # No records need enrichment, skip processing
                context["stage_4_completed"] = True
                context["authority_enrichment_skipped"] = True
                context["enriched_data"] = processed_data
                return context

            # Initialize enrichment statistics
            enrichment_stats = {
                "total_records": len(processed_data),
                "records_for_enrichment": len(records_for_enrichment),
                "enriched_records": 0,
                "authority_sources_used": {},
                "enrichment_time": 0,
                "api_calls_made": 0,
                "cache_hits": 0,
                "enrichment_errors": [],
            }

            start_time = time.time()

            # Perform authority enrichment
            enriched_data = []
            for record in processed_data:
                if record in records_for_enrichment:
                    try:
                        enriched_record = self._enrich_single_record(record, authority_config)
                        enriched_data.append(enriched_record)
                        enrichment_stats["enriched_records"] += 1
                    except Exception as e:
                        error_msg = f"Authority enrichment failed for record {record.get('GlobalID', 'unknown')}: {str(e)}"
                        enrichment_stats["enrichment_errors"].append(error_msg)
                        logger.warning(error_msg)

                        # Add record with error flag
                        record["authority_enrichment_error"] = str(e)
                        record["authority_enrichment_status"] = "failed"
                        enriched_data.append(record)
                else:
                    # Record doesn't need enrichment
                    record["authority_enrichment_status"] = "skipped"
                    enriched_data.append(record)

            # Calculate final statistics
            enrichment_stats["enrichment_time"] = time.time() - start_time
            self._calculate_enrichment_stats(enrichment_stats)

            # Update context
            context["enriched_data"] = enriched_data
            context["authority_enrichment_stats"] = enrichment_stats
            context["stage_4_completed"] = True

            return context

        except Exception as e:
            raise AuthorityEnrichmentError(f"Stage 4 authority enrichment failed: {str(e)}")

    def _initialize_authority_sources(
        self, authority_config: Dict[str, Any], runtime_profile: str
    ) -> None:
        """Initialize authority sources based on configuration and runtime profile"""

        # Determine which tiers to use based on runtime profile
        tier_config = {
            "quick": ["tier0"],
            "full": ["tier0", "tier1"],
            "extreme": ["tier0", "tier1", "tier2", "tier3"],
        }

        enabled_tiers = tier_config.get(runtime_profile, ["tier0"])

        # Initialize authority sources for enabled tiers
        for tier in enabled_tiers:
            tier_config = authority_config.get(tier, {})
            if tier_config.get("enabled", False):
                self._initialize_tier_sources(tier, tier_config)

    def _initialize_tier_sources(self, tier: str, tier_config: Dict[str, Any]) -> None:
        """Initialize authority sources for a specific tier"""

        # Common authority sources by tier
        tier_sources = {
            "tier0": ["orcid", "scopus", "dblp"],
            "tier1": ["arxiv", "mathscinet", "zbmath", "wikidata", "gnd", "hal", "researchgate"],
            "tier2": ["google_scholar"],
            "tier3": ["general_web"],
        }

        sources = tier_sources.get(tier, [])

        for source_name in sources:
            source_config = tier_config.get(source_name, {})
            if source_config.get("enabled", False):
                try:
                    # Dynamic import and initialization of authority source
                    authority_source = self._create_authority_source(
                        tier, source_name, source_config
                    )
                    if authority_source:
                        self.authority_sources[f"{tier}_{source_name}"] = authority_source

                        # Initialize rate limiter for this source
                        rate_limit = source_config.get("rate_limit", {})
                        if rate_limit:
                            self.rate_limiters[f"{tier}_{source_name}"] = RateLimiter(
                                requests_per_second=rate_limit.get("requests_per_second", 1),
                                burst_limit=rate_limit.get("burst_limit", 5),
                            )
                except Exception as e:
                    logger.warning(f"Failed to initialize {tier}_{source_name}: {str(e)}")

    def _create_authority_source(
        self, tier: str, source_name: str, config: Dict[str, Any]
    ) -> Optional[AuthoritySource]:
        """Create and configure an authority source instance"""
        try:
            # Dynamic import based on tier and source name
            if tier == "tier0":
                if source_name == "orcid":
                    from ..authorities.tier0.orcid import ORCIDAuthority

                    return ORCIDAuthority(config)
                elif source_name == "scopus":
                    from ..authorities.tier0.scopus import ScopusAuthority

                    return ScopusAuthority(config)
                elif source_name == "dblp":
                    from ..authorities.tier0.dblp import DBLPAuthority

                    return DBLPAuthority(config)
            elif tier == "tier1":
                if source_name == "arxiv":
                    from ..authorities.tier1.arxiv import ArXivAuthority

                    return ArXivAuthority(config)
                elif source_name == "mathscinet":
                    from ..authorities.tier1.mathscinet import MathSciNetAuthority

                    return MathSciNetAuthority(config)
                elif source_name == "wikidata":
                    from ..authorities.tier1.wikidata import WikidataAuthority

                    return WikidataAuthority(config)
            elif tier == "tier2":
                if source_name == "google_scholar":
                    from ..authorities.tier2.google_scholar import GoogleScholarAuthority

                    return GoogleScholarAuthority(config)
            elif tier == "tier3":
                if source_name == "general_web":
                    from ..authorities.tier3.general_web import GeneralWebAuthority

                    return GeneralWebAuthority(config)

            return None

        except ImportError as e:
            logger.warning(f"Authority source {tier}_{source_name} not available: {str(e)}")
            return None

    def _filter_records_for_enrichment(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter records that need authority enrichment"""
        records_for_enrichment = []

        for record in data:
            # Check if record needs enrichment
            needs_enrichment = self._record_needs_enrichment(record)

            if needs_enrichment:
                records_for_enrichment.append(record)

        return records_for_enrichment

    def _record_needs_enrichment(self, record: Dict[str, Any]) -> bool:
        """Determine if a record needs authority enrichment"""

        # Skip if already enriched
        if record.get("authority_enrichment_status") == "completed":
            return False

        # Skip if regional processing failed
        regional_metadata = record.get("_regional_metadata", {})
        if regional_metadata.get("processing_status") != "success":
            return False

        # Must have a valid canonical name
        canonical_latin = record.get("CanonicalLatin", "").strip()
        if not canonical_latin or len(canonical_latin) < 2:
            return False

        # Check if it's a research context (publications, academic affiliations, etc.)
        research_indicators = [
            "Institution",
            "Department",
            "Affiliation",
            "Publications",
            "ResearchArea",
            "ORCID",
            "DOI",
            "ArXivID",
        ]

        has_research_context = any(record.get(field) for field in research_indicators)

        # Always enrich if there are clear research indicators
        if has_research_context:
            return True

        # For other records, use heuristics
        # Skip very common names that would generate too many false positives
        common_test_names = ["test", "example", "sample", "unknown", "anonymous"]
        if canonical_latin.lower() in common_test_names:
            return False

        # Enrich if the name looks like a researcher name
        return self._looks_like_researcher_name(canonical_latin)

    def _looks_like_researcher_name(self, name: str) -> bool:
        """Heuristic to determine if a name looks like a researcher name"""

        # Basic checks
        if len(name.split()) < 2:  # Must have at least first and last name
            return False

        # Check for obvious non-name patterns
        if any(char.isdigit() for char in name):  # Contains numbers
            return False

        if len(name) > 100:  # Too long to be a reasonable name
            return False

        # Looks reasonable for enrichment
        return True

    def _enrich_single_record(
        self, record: Dict[str, Any], authority_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich a single record with authority source data"""

        enriched_record = record.copy()

        # Initialize enrichment metadata
        enrichment_metadata = {
            "authority_sources_consulted": [],
            "enrichment_data": {},
            "confidence_scores": {},
            "enrichment_timestamp": time.time(),
        }

        # Extract search terms
        search_terms = self._extract_search_terms(record)

        # Query each available authority source
        for source_id, authority_source in self.authority_sources.items():
            try:
                # Check rate limiting
                rate_limiter = self.rate_limiters.get(source_id)
                if rate_limiter and not rate_limiter.can_proceed():
                    continue

                # Check cache first
                cache_key = f"{source_id}_{hash(str(search_terms))}"
                if cache_key in self.cache:
                    authority_data = self.cache[cache_key]
                    self.enrichment_stats.setdefault("cache_hits", 0)
                    self.enrichment_stats["cache_hits"] += 1
                else:
                    # Query the authority source
                    authority_data = authority_source.search(search_terms)
                    self.cache[cache_key] = authority_data

                    # Update API call statistics
                    self.enrichment_stats.setdefault("api_calls_made", 0)
                    self.enrichment_stats["api_calls_made"] += 1

                # Process authority source results
                if authority_data and authority_data.get("matches"):
                    enrichment_metadata["authority_sources_consulted"].append(source_id)
                    enrichment_metadata["enrichment_data"][source_id] = authority_data

                    # Calculate confidence score for this source
                    confidence_score = self._calculate_confidence_score(
                        search_terms, authority_data, authority_source.get_confidence_multiplier()
                    )
                    enrichment_metadata["confidence_scores"][source_id] = confidence_score

                    # Merge high-confidence data into the record
                    if confidence_score >= 0.8:  # High confidence threshold
                        self._merge_authority_data(enriched_record, authority_data, source_id)

                # Track source usage statistics
                if source_id not in self.enrichment_stats.setdefault("authority_sources_used", {}):
                    self.enrichment_stats["authority_sources_used"][source_id] = 0
                self.enrichment_stats["authority_sources_used"][source_id] += 1

            except Exception as e:
                logger.warning(f"Authority source {source_id} failed: {str(e)}")
                continue

        # Add enrichment metadata to record
        enriched_record["_authority_enrichment"] = enrichment_metadata
        enriched_record["authority_enrichment_status"] = "completed"

        return enriched_record

    def _extract_search_terms(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract search terms from a record for authority source queries"""

        search_terms = {}

        # Primary name fields
        if record.get("CanonicalLatin"):
            search_terms["name"] = record["CanonicalLatin"]

        if record.get("CanonicalNative"):
            search_terms["native_name"] = record["CanonicalNative"]

        # Additional context fields
        context_fields = [
            "Institution",
            "Department",
            "Affiliation",
            "Country",
            "ResearchArea",
            "Subject",
            "Field",
            "Specialization",
        ]

        for field in context_fields:
            if record.get(field):
                search_terms[field.lower()] = record[field]

        # Existing identifiers
        identifier_fields = ["ORCID", "ScopusID", "ResearcherID", "ArXivID"]
        for field in identifier_fields:
            if record.get(field):
                search_terms[field.lower()] = record[field]

        return search_terms

    def _calculate_confidence_score(
        self, search_terms: Dict[str, Any], authority_data: Dict[str, Any], source_multiplier: float
    ) -> float:
        """Calculate confidence score for authority source match"""

        base_confidence = 0.0
        matches = authority_data.get("matches", [])

        if not matches:
            return 0.0

        # Take the best match
        best_match = matches[0]

        # Name similarity score
        name_similarity = self._calculate_name_similarity(
            search_terms.get("name", ""), best_match.get("name", "")
        )
        base_confidence += name_similarity * 0.6

        # Context matching score
        context_score = self._calculate_context_match(search_terms, best_match)
        base_confidence += context_score * 0.3

        # Source reliability score
        source_reliability = best_match.get("reliability_score", 0.5)
        base_confidence += source_reliability * 0.1

        # Apply source-specific multiplier
        final_confidence = min(base_confidence * source_multiplier, 1.0)

        return final_confidence

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        if not name1 or not name2:
            return 0.0

        # Simple token-based similarity
        tokens1 = set(name1.lower().split())
        tokens2 = set(name2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)

        return len(intersection) / len(union) if union else 0.0

    def _calculate_context_match(
        self, search_terms: Dict[str, Any], match_data: Dict[str, Any]
    ) -> float:
        """Calculate how well contextual information matches"""

        context_score = 0.0
        context_fields = ["institution", "department", "country", "field"]
        matches = 0

        for field in context_fields:
            search_value = search_terms.get(field, "").lower()
            match_value = match_data.get(field, "").lower()

            if search_value and match_value:
                if search_value in match_value or match_value in search_value:
                    context_score += 1.0
                matches += 1

        return context_score / matches if matches > 0 else 0.5

    def _merge_authority_data(
        self, record: Dict[str, Any], authority_data: Dict[str, Any], source_id: str
    ) -> None:
        """Merge high-confidence authority data into the record"""

        best_match = authority_data.get("matches", [{}])[0]

        # Merge identifiers
        identifiers = best_match.get("identifiers", {})
        for id_type, id_value in identifiers.items():
            field_name = f"{id_type.upper()}ID"
            if field_name not in record or not record[field_name]:
                record[field_name] = id_value

        # Merge institutional affiliation
        if best_match.get("institution") and not record.get("Institution"):
            record["Institution"] = best_match["institution"]

        # Merge research areas/subjects
        research_areas = best_match.get("research_areas", [])
        if research_areas and not record.get("ResearchArea"):
            record["ResearchArea"] = research_areas[0]  # Take primary area

        # Add source attribution
        if "EnrichmentSources" not in record:
            record["EnrichmentSources"] = []

        if source_id not in record["EnrichmentSources"]:
            record["EnrichmentSources"].append(source_id)

    def _calculate_enrichment_stats(self, enrichment_stats: Dict[str, Any]) -> None:
        """Calculate final enrichment statistics"""

        # Calculate enrichment rate
        total_for_enrichment = enrichment_stats["records_for_enrichment"]
        if total_for_enrichment > 0:
            enrichment_stats["enrichment_success_rate"] = (
                enrichment_stats["enriched_records"] / total_for_enrichment
            )
        else:
            enrichment_stats["enrichment_success_rate"] = 0

        # Calculate performance metrics
        if enrichment_stats["enrichment_time"] > 0:
            enrichment_stats["records_per_second"] = (
                enrichment_stats["enriched_records"] / enrichment_stats["enrichment_time"]
            )
        else:
            enrichment_stats["records_per_second"] = 0

        # Add cache efficiency
        total_queries = enrichment_stats.get("api_calls_made", 0) + enrichment_stats.get(
            "cache_hits", 0
        )
        if total_queries > 0:
            enrichment_stats["cache_hit_rate"] = (
                enrichment_stats.get("cache_hits", 0) / total_queries
            )
        else:
            enrichment_stats["cache_hit_rate"] = 0

        # Summary information
        enrichment_stats["total_authority_sources"] = len(self.authority_sources)
        enrichment_stats["active_authority_sources"] = len(
            enrichment_stats.get("authority_sources_used", {})
        )

    def get_authority_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of authority source performance"""

        summary = {
            "total_sources_available": len(self.authority_sources),
            "cache_size": len(self.cache),
            "source_performance": {},
            "most_used_source": None,
            "fastest_source": None,
        }

        if not self.enrichment_stats:
            return summary

        # Analyze source usage
        sources_used = self.enrichment_stats.get("authority_sources_used", {})
        if sources_used:
            most_used = max(sources_used.items(), key=lambda x: x[1])
            summary["most_used_source"] = most_used[0]

            for source_id, usage_count in sources_used.items():
                summary["source_performance"][source_id] = {
                    "usage_count": usage_count,
                    "available": source_id in self.authority_sources,
                }

        return summary
