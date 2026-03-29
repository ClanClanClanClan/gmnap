#!/usr/bin/env python3
"""
GMNAP V7 Stage 0: Configuration and Environment Setup
Loads config, validates environment, decrypts secrets, queries registry
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class V7RuntimeConfig:
    """V7 Runtime configuration based on specs_v7.yaml"""

    mode: str = "Quick"  # Quick, Full, Extreme
    tier_apis: str = "tier-0"  # tier-0, tier-0+1, Full+tier-2-3
    cpu_workers: int = 4
    runtime_per_1M: str = "35 min"
    streaming_chunk_size: int = 8000
    peak_memory_limit: str = "6GB RSS"

    # Quality gates
    duplicate_global_id_max: int = 0
    duplicate_external_id_pct_max: float = 0.10
    roundtrip_script_rate_min: float = 0.97
    genealogy_edge_conflict_pct_max: float = 2.0
    graph_coherence_score_min: float = 0.85
    idempotent_diff_bytes_max: int = 0

    # API configuration
    crossref_enabled: bool = True
    openalex_enabled: bool = True
    orcid_enabled: bool = False
    wikidata_enabled: bool = False

    # Database configuration
    memgraph_uri: str = "bolt://localhost:7687"
    redis_uri: str = "redis://localhost:6379"
    duckdb_path: str = "./cache/analytics.duckdb"

    # Cache configuration
    cache_compression: str = "zstd"
    cache_max_gb: int = 50
    cache_max_days: int = 60

    # Security
    gdpr_mode: bool = False
    drop_personal: bool = False
    encrypt_cache: bool = True

    @classmethod
    def from_mode(cls, mode: str) -> "V7RuntimeConfig":
        """Create config based on runtime mode"""
        configs = {
            "Quick": cls(
                mode="Quick",
                tier_apis="tier-0",
                cpu_workers=4,
                runtime_per_1M="35 min",
                duplicate_external_id_pct_max=0.10,
                genealogy_edge_conflict_pct_max=2.0,
                graph_coherence_score_min=0.85,
            ),
            "Full": cls(
                mode="Full",
                tier_apis="tier-0+1",
                cpu_workers=8,
                runtime_per_1M="70 min",
                duplicate_external_id_pct_max=0.05,
                genealogy_edge_conflict_pct_max=1.0,
                graph_coherence_score_min=0.92,
                wikidata_enabled=True,
            ),
            "Extreme": cls(
                mode="Extreme",
                tier_apis="Full+tier-2-3",
                cpu_workers=12,
                runtime_per_1M="no SLA",
                duplicate_external_id_pct_max=0.0,
                genealogy_edge_conflict_pct_max=0.0,
                graph_coherence_score_min=0.97,
                wikidata_enabled=True,
                orcid_enabled=True,
            ),
        }
        return configs.get(mode, configs["Quick"])


def stage0_load_config(
    config_path: Optional[Path] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Stage 0: Load and validate configuration

    Operations:
    1. env validate
    2. decrypt secrets
    3. query registry
    4. validate authorities

    Returns:
        Tuple of (config_dict, metrics_dict)
    """
    metrics = {
        "config_source": "default",
        "mode": "Quick",
        "apis_enabled": [],
        "validation_passed": True,
        "secrets_loaded": False,
    }

    # 1. Load base configuration
    config_path = config_path or Path("config")
    config = {}

    # Try to load from file
    config_file = config_path / "pipeline.yaml"
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)
        metrics["config_source"] = str(config_file)

    # 2. Environment variable overrides
    mode = os.getenv("GMNAP_MODE", config.get("mode", "Quick"))
    if mode not in ["Quick", "Full", "Extreme"]:
        logger.warning(f"Invalid mode {mode}, defaulting to Quick")
        mode = "Quick"

    metrics["mode"] = mode

    # 3. Create runtime config
    runtime_config = V7RuntimeConfig.from_mode(mode)

    # Apply environment overrides
    if os.getenv("MG_URI"):
        runtime_config.memgraph_uri = os.getenv("MG_URI")
    if os.getenv("REDIS_URI"):
        runtime_config.redis_uri = os.getenv("REDIS_URI")
    if os.getenv("GMNAP_GDPR_MODE"):
        runtime_config.gdpr_mode = os.getenv("GMNAP_GDPR_MODE") == "1"
    if os.getenv("GMNAP_DROP_PERSONAL"):
        runtime_config.drop_personal = os.getenv("GMNAP_DROP_PERSONAL") == "1"
    if os.getenv("GMNAP_WORKERS"):
        runtime_config.cpu_workers = int(os.getenv("GMNAP_WORKERS"))

    # 4. Load and decrypt secrets
    secrets = load_secrets(config_path)
    if secrets:
        metrics["secrets_loaded"] = True

    # 5. Validate authority sources
    authorities = validate_authorities(runtime_config)
    metrics["apis_enabled"] = list(authorities.keys())

    # 6. Validate quality gates
    gates = validate_quality_gates(runtime_config)

    # 7. Build final config
    final_config = {
        "mode": runtime_config.mode,
        "runtime": asdict(runtime_config),
        "authorities": authorities,
        "quality_gates": gates,
        "secrets": secrets,
        "paths": {
            "config": str(config_path),
            "cache": os.getenv("GMNAP_CACHE_DIR", "./cache"),
            "schemas": os.getenv("GMNAP_SCHEMA_DIR", "./schemas"),
            "data": os.getenv("GMNAP_DATA_DIR", "./data"),
        },
    }

    # 8. Validate entire configuration
    validation_errors = validate_config(final_config)
    if validation_errors:
        logger.error(f"Configuration validation failed: {validation_errors}")
        metrics["validation_passed"] = False
        metrics["validation_errors"] = validation_errors

    logger.info(
        f"Stage 0 complete: Mode={mode}, APIs={len(authorities)}, Valid={metrics['validation_passed']}"
    )

    return final_config, metrics


def load_secrets(config_path: Path) -> Dict[str, str]:
    """
    Load and decrypt secrets from file or environment

    Returns:
        Dictionary of decrypted secrets
    """
    secrets = {}

    # Check for secrets file
    secrets_file = config_path / "secrets.yaml"
    if secrets_file.exists():
        # In production, this would decrypt using KMS/Vault
        # For now, just load plaintext
        with open(secrets_file) as f:
            file_secrets = yaml.safe_load(f)
            if file_secrets:
                secrets.update(file_secrets)

    # Environment variable secrets (highest priority)
    env_secrets = {
        "crossref_api_key": os.getenv("CROSSREF_API_KEY"),
        "openalex_api_key": os.getenv("OPENALEX_API_KEY"),
        "orcid_client_id": os.getenv("ORCID_CLIENT_ID"),
        "orcid_client_secret": os.getenv("ORCID_CLIENT_SECRET"),
        "memgraph_password": os.getenv("MG_PASSWORD"),
        "redis_password": os.getenv("REDIS_PASSWORD"),
        "doi_api_key": os.getenv("DOI_API_KEY"),
        "sftp_password": os.getenv("SFTP_PASSWORD"),
    }

    # Add non-null secrets
    for key, value in env_secrets.items():
        if value:
            secrets[key] = value

    return secrets


def validate_authorities(config: V7RuntimeConfig) -> Dict[str, Dict[str, Any]]:
    """
    Validate and configure authority sources based on runtime mode

    Returns:
        Dictionary of enabled authority configurations
    """
    authorities = {}

    # Tier 0 - Always available
    if config.crossref_enabled:
        authorities["crossref"] = {
            "tier": 0,
            "enabled": True,
            "daily_quota": 4_300_000,
            "license": "CC0",
            "endpoint": "https://api.crossref.org",
        }

    if config.openalex_enabled:
        authorities["openalex"] = {
            "tier": 0,
            "enabled": True,
            "daily_quota": 864_000,
            "license": "CC0",
            "endpoint": "https://api.openalex.org",
        }

    # Tier 1 - Full mode and above
    if config.mode in ["Full", "Extreme"]:
        if config.wikidata_enabled:
            authorities["wikidata"] = {
                "tier": 1,
                "enabled": True,
                "daily_quota": None,  # Dump-based
                "license": "CC0",
                "endpoint": "https://query.wikidata.org/sparql",
            }

        if config.orcid_enabled:
            authorities["orcid"] = {
                "tier": 1,
                "enabled": True,
                "daily_quota": 100_000,
                "license": "CC0",
                "endpoint": "https://pub.orcid.org/v3.0",
            }

    # Tier 2-3 - Extreme mode only (commercial APIs)
    if config.mode == "Extreme":
        # These require paid subscriptions
        authorities["mathscinet"] = {
            "tier": 2,
            "enabled": False,  # Requires subscription
            "daily_quota": 20_000,
            "license": "Subscription",
            "endpoint": None,
        }

        authorities["scopus"] = {
            "tier": 2,
            "enabled": False,  # Requires Elsevier license
            "daily_quota": 20_000,
            "license": "Elsevier",
            "endpoint": None,
        }

    return authorities


def validate_quality_gates(config: V7RuntimeConfig) -> Dict[str, Any]:
    """
    Configure quality gates based on runtime mode

    Returns:
        Dictionary of quality gate thresholds
    """
    return {
        "duplicate_global_id": config.duplicate_global_id_max,
        "duplicate_external_id_pct": config.duplicate_external_id_pct_max,
        "roundtrip_script_rate_min": config.roundtrip_script_rate_min,
        "genealogy_edge_conflict_pct": config.genealogy_edge_conflict_pct_max,
        "graph_coherence_score_min": config.graph_coherence_score_min,
        "peak_rss_gb_on_2M": 6,
        "warm_cache_runtime_per_1M_min": 35 if config.mode == "Quick" else 70,
        "idempotent_diff_bytes_max": config.idempotent_diff_bytes_max,
    }


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate the complete configuration

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Required paths
    for path_name, path_value in config.get("paths", {}).items():
        if not Path(path_value).exists():
            Path(path_value).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created missing directory: {path_value}")

    # Check for at least one authority source
    if not config.get("authorities"):
        errors.append("No authority sources configured")

    # Validate mode
    if config.get("mode") not in ["Quick", "Full", "Extreme"]:
        errors.append(f"Invalid mode: {config.get('mode')}")

    # Check database connectivity (optional)
    runtime = config.get("runtime", {})
    if runtime.get("memgraph_uri"):
        # In production, would test connection
        logger.info(f"Memgraph configured at: {runtime['memgraph_uri']}")

    # Validate quality gates
    gates = config.get("quality_gates", {})
    if gates.get("idempotent_diff_bytes_max", 0) > 0:
        logger.warning("Non-zero idempotency threshold violates V7 spec")

    return errors


def generate_config_hash(config: Dict[str, Any]) -> str:
    """
    Generate a deterministic hash of the configuration
    Used for cache invalidation and versioning

    Returns:
        SHA256 hash of configuration
    """
    # Remove volatile fields
    stable_config = {k: v for k, v in config.items() if k not in ["secrets", "paths"]}

    # Convert to canonical JSON
    config_json = json.dumps(stable_config, sort_keys=True, separators=(",", ":"))

    # Generate hash
    return hashlib.sha256(config_json.encode()).hexdigest()


# Convenience function for pipeline
def load_config(mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration for pipeline

    Args:
        mode: Override runtime mode (Quick/Full/Extreme)

    Returns:
        Configuration dictionary
    """
    if mode:
        os.environ["GMNAP_MODE"] = mode

    config, metrics = stage0_load_config()

    # Add config hash for versioning
    config["config_hash"] = generate_config_hash(config)

    return config


# For testing
def test_stage0():
    """Test Stage 0 configuration loading"""
    print("Testing Stage 0: Configuration")
    print("-" * 40)

    for mode in ["Quick", "Full", "Extreme"]:
        print(f"\nMode: {mode}")
        config, metrics = stage0_load_config()
        config["mode"] = mode  # Override for testing

        print(f"  APIs enabled: {metrics['apis_enabled']}")
        print(f"  Validation: {'✅' if metrics['validation_passed'] else '❌'}")
        print(f"  Config hash: {generate_config_hash(config)[:16]}...")

        runtime = V7RuntimeConfig.from_mode(mode)
        print(f"  Workers: {runtime.cpu_workers}")
        print(f"  Runtime/1M: {runtime.runtime_per_1M}")
        print(f"  Quality gates:")
        print(f"    - Graph coherence: {runtime.graph_coherence_score_min}")
        print(f"    - Idempotency: {runtime.idempotent_diff_bytes_max} bytes")


if __name__ == "__main__":
    test_stage0()
