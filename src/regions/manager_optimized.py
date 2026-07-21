"""
Optimized Region detection and management for GMNAP.
Performance improvements:
1. Singleton pattern for FastText model loading
2. Lazy loading of regions only when needed
3. Cache region detection results
4. Only load regions that are actually implemented
5. Persistent fastText CLI worker (2000× speedup on the CLI tiebreaker
   path: 43 q/s with subprocess.run per query → ~85 k q/s with a single
   long-lived subprocess reading lines from stdin).
"""

# Marker so pipeline can assert correct class is wired (prevents wrong-file regression)
_V7_OPTIMIZED = True

import atexit
import dataclasses
import functools
import logging
import os
import re
import subprocess
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Module-level so the per-call hot path in `detect_region` is free
# of repeated `import` lookups. The calibrator's `apply()` is a
# no-op identity when GMNAP_CALIBRATE_CONFIDENCE is unset, so the
# cost there is one env-var read per call (cached after first hit).
from src.regions.calibration import apply as _apply_calibration  # noqa: E402

# Initialize logger first
logger = logging.getLogger(__name__)

# Try to import fasttext, but make it optional for Docker builds
try:
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*load_model does not return.*")
        import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False
    logger.warning(
        "fasttext not available - ML detection disabled, using rules-based detection only"
    )

from src.core.cache.sized_lru import SizedLRU
from src.core.security_validator import SecurityError, SecurityValidator
from src.core.unicode_handler import UnicodeNormalizer
from src.regions.detection.fasttext_worker import (  # noqa: F401
    FastTextCLIWorker,
    get_fasttext_model,
)
from src.regions.detection.result import RegionDetectionResult  # noqa: F401

# ── R45 facade: the scorer / fastText worker / result dataclass were split
#    into src/regions/detection/ (this file was 6,851 lines). Re-exported
#    here so every existing `from src.regions.manager_optimized import X`
#    and internal RegionManager reference keeps working unchanged.
from src.regions.detection.scorer import (  # noqa: F401
    _DIASPORA_DOWNWEIGHT,
    _GIVEN_TO_REGIONS,
    _HISPANIC_SHARED_SURNAMES,
    _MEDIUM,
    _STRONG,
    _WORD,
    LEAF_TO_GROUP,
    MEDIUM_SUFFIX_WEIGHT_GROUP,
    MEDIUM_SUFFIX_WEIGHT_LEAF,
    MEDIUM_SUFFIXES_TO_GROUP,
    MEDIUM_SUFFIXES_TO_LEAF,
    REGION_GROUPS,
    SIGNATURE_SUFFIXES,
    _latin_tokens,
    _load_learned_features,
    _nudge_by_doi_affiliation,
    _score_priority_rules,
    _wb,
)

from .base import REGION_CODES, RegionSpec, get_region_for_territory

# Token extraction and word-boundary utilities for systematic pattern matching


class RegionManager:
    """
    Optimized region detection and routing manager.

    Key optimizations:
    1. Singleton FastText model loading
    2. Lazy region loading
    3. Detection result caching
    4. Only load actually implemented regions
    """

    # Marker so pipeline can assert correct class is wired (prevents wrong-file regression)
    _V7_OPTIMIZED = True

    # List of actually implemented regions (all V7 regions with processor.py files)
    IMPLEMENTED_REGIONS = {
        # A-groups (Anglo-sphere/Western)
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        # B-groups (Slavic)
        "B1",
        "B2",
        "B3",
        # C-groups (Middle East/Turkic)
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7",
        "C8",
        "C9",
        # D-groups (South Asia)
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        # E-groups (East Asia)
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
        "E7",
        # F-groups (Africa)
        "F1",
        "F2",
        "F3",
        "F4",
        # G-groups (Latin America)
        "G1",
        # Special groups
        "H1",  # Historical
        "R0",  # Residual Latin-ASCII
        "Z0",  # Quarantine
    }

    # Expert Phase 3: Lexical signal ensemble configuration
    SIGNALS_DIR_ENV = "GMNAP_SIGNALS_DIR"
    SIGNALS_CACHE = None

    def __init__(self, config_dir: Path = Path("./config")):
        self.config_dir = config_dir
        self._regions: Dict[str, RegionSpec] = {}
        self._unicode_normalizer = UnicodeNormalizer()
        self._security_validator = SecurityValidator()  # Add security validation
        self._lang_detector = None
        self._lang_detector_loaded = False
        self._diaspora_config = {}
        self._doi_prefix_map = {}
        self._regions_loaded = False
        # Expert solution: Bounded cache to prevent memory growth
        self._detection_cache = SizedLRU(max_bytes=64 * 1024 * 1024)  # 64MB cache
        # Phase 2 ML models (stubs until trained)
        self._ml_models_loaded = False
        self._ft = None
        self._clf = None
        # Phase 3 Authority cache (SizedLRU with ~10MB limit)
        self._authority_cache = SizedLRU(max_bytes=10 * 1024 * 1024)
        # Phase 2 Step 7: Surname fastText model (lazy loaded, Python or CLI)
        self._surname_ft = None
        self._surname_ft_attempted = False
        self._surname_ft_cli_path = None
        self._surname_ft_model_path = None
        # Persistent fastText CLI worker (lazy-spawned; see FastTextCLIWorker).
        # Owns exactly one subprocess for the lifetime of this RegionManager.
        self._ft_cli_worker: Optional["FastTextCLIWorker"] = None
        self._initialize_core()

    def _load_signal_sets(self):
        """
        Expert Phase 3: Load JSONL signal files from GMNAP_SIGNALS_DIR (recursively).
        Caches in-memory for performance. Each signal has: id, region, subregion, kind,
        field, value, regex, weight, priority, gates (optional).
        """
        import glob
        import json
        import os

        if RegionManager.SIGNALS_CACHE is not None:
            return RegionManager.SIGNALS_CACHE
        base = os.environ.get(self.SIGNALS_DIR_ENV)
        out = []
        if base and os.path.isdir(base):
            for fp in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True):
                with open(fp, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            out.append(json.loads(line))
                        except Exception:
                            continue
        RegionManager.SIGNALS_CACHE = out
        logger.info(
            f"Expert Phase 3: Loaded {len(out)} lexical signals from {base or 'no directory'}"
        )
        return out

    def _score_with_signals(self, entry):
        """
        Expert Phase 3: Score candidate regions using loaded lexical signals.
        Returns: (scores: dict[region_code->float], matched_signal_ids: list[str])
        """
        signals = self._load_signal_sets()
        full = (
            entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        ).lower()
        given = (entry.get("Given") or "").lower()
        surname = (entry.get("Surname") or "").lower()
        scores = {}
        matched = []
        for s in signals:
            # Skip country signatures (they use affiliation data, not name patterns)
            if "country" in s:
                continue
            # If Given/Surname not provided, try matching against full name for all fields
            if s["field"] == "full":
                field_text = full
            elif s["field"] == "given":
                field_text = given if given else full
            else:  # surname
                field_text = surname if surname else full
            if not field_text:
                continue
            val = s["value"]
            ok = False
            if s.get("regex"):
                import re

                try:
                    if re.search(val, field_text):
                        ok = True
                except re.error:
                    continue
            else:
                if s["kind"] == "prefix":
                    ok = field_text.startswith(val.strip())
                elif s["kind"] == "suffix":
                    ok = field_text.endswith(val)
                elif s["kind"] == "token":
                    # Token match requires word boundaries (not substring)
                    ok = f" {val} " in f" {field_text} " or field_text == val
                else:
                    ok = val in field_text
            if ok:
                r = s["region"]
                scores[r] = scores.get(r, 0.0) + float(s.get("weight", 1.0))
                matched.append(s["id"])
        return scores, matched

    def _detect_by_priority_signals(self, entry, fallback=None):
        """
        Expert Phase 3: Detect region using lexical signal ensemble.
        Returns detection result with region_code, confidence, method, and matched signals.
        """
        scores, matched = self._score_with_signals(entry)
        if not scores:
            return fallback
        best_region = max(scores.items(), key=lambda kv: kv[1])[0]
        conf = min(0.98, 0.50 + (scores[best_region] / 10.0))
        return {
            "region_code": best_region,
            "confidence": conf,
            "detection_method": "lex-signal-ensemble",
            "metadata": {"matched_signals": matched, "scores": scores},
        }

    def load_ml_models(self, fasttext_path=None, clf_path=None):
        """Phase 2: Load ML models for ensemble detection."""
        if not FASTTEXT_AVAILABLE:
            logger.warning(
                "ML models not loaded: fasttext package not available (Docker minimal mode)"
            )
            self._ml_models_loaded = False
            return

        import pickle

        try:
            if fasttext_path:
                self._ft = fasttext.load_model(fasttext_path)
                logger.info(f"Loaded FastText model from {fasttext_path}")
            if clf_path:
                # Load the full model bundle (includes vectorizers)
                with open(clf_path, "rb") as f:
                    bundle = pickle.load(f)
                    self._clf = bundle["model"]
                    self._label_encoder = bundle["label_encoder"]
                    self._tfidf = bundle["tfidf"]
                    self._cat_vectorizer = bundle["cat_vectorizer"]
                logger.info(f"Loaded classifier bundle from {clf_path}")
            self._ml_models_loaded = True
        except Exception as e:
            logger.warning(f"Failed to load ML models: {e}")
            self._ml_models_loaded = False  # Hard fail-safe

    def _extract_ml_features(self, name: str):
        """Phase 2: Extract features matching training code."""
        import numpy as np

        name_lower = name.lower()
        tokens = name_lower.split()

        # Numeric features
        numeric_features = [
            len(name_lower),  # length
            len(tokens),  # token_count
            int("-" in name),  # has_hyphen
            int("'" in name),  # has_apostrophe
            np.mean([len(t) for t in tokens]) if tokens else 0,  # avg_token_len
            max([len(t) for t in tokens]) if tokens else 0,  # max_token_len
            (
                sum(1 for c in name_lower if c in "aeiou") / len(name_lower)
                if name_lower
                else 0
            ),  # vowel_ratio
            int(any(ord(c) > 127 for c in name)),  # has_diacritic
        ]

        # Categorical features (suffix/prefix patterns)
        suffix_2 = tokens[-1][-2:] if tokens and len(tokens[-1]) >= 2 else ""
        suffix_3 = tokens[-1][-3:] if tokens and len(tokens[-1]) >= 3 else ""
        suffix_4 = tokens[-1][-4:] if tokens and len(tokens[-1]) >= 4 else ""
        prefix_2 = tokens[0][:2] if tokens and len(tokens[0]) >= 2 else ""
        prefix_3 = tokens[0][:3] if tokens and len(tokens[0]) >= 3 else ""

        categorical = "_".join([suffix_2, suffix_3, suffix_4, prefix_2, prefix_3])

        return numeric_features, name_lower, categorical

    def _detect_by_ml_ensemble(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Phase 2: ML ensemble detection using trained models."""
        if not self._ml_models_loaded:
            return None
        if not hasattr(self, "_clf") or self._clf is None:
            return None

        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        if not name:
            return None

        try:
            import numpy as np

            # Extract features matching training
            numeric_feats, name_lower, categorical = self._extract_ml_features(name)

            # TF-IDF char n-grams
            tfidf_feats = self._tfidf.transform([name_lower]).toarray()

            # Categorical features
            cat_data = [{"cat": categorical}]
            cat_feats = self._cat_vectorizer.transform(cat_data)

            # Combine all features
            X = np.hstack(
                [np.array(numeric_feats).reshape(1, -1), tfidf_feats, cat_feats]
            )

            # Predict
            y_pred = self._clf.predict(X)[0]
            y_proba = self._clf.predict_proba(X)[0]

            region = self._label_encoder.inverse_transform([y_pred])[0]
            confidence = float(y_proba.max())

            # Optional: Combine with FastText if available
            ft_region = None
            if self._ft and hasattr(self._ft, "predict"):
                ft_pred = self._ft.predict(name.replace("-", " "), k=1)
                if ft_pred and len(ft_pred[0]) > 0:
                    ft_region = ft_pred[0][0].replace("__label__", "")

            # Only return if confidence >= 0.85 (expert's target)
            if confidence >= 0.85:
                return RegionDetectionResult(
                    region_code=region,
                    confidence=min(confidence, 0.95),
                    detection_method="ml-ensemble",
                    metadata={
                        "xgb_region": region,
                        "xgb_confidence": confidence,
                        "ft_region": ft_region,
                    },
                )

            return None

        except Exception as e:
            logger.debug(f"ML ensemble detection failed: {e}")
            return None

    async def _detect_by_external_authority(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """
        Phase 3: External authority detection (cache-only in OFFLINE mode).

        Per expert's spec: Only uses cache, never blocks on live API calls in Quick mode.
        Later: Add async fetchers (ORCID/Wikidata/DOI) with TTL caching.
        """
        import os

        # Only if OFFLINE=0 and cached hit exists; otherwise skip
        if os.getenv("OFFLINE", "1") == "1":
            return None
        gid = entry.get("GlobalID") or entry.get("ID")
        if not gid:
            return None
        hit = self._authority_cache.get(gid)
        if not hit:
            return None
        # hit = {"region": "E1", "conf": 0.95, "source": "orcid-country"}
        return RegionDetectionResult(
            region_code=hit["region"],
            confidence=hit["conf"],
            detection_method=f"auth-{hit['source']}",
            metadata={"authority_source": hit.get("source"), "cached": True},
        )

    def add_authority_cache_entry(
        self, global_id: str, region: str, confidence: float, source: str
    ):
        """
        Phase 3: Add an entry to the authority cache.

        Args:
            global_id: GlobalID or ID for the entry
            region: Region code (e.g., "E1", "A2")
            confidence: Confidence score (0.0-1.0, typically ≥0.90 for authorities)
            source: Source name (e.g., "orcid-country", "wikidata", "doi-affiliation")
        """
        if not global_id or not region:
            return

        cache_entry = {"region": region, "conf": confidence, "source": source}
        self._authority_cache.put(global_id, cache_entry)
        logger.debug(
            f"Added authority cache: {global_id} → {region} ({confidence:.2f}, {source})"
        )

    def load_authority_cache_from_file(self, filepath: str):
        """
        Phase 3: Load authority cache from JSON/JSONL file.

        Expected format (JSONL):
        {"id": "some-global-id", "region": "E1", "conf": 0.95, "source": "orcid-country"}

        Or JSON array:
        [{"id": "...", "region": "...", "conf": 0.95, "source": "..."}]
        """
        import json
        import os

        if not os.path.exists(filepath):
            logger.warning(f"Authority cache file not found: {filepath}")
            return 0

        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                # Try JSONL first
                first_char = f.read(1)
                f.seek(0)

                if first_char == "[":
                    # JSON array
                    data = json.load(f)
                    for entry in data:
                        if "id" in entry and "region" in entry:
                            self.add_authority_cache_entry(
                                global_id=entry["id"],
                                region=entry["region"],
                                confidence=entry.get(
                                    "conf", entry.get("confidence", 0.95)
                                ),
                                source=entry.get("source", "file-import"),
                            )
                            count += 1
                else:
                    # JSONL
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if "id" in entry and "region" in entry:
                                self.add_authority_cache_entry(
                                    global_id=entry["id"],
                                    region=entry["region"],
                                    confidence=entry.get(
                                        "conf", entry.get("confidence", 0.95)
                                    ),
                                    source=entry.get("source", "file-import"),
                                )
                                count += 1
                        except json.JSONDecodeError:
                            continue

            logger.info(f"Loaded {count} authority cache entries from {filepath}")
            return count

        except Exception as e:
            logger.error(f"Failed to load authority cache from {filepath}: {e}")
            return 0

    def get_authority_cache_stats(self) -> Dict[str, Any]:
        """Phase 3: Get statistics about the authority cache."""
        return {
            "entries": (
                len(self._authority_cache._data)
                if hasattr(self._authority_cache, "_data")
                else 0
            ),
            "size_bytes": (
                self._authority_cache._size
                if hasattr(self._authority_cache, "_size")
                else 0
            ),
            "max_bytes": (
                self._authority_cache.max_bytes
                if hasattr(self._authority_cache, "max_bytes")
                else 0
            ),
        }

    @property
    def lang_detector(self):
        """Lazy-load the FastText language detector."""
        if not self._lang_detector_loaded:
            self._lang_detector_loaded = True
            self._lang_detector = get_fasttext_model(self.config_dir)
            if self._lang_detector:
                logger.info("FastText language detector loaded (lazy)")
            else:
                logger.warning("FastText language detector not available")
        return self._lang_detector

    def _initialize_core(self):
        """Initialize only core components (not regions)."""
        # FastText model will be loaded lazily when needed
        # self._lang_detector = get_fasttext_model(self.config_dir)

        # Load diaspora configuration
        self._load_diaspora_config()

        # Load DOI prefix mappings
        self._load_doi_prefix_map()

        # Initialize script to region mappings (only implemented regions)
        self._init_script_mappings()

        # Initialize surname pattern databases
        self._init_surname_patterns()

    def _load_diaspora_config(self):
        """Load diaspora overlay configuration."""
        diaspora_path = self.config_dir / "diaspora.yaml"
        if diaspora_path.exists():
            import yaml

            with open(diaspora_path) as f:
                self._diaspora_config = yaml.safe_load(f) or {}
            logger.info(
                f"Loaded diaspora config with {len(self._diaspora_config)} entries"
            )

    def _load_doi_prefix_map(self):
        """Load DOI prefix to country mappings."""
        # Common DOI prefixes and their associated countries
        self._doi_prefix_map = {
            "10.1007": "DE",  # Springer (Germany)
            "10.1016": "NL",  # Elsevier (Netherlands)
            "10.1038": "GB",  # Nature (UK)
            "10.1126": "US",  # Science (USA)
            "10.1002": "US",  # Wiley (USA)
            "10.1021": "US",  # ACS (USA)
            "10.1088": "GB",  # IOP (UK)
            "10.1103": "US",  # APS (USA)
            "10.1109": "US",  # IEEE (USA)
            "10.1145": "US",  # ACM (USA)
            "10.1137": "US",  # SIAM (USA)
            "10.1090": "US",  # AMS (USA)
            "10.1063": "US",  # AIP (USA)
            "10.1093": "GB",  # Oxford (UK)
            "10.1017": "GB",  # Cambridge (UK)
            "10.3390": "CH",  # MDPI (Switzerland)
            "10.1080": "GB",  # Taylor & Francis (UK)
            "10.1111": "GB",  # Blackwell (UK)
            "10.1155": "US",  # Hindawi (USA/Egypt)
            "10.1371": "US",  # PLOS (USA)
            "10.4171": "CH",  # EMS (Switzerland)
        }

    def _init_script_mappings(self):
        """Initialize Unicode script to region mappings (all V7 regions)."""
        # Map to all V7 regions that are actually implemented
        self._script_to_regions = {
            "Latin": [
                r
                for r in [
                    # Western families first (still candidates)
                    "A1",
                    "A2",
                    "A3",
                    "A4",
                    "A5",
                    # Slavic & Greek (romanized forms common)
                    "B1",
                    "B2",
                    "B3",  # East Slavic, South Slavic, Greek (romanized)
                    # Middle East & Caucasus (all can be romanized)
                    "C1",
                    "C2",
                    "C3",
                    "C4",
                    "C5",
                    "C6",
                    "C7",
                    "C8",
                    "C9",
                    # South Asia (romanized extensively)
                    "D1",
                    "D2",
                    "D3",
                    "D4",
                    "D5",
                    # East/Southeast Asia (romanized forms)
                    "E1",  # Sinophone Mainland (Pinyin)
                    "E2",  # Traditional Chinese (Wade-Giles/Cantonese)
                    "E3",  # Japan (Hepburn/Kunrei romanization)
                    "E4",  # Korea (RR/MR romanization)
                    "E5",  # Vietnam (Quốc ngữ Latin script)
                    "E6",  # Mainland SEA (Thai/Lao/Khmer/Myanmar romanized)
                    "E7",  # Maritime SEA (Indonesian/Malay/Filipino Latin)
                    # Sub-Saharan Africa (mostly Latin script)
                    "F1",
                    "F2",
                    "F3",
                    "F4",
                    # Latin America
                    "G1",
                    # Special regions
                    "H1",  # Historical (Latin/romanized classical names)
                    "R0",  # Residual Latin ASCII
                ]
                if r in self.IMPLEMENTED_REGIONS
            ],
            "Cyrillic": [
                r for r in ["B1", "B2", "C1"] if r in self.IMPLEMENTED_REGIONS
            ],
            "Greek": [r for r in ["B3"] if r in self.IMPLEMENTED_REGIONS],
            "Arabic": [
                r
                for r in ["C1", "C2", "C3", "C4", "C5"]
                if r in self.IMPLEMENTED_REGIONS
            ],
            "Hebrew": [r for r in ["C6"] if r in self.IMPLEMENTED_REGIONS],
            "Devanagari": [r for r in ["D1", "D2"] if r in self.IMPLEMENTED_REGIONS],
            "Bengali": [r for r in ["D3"] if r in self.IMPLEMENTED_REGIONS],
            "Tamil": [r for r in ["D2"] if r in self.IMPLEMENTED_REGIONS],
            "Telugu": [r for r in ["D2"] if r in self.IMPLEMENTED_REGIONS],
            "Sinhala": [r for r in ["D5"] if r in self.IMPLEMENTED_REGIONS],
            "Thai": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Myanmar": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Georgian": [r for r in ["C8"] if r in self.IMPLEMENTED_REGIONS],
            "Armenian": [r for r in ["C7"] if r in self.IMPLEMENTED_REGIONS],
            "CJK": [r for r in ["E1", "E2", "E3"] if r in self.IMPLEMENTED_REGIONS],
            "Hangul": [r for r in ["E4"] if r in self.IMPLEMENTED_REGIONS],
            "Ethiopic": [r for r in ["F3"] if r in self.IMPLEMENTED_REGIONS],
            "Vietnamese": [r for r in ["E5"] if r in self.IMPLEMENTED_REGIONS],
            "Khmer": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Lao": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Malay": [r for r in ["E7"] if r in self.IMPLEMENTED_REGIONS],
        }

    def _ensure_regions_loaded(self):
        """Lazy load regions only when needed."""
        if not self._regions_loaded:
            self._load_regions()
            self._regions_loaded = True

    def register_region(self, region: RegionSpec) -> None:
        """Register a region specification."""
        # Only register if it's in the implemented list
        if region.code in self.IMPLEMENTED_REGIONS:
            self._regions[region.code] = region
            logger.info(
                f"Registered region {region.code}: {REGION_CODES.get(region.code)}"
            )
        else:
            logger.debug(f"Skipping unimplemented region {region.code}")

    def get_region(self, code: str) -> Optional[RegionSpec]:
        """Get region specification by code."""
        self._ensure_regions_loaded()
        return self._regions.get(code)

    def detect_region(self, entry: Dict[str, Any]) -> RegionDetectionResult:
        """
        Detect region for an entry using multi-stage detection.

        Args:
            entry: Dictionary containing entry data
        """
        # SECURITY: Validate and sanitize entry before processing
        try:
            sanitized_entry = self._security_validator.validate_entry(entry)
        except SecurityError as e:
            # Return safe error result without exposing attack details
            logger.warning(f"Security validation failed: {e}")
            return RegionDetectionResult(
                region_code="XX",  # Unknown/error region
                confidence=0.0,
                detection_method="security_blocked",
                metadata={"error": "Invalid input detected"},
            )

        # Ensure regions are loaded
        self._ensure_regions_loaded()

        # Create cache key from sanitized entry data — include CountryCodes
        # to avoid collisions when the same name appears with different CCs
        # (e.g. "Lee, Bruce" with CC=US vs CC=KR must not share a cache slot).
        cc = ",".join(sanitized_entry.get("CountryCodes", []))
        inst = sanitized_entry.get("Institution", "")
        # BirthYear participates because the diaspora overlay (spec §3) makes
        # geo detection ERA-dependent: the same name+CC can resolve to
        # different geo regions in different eras (e.g. TH pre/post-2015).
        # Without it, era-distinct entries collide in one cache slot (R49).
        by = str(sanitized_entry.get("BirthYear", ""))
        cache_key = (
            (
                sanitized_entry.get("CanonicalLatin", "")
                or sanitized_entry.get("CanonicalNative", "")
            )
            + "|"
            + cc
            + "|"
            + inst
            + "|"
            + by
        )

        # Check cache
        cached_result = self._detection_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Detect region — ALWAYS via the synchronous path. detect_region
        # is a sync method, and detection's authority phase is correctly
        # cache-only (live authority fetches are stage 4's job, not the
        # per-entry detection hot path). This previously picked sync-vs-
        # async by whether an event loop was running:
        #   - async caller (the API)  -> _detect_region_uncached_sync
        #     -> _infer_name_origin (cache-only authority)
        #   - sync caller (CLI/tests) -> asyncio.run(_..._async)
        #     -> _infer_name_origin_async (LIVE _detect_by_external_authority)
        # so the SAME entry was routed through DIFFERENT authority logic
        # depending on the caller's context (a context-dependent detection
        # divergence at OFFLINE=0). Using the sync path unconditionally
        # makes detection deterministic across the API, CLI and tests, and
        # drops the asyncio.run()/get_running_loop dance entirely. (The
        # async _detect_region_uncached_async / _infer_name_origin_async
        # are now unused by detection.)
        result = self._detect_region_uncached_sync(sanitized_entry)

        # Optional confidence calibration (PAV isotonic, opt-in via
        # GMNAP_CALIBRATE_CONFIDENCE=1). When disabled, this is a
        # no-op identity. Applied *before* caching so cached values
        # already carry the calibrated score.
        #
        # Hot path: when the env var is unset, `_apply_calibration`
        # returns its input unchanged via `os.getenv` short-circuit,
        # so we pay one function call + one env-var read per
        # detection. We avoid `getattr`/`float()` on the fast path
        # because RegionDetectionResult always has a numeric
        # `confidence` field on a successful detection.
        if result is not None and result.confidence is not None:
            calibrated = _apply_calibration(result.confidence)
            if calibrated != result.confidence:
                # RegionDetectionResult is a dataclass; build a new
                # one with the calibrated confidence rather than
                # mutating in place (the cache holds references).
                result = dataclasses.replace(result, confidence=calibrated)

        # Cache result
        if cache_key:
            self._detection_cache.put(cache_key, result)

        return result

    def _infer_geo(self, entry: Dict[str, Any]):
        """Geographic inference: CC -> ROR -> structured affiliation -> DOI."""
        # Diaspora overlay (spec §3): era-scoped CC->region overrides take
        # precedence over the static territory mapping.
        overlay = self._detect_by_diaspora(entry)
        if overlay is not None:
            return (
                overlay.region_code,
                overlay.confidence,
                overlay.detection_method,
                overlay.metadata,
            )

        # CountryCodes
        country_codes = entry.get("CountryCodes", [])

        # Region overlay map (spec §2a) — R55 wiring. Sub-national codes
        # ("IN-WB", "CH-FR", "LK-TA", …) are strictly more specific than the
        # 2-letter CC, so they take precedence over the plain territory
        # lookup: "IN-WB" -> D3 (Bengali) where bare "IN" -> D1. Scan ALL
        # provided codes (an entry may carry ["IN-WB", "IN"]). Before this,
        # a sub-national code silently fell through get_region_for_territory
        # to R0 and the entry lost its geo signal entirely.
        from src.regions.base import get_region_for_overlay

        for code in country_codes:
            if not isinstance(code, str):
                continue
            overlay_region = get_region_for_overlay(code)
            if overlay_region and overlay_region in self.IMPLEMENTED_REGIONS:
                return (
                    overlay_region,
                    0.88,  # above the 0.85 plain-CC path: strictly more specific
                    "region-overlay",
                    {"overlay_code": code.upper().strip()},
                )

        if country_codes:
            region = get_region_for_territory(country_codes[0])
            if region in self.IMPLEMENTED_REGIONS:
                return (region, 0.85, "country-code", {"country": country_codes[0]})

        # Institution/ROR
        result = self._detect_by_affiliation(entry)
        if result and result.confidence >= 0.80:
            return (
                result.region_code,
                result.confidence,
                result.detection_method,
                result.metadata,
            )

        # DOI prefix
        result = self._detect_by_doi(entry)
        if result:
            return (
                result.region_code,
                result.confidence,
                result.detection_method,
                result.metadata,
            )

        return None

    def _run_name_origin_cascade(self, entry: Dict[str, Any]):
        """Shared name-origin cascade used by both sync and async paths.

        Returns a (region, confidence, method, metadata) tuple.
        """
        # Decisive-script fast path (R52): Hangul is used ONLY for Korean —
        # unlike Han ideographs (shared across CJK), ANY Hangul character is
        # conclusive. This must precede surname-exact: "Lee, 정은" was
        # resolving A1@0.95 via the adjudicated-Anglo surname "Lee" with the
        # Hangul given name never examined, and single-jamo surnames
        # ("김, Min-jun") fell through to R0 because the script-ratio
        # threshold ignored short Hangul runs.
        name_for_script = entry.get("CanonicalLatin", "") or entry.get(
            "CanonicalNative", ""
        )
        if any(
            "\uac00" <= ch <= "\ud7af" or "\u1100" <= ch <= "\u11ff"
            for ch in name_for_script
        ):
            return ("E4", 0.95, "script-hangul", {"script": "Hangul"})

        # Surname exact match (high confidence)
        result = self._detect_by_surname(entry)
        if result and result.confidence >= 0.95:
            # A1/G1 mixed-name check: if surname matches G1 but is also
            # a common Hispanic-in-A1 name, skip to scorer for disambiguation
            surname = result.metadata.get("surname", "")
            if result.region_code == "G1" and surname in _HISPANIC_SHARED_SURNAMES:
                pass  # let the scorer handle A1/G1 competition
            else:
                return (
                    result.region_code,
                    result.confidence,
                    result.detection_method,
                    result.metadata,
                )

        # Hybrid CJK name detection
        result = self._detect_hybrid_name(entry)
        if result and result.confidence >= 0.95:
            return (
                result.region_code,
                result.confidence,
                result.detection_method,
                result.metadata,
            )

        # Script + priority rules
        scorer_hint = {}  # Capture group/candidate hints from scorer abstentions
        result = self._detect_by_script(entry)
        if result:
            if result.detection_method in ("scorer-abstain", "weak-evidence-abstain"):
                # Capture group hint from scorer for terminal R0 metadata.
                # weak_group/weak_best_region (R58) ride along for the
                # same-group fastText gate below but are deliberately NOT the
                # 'group' key — terminal R0 must not claim a group_region
                # from a sub-2.0 single-suffix hit.
                scorer_hint = {
                    k: v
                    for k, v in result.metadata.items()
                    if k
                    in (
                        "group",
                        "best_region",
                        "best_score",
                        "margin",
                        "reason",
                        "weak_group",
                        "weak_best_region",
                    )
                }
                # R58.8 (adversarial verification): a 'given_only_no_surname'
                # abstention scores GIVEN-name fragments only — often a
                # coin-flip tie between groups. Its group/best_region must
                # neither anchor the ft gate (verified wrong leaves: 'Thabo
                # Mbeki'→E3/JAPANESE@0.74, 'Ján Ďurica'→A2) nor surface as an
                # output group_region claim (verified wrong claims: Wee→
                # ANGLO, 'Mitra Fatemi'→JAPANESE, 'Martin Ødegaard'→SLAVIC).
                # The reason stays for debugging; the authority dies here.
                if scorer_hint.get("reason") == "given_only_no_surname":
                    scorer_hint.pop("group", None)
                    scorer_hint.pop("best_region", None)
                    scorer_hint.pop("weak_group", None)
                    scorer_hint.pop("weak_best_region", None)
                # R59.2 (held-out finding: 'Mohsen Asgharzadeh' abstained
                # with a NORDIC_BALTIC claim): a DEAD TIE (margin == 0, e.g.
                # A3 2.5 vs C2 2.5) carries no group information — which
                # side lands in best_region is arbitrary. A tie claims
                # nothing.
                if (
                    scorer_hint.get("margin") == 0
                    and scorer_hint.get("reason") == "low_score_or_margin"
                ):
                    scorer_hint.pop("group", None)
                    scorer_hint.pop("best_region", None)
            elif (
                result.detection_method == "script"
                and result.metadata.get("script") == "Latin"
            ):
                pass  # Latin script fallback is unreliable for name-origin; skip
            elif result.confidence >= 0.60:
                result = self._apply_affiliation_tiebreak(entry, result)
                return (
                    result.region_code,
                    result.confidence,
                    result.detection_method,
                    result.metadata,
                )

        # ICU processing
        result = self._detect_by_icu(entry)
        if result and result.confidence >= 0.60:
            result = self._apply_affiliation_tiebreak(entry, result)
            return (
                result.region_code,
                result.confidence,
                result.detection_method,
                result.metadata,
            )

        # FastText language detection
        if self.lang_detector:
            result = self._detect_by_language(entry)
            if result and result.confidence >= 0.7:
                return (
                    result.region_code,
                    result.confidence,
                    result.detection_method,
                    result.metadata,
                )

        # R58: orthographic group anchor (src/regions/detection/orthography.py)
        # — distinctive surname diacritics establish a GROUP so the same-group
        # gate below can let fastText refine to a leaf. Never overrides a real
        # scorer group. Judge modifications: Tier-1 signature marks beat weak
        # suffix hints; a Tier-2 anchor CONFLICTING with a weak hint yields no
        # anchor; a confident cross-group ft verdict (>=0.80) vetoes Tier-2.
        ortho = None
        if not scorer_hint.get("group"):
            from src.regions.detection.orthography import detect_ortho_group_anchor

            ortho = detect_ortho_group_anchor(
                entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
            )
            weak = scorer_hint.get("weak_group")
            if ortho is not None and ortho.tier == 2 and weak:
                if ortho.kind in ("group", "group_cap") and ortho.payload != weak:
                    ortho = None
                elif ortho.kind == "permitted" and weak not in ortho.payload:
                    ortho = None

        # Surname fastText model (Step 7 - lazy loaded, same-group gated)
        ft_result = self._detect_by_surname_fasttext(entry)
        ortho_vetoed = False
        if ft_result:
            ft_group = LEAF_TO_GROUP.get(ft_result.region_code)
            rules_group = scorer_hint.get("group")
            # R58: a weak-evidence (<2.0) scorer hit still anchors the gate —
            # ft may refine it WITHIN that group ('Kratsios' weak-HELLENIC +
            # ft B3 -> B3), while a cross-group ft verdict lets the weak hint
            # die with the abstention ('Lörler' weak-HELLENIC + ft A2 -> R0).
            anchor_group = rules_group or scorer_hint.get("weak_group")

            # Tier-2 ortho anchors are VETOED by a confident cross-group ft
            # verdict (the Maghrebi-French trap: 'René Aïd' carries ï but ft
            # says ARABIC — the orthography is transliteration, not French
            # origin). Tier-1 signature marks are veto-immune. R59.5: the
            # veto consults the FOLDED surname as a second witness when the
            # raw-form verdict misses the bar — the de-biased model splits
            # its confidence across romanization variants ('aïd' C3@0.57
            # raw, 'aid' C5@0.89 folded; both ARABIC-family, and the old
            # model's raw 0.90 was a geo-label artifact). Same 0.80 bar,
            # no new thresholds.
            if ortho is not None and ortho.tier == 2 and ft_group:
                ft_prob = ft_result.metadata.get("ft_prob", 0)

                def _cross_group_confident(target_ok) -> bool:
                    if not target_ok(ft_group) and ft_prob >= 0.80:
                        return True
                    raw_sur = ft_result.metadata.get("surname") or ""
                    folded = (
                        unicodedata.normalize("NFKD", raw_sur)
                        .encode("ascii", "ignore")
                        .decode("ascii")
                    )
                    if folded and folded != raw_sur:
                        fp = self._ft_folded_verdict(folded)
                        if fp is not None:
                            f_group, f_prob = fp
                            if not target_ok(f_group) and f_prob >= 0.80:
                                return True
                    return False

                if ortho.kind in ("group", "group_cap"):
                    if _cross_group_confident(lambda g: g == ortho.payload):
                        ortho = None
                        ortho_vetoed = True
                elif ortho.kind == "permitted":
                    if _cross_group_confident(lambda g: g in ortho.payload):
                        ortho = None
                        ortho_vetoed = True

            # Ortho anchors join the gate: a 'group' anchor acts like a rules
            # group; 'permitted' sets accept ft leaves inside the set;
            # 'group_cap' (Benaïm guard) never licenses a LEAF — the group
            # claim it justifies is surfaced on the terminal abstention below.
            if anchor_group is None and ortho is not None:
                if ortho.kind == "group":
                    anchor_group = ortho.payload
                # R59.5: an ANCHORLESS multi-group 'permitted' set no longer
                # licenses a leaf. The removed branch let fastText choose
                # BETWEEN the set's groups (š/č/ž -> {SLAVIC, BALTIC}), which
                # is exactly the decision the same-group principle forbids —
                # and the R59 retrained model produced the measured
                # counterexample: 'Grušas, Gintaras' (Lithuanian, C9) emitted
                # B2@0.75 because ft was confidently wrong ACROSS the set's
                # group boundary (B2@0.93). The flaw was latent with the old
                # geo-labeled model only because it rarely cleared the
                # prob/margin bar here. Permitted sets still function where
                # they are principled: intersected with a weak scorer hint
                # (single group, above) and as an ft-veto surface. Bare
                # permitted-sets claim nothing — the terminal abstention
                # keeps them out of group-level output too.

            if anchor_group is not None:
                # An anchor exists — fastText must agree with it.
                # R58: ft emission additionally requires a >=4-char surname,
                # UNCONDITIONALLY. Reaching this tier at all means the scorer
                # abstained, so every anchor here is a HINT (scorer-abstain
                # group — often driven by GIVEN names — or a sub-2.0 weak
                # suffix), never a confirmed group. Short romanized surnames
                # are homograph territory across families: 'Timothy L. H.
                # Wee' got an ANGLO hint from its given names while the
                # surname 'wee' (adjudicated E1, Chinese-Singaporean) drew
                # ft's documented-biased A1@0.999 — hint and model error
                # CORRELATE, so agreement is not independent evidence. The
                # >=4 cutoff mirrors the curated dictionary's P2 policy,
                # which excludes tan/yan/wee/foo/ng for the same reason.
                surname_len = len(
                    (ft_result.metadata.get("surname") or "").replace(" ", "")
                )
                if ft_group == anchor_group and surname_len >= 4:
                    # Same group: accept with tighter threshold
                    if (
                        ft_result.metadata.get("ft_prob", 0) >= 0.70
                        and (
                            ft_result.metadata.get("ft_prob", 0)
                            - ft_result.metadata.get("ft_prob2", 0)
                        )
                        >= 0.20
                    ):
                        ft_result.metadata["gated"] = (
                            "same_group" if rules_group else "same_group_weak"
                        )
                        return (
                            ft_result.region_code,
                            ft_result.confidence,
                            ft_result.detection_method,
                            ft_result.metadata,
                        )
                # Different group: reject fastText, keep rules group hint
            # R58: the former 'ft_only_high_conf' branch (raw promotion with
            # NO group anchor at prob>=0.80, margin>=0.25) is REMOVED, and no
            # threshold knob may ever reinstate it. Measured against the
            # 271-name adjudicated pilot ground truth, raw promotion tops out
            # at 77-81% verifiable-leaf precision even at prob>=0.99, and the
            # model is confidently wrong AT prob 1.0 ('U. Cetin'->A1@1.00,
            # true C1; 'R. S. Hazra'->A1@1.00, true D3; 'Nizar
            # Touzi'->A1@0.98, true C3) with a systematic A1 over-prediction
            # bias. The project's contract is 100% emitted-leaf precision:
            # fastText NEVER emits without a group anchor (scorer, weak-
            # evidence, or orthographic). See docs/calibration.md (R58) and
            # tools/ft_threshold_sweep.py for the reproducible rejection.

        # Terminal: R0 (never A1). Include scorer hints for group-level output.
        # R58: an unvetoed orthographic 'group'/'group_cap' anchor is honest
        # group-level knowledge even when no leaf could be emitted — surface
        # it so GroupRegion carries e.g. GERMANIC_WESTERN for 'Pagès' (the
        # Benaïm guard capped the leaf, not the group). Vetoed anchors and
        # bare permitted-sets claim nothing. Tier-2 anchors surface ONLY when
        # the ft veto had its chance (a rules-only install must not claim
        # GERMANIC for Maghrebi-French 'Aïd' just because no model was there
        # to contradict it); Tier-1 signature marks are exclusive by
        # construction and stand on their own.
        if (
            ortho is not None
            and not ortho_vetoed
            and ortho.kind in ("group", "group_cap")
            and (ortho.tier == 1 or ft_result is not None)
        ):
            # R58.8: group_region is promoted by _merge_geo_name from
            # metadata['best_region'] via LEAF_TO_GROUP — the 'group' key
            # alone never reaches the output axis (verified: the R58.5
            # terminal left GroupRegion=None). Supply a deterministic
            # representative leaf of the anchored group so the claim is
            # actually visible downstream.
            rep_leaf = min(
                (l for l, g in LEAF_TO_GROUP.items() if g == ortho.payload),
                default=None,
            )
            scorer_hint = {
                **scorer_hint,
                "group": ortho.payload,
                "reason": "ortho-group-anchor",
                "ortho_marks": ortho.marks,
            }
            if rep_leaf:
                scorer_hint["best_region"] = rep_leaf
        return ("R0", 0.10, "name-abstain", scorer_hint)

    def _infer_name_origin(self, entry: Dict[str, Any]):
        """Name-origin inference: patterns -> scorer -> ML -> R0 (terminal)."""
        # Phase 3: Authority detection (cache-only, synchronous)
        import os

        if os.getenv("OFFLINE", "1") == "0":
            gid = entry.get("GlobalID") or entry.get("ID")
            if gid:
                hit = self._authority_cache.get(gid)
                if hit and hit.get("conf", 0) >= 0.90:
                    return (
                        hit["region"],
                        hit["conf"],
                        f"auth-{hit['source']}",
                        {"authority_source": hit.get("source"), "cached": True},
                    )

        # Phase 2: ML ensemble (returns None if models not loaded)
        result = self._detect_by_ml_ensemble(entry)
        if result and result.confidence >= 0.85:
            return (
                result.region_code,
                result.confidence,
                result.detection_method,
                result.metadata,
            )

        return self._run_name_origin_cascade(entry)

    @staticmethod
    def _merge_geo_name(geo, name):
        """Merge geo and name-origin inference into a final result.

        Priority logic:
        - CC-based geo is explicit ground truth → always primary for region_code
        - Name-origin goes into name_region for diaspora detection
        - When no CC, name-origin is primary
        - Conflict flagged when geo and name disagree
        """
        conflict = geo is not None and name[0] != "R0" and geo[0] != name[0]

        # CC-based geo is explicit ground truth — always wins for region_code.
        # Name-origin is preserved in name_region for diaspora detection.
        if geo is not None and geo[2] == "country-code":
            primary = geo
        elif name[0] != "R0":
            primary = name
        elif geo is not None:
            primary = geo
        else:
            # Use name tuple directly to preserve scorer hints (group, best_region)
            primary = name

        # Surface group_region: from LEAF_TO_GROUP for known regions,
        # or from scorer hints when R0 (the scorer may know the group
        # even when it can't determine the leaf).
        group = LEAF_TO_GROUP.get(primary[0])
        if not group and primary[0] == "R0":
            # Check scorer hints for group-level output
            hint_region = primary[3].get("best_region")
            if hint_region:
                group = LEAF_TO_GROUP.get(hint_region)

        # Determine resolution level
        if primary[0] in ("R0", "Z0"):
            resolution = "group" if group else "abstain"
        else:
            resolution = "leaf"

        # Extract candidates from scorer metadata
        candidates = primary[3].get("candidates")

        return RegionDetectionResult(
            region_code=primary[0],
            confidence=primary[1],
            detection_method=primary[2],
            metadata=primary[3],
            geo_region=geo[0] if geo else None,
            name_region=name[0],
            group_region=group,
            conflict=conflict,
            resolution_level=resolution,
            candidates=candidates,
        )

    def _infer_name_origin_fast(self, entry: Dict[str, Any]):
        """Fast name-origin check: signature suffixes + surname exact only.

        Used when CC provides definitive geo — we only need diaspora flags,
        not full scorer resolution.  O(1) per entry instead of O(features).
        """
        # Surname exact match (high confidence, fast lookup)
        result = self._detect_by_surname(entry)
        if result and result.confidence >= 0.95:
            return (
                result.region_code,
                result.confidence,
                result.detection_method,
                result.metadata,
            )
        # Hybrid CJK name detection (fast)
        result = self._detect_hybrid_name(entry)
        if result and result.confidence >= 0.95:
            return (
                result.region_code,
                result.confidence,
                result.detection_method,
                result.metadata,
            )
        # No strong name signal — abstain
        return ("R0", 0.10, "name-fast-abstain", {})

    def _detect_region_uncached_sync(
        self, entry: Dict[str, Any]
    ) -> RegionDetectionResult:
        """
        Synchronous version of region detection.
        Uses split geo/name-origin inference (Phase 2 architectural refactor).
        """
        geo = self._infer_geo(entry)
        # Fast path: when CC provides definitive geo, skip full scorer.
        # Only run fast name-origin (surname exact + CJK) for diaspora detection.
        # A spec-§2a overlay hit is strictly MORE definitive than a plain CC,
        # so it qualifies for the same fast path (R55).
        if geo is not None and geo[2] in ("country-code", "region-overlay"):
            name = self._infer_name_origin_fast(entry)
        else:
            name = self._infer_name_origin(entry)
        return self._merge_geo_name(geo, name)

    async def _infer_name_origin_async(self, entry: Dict[str, Any]):
        """Async name-origin inference: authority -> patterns -> scorer -> ML -> R0."""
        # Phase 3: Authority detection (async, cached only in OFFLINE mode)
        result = await self._detect_by_external_authority(entry)
        if result and result.confidence >= 0.90:
            return (
                result.region_code,
                result.confidence,
                result.detection_method,
                result.metadata,
            )

        # Phase 2: ML ensemble (returns None if models not loaded)
        result = self._detect_by_ml_ensemble(entry)
        if result and result.confidence >= 0.85:
            return (
                result.region_code,
                result.confidence,
                result.detection_method,
                result.metadata,
            )

        return self._run_name_origin_cascade(entry)

    async def _detect_region_uncached_async(
        self, entry: Dict[str, Any]
    ) -> RegionDetectionResult:
        """
        Async version of region detection.
        Uses split geo/name-origin inference (Phase 2 architectural refactor).
        """
        geo = self._infer_geo(entry)
        # Fast path: when CC provides definitive geo, skip full scorer.
        # Spec-§2a overlay hits are more definitive than plain CCs (R55).
        if geo is not None and geo[2] in ("country-code", "region-overlay"):
            name = self._infer_name_origin_fast(entry)
        else:
            name = await self._infer_name_origin_async(entry)
        return self._merge_geo_name(geo, name)

    def _load_surname_fasttext(self):
        """Lazy load surname fastText classifier model."""
        if self._surname_ft is not None:
            return self._surname_ft
        if self._surname_ft_attempted:
            return None
        self._surname_ft_attempted = True

        # Try multiple paths for the surname classifier
        model_candidates = [
            Path("data/ml_training/ft_name_classifier.ftz"),
            Path("data/ml_training/ft_name_classifier.bin"),
            Path("data/ml_training/surname_classifier.ftz"),
            Path("data/ml_training/surname_classifier.bin"),
            self.config_dir / "ft_name_classifier.ftz",
            self.config_dir / "surname_classifier.ftz",
        ]

        if not FASTTEXT_AVAILABLE:
            # Fallback: try CLI binary
            return self._load_surname_fasttext_cli(model_candidates)

        candidates = model_candidates
        for path in candidates:
            if path.exists():
                try:
                    import os
                    import sys

                    old_stderr = sys.stderr
                    try:
                        sys.stderr = open(os.devnull, "w")
                        self._surname_ft = fasttext.load_model(str(path))
                    finally:
                        sys.stderr.close()
                        sys.stderr = old_stderr
                    logger.info(f"Loaded surname fastText model from {path}")
                    return self._surname_ft
                except Exception as e:
                    logger.warning(
                        f"Failed to load surname fastText model from {path}: {e}"
                    )

        # LOUD, ONE-TIME (this method is guarded by _surname_ft_attempted).
        # R54: this used to be a DEBUG log, so a fresh clone silently ran in
        # rules-only mode with no hint the ML tiebreaker was missing — and the
        # docs' detection KPIs assume the model is present. Say so clearly.
        logger.warning(
            "fastText name classifier NOT found (looked for "
            "data/ml_training/ft_name_classifier.ftz and 5 fallbacks). "
            "Region detection is running RULES-ONLY — the ML tiebreaker that "
            "the documented detection KPIs assume is disabled. The model is "
            "gitignored (50 MB); obtain it with `git lfs pull` (if the "
            "maintainer LFS-committed it) or rebuild it from the committed "
            "training corpus: `make model` (see scripts/ml/build_name_classifier.py)."
        )
        return None

    def _load_surname_fasttext_cli(self, model_candidates):
        """Fallback: use fasttext CLI binary instead of Python module."""
        import shutil

        cli_path = shutil.which("fasttext")
        if not cli_path:
            home = Path.home()
            for p in [
                "/usr/local/bin/fasttext",
                "/opt/homebrew/bin/fasttext",
                str(home / ".local" / "bin" / "fasttext"),
                "bin/fasttext",
            ]:
                if Path(p).exists():
                    cli_path = p
                    break
        if not cli_path:
            return None

        model_path = None
        for p in model_candidates:
            if p.exists():
                model_path = str(p)
                break
        if not model_path:
            return None

        self._surname_ft_cli_path = cli_path
        self._surname_ft_model_path = model_path
        self._surname_ft = "CLI_MODE"
        logger.info(f"Using fasttext CLI at {cli_path} with model {model_path}")
        return self._surname_ft

    def _predict_via_cli(self, text):
        """Call fasttext predict-prob via the persistent CLI worker.

        Falls through to a one-shot ``subprocess.run`` only if the
        worker can't start (e.g. binary missing after earlier
        detection). On the hot path this goes through a single
        long-lived subprocess (see ``FastTextCLIWorker``) which is
        ~2000× faster than fork+exec per query.
        """
        if self._ft_cli_worker is None:
            if self._surname_ft_cli_path and self._surname_ft_model_path:
                # Use the process-wide singleton so re-instantiating
                # RegionManager (e.g. in test suites) doesn't leak a
                # fresh subprocess per instance.
                self._ft_cli_worker = FastTextCLIWorker.get(
                    cli_path=self._surname_ft_cli_path,
                    model_path=self._surname_ft_model_path,
                )
            else:
                return None, 0.0, 0.0
        return self._ft_cli_worker.predict(text)

    def _ft_folded_verdict(self, folded_surname: str):
        """(group, prob) of the model's top-1 on a FOLDED surname, or None.

        R59.5: second witness for the Tier-2 ortho veto — the model
        splits confidence across romanization variants, so a raw-form
        verdict under the veto bar can hide a confident folded-form one
        ('aïd' C3@0.57 vs 'aid' C5@0.89).
        """
        model = self._load_surname_fasttext()
        if model is None or not folded_surname:
            return None
        try:
            if model == "CLI_MODE":
                label, p1, _p2 = self._predict_via_cli(folded_surname)
            else:
                pairs = self._ft_predict_pairs(model, folded_surname, k=1)
                if not pairs:
                    return None
                p1, label = pairs[0]
                label = str(label).replace("__label__", "")
        except Exception:
            return None
        if not label:
            return None
        return (LEAF_TO_GROUP.get(label), float(p1))

    def _detect_by_surname_fasttext(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """
        Phase 2 Step 7: Use surname fastText model as fallback when rules abstain.
        Only used if prediction prob >= 0.50 AND not overriding a signature suffix.
        """
        model = self._load_surname_fasttext()
        if model is None:
            return None

        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        if not name:
            return None

        # Extract surname for prediction
        if "," in name:
            surname = name.split(",")[0].strip()
        else:
            parts = name.strip().split()
            surname = parts[-1] if parts else name

        surname_lower = surname.lower().strip()
        if not surname_lower or len(surname_lower) < 2:
            return None

        # Check if surname ends with a signature suffix -- if so, do not override
        for suf in SIGNATURE_SUFFIXES:
            if surname_lower.endswith(suf) and len(surname_lower) > len(suf) + 1:
                return None  # signature suffix already handled by rules

        try:
            if model == "CLI_MODE":
                label, p1, p2 = self._predict_via_cli(surname_lower)
            else:
                pairs = self._ft_predict_pairs(model, surname_lower, k=2)
                if pairs:
                    label = pairs[0][1].replace("__label__", "")
                    p1 = pairs[0][0]
                    p2 = pairs[1][0] if len(pairs) > 1 else 0.0
                else:
                    return None

            # Expert criteria: p1 >= 0.50 AND margin p1-p2 >= 0.15.
            # Env-overridable (same defaults as production) for RC-curve
            # threshold sweeps.
            _ft_p1 = float(os.getenv("GMNAP_FASTTEXT_P1", "0.50"))
            _ft_margin = float(os.getenv("GMNAP_FASTTEXT_MARGIN", "0.15"))
            if (
                label
                and p1 >= _ft_p1
                and (p1 - p2) >= _ft_margin
                and label in self.IMPLEMENTED_REGIONS
            ):
                return RegionDetectionResult(
                    region_code=label,
                    confidence=min(0.75, p1 * 0.80),
                    detection_method="surname-fasttext",
                    metadata={
                        "surname": surname_lower,
                        "ft_prob": p1,
                        "ft_prob2": p2,
                        "ft_label": label,
                        "ft_mode": "cli" if model == "CLI_MODE" else "python",
                    },
                )
        except Exception as e:
            # LOUD, ONE-TIME. R58 (real-data pilot root cause): this used to
            # be a logger.debug, and the fasttext wheel's predict() raises
            # ValueError under NumPy 2.x ("Unable to avoid copy...") — so the
            # ENTIRE ML tier was silently dead on modern installs while the
            # docs cited its accuracy. A dead tier must announce itself.
            if not getattr(self, "_surname_ft_error_warned", False):
                self._surname_ft_error_warned = True
                logger.warning(
                    "Surname fastText prediction FAILED (%s: %s) — the ML "
                    "tiebreaker tier is NOT contributing to detection. If "
                    "this mentions numpy array copies, the installed "
                    "fasttext wheel is NumPy-2-incompatible; the pipeline's "
                    "low-level fallback should have handled it — report "
                    "this.",
                    type(e).__name__,
                    e,
                )

        return None

    @staticmethod
    def _ft_predict_pairs(model, text: str, k: int = 2):
        """Predict via fastText, robust to the NumPy-2 wheel incompatibility.

        fasttext's Python ``predict()`` wraps its result in
        ``np.array(probs, copy=False)``, which RAISES under NumPy >= 2 (the
        copy=False semantics changed) — silently killing the ML tier on any
        modern install (R58 pilot root cause). The underlying
        ``model.f.predict`` returns plain (prob, label) tuples with no numpy
        involved, so use it directly and keep the high-level call only as a
        fallback for exotic builds. Returns a list of (prob, label) sorted
        by prob desc, or [].
        """
        f = getattr(model, "f", None)
        if f is not None:
            # signature: f.predict(text, k, threshold, on_unicode_error)
            pairs = f.predict(text, k, 0.0, "strict")
            return [(float(p), str(lbl)) for p, lbl in pairs]
        labels, probs = model.predict(text, k=k)
        return [(float(p), str(lbl)) for lbl, p in zip(labels, probs)]

    def _detect_by_script(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Detect region based on Unicode script analysis with priority rules + fallback."""
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        if not name:
            return None
        scripts = self._analyze_scripts(name)
        # Empty when the input is pure numbers, punctuation, or other
        # non-letter characters — script analysis filters those out.
        # Without this guard, max(scripts.items()) raises ValueError
        # which propagates all the way to detect_region's caller as
        # an uncaught crash on garbage input. Treat "no detectable
        # script" the same way we treat "name is empty" → fall
        # through to the rest of the cascade (R0 fallback).
        if not scripts:
            return None
        total = sum(scripts.values()) or 1
        dominant, dom_count = max(scripts.items(), key=lambda kv: kv[1])
        if dom_count / total < 0.5:
            return None
        possible = self._script_to_regions.get(dominant, [])

        # EXPERT PHASE 3: Try lexical signal ensemble first (replaces old priority rules)
        signal_result = self._detect_by_priority_signals(entry)
        if signal_result and signal_result.get("region_code") in possible:
            # Signal matched one of the script-compatible regions
            dom_ratio = min(1.0, dom_count / total)
            signal_conf = signal_result.get("confidence", 0.0)
            # Blend script dominance with signal confidence
            final_conf = min(0.95, 0.3 * dom_ratio + 0.7 * signal_conf)
            final_conf = _nudge_by_doi_affiliation(
                entry, signal_result["region_code"], final_conf
            )
            return RegionDetectionResult(
                region_code=signal_result["region_code"],
                confidence=final_conf,
                detection_method="script-signal-ensemble",
                metadata={
                    "script": dominant,
                    "script_ratio": dom_ratio,
                    "signal_confidence": signal_conf,
                    **signal_result.get("metadata", {}),
                },
            )

        # Fallback to OLD priority rules if signals don't match script-compatible regions
        region, conf, dbg = _score_priority_rules(name, possible)
        # If scorer explicitly abstained (margin too low or weak evidence), return R0
        if region is None and dbg.get("reason") in (
            "low_score_or_margin",
            "no_scores",
            "no_signal",
            "given_only_no_surname",
            "mixed_anglo_hispanic",
            "sovietized_turkic",
        ):
            return RegionDetectionResult(
                region_code="R0",
                confidence=0.20,
                detection_method="scorer-abstain",
                metadata=dbg,
            )
        if region and conf >= 0.60:
            # Fix 4: Don't force a Latin-script winner with weak evidence
            raw_score = dbg.get("best_score", 0)
            if raw_score < 2.0:
                return RegionDetectionResult(
                    region_code="R0",
                    confidence=0.20,
                    detection_method="weak-evidence-abstain",
                    metadata={
                        "reasons": dbg.get("reasons", []),
                        "best_score": raw_score,
                        # R58: a weak (<2.0) hit can still serve as a GROUP
                        # anchor for the same-group fastText gate — but it
                        # must NOT be exposed under the 'group'/'best_region'
                        # keys, which flow into terminal-R0 metadata and
                        # would surface a group_region claimed from a single
                        # 1.2-score bare-suffix hit (breaking the 100 %
                        # group-or-better KPI). Distinct weak_* keys: the ft
                        # gate reads them; nothing else does.
                        "weak_group": LEAF_TO_GROUP.get(region),
                        "weak_best_region": region,
                    },
                )
            dom_ratio = min(1.0, dom_count / total)
            final_conf = min(0.90, 0.5 * dom_ratio + 0.5 * conf)
            final_conf = _nudge_by_doi_affiliation(entry, region, final_conf)
            return RegionDetectionResult(
                region_code=region,
                confidence=final_conf,
                detection_method="script-priority",
                metadata={"script": dominant, "script_ratio": dom_ratio, **dbg},
            )

        # Fallback to original selector for names not in priority lexicons
        best_region = self._select_best_region_from_script(entry, possible)
        if best_region:
            confidence = 0.7 if dominant == "Latin" else dom_count / total
            final_conf = _nudge_by_doi_affiliation(entry, best_region, confidence)
            return RegionDetectionResult(
                region_code=best_region,
                confidence=final_conf,
                detection_method="script",
                metadata={"script": dominant, "script_ratio": dom_count / total},
            )
        return None

    def _detect_by_icu(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """V7 Stage 2: ICU processing - Unicode normalization with priority rules."""
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        if not name:
            return None
        icu_name = self._unicode_normalizer.normalize(name)  # ICU normalization
        scripts = self._analyze_scripts(icu_name)
        # Same guard as `_detect_by_script` above — empty scripts dict
        # for pure-numbers / pure-punctuation input.
        if not scripts:
            return None
        total = sum(scripts.values()) or 1
        dominant, dom_count = max(scripts.items(), key=lambda kv: kv[1])
        possible = self._script_to_regions.get(dominant, [])
        region, conf, dbg = _score_priority_rules(icu_name, possible)
        # R58 (pilot: 'Francis Lörler' -> B3@0.76 via icu-priority): for Latin
        # input the ICU normalization is a no-op, so this scorer call exactly
        # duplicates _detect_by_script's — minus its Fix-4 weak-evidence gate.
        # Every pilot AND benchmark icu-priority emission was a single
        # uncorroborated 1.2-1.9 suffix hit that the script path had just
        # REJECTED as weak evidence, resurrected here at 0.76-0.81. Apply the
        # same standard; the weak signal still reaches the same-group fastText
        # gate via the weak_group anchor (see _detect_by_script), which
        # recovers the genuinely-correct subset (e.g. Greek -is names whose ft
        # verdict agrees within HELLENIC) and drops the cross-group misfires.
        if region and dbg.get("best_score", 0) < 2.0:
            return None
        if region:
            final_conf = min(
                0.90, 0.4 * (dom_count / total) + 0.6 * conf
            )  # ICU shouldn't auto-win
            final_conf = _nudge_by_doi_affiliation(entry, region, final_conf)
            return RegionDetectionResult(
                region_code=region,
                confidence=final_conf,
                detection_method="icu-priority",
                metadata={"script": dominant, "icu": True, **dbg},
            )
        return None

    def _select_best_region_from_script(
        self, entry: Dict[str, Any], possible_regions: List[str]
    ) -> Optional[str]:
        """Select best region from script matches using surname patterns and country codes."""
        # Get country code
        country_codes = entry.get("CountryCodes", [])
        if country_codes:
            country = country_codes[0]
            # Check if country directly maps to one of the possible regions
            expected_region = get_region_for_territory(country)
            if (
                expected_region in possible_regions
                and expected_region in self.IMPLEMENTED_REGIONS
            ):
                return expected_region

        # Use surname pattern detection for Latin script regions
        name = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if name and "Latin" in [
            script
            for script, regions in self._script_to_regions.items()
            if any(r in possible_regions for r in regions)
        ]:
            surname_region = self._detect_by_surname_patterns(name, possible_regions)
            if surname_region and surname_region in self.IMPLEMENTED_REGIONS:
                return surname_region

            # Additional pattern matching for romanized names (fallback if surname patterns didn't match)
            name_lower = name.lower()

            # Chinese romanized surnames (E1)
            chinese_surnames = [
                "li ",
                "wang ",
                "zhang ",
                "liu ",
                "chen ",
                "yang ",
                "huang ",
                "zhao ",
                "wu ",
                "zhou ",
                "xu ",
                "sun ",
                "lu ",
                "shen",
            ]
            if any(pattern in name_lower for pattern in chinese_surnames):
                if "E1" in possible_regions and "E1" in self.IMPLEMENTED_REGIONS:
                    return "E1"

            # Indian surnames (D1/D3)
            indian_surnames = [
                "singh",
                "kumar",
                "sharma",
                "gupta",
                "biswas",
                "banerjee",
                "chatterjee",
                "das",
                "bal",
            ]
            if any(pattern in name_lower for pattern in indian_surnames):
                if "D3" in possible_regions and "D3" in self.IMPLEMENTED_REGIONS:
                    return "D3"
                if "D1" in possible_regions and "D1" in self.IMPLEMENTED_REGIONS:
                    return "D1"

            # Korean romanized surnames (E4)
            korean_surnames = [
                "kim ",
                "lee ",
                "park ",
                "choi ",
                "jung ",
                "jeon ",
                "kang ",
            ]
            if any(pattern in name_lower for pattern in korean_surnames):
                if "E4" in possible_regions and "E4" in self.IMPLEMENTED_REGIONS:
                    return "E4"

            # Persian surnames (C2)
            persian_patterns = ["zadeh", "pour", "feyzbakhsh", "khani"]
            if any(pattern in name_lower for pattern in persian_patterns):
                if "C2" in possible_regions and "C2" in self.IMPLEMENTED_REGIONS:
                    return "C2"

        # Apply heuristics based on script type
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")

        # CJK script heuristics (only if name contains CJK characters)
        scripts = self._analyze_scripts(canonical)
        has_cjk = scripts.get("CJK", 0) > 0

        if has_cjk and any(region in ["E1", "E2", "E3"] for region in possible_regions):
            # Improved Japanese detection using more specific patterns
            # Japanese-specific surname combinations and patterns
            japanese_surname_patterns = [
                "田中",
                "山田",
                "佐藤",
                "鈴木",
                "高橋",
                "田口",
                "川口",
                "木村",
                "林田",
            ]
            chinese_indicators = [
                "王",
                "李",
                "张",
                "刘",
                "陈",
                "杨",
                "黄",
                "赵",
                "吴",
                "周",
                "小明",
                "小红",
                "小华",
            ]

            # Check for explicit Chinese patterns first
            if any(indicator in canonical for indicator in chinese_indicators):
                if "E1" in possible_regions and "E1" in self.IMPLEMENTED_REGIONS:
                    return "E1"

            # Check for Japanese surname patterns
            if any(pattern in canonical for pattern in japanese_surname_patterns):
                if "E3" in possible_regions and "E3" in self.IMPLEMENTED_REGIONS:
                    return "E3"

            # Check for Japanese-specific combinations (surname + taro/ko/etc)
            if any(ending in canonical for ending in ["太郎", "花子", "一郎", "次郎"]):
                if "E3" in possible_regions and "E3" in self.IMPLEMENTED_REGIONS:
                    return "E3"

            # Default to Chinese for most CJK content
            if "E1" in possible_regions and "E1" in self.IMPLEMENTED_REGIONS:
                return "E1"

        # Arabic script heuristics - prioritize C3 (Arabic) over C1 (Turkic)
        if any(region in ["C1", "C2", "C3", "C4", "C5"] for region in possible_regions):
            if "C3" in possible_regions and "C3" in self.IMPLEMENTED_REGIONS:
                return "C3"

        # Fallback to first implemented region
        for region in possible_regions:
            if region in self.IMPLEMENTED_REGIONS:
                return region

        return None

    def _detect_by_surname(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Detect region using direct surname pattern matching."""
        name = entry.get("CanonicalLatin", "")
        if not name:
            return None

        # Extract surname from "Family, Given" format
        if "," in name:
            family_name = name.split(",")[0].strip().lower()
        else:
            # For names without comma, check both first and last parts
            # as different cultures place surnames differently
            parts = name.strip().split()
            if len(parts) < 2:
                return None

            # Check both possibilities: "Family Given" (Korean/Chinese/Japanese) and "Given Family" (Western)
            candidates = [
                parts[0].lower(),  # First part (Korean/CJK style)
                parts[-1].lower(),  # Last part (Western style)
            ]

            # Find best match from both candidates
            best_match = None
            best_score = 0
            best_surname = None

            # Track ambiguous matches
            matches = []

            for candidate in candidates:
                # Clean surname for matching
                cleaned_candidate = self._clean_surname_for_matching(candidate)

                # R58: iterate hardcoded AND yaml-supplement regions (a
                # supplement-only region like H1 has no hardcoded set).
                # sorted() keeps candidate scanning deterministic.
                for region_code in sorted(
                    set(self.surname_patterns) | set(self._surname_yaml)
                ):
                    surnames = self.surname_patterns.get(region_code, frozenset())
                    # Only check implemented regions
                    if region_code not in self.IMPLEMENTED_REGIONS:
                        continue

                    score = 0

                    # R58 yaml-supplement direct match — EXACT-only, and with
                    # a position guard: only CJK-order regions (E1/E3) may
                    # match the FIRST token as a surname; for every other
                    # region the supplement applies to the Western position
                    # (parts[-1]) only. Kills the verified given-name
                    # misfires: 'T. Güneş' (taha is a Turkish given name;
                    # c3.yaml carries taha for 'Diaaeldin Taha' at parts[-1])
                    # and 'Mitra Fatemi' (Persian given name vs d3.yaml
                    # mitra for 'Siddharth Mitra').
                    in_yaml = cleaned_candidate in self._surname_yaml.get(
                        region_code, frozenset()
                    )
                    if (
                        in_yaml
                        and candidate == parts[0].lower()
                        and len(parts) >= 2
                        and region_code not in ("E1", "E3")
                    ):
                        in_yaml = False

                    # R59.2 (held-out finding): the FIRST token is a surname
                    # only in surname-first naming orders. The hardcoded
                    # tables were matched at parts[0] for EVERY region, so
                    # GIVEN names hijacked Western-region tables: 'Thomas
                    # Reichelt' -> A1 via the given name Thomas; 'Saeed
                    # Tafazolian' -> C3 via the given name Saeed. Restrict
                    # parts[0] candidacy to surname-first regions (CJK +
                    # Vietnamese); comma forms and parts[-1] are untouched.
                    in_table = cleaned_candidate in surnames
                    if (
                        in_table
                        and candidate == parts[0].lower()
                        and len(parts) >= 2
                        and region_code not in ("E1", "E2", "E3", "E4", "E5")
                    ):
                        in_table = False

                    # Direct match
                    if in_table or in_yaml:
                        score = 10
                        # For ambiguous surnames like "Lee", check given name
                        # patterns. R58.8: 'lim' (Korean 임 AND Hokkien 林 —
                        # 'Lim Chin Siong' emitted E4@0.95) and 'do' (Korean
                        # 도 AND folded Vietnamese Đỗ — 'Do Thi Huong'
                        # emitted E4@0.95) join the ambiguity set.
                        if (
                            cleaned_candidate
                            in [
                                "lee",
                                "li",
                                "kim",
                                "lim",
                                "do",
                                "han",
                                "yu",
                                "kang",
                                "song",
                            ]
                            and len(parts) >= 2
                        ):
                            # Check for Western and Korean given name patterns
                            given_parts = (
                                parts[1:]
                                if candidate == parts[0].lower()
                                else parts[:-1]
                            )
                            given_str = " ".join(given_parts).lower()

                            # Check if any given name part is clearly Western
                            has_western_given = any(
                                self._is_western_given_name(part)
                                for part in given_parts
                            )

                            # Common Korean given name patterns and surnames used as given names
                            korean_patterns = [
                                "-",
                                "jong",
                                "sung",
                                "jin",
                                "min",
                                "hyun",
                                "jung",
                                "bak",
                                "hoon",
                                "woo",
                                "jae",
                                "young",
                                "seok",
                                "han",
                                "lee",
                                "kim",
                                "park",
                                "choi",
                                "cho",
                                "kang",
                                "yoon",
                                "jang",
                            ]
                            has_korean_pattern = any(
                                p in given_str for p in korean_patterns
                            )

                            if has_western_given and region_code.startswith("A"):
                                score = 15  # Strong boost for Western given names with Western regions
                            elif has_korean_pattern and region_code == "E4":
                                score = 12  # Boost Korean match
                            elif (
                                not has_korean_pattern
                                and not has_western_given
                                and region_code != "E4"
                            ):
                                score = 11  # Slight boost for non-Korean
                            elif has_western_given and region_code == "E4":
                                score = 5  # Reduce Korean score for Western given names
                            elif (
                                cleaned_candidate
                                in ("lim", "do", "han", "yu", "kang", "song")
                                and region_code == "E4"
                                and not has_korean_pattern
                            ):
                                # R58.8: lim/do exist ONLY in the E4 table,
                                # so without positive Korean evidence they
                                # must not emit at all — fall through to the
                                # scorer/ft tiers ('Lim Chin Siong',
                                # 'Do Thi Huong' abstain here instead of
                                # claiming Korea at 0.95).
                                score = 0
                    else:
                        # Partial match scoring - only for surnames of reasonable length
                        for surname in surnames:
                            # Skip very short surnames for partial matching to avoid false positives
                            if len(surname) < 3 or len(cleaned_candidate) < 3:
                                continue

                            # Prefix matching (more reliable)
                            if cleaned_candidate.startswith(
                                surname
                            ) or surname.startswith(cleaned_candidate):
                                score = max(score, 7)
                            # Substring matching (less reliable, require longer match)
                            elif len(surname) >= 4 and len(cleaned_candidate) >= 4:
                                if (
                                    surname in cleaned_candidate
                                    or cleaned_candidate in surname
                                ):
                                    score = max(score, 5)

                    if score >= 10:
                        matches.append((region_code, score, cleaned_candidate))

                    if score > best_score:
                        best_score = score
                        best_match = region_code
                        best_surname = cleaned_candidate

            if best_match and best_score >= 5:
                confidence = 0.95 if best_score >= 10 else 0.85
                return RegionDetectionResult(
                    region_code=best_match,
                    confidence=confidence,
                    detection_method="surname",
                    metadata={"surname": best_surname, "score": best_score},
                )

            return None

        # For comma-separated names, process normally
        # Clean surname for matching
        family_name = self._clean_surname_for_matching(family_name)

        # Score each region based on surname matches
        region_scores = {}

        # R58: include yaml-supplement-only regions (sorted = deterministic).
        for region_code in sorted(set(self.surname_patterns) | set(self._surname_yaml)):
            surnames = self.surname_patterns.get(region_code, frozenset())
            # Only check implemented regions
            if region_code not in self.IMPLEMENTED_REGIONS:
                continue

            score = 0

            # Direct match. The comma form declares the surname position, so
            # the R58 yaml supplement applies without a position guard —
            # still EXACT-only (partial loops below iterate hardcoded sets).
            if family_name in surnames or family_name in self._surname_yaml.get(
                region_code, frozenset()
            ):
                score = 10
                # For ambiguous surnames, check given name for disambiguation
                # (R58.8: lim/do joined — see the no-comma branch rationale).
                if (
                    family_name
                    in ["lee", "li", "kim", "lim", "do", "han", "yu", "kang", "song"]
                    and "," in name
                ):
                    given_parts = name.split(",")[1].strip().lower()
                    # Common Korean given name patterns
                    korean_patterns = [
                        "-",
                        "jong",
                        "sung",
                        "jin",
                        "min",
                        "hyun",
                        "jung",
                        "myung",
                        "bak",
                        "hoon",
                        "woo",
                        "jae",
                        "young",
                        "seok",
                        "han",
                    ]
                    has_korean_pattern = any(p in given_parts for p in korean_patterns)

                    if has_korean_pattern and region_code == "E4":
                        score = 12  # Boost Korean match
                    elif not has_korean_pattern and region_code != "E4":
                        score = 11  # Slight boost for non-Korean
                    elif (
                        family_name in ("lim", "do", "han", "yu", "kang", "song")
                        and region_code == "E4"
                        and not has_korean_pattern
                    ):
                        # R58.8: no positive Korean evidence -> no E4 claim
                        # ('Lim, Chin Siong' / 'Do, Thi Huong' fall through).
                        score = 0
            else:
                # Partial match scoring - only for surnames of reasonable length
                for surname in surnames:
                    # Skip very short surnames for partial matching to avoid false positives
                    if len(surname) < 3 or len(family_name) < 3:
                        continue

                    # Prefix matching (more reliable)
                    if family_name.startswith(surname) or surname.startswith(
                        family_name
                    ):
                        score = max(score, 7)
                    # Substring matching (less reliable, require longer match)
                    elif len(surname) >= 4 and len(family_name) >= 4:
                        if surname in family_name or family_name in surname:
                            score = max(score, 5)

            if score > 0:
                region_scores[region_code] = score

        if region_scores:
            best_score = max(region_scores.values())
            if best_score >= 5:
                # Get all regions with the best score
                best_matches = [r for r, s in region_scores.items() if s == best_score]

                if len(best_matches) == 1:
                    best_match = best_matches[0]
                else:
                    # Prefer E4 for ambiguous Asian surnames
                    if "E4" in best_matches and family_name in [
                        "lee",
                        "li",
                        "kim",
                        "park",
                        "choi",
                    ]:
                        best_match = "E4"
                    else:
                        best_match = best_matches[0]
            confidence = 0.95 if best_score >= 10 else 0.85
            return RegionDetectionResult(
                region_code=best_match,
                confidence=confidence,
                detection_method="surname",
                metadata={"surname": family_name, "score": best_score},
            )

        return None

    def _detect_by_language(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Detect region based on language identification."""
        if not self.lang_detector:
            return None

        text = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not text or len(text) < 10:  # Need reasonable text length
            return None

        try:
            # FastText returns ((label,), (confidence,))
            predictions = self.lang_detector.predict(text, k=3)

            # Map language codes to regions (only implemented ones)
            lang_to_region = {
                "en": "A1",
                "es": "G1",
                "pt": "G1",
                "fr": "A2",
                "de": "A2",
                "it": "A2",
                "nl": "A2",
                "ru": "B1",
                "uk": "B1",
                "pl": "B2",
                "cs": "B2",
                "sk": "B2",
                "hr": "B2",
                "sr": "B2",
                "sl": "B2",
                "ar": "C3",
                "fa": "C2",
                "tr": "C1",
                "he": "C6",
                "hi": "D1",
                "ur": "D4",
                "bn": "D3",
                "ta": "D2",
                "te": "D2",
                "si": "D5",
                "zh": "E1",
                "ja": "E3",
                "ko": "E4",
                "vi": "E5",
                "th": "E6",
                "id": "E7",
                "ms": "E7",
                "tl": "E7",
                "sw": "F1",
                "am": "F3",
            }

            for (lang_label,), (conf,) in zip(predictions[0], predictions[1]):
                lang_code = lang_label.replace("__label__", "")
                region = lang_to_region.get(lang_code)
                if region and region in self.IMPLEMENTED_REGIONS and conf > 0.5:
                    return RegionDetectionResult(
                        region_code=region,
                        confidence=min(conf, 0.9),  # Cap confidence
                        detection_method="language",
                        metadata={"language": lang_code, "lang_confidence": conf},
                    )
        except Exception as e:
            logger.debug(f"Language detection failed: {e}")

        return None

    def _detect_by_affiliation(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Detect region from institution/affiliation using ROR lookup."""
        # Try Institution field first (common in pipeline output)
        institution = entry.get("Institution") or entry.get("institution") or ""
        if institution:
            try:
                from src.collectors.ror_client import get_ror_lookup

                ror = get_ror_lookup()
                cc = ror.lookup(institution)
                if cc:
                    region = get_region_for_territory(cc)
                    if region and region in self.IMPLEMENTED_REGIONS:
                        return RegionDetectionResult(
                            region_code=region,
                            confidence=0.85,
                            detection_method="ror-affiliation",
                            metadata={
                                "institution": institution,
                                "country": cc,
                            },
                        )
            except ImportError:
                pass

        # Try Affiliations list (structured with country field)
        affiliations = entry.get("Affiliations", [])
        for affiliation in affiliations:
            if isinstance(affiliation, dict):
                country = affiliation.get("country")
                if country:
                    region = get_region_for_territory(country)
                    if region and region in self.IMPLEMENTED_REGIONS:
                        return RegionDetectionResult(
                            region_code=region,
                            confidence=0.80,
                            detection_method="affiliation-country",
                            metadata={
                                "country": country,
                                "affiliation": affiliation.get("name"),
                            },
                        )

        return None

    def _detect_by_doi(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region based on DOI prefix."""
        dois = entry.get("DOIs", [])
        if not dois:
            return None

        for doi in dois:
            # Extract prefix (e.g., "10.1007" from "10.1007/s00220-021-04123-0")
            if "/" in doi:
                prefix = doi.split("/")[0]
                country = self._doi_prefix_map.get(prefix)
                if country:
                    region = get_region_for_territory(country)
                    if region and region in self.IMPLEMENTED_REGIONS:
                        return RegionDetectionResult(
                            region_code=region,
                            confidence=0.6,
                            detection_method="doi",
                            metadata={"doi_prefix": prefix, "country": country},
                        )

        return None

    @staticmethod
    def _diaspora_range_contains(rng: str, year: int) -> bool:
        """Spec §3 interval syntax: "..2015", "2016..", "1980..2000" — the
        committed config also uses the dash forms "-2015" / "2016-".
        Bounds are inclusive."""
        rng = str(rng).strip().replace("..", "-")
        if "-" not in rng:
            return rng.isdigit() and int(rng) == year
        start, _, end = rng.partition("-")
        if start and year < int(start):
            return False
        if end and year > int(end):
            return False
        return True

    def _detect_by_diaspora(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Spec §3 diaspora overlay: era-scoped CC->region overrides from
        config/diaspora.yaml (loaded into self._diaspora_config since Phase 2
        but never READ — the previous body was a stub returning None,
        MASTERPLAN §3.5). A country's rules map date intervals to regions
        (e.g. TH pre-2015 -> E6, 2016- -> A1). The entry's era signal is
        BirthYear; entries without one can't be placed in an interval and
        fall through to the static territory mapping.
        """
        if not self._diaspora_config:
            return None
        countries = entry.get("CountryCodes", [])
        year_raw = entry.get("BirthYear")
        if not countries or year_raw in (None, ""):
            return None
        try:
            year = int(str(year_raw)[:4])
        except (TypeError, ValueError):
            return None
        for cc in countries:
            rules = self._diaspora_config.get(cc)
            if not rules:
                continue
            for rule in rules:
                region = rule.get("region")
                rng = rule.get("range")
                if not region or rng in (None, ""):
                    continue
                try:
                    matched = self._diaspora_range_contains(rng, year)
                except (TypeError, ValueError):
                    continue
                if matched and region in self.IMPLEMENTED_REGIONS:
                    return RegionDetectionResult(
                        region_code=region,
                        confidence=0.9,
                        detection_method="diaspora_overlay",
                        metadata={"country": cc, "range": str(rng)},
                        geo_region=region,
                    )
        return None

    def _detect_hybrid_name(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """
        Detect hybrid names (Latin given + CJK surname).

        Expert's guidance: "CJK surname trumps Anglo given name"
        Examples:
        - Robert Chen → E1 (Chinese surname primary)
        - Michael Kim → E4 (Korean surname primary)
        - Jennifer Lee → E4 (Korean surname primary)

        Works on both:
        1. Mixed script names (Latin + Chinese characters/Hangul)
        2. Pure Latin romanizations (Robert Chen, etc.)

        Returns early with high confidence (0.95) if CJK surname detected.
        """
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        if not name:
            return None

        # Extract tokens
        tokens = name.split()
        if len(tokens) < 2:
            return None

        # Common Anglo given names (to detect hybrid pattern)
        # Only trigger if we have Anglo given + CJK surname
        anglo_given_names = {
            "robert",
            "michael",
            "david",
            "jennifer",
            "daniel",
            "daniel",
            "john",
            "james",
            "william",
            "richard",
            "joseph",
            "thomas",
            "charles",
            "christopher",
            "matthew",
            "anthony",
            "donald",
            "mark",
            "paul",
            "steven",
            "andrew",
            "kenneth",
            "george",
            "joshua",
            "kevin",
            "brian",
            "edward",
            "ronald",
            "timothy",
            "jason",
            "jeffrey",
            "ryan",
            "jacob",
            "gary",
            "nicholas",
            "eric",
            "jonathan",
            "stephen",
            "larry",
            "justin",
            "scott",
            "brandon",
            "benjamin",
            "samuel",
            "raymond",
            "gregory",
            "mary",
            "patricia",
            "linda",
            "barbara",
            "elizabeth",
            "susan",
            "jessica",
            "sarah",
            "karen",
            "nancy",
            "lisa",
            "betty",
            "margaret",
            "sandra",
            "ashley",
            "dorothy",
            "kimberly",
            "emily",
            "donna",
            "michelle",
            "carol",
            "amanda",
            "melissa",
            "deborah",
            "stephanie",
            "rebecca",
            "sharon",
            "laura",
            "cynthia",
            "kathleen",
            "amy",
            "anna",
            "angela",
            "martha",
            "ruth",
            "christine",
            "diane",
        }

        # Check if first token is an Anglo given name
        first_token = tokens[0].lower()
        has_anglo_given = first_token in anglo_given_names

        # Common Chinese surnames (1-2 char, Latin romanization)
        chinese_surnames = {
            "wang",
            "li",
            "zhang",
            "liu",
            "chen",
            "yang",
            "zhao",
            "huang",
            "zhou",
            "wu",
            "xu",
            "sun",
            "ma",
            "zhu",
            "hu",
            "guo",
            "lin",
            "he",
            "gao",
            "luo",
            "zheng",
            "liang",
            "xie",
            "song",
            "tang",
            "han",
            "feng",
            "yu",
            "dong",
            "xiao",
            "cheng",
            "cao",
            "yuan",
            "deng",
            "xu",
            "fu",
            "shen",
            "peng",
            "lu",
            "su",
            "lu",
            "jiang",
            "cai",
            "jia",
            "ding",
            "wei",
            "xue",
            "ye",
            "yan",
            "pan",
            "du",
            "dai",
            "xia",
            "zhong",
            "wang",
            "tian",
            "ren",
            "jiang",
            "fan",
            "shi",
            "yao",
            "tan",
            "sheng",
            "gu",
            "qiu",
            "meng",
            # R59.2: "long" removed — also a common Anglo surname
            # ('Christopher D. Long' -> E1@0.95 via the trump rule; the rule
            # is only sound for distinctly-CJK surnames).
            "wan",
            "duan",
            "zhang",
            "qian",
            "tang",
            "yin",
            "lai",
            "chang",
        }

        # Common Korean surnames (Latin romanization)
        korean_surnames = {
            "kim",
            "lee",
            "park",
            "choi",
            "jung",
            "kang",
            "cho",
            "yoon",
            "jang",
            "lim",
            "han",
            "oh",
            "shin",
            "seo",
            "kwon",
            "song",
            "hong",
            "ahn",
            "koo",
            "moon",
            "yang",
            "baek",
            "son",
            "ha",
            "yoo",
            "nam",
            "shim",
            "noh",
            "jeong",
            "hwang",
            "cha",
            "joo",
            "ko",
            "bae",
            "heo",
            "min",
            "goh",
            "suh",
            "yim",
            "jeon",
        }

        # Check for CJK surname in tokens
        # Hybrid pattern: Anglo given name + CJK surname
        # Assume last token is surname (Western order: "Robert Chen")
        last_token = tokens[-1].lower()

        # Only trigger if we have Anglo given + CJK surname
        if has_anglo_given:
            if last_token in chinese_surnames:
                return RegionDetectionResult(
                    region_code="E1",
                    confidence=0.95,
                    detection_method="hybrid-cjk-surname",
                    metadata={
                        "given": first_token,
                        "surname": last_token,
                        "cjk_type": "chinese",
                        "reason": "CJK surname trumps Anglo given name",
                    },
                )
            elif last_token in korean_surnames:
                return RegionDetectionResult(
                    region_code="E4",
                    confidence=0.95,
                    detection_method="hybrid-cjk-surname",
                    metadata={
                        "given": first_token,
                        "surname": last_token,
                        "cjk_type": "korean",
                        "reason": "CJK surname trumps Anglo given name",
                    },
                )

        return None

    def _apply_affiliation_tiebreak(
        self, entry: Dict[str, Any], result: RegionDetectionResult
    ) -> RegionDetectionResult:
        """
        Apply affiliation tie-breaking for ambiguous family regions.

        Expert's guidance: "Use affiliation ONLY for tie-breaking within families"

        Ambiguous families:
        - {A2, G1}: Spanish names (Spain vs Latin America)
        - {E1, E2}: Chinese names (Mainland vs Taiwan/HK)
        - {C3, C4, C5}: Arabic names (Levant vs Gulf vs Maghreb)

        Args:
            entry: Name entry dict
            result: Initial detection result from priority rules

        Returns:
            Modified result if tie-break applied, otherwise original result
        """
        # Define ambiguous families
        FAMILY_TIESETS = [
            frozenset({"A2", "G1"}),  # Spanish
            frozenset({"E1", "E2"}),  # Chinese
            frozenset({"C3", "C4", "C5"}),  # Arabic
        ]

        # Check if current result is in an ambiguous family
        current_region = result.region_code
        in_family = None
        for family in FAMILY_TIESETS:
            if current_region in family:
                in_family = family
                break

        if not in_family:
            # Not ambiguous - return as-is
            return result

        # Get affiliation region
        affiliations = entry.get("Affiliations", [])
        if not affiliations:
            # No affiliation data - return as-is
            return result

        # Extract country from affiliation
        affiliation_region = None
        for affiliation in affiliations:
            if isinstance(affiliation, dict):
                country = affiliation.get("country")
                if country:
                    affiliation_region = get_region_for_territory(country)
                    break

        if not affiliation_region or affiliation_region not in in_family:
            # Affiliation not in same family - return as-is
            return result

        # Apply tie-break: use affiliation to resolve ambiguity
        return RegionDetectionResult(
            region_code=affiliation_region,
            confidence=min(0.90, result.confidence + 0.10),  # Boost confidence slightly
            detection_method=f"{result.detection_method}+affiliation-tiebreak",
            metadata={
                **result.metadata,
                "tiebreak_family": list(in_family),
                "original_region": current_region,
                "affiliation_region": affiliation_region,
                "reason": "Affiliation tie-break within ambiguous family",
            },
        )

    def _analyze_scripts(self, text: str) -> Dict[str, int]:
        """Analyze Unicode scripts in text."""
        script_counts = {}

        for char in text:
            if char.isalpha():
                # Get Unicode script
                script = self._get_unicode_script(char)
                script_counts[script] = script_counts.get(script, 0) + 1

        return script_counts

    def _get_unicode_script(self, char: str) -> str:
        """Determine Unicode script of a character."""
        # Simplified script detection - real implementation would use unicodedata
        code = ord(char)

        # Basic Latin
        if 0x0041 <= code <= 0x007A:
            return "Latin"
        # Latin Extended
        elif 0x0100 <= code <= 0x024F:
            return "Latin"
        # Cyrillic
        elif 0x0400 <= code <= 0x04FF:
            return "Cyrillic"
        # Greek
        elif 0x0370 <= code <= 0x03FF:
            return "Greek"
        # Arabic
        elif 0x0600 <= code <= 0x06FF:
            return "Arabic"
        # Hebrew
        elif 0x0590 <= code <= 0x05FF:
            return "Hebrew"
        # Devanagari
        elif 0x0900 <= code <= 0x097F:
            return "Devanagari"
        # Bengali
        elif 0x0980 <= code <= 0x09FF:
            return "Bengali"
        # Tamil
        elif 0x0B80 <= code <= 0x0BFF:
            return "Tamil"
        # Telugu
        elif 0x0C00 <= code <= 0x0C7F:
            return "Telugu"
        # Sinhala
        elif 0x0D80 <= code <= 0x0DFF:
            return "Sinhala"
        # Thai
        elif 0x0E00 <= code <= 0x0E7F:
            return "Thai"
        # Myanmar
        elif 0x1000 <= code <= 0x109F:
            return "Myanmar"
        # Georgian
        elif 0x10A0 <= code <= 0x10FF:
            return "Georgian"
        # Hangul
        elif 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
            return "Hangul"
        # CJK
        elif 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            return "CJK"
        # Hiragana/Katakana
        elif 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF:
            return "CJK"
        # Armenian
        elif 0x0530 <= code <= 0x058F:
            return "Armenian"
        # Ethiopic
        elif 0x1200 <= code <= 0x137F:
            return "Ethiopic"
        else:
            return "Unknown"

    def _init_surname_patterns(self):
        """Initialize surname pattern databases for implemented regions only."""
        self.surname_patterns = {}

        # Only add patterns for implemented regions
        if "A1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["A1"] = {
                # Common Anglo surnames (Hispanic names removed — handled by scorer)
                "smith",
                "johnson",
                "williams",
                "brown",
                "jones",
                "miller",
                "davis",
                "wilson",
                "anderson",
                "thomas",
                "taylor",
                "moore",
                "jackson",
                "martin",
                "lee",
                "perez",
                "thompson",
                "white",
                "harris",
                "sanchez",
                "clark",
                # Mathematician surnames
                "newton",
                "darwin",
                "maxwell",
                "faraday",
                "kelvin",
                "rayleigh",
                "hardy",
                "littlewood",
                "ramsey",
                "turing",
                "russell",
                "whitehead",
                "hamilton",
                "cayley",
                "sylvester",
                "boole",
                "de morgan",
                "babbage",
                "lovelace",
            }

        if "A2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["A2"] = {
                # German
                "müller",
                "schmidt",
                "schneider",
                "fischer",
                "weber",
                "meyer",
                "wagner",
                "becker",
                "schulz",
                "hoffmann",
                "schäfer",
                "koch",
                "bauer",
                "richter",
                "gauss",
                "riemann",
                "hilbert",
                "weierstrass",
                "cantor",
                "dedekind",
                "kronecker",
                "kummer",
                "dirichlet",
                "jacobi",
                "weyl",
                "noether",
                "artin",
                "hasse",
                "hecke",
                "minkowski",
                "hurwitz",
                "landau",
                "siegel",
                "selberg",
                "einstein",
                "planck",
                "heisenberg",
                "schrödinger",
                "born",
                "bohr",
                # French
                "bernard",
                "dubois",
                "thomas",
                "robert",
                "richard",
                "petit",
                "durand",
                "cauchy",
                "lagrange",
                "laplace",
                "fourier",
                "poisson",
                "hermite",
                "poincaré",
                "hadamard",
                "lebesgue",
                "borel",
                "cartan",
                "weil",
                "serre",
                "grothendieck",
                "deligne",
                "connes",
                "villani",
                "demailly",
                # Dutch
                "van der waals",
                "lorentz",
                "zeeman",
                "kamerlingh",
                "huygens",
                "stevin",
                "van der waerden",
                "brouwer",
                "de groot",
                # Belgian
                "deligne",
                "bourgain",
                "daubechies",
                # Austrian
                "schrödinger",
                "pauli",
                "mach",
                "boltzmann",
                "doppler",
                "gödel",
                # Swiss
                "euler",
                "bernoulli",
                "steiner",
                # Italian (Northern)
                "rossi",
                "ferrari",
                "russo",
                "bianchi",
                "romano",
                "colombo",
                "ricci",
                "fibonacci",
                "galilei",
                "torricelli",
                "volta",
                "avogadro",
                "fermi",
                "levi-civita",
                "ricci-curbastro",
                "betti",
                "cremona",
                "peano",
                "bombieri",
                "fubini",
                "vitali",
                # Hungarian (R58.7: consolidated here — HU→A2 per the R51
                # maintainer ruling and the benchmark's own Erdős→A2 pins;
                # the duplicate A3 block is gone)
                "nagy",
                "kovács",
                "tóth",
                "szabó",
                "horváth",
                "varga",
                "kiss",
                "molnár",
                "németh",
                "farkas",
                "balogh",
                "papp",
                "takács",
                "juhász",
                "neumann",
                "wigner",
                "teller",
                "kármán",
                "pólya",
                "szegő",
                "riesz",
                "haar",
                "turán",
                "rényi",
                "lovász",
                "szemerédi",
                "babai",
                "erdős",
                "bollobás",
                "katona",
                "kövári",
                "szekeres",
                "komlós",
                "simonovits",
                # Polish mathematicians
                "banach",
                "steinhaus",
                "mazur",
                "schauder",
                "kuratowski",
                "sierpiński",
                "tarski",
                "mostowski",
                "knaster",
                "borsuk",
                "ulam",
                "zygmund",
                # Portuguese (PT → A2)
                "santos",
                "oliveira",
                "rodrigues",
                "almeida",
                "fernandes",
                "carvalho",
                "gomes",
                "martins",
                "pinto",
                "soares",
                "correia",
                "teixeira",
                "ferreira",
                "lopes",
                "pereira",
                "coelho",
                "nogueira",
                "figueiredo",
                "azevedo",
            }

        if "A3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["A3"] = {
                # Swedish
                "andersson",
                "johansson",
                "karlsson",
                "nilsson",
                "eriksson",
                "larsson",
                "olsson",
                "persson",
                "svensson",
                "gustafsson",
                "pettersson",
                "jonsson",
                # Norwegian
                "hansen",
                "johansen",
                "olsen",
                "larsen",
                "andersen",
                "pedersen",
                "nielsen",
                "kristiansen",
                "jensen",
                "carlsen",
                "lie",
                "abel",
                # Danish
                "nielsen",
                "jensen",
                "hansen",
                "pedersen",
                "andersen",
                "christensen",
                "larsen",
                "sørensen",
                "rasmussen",
                "jørgensen",
                "petersen",
                "madsen",
                # Icelandic (patronymic)
                "einarsson",
                "sigurdsson",
                "guðmundsson",
                "jónsson",
                "ólafsson",
                "magnusson",
                "þórsson",
                "ragnarsson",
                "björnsson",
                "stefánsson",
                # Finnish
                "virtanen",
                "korhonen",
                "mäkinen",
                "nieminen",
                "mäkelä",
                "hämäläinen",
                "laine",
                "heikkinen",
                "koskinen",
                "järvinen",
                "lehtonen",
                "saarinen",
                # Estonian
                "tamm",
                "saar",
                "mägi",
                "kask",
                "kukk",
                "sepp",
                "kõiv",
                "rebane",
                "hunt",
                "roos",
                "vaher",
                "männik",
                "kadak",
                "kallas",
                # Latvian
                "bērziņš",
                "kalniņš",
                "ozoliņš",
                "liepiņš",
                "vilks",
                "priede",
                "krūmiņš",
                "jansons",
                "pētersons",
                "kļaviņš",
                # R58.7: the '# Hungarian' block that lived here was REMOVED.
                # A3 is Nordic-Baltic; Hungarian surnames (Erdős, Bollobás,
                # Katona, …) emitted A3@0.95 — wrong leaf AND wrong group
                # (NORDIC_BALTIC), contradicting the project's own benchmark,
                # which pins Erdős under A2 (HU→A2, R51 maintainer ruling).
                # Nine of those names were ALSO in the A2 table, so which
                # wrong leaf won was an arbitrary tie-break. Hungarian names
                # now live ONLY in the A2 block below.
            }

        if "B1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["B1"] = {
                # Russian
                "ivanov",
                "smirnov",
                "kuznetsov",
                "popov",
                "sokolov",
                "lebedev",
                "kozlov",
                "novikov",
                "morozov",
                "petrov",
                "volkov",
                "solovyov",
                "vasilyev",
                "zaytsev",
                "pavlov",
                "semyonov",
                "golubev",
                "vinogradov",
                "chebyshev",
                "lobachevsky",
                "markov",
                "lyapunov",
                "kolmogorov",
                "khinchin",
                "alexandrov",
                "pontryagin",
                "shafarevich",
                "gel'fand",
                "arnol'd",
                "sinai",
                "novikov",
                "manin",
                "kirillov",
                "faddeev",
                "putin",
                "medvedev",
                "gorbachev",
                "yeltsin",
                "brezhnev",
                "khrushchev",
                # Ukrainian
                "shevchenko",
                "bondarenko",
                "kovalenko",
                "tkachenko",
                "kravchenko",
                "oliynyk",
                "kovalchuk",
                "shevchuk",
                "polishchuk",
                "bondarchuk",
                "zelensky",
                "poroshenko",
                "yanukovych",
                "yushchenko",
                "kuchma",
            }

        if "B2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["B2"] = {
                # Polish
                "nowak",
                "kowalski",
                "wiśniewski",
                "wójcik",
                "kowalczyk",
                "kamiński",
                "lewandowski",
                "zieliński",
                "szymański",
                "woźniak",
                "dąbrowski",
                "kozłowski",
                "jankowski",
                "mazur",
                "wojciechowski",
                "kwiatkowski",
                "krawczyk",
                "kaczmarek",
                "piotrowski",
                "grabowski",
                # Czech
                "novák",
                "svoboda",
                "novotný",
                "dvořák",
                "černý",
                "procházka",
                "krejčí",
                "čech",
                "bolzano",
                # Slovak
                "kováč",
                "horváth",
                "baláž",
                "szabó",
                "molnár",
                "lukáč",
                "kováčik",
                # Croatian
                "horvat",
                "kovačić",
                "babić",
                "marić",
                "jurić",
                "pavlović",
                "kovač",
                "božić",
                "mohorovičić",
                # Serbian
                "jovanović",
                "petrović",
                "nikolić",
                "marković",
                "đorđević",
                "stojanović",
                "milić",
                "milanković",
                # Slovenian
                "novak",
                "horvat",
                "krajnc",
                "kovač",
                "potočnik",
                "vidmar",
            }

        if "B3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["B3"] = {
                # Ancient Greek mathematicians
                "euclid",
                "archimedes",
                "apollonius",
                "diophantus",
                "pappus",
                "ptolemy",
                "thales",
                "pythagoras",
                "eratosthenes",
                "hipparchus",
                "menelaus",
                # Modern Greek surnames
                "papadopoulos",
                "georgiou",
                "dimitriou",
                "ioannou",
                "constantinou",
                "nikolaou",
                "christou",
                "michail",
                "stavros",
                "kostas",
                "yannis",
                "christodoulou",
                "papageorgiou",
                "hadjidakis",
                "chatzidakis",
                # Common patterns (-opoulos, -akis, -ou)
                "antonopoulos",
                "giannopoulos",
                "economopoulos",
                "theodoropoulos",
                "stefanakis",
                "nikolakis",
                "dimitrakis",
                "georgakis",
                "christakis",
                # Greek script versions (for mixed detection)
                "παπαδόπουλος",
                "γεωργίου",
                "δημητρίου",
                "ιωάννου",
                "κωνσταντίνου",
                "νικολάου",
                "χρήστου",
                "μιχαήλ",
                "σταύρος",
                "κώστας",
                "γιάννης",
            }

        if "C2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C2"] = {
                # Persian
                "ahmadi",
                "hosseini",
                "mohammadi",
                "rezaei",
                "karimi",
                "moradi",
                "ali",
                "rahimi",
                "rostami",
                "nazari",
                "safari",
                "hashemi",
                "khayyam",
                "tusi",
                "kashani",
                "biruni",
                "khwarizmi",
                "karaji",
                "mirzakhani",
                # Tajik
                "rahmonov",
                "safarov",
                "karimov",
                "nazarov",
                "rustamov",
            }

        if "C3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C3"] = {
                # Arabic (Levant/Egypt)
                "hassan",
                "hussein",
                "ahmad",
                "mahmoud",
                "ibrahim",
                "mohamed",
                "abdullah",
                "yousef",
                "khalil",
                "rahman",
                "hamza",
                "omar",
                "saleh",
                "saeed",
                "nasser",
                "jaber",
                "haddad",
                "khoury",
                "al-khwarizmi",
                "alhazen",
                "al-kindi",
                "al-battani",
                "al-biruni",
                "al-kashi",
                "al-tusi",
                "al-din",
                "al-jazari",
                "al-qalasadi",
                # Add more Arabic patterns without hyphen
                "muhammad",
                "khwarizmi",
                "alkhwarizmi",
                "jabir",
                "aljabir",
                "sina",
                "farabi",
                "alfarabi",
            }

        if "C4" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C4"] = {
                # Gulf Arabic
                "al-rashid",
                "al-sabah",
                "al-thani",
                "al-nahyan",
                "al-maktoum",
                "al-khalifa",
                "al-said",
                "al-otaibi",
                "al-mutairi",
                "al-harbi",
                "al-ghamdi",
                "al-qahtani",
                "al-shammari",
                "al-anazi",
                "al-tamimi",
            }

        if "D1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["D1"] = {
                # Hindi Belt
                "sharma",
                "verma",
                "gupta",
                "kumar",
                "singh",
                "yadav",
                "mishra",
                "pandey",
                "patel",
                "tiwari",
                "jain",
                "agarwal",
                "mehta",
                "joshi",
                "chauhan",
                "gautam",
                "kaur",
                "malhotra",
                "kapoor",
                "chopra",
                "ramanujan",
                "chandrasekhar",
                "raman",
                "mahalanobis",
                "rao",
                "das",
                "sen",
                # R58.8: bose/bhattacharya/mukherjee/chatterjee/saha REMOVED
                # from D1 — they are distinctly BENGALI surnames and the
                # hybrid-CJK fallback already routes them to D3; having them
                # here made the emitted leaf depend on which tier caught the
                # name (Chatterjee -> D1@0.95 exact vs Banerjee -> D3).
            }

        if "E1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E1"] = {
                # Chinese (Mainland)
                "wang",
                "li",
                "zhang",
                "liu",
                "chen",
                "yang",
                "huang",
                "zhao",
                "zhou",
                "wu",
                "xu",
                "sun",
                "ma",
                "zhu",
                "hu",
                "guo",
                "he",
                "lin",
                "luo",
                "gao",
                "zheng",
                "liang",
                "xie",
                "song",
                "tang",
                "chern",
                "yau",
                "tao",
                "hua",
                "shen",
                "feng",
                "cao",
                "deng",
            }

        if "E3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E3"] = {
                # Japanese
                "sato",
                "suzuki",
                "takahashi",
                "tanaka",
                "watanabe",
                "ito",
                "yamamoto",
                "nakamura",
                "kobayashi",
                "kato",
                "yoshida",
                "yamada",
                "sasaki",
                "yamaguchi",
                "saito",
                "matsumoto",
                "inoue",
                "kimura",
                "hayashi",
                "shimizu",
                "yamazaki",
                "mori",
                "abe",
                "ikeda",
                "hashimoto",
                "yamashita",
                "ishikawa",
                "nakajima",
                "maeda",
                "fujita",
                "kiyoshi",
                "kunihiko",
                "shigefumi",
                "heisuke",
                "goro",
                "mikio",
            }

        if "G1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["G1"] = {
                # Spanish
                "garcía",
                "rodríguez",
                "gonzález",
                "fernández",
                "lópez",
                "martínez",
                "sánchez",
                "pérez",
                "gómez",
                "ruiz",
                "hernández",
                "jiménez",
                "díaz",
                "moreno",
                "muñoz",
                "álvarez",
                "romero",
                "navarro",
                "torres",
                "domínguez",
                "vázquez",
                "ramos",
                "castro",
                "ortiz",
                # Portuguese
                "santos",
                "oliveira",
                "souza",
                "rodrigues",
                "almeida",
                "nascimento",
                "lima",
                "araújo",
                "fernandes",
                "carvalho",
                "gomes",
                "martins",
                "rocha",
                "ribeiro",
                "alves",
                "monteiro",
                "mendes",
                "barros",
                "freitas",
                "barbosa",
                "pinto",
                "cavalcanti",
                # Latin American
                "garcia",
                "rodriguez",
                "gonzalez",
                "fernandez",
                "lopez",
                "martinez",
                "sanchez",
                "perez",
                "gomez",
                "ruiz",
                "hernandez",
                "jimenez",
                "diaz",
                "moreno",
                "munoz",
                "alvarez",
                "romero",
                "navarro",
            }

        if "E4" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E4"] = {
                # Most common Korean surnames
                "kim",
                "lee",
                "park",
                "choi",
                "jung",
                "kang",
                "cho",
                "yoon",
                "jang",
                "lim",
                "han",
                "oh",
                "seo",
                "shin",
                "kwon",
                "hwang",
                "ahn",
                "song",
                "yoo",
                "hong",
                "jeon",
                "go",
                "moon",
                "yang",
                "baek",
                "heo",
                "nam",
                "sim",
                "won",
                "kwak",
                "son",
                "myung",
                "noh",
                "koo",
                "ryu",
                "jin",
                "ma",
                "cha",
                "yu",
                "do",
                "bae",
                "seok",
                "woo",
                "min",
                "gang",
                "ko",
                "goo",
                "tae",
                "pyo",
                "ha",
                "roh",
                "rhee",
                "yeon",
                "cha",
                "bang",
                "ki",
                "jeong",
                "chae",
                "chun",
                # Mathematician surnames
                "kim",
                "lee",
                "park",
                "choi",
                "cho",
                "kang",
                "moon",
                "seo",
                "han",
                "shin",
                "kwon",
                "jung",
                "oh",
                "yoon",
                "jang",
                "hwang",
                "song",
                "ahn",
                "lim",
                "hong",
                # Romanization variants
                "gim",
                "ri",
                "bak",
                "choe",
                "jeong",
                "gang",
                "jo",
                "yun",
                "jang",
                "im",
            }

        # R58: curated per-region `surname_exact:` YAML supplements
        # (config/regions/<code>.yaml — same file and cache as the processor
        # override hook). EXACT-only membership at the direct-match position;
        # never fed to the prefix/substring partial loops, so a supplement
        # entry can neither prefix-fire on longer surnames nor create new
        # 0.85-confidence results anywhere. Entries derive from the R58
        # adjudicated pilot ground truth under the curation policy recorded
        # in each YAML header. Load-time cross-region uniqueness gate:
        # a key claimed by any hardcoded set or by two supplements is
        # DROPPED (loudly) — deterministic fail-safe over silent ambiguity.
        from src.regions.base import load_region_yaml

        self._surname_yaml: Dict[str, set] = {}
        hardcoded_claims: Dict[str, str] = {}
        for rc, pats in self.surname_patterns.items():
            for s in pats:
                hardcoded_claims.setdefault(s, rc)
        yaml_claims: Dict[str, str] = {}
        for code in sorted(self.IMPLEMENTED_REGIONS):
            raw = load_region_yaml(code).get("surname_exact") or []
            if not isinstance(raw, list):
                logger.warning(
                    "surname_exact in %s.yaml is not a list — ignored", code.lower()
                )
                continue
            for s in sorted({str(x) for x in raw}):
                key = self._clean_surname_for_matching(
                    unicodedata.normalize("NFC", s).lower().strip()
                )
                if not key or len(key) < 2:
                    continue
                if key in hardcoded_claims:
                    if hardcoded_claims[key] != code:
                        logger.warning(
                            "surname_exact %r in %s.yaml collides with the "
                            "hardcoded %s set — dropped",
                            key,
                            code.lower(),
                            hardcoded_claims[key],
                        )
                    continue  # same-region duplicate of hardcoded: redundant
                prior = yaml_claims.get(key)
                if prior is not None and prior != code:
                    logger.warning(
                        "surname_exact %r claimed by both %s.yaml and %s.yaml "
                        "— dropped from BOTH (ambiguous)",
                        key,
                        prior.lower(),
                        code.lower(),
                    )
                    self._surname_yaml.get(prior, set()).discard(key)
                    continue
                yaml_claims[key] = code
                self._surname_yaml.setdefault(code, set()).add(key)
        if self._surname_yaml:
            logger.info(
                "Loaded surname_exact YAML supplements: %s",
                {k: len(v) for k, v in sorted(self._surname_yaml.items())},
            )

    def _detect_by_surname_patterns(
        self, name: str, possible_regions: List[str]
    ) -> Optional[str]:
        """Detect region using surname pattern matching."""
        if not hasattr(self, "surname_patterns"):
            return None

        # Extract surname from "Family, Given" format
        if "," in name:
            family_name = name.split(",")[0].strip().lower()
        else:
            # For Asian names, check if first part is a known surname
            parts = name.strip().split()
            if len(parts) >= 2:
                # Check if first part is an Asian surname (E1, E3, E4 regions)
                first_part = parts[0].lower()
                first_part_clean = self._clean_surname_for_matching(first_part)

                # Check if it's a known Asian surname
                is_asian_surname = False
                for region_code in ["E1", "E3", "E4"]:
                    if (
                        region_code in self.surname_patterns
                        and region_code in self.IMPLEMENTED_REGIONS
                    ):
                        if first_part_clean in self.surname_patterns[region_code]:
                            is_asian_surname = True
                            break

                # Check if the first name is clearly Western
                is_western_given = self._is_western_given_name(parts[0])

                if is_asian_surname and not is_western_given:
                    family_name = first_part_clean
                elif is_western_given:
                    # Western format: "Given Family" - even if surname is Asian
                    # For Western given names, prioritize Western regions
                    western_regions = [
                        r
                        for r in possible_regions
                        if r.startswith("A") or r.startswith("G")
                    ]
                    if western_regions:
                        return western_regions[0]
                    family_name = parts[-1].lower()
                else:
                    # Western format: "Given Family"
                    family_name = parts[-1].lower()
            else:
                return None

        # Clean surname for matching
        family_name = self._clean_surname_for_matching(family_name)

        # Score each possible region based on surname matches
        region_scores = {}

        for region in possible_regions:
            if region in self.surname_patterns and region in self.IMPLEMENTED_REGIONS:
                surnames = self.surname_patterns[region]

                # Direct match
                if family_name in surnames:
                    region_scores[region] = 10
                else:
                    # Partial match scoring
                    for surname in surnames:
                        if family_name.startswith(surname) or surname.startswith(
                            family_name
                        ):
                            region_scores[region] = max(region_scores.get(region, 0), 7)
                        elif len(surname) >= 3 and (
                            _wb(surname).search(family_name)
                            or _wb(family_name).search(surname)
                        ):
                            region_scores[region] = max(region_scores.get(region, 0), 5)

        # Return region with highest score (minimum score of 7 to avoid false positives)
        if region_scores:
            # Find all regions with the highest score
            max_score = max(region_scores.values())
            if max_score >= 7:
                top_regions = [r for r, s in region_scores.items() if s == max_score]

                # If there's only one top region, return it
                if len(top_regions) == 1:
                    return top_regions[0]

                # Disambiguation for tied scores
                # Check for East Asian name patterns (hyphenated given names)
                remaining_name = name.replace(family_name, "", 1).strip()
                if remaining_name:
                    # Korean names often have hyphenated given names
                    if "-" in remaining_name and "E4" in top_regions:
                        return "E4"
                    # Check for Korean given name patterns (2-3 syllables)
                    if "E4" in top_regions and len(remaining_name.split("-")) in [2, 3]:
                        return "E4"

                # Default: prefer non-English for ambiguous Asian surnames
                if "lee" in family_name.lower() and "E4" in top_regions:
                    return "E4"

                # Otherwise return the first match
                return top_regions[0]

        return None

    def _is_western_given_name(self, name: str) -> bool:
        """Check if a name is a common Western given name."""
        western_given_names = {
            "john",
            "james",
            "robert",
            "michael",
            "william",
            "david",
            "richard",
            "thomas",
            "christopher",
            "charles",
            "daniel",
            "matthew",
            "anthony",
            "mark",
            "donald",
            "steven",
            "paul",
            "andrew",
            "joshua",
            "kenneth",
            "kevin",
            "brian",
            "george",
            "edward",
            "ronald",
            "timothy",
            "jason",
            "jeffrey",
            "ryan",
            "jacob",
            "gary",
            "nicholas",
            "eric",
            "jonathan",
            "stephen",
            "larry",
            "justin",
            "scott",
            "brandon",
            "benjamin",
            "samuel",
            "gregory",
            "alexander",
            "patrick",
            "frank",
            "raymond",
            "jack",
            "dennis",
            "jerry",
            "tyler",
            "aaron",
            "jose",
            "henry",
            "adam",
            "douglas",
            "peter",
            "zachary",
            "noah",
            "walter",
            "christian",
            "javier",
            "harold",
            "arthur",
            # Common female names
            "mary",
            "patricia",
            "jennifer",
            "linda",
            "elizabeth",
            "barbara",
            "susan",
            "jessica",
            "sarah",
            "karen",
            "nancy",
            "lisa",
            "betty",
            "helen",
            "sandra",
            "donna",
            "carol",
            "ruth",
            "sharon",
            "michelle",
            "laura",
            "sarah",
            "kimberly",
            "deborah",
            "dorothy",
            "lisa",
            "nancy",
            "karen",
            "betty",
            "helen",
            "sandra",
            "donna",
            "carol",
            "ruth",
            "sharon",
            "michelle",
            "laura",
            "emily",
            "kimberly",
            "deborah",
            "dorothy",
            "amy",
            "angela",
            "ashley",
            "brenda",
            "emma",
            "olivia",
            "cynthia",
            "marie",
            "janet",
            "catherine",
            "frances",
            "christine",
            "samantha",
            "debra",
            "rachel",
            "carolyn",
            "janet",
            "virginia",
            "maria",
            "heather",
            "diane",
            "julie",
            "joyce",
            "victoria",
            "kelly",
            "christina",
            "joan",
            "evelyn",
            "judith",
            "megan",
            "cheryl",
            "andrea",
            "hannah",
            "jacqueline",
            "martha",
            "gloria",
            "teresa",
        }
        return name.lower().strip() in western_given_names

    def _clean_surname_for_matching(self, surname: str) -> str:
        """Clean surname by removing common particles and prefixes."""
        # Remove common particles (case insensitive)
        particles = {
            "de",
            "del",
            "della",
            "delle",
            "dello",
            "di",
            "da",
            "dal",
            "dalla",
            "du",
            "des",
            "le",
            "la",
            "les",
            "dos",
            "das",
            "do",
            "da",
            "von",
            "van",
            "der",
            "den",
            "het",
            "ten",
            "ter",
            "te",
            "zum",
            "zur",
            "am",
            "im",
            "zu",
            "auf",
            "unter",
            "al",
            "ibn",
            "abu",
            "bin",
            "ben",
            "bat",
            "o'",
            "mc",
            "mac",
            "fitz",
        }

        # Split on spaces and hyphens
        parts = surname.replace("-", " ").split()
        if len(parts) > 1:
            # Check if first part is a particle
            if parts[0].lower() in particles:
                return " ".join(parts[1:])
            # Check if it starts with particle patterns
            for particle in particles:
                if surname.startswith(particle.lower() + " "):
                    return surname[len(particle) + 1 :]

        return surname

    def _load_regions(self):
        """Load and register only actually implemented region implementations."""
        import importlib

        # Load all V7 regions that have processor implementations
        region_imports = {
            # A-groups (Anglo-sphere/Western)
            "A1": ("src.regions.a_groups.a1_anglo_sphere", "A1_AngloSphere"),
            "A2": ("src.regions.a_groups.a2_western_europe", "A2_WesternEurope"),
            "A3": (
                "src.regions.a_groups.a3_nordic_baltic.processor",
                "A3NordicBalticProcessor",
            ),
            "A4": ("src.regions.a_groups.a4_oceania.processor", "A4OceaniaProcessor"),
            "A5": (
                "src.regions.a_groups.a5_caribbean.processor",
                "A5CaribbeanProcessor",
            ),
            # B-groups (Slavic)
            "B1": ("src.regions.b_groups.b1_east_slavic", "B1_EastSlavic"),
            "B2": (
                "src.regions.b_groups.b2_south_slavic_central",
                "B2_SouthSlavicCentral",
            ),
            "B3": ("src.regions.b_groups.b3_greek.processor", "B3GreekProcessor"),
            # C-groups (Middle East/Turkic)
            "C1": ("src.regions.c_groups.c1_turkic.processor", "C1TurkicProcessor"),
            "C2": ("src.regions.c_groups.c2_persian_tajik", "C2_PersianTajik"),
            "C3": ("src.regions.c_groups.c3_arabic_levant_nile", "C3_ArabicLevantNile"),
            "C4": ("src.regions.c_groups.c4_arabic_gulf", "C4_ArabicGulf"),
            "C5": (
                "src.regions.c_groups.c5_arabic_maghreb.processor",
                "C5_ArabicMaghreb",
            ),
            "C6": (
                "src.regions.c_groups.c6_hebrew_diaspora.processor",
                "C6_HebrewDiaspora",
            ),
            "C7": ("src.regions.c_groups.c7_armenian.processor", "C7_Armenian"),
            "C8": ("src.regions.c_groups.c8_georgian.processor", "C8_Georgian"),
            "C9": (
                "src.regions.c_groups.c9_baltic.processor",
                "C9_Baltic",
            ),
            # D-groups (South Asia)
            "D1": (
                "src.regions.d_groups.d1_south_asia_hindi_belt",
                "D1_SouthAsiaHindiBelt",
            ),
            "D2": (
                "src.regions.d_groups.d2_south_asia_dravidian.processor",
                "D2_SouthAsiaDravidian",
            ),
            "D3": (
                "src.regions.d_groups.d3_south_asia_bengali.processor",
                "D3_SouthAsiaBengali",
            ),
            "D4": (
                "src.regions.d_groups.d4_pakistan_urdu.processor",
                "D4_PakistanUrdu",
            ),
            "D5": ("src.regions.d_groups.d5_sinhala.processor", "D5_Sinhala"),
            # E-groups (East Asia)
            "E1": (
                "src.regions.e_groups.e1_sinophone_mainland",
                "E1_SinophoneMainland",
            ),
            "E2": (
                "src.regions.e_groups.e2_traditional_chinese.processor",
                "E2_TraditionalChinese",
            ),
            "E3": ("src.regions.e_groups.e3_japan", "E3_Japan"),
            "E4": ("src.regions.e_groups.e4_korea.processor", "E4KoreanProcessor"),
            "E5": ("src.regions.e_groups.e5_vietnam.processor", "E5_Vietnam"),
            "E6": ("src.regions.e_groups.e6_mainland_sea.processor", "E6_MainlandSEA"),
            "E7": (
                "src.regions.e_groups.e7_maritime_sea.processor",
                "E7MaritimeSEAProcessor",
            ),
            # F-groups (Africa)
            "F1": (
                "src.regions.f_groups.f1_ssa_francophone.processor",
                "F1_SSAFrancophone",
            ),
            "F2": (
                "src.regions.f_groups.f2_ssa_anglophone.processor",
                "F2_SSAAnglophone",
            ),
            "F3": (
                "src.regions.f_groups.f3_horn_of_africa.processor",
                "F3_HornOfAfrica",
            ),
            "F4": (
                "src.regions.f_groups.f4_lusophone_africa.processor",
                "F4_LusophoneAfrica",
            ),
            # G-groups (Latin America)
            "G1": ("src.regions.g_groups.g1_latin_america", "G1_LatinAmerica"),
            # Special groups
            "H1": ("src.regions.special.h1_historical.processor", "H1_Historical"),
            "R0": (
                "src.regions.special.r0_residual_latin_ascii.processor",
                "R0_ResidualLatinAscii",
            ),
            "Z0": ("src.regions.special.z0_quarantine.processor", "Z0_Quarantine"),
        }

        regions_loaded = 0

        for region_code in self.IMPLEMENTED_REGIONS:
            if region_code in region_imports:
                module_path, class_name = region_imports[region_code]
                try:
                    # Import the module
                    module = importlib.import_module(module_path)

                    # Get the class
                    region_class = getattr(module, class_name)

                    # Instantiate the region
                    region_instance = region_class()

                    # Register the region
                    self.register_region(region_instance)
                    regions_loaded += 1

                except Exception as e:
                    logger.error(
                        f"Could not load region {region_code} from {module_path}: {e}"
                    )

        logger.info(f"Loaded {regions_loaded} implemented regions successfully")
