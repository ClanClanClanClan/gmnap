"""
AI-Enhanced Name Intelligence for GMNAP V7
Machine learning powered name disambiguation and analysis
"""

import logging
import pickle
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import re
from pathlib import Path

# ML and NLP imports (graceful fallback if not available)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import DBSCAN
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.decomposition import TruncatedSVD

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import difflib

    DIFFLIB_AVAILABLE = True
except ImportError:
    DIFFLIB_AVAILABLE = False


@dataclass
class NameAnalysisResult:
    """Results from AI name analysis"""

    canonical_confidence: float
    disambiguation_suggestions: List[Dict[str, Any]]
    regional_confidence: Dict[str, float]
    similarity_matches: List[Dict[str, Any]]
    name_patterns: Dict[str, Any]
    quality_score: float
    risk_factors: List[str]


class NameIntelligenceEngine:
    """
    AI-Enhanced Name Intelligence Engine

    Features:
    - Machine learning based name disambiguation
    - Similarity detection and clustering
    - Pattern recognition across cultures
    - Quality assessment and risk detection
    - Confidence scoring with ensemble methods
    """

    def __init__(self, model_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.model_path = model_path or "cache/ai_models"

        # Create model directory
        Path(self.model_path).mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.vectorizer = None
        self.clustering_model = None
        self.dimensionality_reducer = None

        # Name pattern databases
        self.cultural_patterns = {}
        self.common_prefixes = set()
        self.common_suffixes = set()
        self.title_patterns = set()

        # Knowledge base
        self.name_frequency_db = defaultdict(int)
        self.regional_name_db = defaultdict(set)
        self.disambiguation_history = {}

        # Model state
        self.is_trained = False
        self.training_samples = 0

        self._initialize_patterns()

        if not SKLEARN_AVAILABLE:
            self.logger.warning("scikit-learn not available. Some AI features will be limited.")

    def _initialize_patterns(self):
        """Initialize cultural name patterns"""
        # Common academic titles and prefixes
        self.title_patterns = {
            "prof",
            "professor",
            "dr",
            "doctor",
            "phd",
            "ph.d",
            "mr",
            "mrs",
            "ms",
            "miss",
            "sir",
            "dame",
            "lord",
            "lady",
        }

        # Common name prefixes by culture
        self.common_prefixes = {
            "von",
            "van",
            "de",
            "del",
            "della",
            "di",
            "da",
            "dos",
            "das",
            "al",
            "el",
            "ibn",
            "bin",
            "abu",
            "abd",
            "mc",
            "mac",
            "o'",
            "ó",
            "ben",
            "bar",
            "bat",
            "saint",
            "st",
            "santa",
        }

        # Common name suffixes
        self.common_suffixes = {"jr", "sr", "ii", "iii", "iv", "v", "junior", "senior"}

        # Cultural pattern templates
        self.cultural_patterns = {
            "western": {
                "structure": ["given", "family"],
                "markers": ["comma_separated", "space_separated"],
            },
            "eastern": {
                "structure": ["family", "given"],
                "markers": ["no_comma", "traditional_order"],
            },
            "arabic": {
                "structure": ["given", "patronymic", "family"],
                "markers": ["ibn", "bin", "abd", "al"],
            },
            "spanish": {
                "structure": ["given", "paternal", "maternal"],
                "markers": ["compound_surnames", "de", "del"],
            },
        }

    async def analyze_name(
        self, name: str, context: Optional[Dict[str, Any]] = None
    ) -> NameAnalysisResult:
        """Perform comprehensive AI analysis of a name"""
        self.logger.debug(f"Analyzing name: {name}")

        # Basic preprocessing
        cleaned_name = self._preprocess_name(name)

        # Pattern analysis
        patterns = self._analyze_patterns(cleaned_name)

        # Similarity analysis
        similarity_matches = await self._find_similar_names(cleaned_name)

        # Regional analysis
        regional_confidence = self._analyze_regional_patterns(cleaned_name)

        # Quality assessment
        quality_score = self._assess_quality(cleaned_name, patterns)

        # Risk detection
        risk_factors = self._detect_risks(cleaned_name, patterns)

        # Disambiguation suggestions
        disambiguation_suggestions = self._generate_disambiguation_suggestions(
            cleaned_name, patterns, similarity_matches
        )

        # Overall confidence calculation
        canonical_confidence = self._calculate_confidence(
            patterns, quality_score, len(risk_factors)
        )

        return NameAnalysisResult(
            canonical_confidence=canonical_confidence,
            disambiguation_suggestions=disambiguation_suggestions,
            regional_confidence=regional_confidence,
            similarity_matches=similarity_matches,
            name_patterns=patterns,
            quality_score=quality_score,
            risk_factors=risk_factors,
        )

    def _preprocess_name(self, name: str) -> str:
        """Preprocess name for analysis"""
        # Basic cleaning
        cleaned = re.sub(r"\s+", " ", name.strip())

        # Handle common abbreviations
        cleaned = re.sub(r"\bprof\b\.?", "professor", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bdr\b\.?", "doctor", cleaned, flags=re.IGNORECASE)

        return cleaned

    def _analyze_patterns(self, name: str) -> Dict[str, Any]:
        """Analyze structural patterns in the name"""
        patterns = {
            "has_comma": "," in name,
            "word_count": len(name.split()),
            "has_titles": any(title in name.lower() for title in self.title_patterns),
            "has_prefixes": any(prefix in name.lower() for prefix in self.common_prefixes),
            "has_suffixes": any(suffix in name.lower() for suffix in self.common_suffixes),
            "has_numbers": bool(re.search(r"\d", name)),
            "has_special_chars": bool(re.search(r"[^\w\s,.-]", name)),
            "length": len(name),
            "capitalization_pattern": self._analyze_capitalization(name),
        }

        # Detect likely cultural pattern
        patterns["likely_culture"] = self._detect_cultural_pattern(name, patterns)

        return patterns

    def _analyze_capitalization(self, name: str) -> str:
        """Analyze capitalization patterns"""
        words = name.split()

        all_caps = all(word.isupper() for word in words if word.isalpha())
        all_lower = all(word.islower() for word in words if word.isalpha())
        title_case = all(
            word[0].isupper() and word[1:].islower()
            for word in words
            if word.isalpha() and len(word) > 1
        )

        if all_caps:
            return "ALL_CAPS"
        elif all_lower:
            return "all_lower"
        elif title_case:
            return "Title_Case"
        else:
            return "Mixed_Case"

    def _detect_cultural_pattern(self, name: str, patterns: Dict[str, Any]) -> str:
        """Detect likely cultural naming pattern"""
        name_lower = name.lower()

        # Arabic pattern detection
        if any(marker in name_lower for marker in ["ibn", "bin", "abd", "al-"]):
            return "arabic"

        # Spanish pattern detection
        if any(marker in name_lower for marker in ["de ", "del ", "de la "]):
            return "spanish"

        # Asian pattern detection (family name first, no comma)
        if not patterns["has_comma"] and patterns["word_count"] >= 2:
            # This is a heuristic - more sophisticated detection would use regional context
            return "eastern_possible"

        # Western pattern (comma separated or given-family order)
        if patterns["has_comma"]:
            return "western"

        return "unknown"

    async def _find_similar_names(self, name: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Find similar names using various similarity measures"""
        if not DIFFLIB_AVAILABLE:
            return []

        similar_names = []

        # Check against known names in frequency database
        for known_name, frequency in self.name_frequency_db.items():
            if known_name == name:
                continue

            # Calculate various similarity measures
            similarities = {
                "sequence_similarity": difflib.SequenceMatcher(
                    None, name.lower(), known_name.lower()
                ).ratio(),
                "jaro_winkler": self._jaro_winkler_similarity(name.lower(), known_name.lower()),
                "edit_distance": self._normalized_edit_distance(name.lower(), known_name.lower()),
            }

            # Calculate composite similarity
            composite_similarity = (
                similarities["sequence_similarity"] * 0.4
                + similarities["jaro_winkler"] * 0.4
                + (1 - similarities["edit_distance"]) * 0.2
            )

            if composite_similarity >= threshold:
                similar_names.append(
                    {
                        "name": known_name,
                        "similarity": composite_similarity,
                        "frequency": frequency,
                        "similarities": similarities,
                    }
                )

        # Sort by similarity score
        similar_names.sort(key=lambda x: x["similarity"], reverse=True)

        return similar_names[:10]  # Return top 10

    def _jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity (simplified implementation)"""
        if not s1 or not s2:
            return 0.0

        if s1 == s2:
            return 1.0

        # Simplified Jaro similarity
        len1, len2 = len(s1), len(s2)
        match_window = max(len1, len2) // 2 - 1
        match_window = max(0, match_window)

        matches = 0
        s1_matches = [False] * len1
        s2_matches = [False] * len2

        # Find matches
        for i in range(len1):
            start = max(0, i - match_window)
            end = min(i + match_window + 1, len2)

            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = s2_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        # Count transpositions
        transpositions = 0
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

        jaro = (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3

        # Winkler modification
        prefix_len = 0
        for i in range(min(len1, len2, 4)):
            if s1[i] == s2[i]:
                prefix_len += 1
            else:
                break

        return jaro + (0.1 * prefix_len * (1 - jaro))

    def _normalized_edit_distance(self, s1: str, s2: str) -> float:
        """Calculate normalized edit distance"""
        if not s1 or not s2:
            return 1.0

        if s1 == s2:
            return 0.0

        # Dynamic programming approach
        len1, len2 = len(s1), len(s2)
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,  # deletion
                    dp[i][j - 1] + 1,  # insertion
                    dp[i - 1][j - 1] + cost,  # substitution
                )

        return dp[len1][len2] / max(len1, len2)

    def _analyze_regional_patterns(self, name: str) -> Dict[str, float]:
        """Analyze regional/cultural patterns in the name"""
        regional_scores = {}

        # Simple pattern matching approach
        # In production, this would use trained models

        patterns = {
            "western": ["smith", "johnson", "williams", "jones", "brown"],
            "eastern": ["wang", "li", "zhang", "liu", "chen"],
            "arabic": ["mohammed", "ahmad", "ali", "hassan", "ibrahim"],
            "spanish": ["garcia", "rodriguez", "martinez", "lopez", "gonzalez"],
        }

        name_lower = name.lower()

        for region, common_names in patterns.items():
            score = 0.0
            for common_name in common_names:
                if common_name in name_lower:
                    score = max(score, 0.8)
                else:
                    # Check similarity
                    similarity = difflib.SequenceMatcher(None, name_lower, common_name).ratio()
                    if similarity > 0.6:
                        score = max(score, similarity * 0.5)

            regional_scores[region] = score

        return regional_scores

    def _assess_quality(self, name: str, patterns: Dict[str, Any]) -> float:
        """Assess the quality of name formatting and completeness"""
        quality_factors = []

        # Length check
        if 5 <= patterns["length"] <= 100:
            quality_factors.append(0.2)
        elif patterns["length"] < 5 or patterns["length"] > 100:
            quality_factors.append(-0.3)

        # Word count check
        if 2 <= patterns["word_count"] <= 4:
            quality_factors.append(0.2)
        elif patterns["word_count"] == 1:
            quality_factors.append(-0.2)
        elif patterns["word_count"] > 5:
            quality_factors.append(-0.1)

        # Capitalization check
        if patterns["capitalization_pattern"] == "Title_Case":
            quality_factors.append(0.2)
        elif patterns["capitalization_pattern"] == "ALL_CAPS":
            quality_factors.append(-0.1)
        elif patterns["capitalization_pattern"] == "all_lower":
            quality_factors.append(-0.2)

        # Special characters check
        if not patterns["has_special_chars"]:
            quality_factors.append(0.1)
        else:
            quality_factors.append(-0.2)

        # Numbers check (usually negative for names)
        if patterns["has_numbers"]:
            quality_factors.append(-0.3)

        # Calculate final quality score (0-1 scale)
        base_score = 0.5
        final_score = base_score + sum(quality_factors)

        return max(0.0, min(1.0, final_score))

    def _detect_risks(self, name: str, patterns: Dict[str, Any]) -> List[str]:
        """Detect potential risks or issues with the name"""
        risks = []

        if patterns["has_numbers"]:
            risks.append("Contains numbers")

        if patterns["has_special_chars"]:
            risks.append("Contains special characters")

        if patterns["length"] < 3:
            risks.append("Very short name")

        if patterns["length"] > 150:
            risks.append("Unusually long name")

        if patterns["word_count"] > 6:
            risks.append("Too many name components")

        if patterns["capitalization_pattern"] == "ALL_CAPS":
            risks.append("All caps formatting")

        # Check for potential test data
        test_patterns = ["test", "example", "sample", "dummy", "fake"]
        if any(pattern in name.lower() for pattern in test_patterns):
            risks.append("Possible test data")

        return risks

    def _generate_disambiguation_suggestions(
        self, name: str, patterns: Dict[str, Any], similar_names: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for name disambiguation"""
        suggestions = []

        # Format standardization suggestions
        if patterns["capitalization_pattern"] != "Title_Case":
            suggestions.append(
                {
                    "type": "formatting",
                    "suggestion": "Standardize capitalization to Title Case",
                    "confidence": 0.8,
                }
            )

        # Structure suggestions
        if not patterns["has_comma"] and patterns["word_count"] >= 2:
            # Suggest family-name-first format
            words = name.split()
            if len(words) >= 2:
                family_first = f"{words[-1]}, {' '.join(words[:-1])}"
                suggestions.append(
                    {
                        "type": "structure",
                        "suggestion": f'Consider family-first format: "{family_first}"',
                        "confidence": 0.6,
                    }
                )

        # Similar name suggestions
        for similar in similar_names[:3]:  # Top 3 similar names
            suggestions.append(
                {
                    "type": "similarity",
                    "suggestion": f'Similar to: "{similar["name"]}" (similarity: {similar["similarity"]:.2f})',
                    "confidence": similar["similarity"],
                }
            )

        return suggestions

    def _calculate_confidence(
        self, patterns: Dict[str, Any], quality_score: float, risk_count: int
    ) -> float:
        """Calculate overall confidence in the canonical form"""
        # Base confidence from quality
        confidence = quality_score

        # Adjust based on structural patterns
        if patterns["has_comma"] and 2 <= patterns["word_count"] <= 4:
            confidence += 0.1

        if patterns["capitalization_pattern"] == "Title_Case":
            confidence += 0.1

        # Penalize risks
        confidence -= risk_count * 0.1

        # Ensure bounds
        return max(0.0, min(1.0, confidence))

    async def train_on_batch(self, training_data: List[Dict[str, Any]]):
        """Train the AI models on a batch of name data"""
        if not SKLEARN_AVAILABLE:
            self.logger.warning("Cannot train: scikit-learn not available")
            return

        self.logger.info(f"Training on batch of {len(training_data)} samples")

        # Extract features for training
        names = [sample["name"] for sample in training_data]

        # Update frequency database
        for sample in training_data:
            self.name_frequency_db[sample["name"]] += 1
            if "region" in sample:
                self.regional_name_db[sample["region"]].add(sample["name"])

        # Train vectorizer if not already initialized
        if self.vectorizer is None:
            self.vectorizer = TfidfVectorizer(
                max_features=5000, ngram_range=(1, 2), stop_words="english"
            )

        # Fit/update vectorizer
        try:
            name_vectors = self.vectorizer.fit_transform(names)

            # Train clustering model
            if len(names) > 10:  # Need minimum samples for clustering
                self.clustering_model = DBSCAN(eps=0.3, min_samples=2)
                clusters = self.clustering_model.fit_predict(name_vectors.toarray())

                self.logger.info(f"Identified {len(set(clusters))} name clusters")

            self.training_samples += len(training_data)
            self.is_trained = True

        except Exception as e:
            self.logger.error(f"Training failed: {e}")

    def save_model(self, path: Optional[str] = None):
        """Save the trained model to disk"""
        save_path = path or f"{self.model_path}/name_intelligence_model.pkl"

        model_data = {
            "vectorizer": self.vectorizer,
            "clustering_model": self.clustering_model,
            "name_frequency_db": dict(self.name_frequency_db),
            "regional_name_db": {k: list(v) for k, v in self.regional_name_db.items()},
            "training_samples": self.training_samples,
            "is_trained": self.is_trained,
        }

        try:
            with open(save_path, "wb") as f:
                pickle.dump(model_data, f)
            self.logger.info(f"Model saved to {save_path}")
        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")

    def load_model(self, path: Optional[str] = None):
        """Load a trained model from disk"""
        load_path = path or f"{self.model_path}/name_intelligence_model.pkl"

        try:
            with open(load_path, "rb") as f:
                model_data = pickle.load(f)

            self.vectorizer = model_data.get("vectorizer")
            self.clustering_model = model_data.get("clustering_model")
            self.name_frequency_db = defaultdict(int, model_data.get("name_frequency_db", {}))
            self.regional_name_db = defaultdict(set)
            for region, names in model_data.get("regional_name_db", {}).items():
                self.regional_name_db[region] = set(names)
            self.training_samples = model_data.get("training_samples", 0)
            self.is_trained = model_data.get("is_trained", False)

            self.logger.info(f"Model loaded from {load_path}")

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")


class EnsembleNameDisambiguator:
    """
    Ensemble approach to name disambiguation using multiple AI techniques
    """

    def __init__(self):
        self.engines = {}
        self.weights = {}
        self.logger = logging.getLogger(__name__)

    def add_engine(self, name: str, engine: NameIntelligenceEngine, weight: float = 1.0):
        """Add an intelligence engine to the ensemble"""
        self.engines[name] = engine
        self.weights[name] = weight
        self.logger.info(f"Added engine '{name}' with weight {weight}")

    async def ensemble_analysis(
        self, name: str, context: Optional[Dict[str, Any]] = None
    ) -> NameAnalysisResult:
        """Run ensemble analysis using all available engines"""
        if not self.engines:
            raise ValueError("No engines available for ensemble analysis")

        results = []

        # Run analysis on all engines
        for engine_name, engine in self.engines.items():
            try:
                result = await engine.analyze_name(name, context)
                results.append((engine_name, result, self.weights[engine_name]))
            except Exception as e:
                self.logger.error(f"Engine '{engine_name}' failed: {e}")

        if not results:
            raise RuntimeError("All engines failed")

        # Combine results using weighted averaging
        return self._combine_results(results)

    def _combine_results(
        self, results: List[Tuple[str, NameAnalysisResult, float]]
    ) -> NameAnalysisResult:
        """Combine results from multiple engines"""
        total_weight = sum(weight for _, _, weight in results)

        # Weighted average for numerical scores
        canonical_confidence = (
            sum(result.canonical_confidence * weight for _, result, weight in results)
            / total_weight
        )

        quality_score = (
            sum(result.quality_score * weight for _, result, weight in results) / total_weight
        )

        # Combine suggestions (remove duplicates)
        all_suggestions = []
        seen_suggestions = set()

        for _, result, weight in results:
            for suggestion in result.disambiguation_suggestions:
                suggestion_key = f"{suggestion['type']}:{suggestion['suggestion']}"
                if suggestion_key not in seen_suggestions:
                    suggestion["confidence"] *= weight / total_weight
                    all_suggestions.append(suggestion)
                    seen_suggestions.add(suggestion_key)

        # Combine similarity matches
        all_matches = []
        for _, result, _ in results:
            all_matches.extend(result.similarity_matches)

        # Sort and deduplicate matches
        unique_matches = {}
        for match in all_matches:
            key = match["name"]
            if key not in unique_matches or match["similarity"] > unique_matches[key]["similarity"]:
                unique_matches[key] = match

        similarity_matches = sorted(
            unique_matches.values(), key=lambda x: x["similarity"], reverse=True
        )[:10]

        # Combine risk factors
        all_risks = set()
        for _, result, _ in results:
            all_risks.update(result.risk_factors)

        # Combine regional confidence (weighted average)
        regional_confidence = defaultdict(float)
        for _, result, weight in results:
            for region, confidence in result.regional_confidence.items():
                regional_confidence[region] += confidence * weight / total_weight

        # Combine patterns (use most confident result)
        best_result = max(results, key=lambda x: x[1].canonical_confidence)[1]

        return NameAnalysisResult(
            canonical_confidence=canonical_confidence,
            disambiguation_suggestions=all_suggestions,
            regional_confidence=dict(regional_confidence),
            similarity_matches=similarity_matches,
            name_patterns=best_result.name_patterns,
            quality_score=quality_score,
            risk_factors=list(all_risks),
        )
