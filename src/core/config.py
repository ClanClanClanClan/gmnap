"""
Configuration management system for GMNAP.
Handles pipeline configuration, environment settings, and runtime parameters.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration."""

    type: str = "duckdb"  # duckdb or sqlite
    path: str = "./data/gmnap.db"
    connection_timeout: int = 30
    max_connections: int = 10
    enable_wal: bool = True
    enable_compression: bool = True


@dataclass
class ProcessingConfig:
    """Processing configuration."""

    batch_size: int = 1000
    max_workers: int = 4
    chunk_size: int = 10000
    memory_limit_mb: int = 2048
    timeout_seconds: int = 300
    enable_parallel: bool = True
    enable_caching: bool = True


@dataclass
class UnicodeConfig:
    """Unicode processing configuration."""

    preserve_combining: bool = True
    handle_ligatures: bool = True
    handle_sharp_s: bool = True
    handle_greek_tonos: bool = True
    normalization_form: str = "NFC"


@dataclass
class ValidationConfig:
    """Validation configuration."""

    strict_mode: bool = False
    validate_unicode: bool = True
    validate_regions: bool = True
    validate_dates: bool = True
    max_name_length: int = 500
    min_confidence_score: float = 0.0
    max_confidence_score: float = 1.0


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration."""

    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_metrics: bool = True
    metrics_interval: int = 60
    enable_tracing: bool = False
    trace_sample_rate: float = 0.1


@dataclass
class CacheConfig:
    """Cache configuration."""

    cache_dir: str = "./cache"
    max_cache_size_mb: int = 1024
    cache_ttl_seconds: int = 3600
    enable_compression: bool = True
    compression_level: int = 6


@dataclass
class SecurityConfig:
    """Security configuration."""

    enable_input_validation: bool = True
    max_request_size_mb: int = 10
    rate_limit_requests: int = 1000
    rate_limit_window_seconds: int = 60
    allowed_file_extensions: list = field(
        default_factory=lambda: [".yaml", ".yml", ".json"]
    )


@dataclass
class APIConfig:
    """API configuration for external services."""

    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    user_agent: str = "GMNAP/1.0"
    enable_ssl_verification: bool = True


@dataclass
class GMNAPConfig:
    """Main GMNAP configuration."""

    environment: Environment = Environment.DEVELOPMENT
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    unicode: UnicodeConfig = field(default_factory=UnicodeConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    api: APIConfig = field(default_factory=APIConfig)

    # Pipeline specific settings
    pipeline_mode: str = "full"
    checkpoint_enabled: bool = True
    checkpoint_interval: int = 1000

    # Region specific settings
    regions_enabled: list = field(default_factory=lambda: ["all"])
    regions_parallel: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GMNAPConfig":
        """Create configuration from dictionary."""
        # Handle environment enum
        if "environment" in data and isinstance(data["environment"], str):
            data["environment"] = Environment(data["environment"])

        # Handle nested configurations
        if "database" in data and isinstance(data["database"], dict):
            data["database"] = DatabaseConfig(**data["database"])
        if "processing" in data and isinstance(data["processing"], dict):
            # Handle legacy 'batch' field by renaming to 'batch_size'
            processing_data = data["processing"].copy()
            if "batch" in processing_data and "batch_size" not in processing_data:
                processing_data["batch_size"] = processing_data.pop("batch")
            # Remove any unexpected fields
            expected_fields = {
                "batch_size",
                "max_workers",
                "chunk_size",
                "memory_limit_mb",
                "timeout_seconds",
                "enable_parallel",
                "enable_caching",
            }
            processing_data = {
                k: v for k, v in processing_data.items() if k in expected_fields
            }
            data["processing"] = ProcessingConfig(**processing_data)
        if "unicode" in data and isinstance(data["unicode"], dict):
            unicode_data = data["unicode"].copy()
            # Handle legacy field names
            if "handle" in unicode_data and "handle_ligatures" not in unicode_data:
                unicode_data["handle_ligatures"] = unicode_data.pop("handle")
            # Remove any unexpected fields
            expected_fields = {
                "preserve_combining",
                "handle_ligatures",
                "handle_sharp_s",
                "handle_greek_tonos",
                "normalization_form",
            }
            unicode_data = {
                k: v for k, v in unicode_data.items() if k in expected_fields
            }
            data["unicode"] = UnicodeConfig(**unicode_data)
        if "validation" in data and isinstance(data["validation"], dict):
            validation_data = data["validation"].copy()
            # Handle legacy field names
            if "strict" in validation_data and "strict_mode" not in validation_data:
                validation_data["strict_mode"] = validation_data.pop("strict")
            # Remove any unexpected fields
            expected_fields = {
                "strict_mode",
                "validate_unicode",
                "validate_regions",
                "validate_dates",
                "max_name_length",
                "min_confidence_score",
                "max_confidence_score",
            }
            validation_data = {
                k: v for k, v in validation_data.items() if k in expected_fields
            }
            data["validation"] = ValidationConfig(**validation_data)
        if "monitoring" in data and isinstance(data["monitoring"], dict):
            data["monitoring"] = MonitoringConfig(**data["monitoring"])
        if "cache" in data and isinstance(data["cache"], dict):
            cache_data = data["cache"].copy()
            # Handle legacy field names
            if "max" in cache_data and "max_cache_size_mb" not in cache_data:
                cache_data["max_cache_size_mb"] = cache_data.pop("max")
            # Remove any unexpected fields
            expected_fields = {
                "cache_dir",
                "max_cache_size_mb",
                "cache_ttl_seconds",
                "enable_compression",
                "compression_level",
            }
            cache_data = {k: v for k, v in cache_data.items() if k in expected_fields}
            data["cache"] = CacheConfig(**cache_data)
        if "security" in data and isinstance(data["security"], dict):
            data["security"] = SecurityConfig(**data["security"])
        if "api" in data and isinstance(data["api"], dict):
            data["api"] = APIConfig(**data["api"])

        # Handle special environment mappings
        if "regions" in data and isinstance(data["regions"], dict):
            if "enabled" in data["regions"]:
                data["regions_enabled"] = data["regions"]["enabled"]
            if "parallel" in data["regions"]:
                data["regions_parallel"] = data["regions"]["parallel"]
            del data["regions"]

        # Filter unexpected top-level fields
        expected_fields = {
            "environment",
            "database",
            "processing",
            "unicode",
            "validation",
            "monitoring",
            "cache",
            "security",
            "api",
            "pipeline_mode",
            "checkpoint_enabled",
            "checkpoint_interval",
            "regions_enabled",
            "regions_parallel",
        }
        filtered_data = {k: v for k, v in data.items() if k in expected_fields}

        return cls(**filtered_data)


class ConfigurationManager:
    """Manages configuration loading and access."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("./config/gmnap.yaml")
        self._config: Optional[GMNAPConfig] = None
        self._env_prefix = "GMNAP_"
        self._weights: Optional[Dict[str, float]] = None
        self._source_manifest: Optional[Dict[str, Any]] = None

    def load(self) -> GMNAPConfig:
        """Load configuration from file and environment."""
        # Start with defaults
        config = GMNAPConfig()

        # Load from file if exists
        if self.config_path.exists():
            file_config = self._load_from_file(self.config_path)
            config = self._merge_config(config, file_config)

        # Override with environment variables
        env_config = self._load_from_env()
        config = self._merge_config(config, env_config)

        # Validate configuration
        self._validate_config(config)

        # Load additional configuration files
        self._load_weights()
        self._load_source_manifest()

        self._config = config
        logger.info(f"Configuration loaded for environment: {config.environment.value}")

        return config

    def _load_from_file(self, path: Path) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        try:
            with open(path, "r") as f:
                if path.suffix in [".yaml", ".yml"]:
                    return yaml.safe_load(f) or {}
                elif path.suffix == ".json":
                    return json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {path.suffix}")
        except Exception as e:
            logger.warning(f"Failed to load config from {path}: {e}")
            return {}

    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}

        for key, value in os.environ.items():
            if key.startswith(self._env_prefix):
                # Convert GMNAP_DATABASE_PATH to database.path
                config_key = key[len(self._env_prefix) :].lower()
                config_path = config_key.split("_")

                # Special handling for multi-word field names
                # Only split on the first underscore to separate section from field
                if len(config_path) >= 2:
                    section = config_path[0]  # e.g., 'processing'
                    field_parts = config_path[1:]  # e.g., ['batch', 'size']
                    field_name = "_".join(field_parts)  # e.g., 'batch_size'

                    # Build nested dictionary
                    if section not in config:
                        config[section] = {}

                    # Convert value type
                    parsed_value = self._parse_env_value(value)
                    config[section][field_name] = parsed_value

                else:
                    # Top-level field (e.g., GMNAP_ENVIRONMENT)
                    parsed_value = self._parse_env_value(value)
                    config[config_path[0]] = parsed_value
        return config

    def _parse_env_value(self, value: str) -> Union[str, int, float, bool, list]:
        """Parse environment variable value to appropriate type."""
        # Boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Number
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # List (comma-separated)
        if "," in value:
            return [v.strip() for v in value.split(",")]

        # String
        return value

    def _merge_config(self, base: GMNAPConfig, override: Dict[str, Any]) -> GMNAPConfig:
        """Merge override configuration into base configuration."""
        base_dict = base.to_dict()
        merged = self._deep_merge(base_dict, override)
        return GMNAPConfig.from_dict(merged)

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recursively merge dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_config(self, config: GMNAPConfig) -> None:
        """Validate configuration values."""
        # Validate paths exist or can be created (skip if read-only or test path)
        db_path = Path(config.database.path)
        if not db_path.parent.exists() and not str(db_path).startswith("/prod"):
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                pass  # Skip if can't create (test environment or read-only)

        cache_path = Path(config.cache.cache_dir)
        if not cache_path.exists():
            try:
                cache_path.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                pass  # Skip if can't create (test environment or read-only)

        # Validate numeric ranges
        if config.processing.batch_size <= 0:
            raise ValueError("Batch size must be positive")

        if config.processing.max_workers <= 0:
            raise ValueError("Max workers must be positive")

        if not 0 <= config.validation.min_confidence_score <= 1:
            raise ValueError("Min confidence score must be between 0 and 1")

        if not 0 <= config.validation.max_confidence_score <= 1:
            raise ValueError("Max confidence score must be between 0 and 1")

        if (
            config.validation.min_confidence_score
            > config.validation.max_confidence_score
        ):
            raise ValueError("Min confidence score cannot be greater than max")

    def get(self) -> GMNAPConfig:
        """Get current configuration."""
        if self._config is None:
            self.load()
        return self._config

    def reload(self) -> GMNAPConfig:
        """Reload configuration from sources."""
        logger.info("Reloading configuration...")
        return self.load()

    def save(self, path: Optional[Path] = None) -> None:
        """Save current configuration to file."""
        save_path = path or self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = self._config.to_dict() if self._config else {}

        # Convert enums to strings
        if "environment" in config_dict and isinstance(
            config_dict["environment"], Environment
        ):
            config_dict["environment"] = config_dict["environment"].value

        with open(save_path, "w") as f:
            if save_path.suffix in [".yaml", ".yml"]:
                yaml.safe_dump(
                    config_dict, f, default_flow_style=False, sort_keys=False
                )
            else:
                json.dump(config_dict, f, indent=2)

        logger.info(f"Configuration saved to {save_path}")

    def _load_weights(self) -> None:
        """Load confidence score weights from weights.yaml."""
        weights_path = self.config_path.parent / "weights.yaml"

        if weights_path.exists():
            try:
                with open(weights_path, "r") as f:
                    weights_data = yaml.safe_load(f) or {}

                # Validate weights
                if not isinstance(weights_data, dict):
                    logger.error("weights.yaml must contain a dictionary")
                    self._weights = {}
                    return

                # Check all values are floats and sum to 1
                total = sum(weights_data.values())
                if abs(total - 1.0) > 0.001:
                    logger.warning(f"Weights sum to {total}, normalizing to 1.0")
                    # Normalize
                    for key in weights_data:
                        weights_data[key] = weights_data[key] / total

                self._weights = weights_data
                logger.info(f"Loaded {len(self._weights)} confidence weights")

            except Exception as e:
                logger.error(f"Failed to load weights.yaml: {e}")
                self._weights = {}
        else:
            # Default weights
            self._weights = {
                "id_score": 0.42,
                "script_certainty": 0.34,
                "msc_match": 0.15,
                "gender_certainty": 0.05,
                "affiliation_match": 0.04,
            }
            logger.info("Using default confidence weights")

    def _load_source_manifest(self) -> None:
        """Load source manifest from source_manifest.json."""
        manifest_path = self.config_path.parent / "source_manifest.json"

        if manifest_path.exists():
            try:
                with open(manifest_path, "r") as f:
                    self._source_manifest = json.load(f)

                # Validate manifest
                if not isinstance(self._source_manifest, dict):
                    logger.error("source_manifest.json must contain a dictionary")
                    self._source_manifest = {}
                    return

                # Check required fields for each source
                for source, config in self._source_manifest.items():
                    required = ["enabled", "daily_quota", "tier"]
                    missing = [field for field in required if field not in config]
                    if missing:
                        logger.warning(f"Source {source} missing fields: {missing}")

                logger.info(f"Loaded manifest for {len(self._source_manifest)} sources")

            except Exception as e:
                logger.error(f"Failed to load source_manifest.json: {e}")
                self._source_manifest = {}
        else:
            # Default manifest
            self._source_manifest = {
                "OpenAlex": {
                    "enabled": True,
                    "daily_quota": 864000,
                    "tier": 0,
                    "base_url": "https://api.openalex.org",
                    "license": "CC0",
                },
                "Crossref": {
                    "enabled": True,
                    "daily_quota": 4300000,
                    "tier": 0,
                    "base_url": "https://api.crossref.org",
                    "license": "CC0",
                },
                "ORCID": {
                    "enabled": True,
                    "daily_quota": 500,
                    "tier": 0,
                    "base_url": "https://pub.orcid.org",
                    "license": "CC0",
                },
            }
            logger.info("Using default source manifest")

    def get_weights(self) -> Dict[str, float]:
        """Get confidence score weights."""
        if self._weights is None:
            self._load_weights()
        return self._weights.copy()

    def get_source_manifest(self) -> Dict[str, Any]:
        """Get source manifest."""
        if self._source_manifest is None:
            self._load_source_manifest()
        return self._source_manifest.copy()


# Global configuration instance
_config_manager: Optional[ConfigurationManager] = None


def get_config() -> GMNAPConfig:
    """Get global configuration instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager.get()


def set_config_path(path: Path) -> None:
    """Set custom configuration file path."""
    global _config_manager
    _config_manager = ConfigurationManager(path)
