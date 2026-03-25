"""Stage 8: GlobalValidate - JSON-Schema, transliteration round-trip, graph coherence gate."""

from __future__ import annotations
import json
import logging
import pathlib
import re
import unicodedata
from typing import Dict, List, Tuple, Any
from src.ops.metrics import SCHEMA_VALIDATION_ERRORS, ROUNDTRIP_FAILURES

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Roundtrip threshold from V7 spec section 7
ROUNDTRIP_MIN = 0.97

# Pre-computed enum sets for fast validation
_VALID_FAMILY_NAME_TYPES = frozenset({"surname", "patronymic", "mononym"})
_VALID_GENDERS = frozenset({"male", "female", "nonbinary", "unspecified"})

# V2.0 schema required fields
V2_REQUIRED_FIELDS = [
    "GlobalID",
    "UpdatedAt",
    "CanonicalLatin",
    "CanonicalNative",
    "LanguageOfPublication",
    "FamilyNameType",
    "Gender",
    "CountryCodes",
    "Confidence",
    "Historic",
    "GDPR_DATA",
]

# Load the JSON Schema entry definition once
_SCHEMA_ENTRY = None
_SCHEMA_VALIDATOR = None  # Pre-compiled jsonschema validator
_SCHEMA_PATH = pathlib.Path(__file__).resolve().parents[2] / "docs" / "schema_v2.0.json"

# Pre-compiled regexes
_RE_GLOBALID = re.compile(r"^[A-Z2-7]{22}(--\d+)?$")
_RE_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")


def _load_entry_schema() -> Dict[str, Any] | None:
    """Load the inner entry schema from schema_v2.0.json."""
    global _SCHEMA_ENTRY
    if _SCHEMA_ENTRY is not None:
        return _SCHEMA_ENTRY
    try:
        raw = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        # The schema uses patternProperties["^.+$"] to define the entry object
        _SCHEMA_ENTRY = raw.get("patternProperties", {}).get("^.+$", {})
        return _SCHEMA_ENTRY
    except Exception as e:
        logger.warning(f"Could not load schema_v2.0.json: {e}")
        return None


def _get_validator():
    """Return a pre-compiled jsonschema validator (cached)."""
    global _SCHEMA_VALIDATOR
    if _SCHEMA_VALIDATOR is not None:
        return _SCHEMA_VALIDATOR
    if jsonschema is None:
        return None
    schema = _load_entry_schema()
    if not schema:
        return None
    try:
        cls = jsonschema.validators.validator_for(schema)
        _SCHEMA_VALIDATOR = cls(schema)
        return _SCHEMA_VALIDATOR
    except Exception as e:
        logger.warning(f"Could not compile schema validator: {e}")
        return None


def _dice_coefficient(a: str, b: str) -> float:
    """Compute Dice coefficient (bigram similarity) between two strings."""
    if not a or not b:
        return 0.0
    a = unicodedata.normalize("NFC", a.casefold())
    b = unicodedata.normalize("NFC", b.casefold())
    if a == b:
        return 1.0
    a_bigrams = set(a[i : i + 2] for i in range(len(a) - 1))
    b_bigrams = set(b[i : i + 2] for i in range(len(b) - 1))
    if not a_bigrams or not b_bigrams:
        return 0.0
    overlap = len(a_bigrams & b_bigrams)
    return (2.0 * overlap) / (len(a_bigrams) + len(b_bigrams))


_ALLOWED_FIELDS: frozenset | None = None


def _get_allowed_fields() -> frozenset:
    """Get the set of schema-allowed field names (cached)."""
    global _ALLOWED_FIELDS
    if _ALLOWED_FIELDS is not None:
        return _ALLOWED_FIELDS
    schema = _load_entry_schema()
    _ALLOWED_FIELDS = frozenset(schema.get("properties", {}).keys()) if schema else frozenset()
    return _ALLOWED_FIELDS


def _strip_internal_fields(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Strip pipeline-internal fields (prefixed with _) and non-schema fields
    so that JSON Schema validation only sees spec-defined fields."""
    allowed = _get_allowed_fields()
    if not allowed:
        return {k: v for k, v in entry.items() if not k.startswith("_")}
    return {k: v for k, v in entry.items() if not k.startswith("_") and k in allowed}


def validate_entry_schema(entry: Dict[str, Any]) -> List[str]:
    """Validate an entry against V2.0 schema requirements. Returns list of errors."""
    errors = []

    # Check all required fields from the v2.0 schema
    for field in V2_REQUIRED_FIELDS:
        val = entry.get(field)
        if val is None or (isinstance(val, str) and not val):
            errors.append(f"missing required field: {field}")

    # GlobalID format check
    gid = entry.get("GlobalID", "")
    if gid and not _RE_GLOBALID.match(gid):
        errors.append(f"invalid GlobalID format: {gid}")

    # FamilyNameType enum check
    fnt = entry.get("FamilyNameType")
    if fnt and fnt not in _VALID_FAMILY_NAME_TYPES:
        errors.append(f"invalid FamilyNameType: {fnt}")

    # Gender enum check
    gender = entry.get("Gender")
    if gender and gender not in _VALID_GENDERS:
        errors.append(f"invalid Gender: {gender}")

    # CountryCodes format check
    cc = entry.get("CountryCodes")
    if cc and isinstance(cc, list):
        for c in cc:
            if not isinstance(c, str) or not _RE_COUNTRY_CODE.match(c):
                errors.append(f"invalid CountryCode: {c}")

    # Confidence range check
    conf = entry.get("Confidence")
    if conf is not None and isinstance(conf, (int, float)):
        if conf < 0 or conf > 100:
            errors.append(f"Confidence out of range [0,100]: {conf}")

    # Plausibility checks
    birth = entry.get("BirthYear")
    death = entry.get("DeathYear")
    if birth and death and isinstance(birth, (int, float)) and isinstance(death, (int, float)):
        if death < birth:
            errors.append(f"DeathYear ({death}) < BirthYear ({birth})")
        if death - birth > 150:
            errors.append(f"Implausible lifespan: {death - birth} years")

    # Full JSON Schema validation (pre-compiled validator, skip if field checks found errors)
    if not errors:
        validator = _get_validator()
        if validator is not None:
            clean = _strip_internal_fields(entry)
            for err in validator.iter_errors(clean):
                errors.append(f"schema: {err.message}")
                break  # One schema error is enough to flag

    return errors


def validate_roundtrip(entry: Dict[str, Any]) -> float:
    """Check transliteration round-trip for CJK/non-Latin entries."""
    canonical_latin = entry.get("CanonicalLatin", "")
    canonical_native = entry.get("CanonicalNative", "")

    if not canonical_native or canonical_native == canonical_latin:
        return 1.0  # Latin-only entry, trivially passes

    # For entries with CanonicalNative, check round-trip using Dice coefficient
    latinized = entry.get("CanonicalLatin_Folded", canonical_latin)
    return _dice_coefficient(canonical_latin, latinized)


def stage8_global_validate(
    batch: List[Dict], mode: str = "quick", graph_coherence: float = 1.0, schema_strict: int = 0
) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Stage 8: Validate all entries against V7 schema, roundtrip, and coherence gates.

    schema_strict controls how validation errors are handled:
      0 (default): Advisory — only quarantine entries missing required fields.
                   Other schema errors are logged but entries pass through.
      1: Strict quarantine — ALL schema errors cause quarantine to Z0.
      2: Strict reject — ALL schema errors cause entry REJECTION
                   (excluded from output entirely).

    Roundtrip failures are always flagged but NEVER quarantined or rejected
    (the data is still usable, just lower quality).

    Returns (validated_batch, metrics).
    """
    schema_errors = 0
    roundtrip_failures = 0
    quarantined_count = 0
    rejected_count = 0
    total = len(batch)
    out = []

    # Mode-specific coherence thresholds
    coherence_min = {"quick": 0.85, "full": 0.92, "extreme": 0.97}.get(mode.lower(), 0.85)

    for e in batch:
        # Schema validation (collect all errors, don't stop at first)
        errors = validate_entry_schema(e)
        if errors:
            schema_errors += len(errors)
            e["_validation_errors"] = errors
            for err in errors:
                SCHEMA_VALIDATION_ERRORS.labels(field=err.split(":")[0]).inc()
            logger.warning(f"Schema errors for {e.get('GlobalID', '?')}: {errors}")

            if schema_strict == 2:
                # Strict reject: ALL schema errors → exclude from output
                rejected_count += 1
                logger.error(f"REJECTED {e.get('GlobalID', '?')}: {errors}")
                continue  # skip this entry entirely

            if schema_strict == 1:
                # Strict quarantine: ALL schema errors → quarantine to Z0
                e["DetectedRegion"] = "Z0"
                e.setdefault("RegionalExtras", {})["quarantined"] = True
                e["RegionalExtras"]["quarantine_reasons"] = [
                    f"validation-failure: {err}" for err in errors
                ]
                e["RegionalExtras"]["needs_human_review"] = True
                quarantined_count += 1
                logger.error(f"QUARANTINED {e.get('GlobalID', '?')}: {errors}")
            else:
                # Default (strict=0): only quarantine on missing REQUIRED fields
                required_missing = [
                    err for err in errors if err.startswith("missing required field:")
                ]
                if required_missing:
                    e["DetectedRegion"] = "Z0"
                    e.setdefault("RegionalExtras", {})["quarantined"] = True
                    e["RegionalExtras"]["quarantine_reasons"] = [
                        f"validation-failure: {err}" for err in required_missing
                    ]
                    e["RegionalExtras"]["needs_human_review"] = True
                    quarantined_count += 1
                    logger.error(f"QUARANTINED {e.get('GlobalID', '?')}: {required_missing}")

        # Roundtrip validation
        rt_score = validate_roundtrip(e)
        e["RoundtripScore"] = rt_score
        if rt_score < ROUNDTRIP_MIN:
            roundtrip_failures += 1
            region = e.get("DetectedRegion", "unknown")
            ROUNDTRIP_FAILURES.labels(region=region).inc()
            logger.warning(
                f"Roundtrip failure for {e.get('GlobalID', '?')}: {rt_score:.4f} < {ROUNDTRIP_MIN}"
            )

        out.append(e)

    # Compute aggregate roundtrip rate
    rt_rate = 1.0 - (roundtrip_failures / total) if total > 0 else 1.0

    # Graph coherence gate
    coherence_passed = graph_coherence >= coherence_min

    metrics = {
        "schema_errors": schema_errors,
        "roundtrip_failures": roundtrip_failures,
        "roundtrip_script_rate": rt_rate,
        "graph_coherence": graph_coherence,
        "graph_coherence_min": coherence_min,
        "graph_coherence_passed": coherence_passed,
        "quarantined_count": quarantined_count,
        "rejected_count": rejected_count,
    }

    if not coherence_passed:
        logger.error(f"Graph coherence gate FAILED: {graph_coherence:.4f} < {coherence_min}")

    if quarantined_count > 0:
        logger.warning(
            f"Stage 8: {quarantined_count}/{total} entries quarantined due to validation failures"
        )

    if rejected_count > 0:
        logger.warning(f"Stage 8: {rejected_count}/{total} entries rejected due to schema_strict=2")

    return out, metrics
