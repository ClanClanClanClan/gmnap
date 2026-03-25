"""
Core GMNAP functionality.
"""

from .config import ConfigurationManager, GMNAPConfig, get_config, set_config_path
from .errors import (
    AuthenticationError,
    CircuitBreaker,
    ConfigurationError,
    DatabaseError,
    ErrorCollector,
    ErrorRecovery,
    GMNAPError,
    NetworkError,
    RateLimitError,
    ResourceExhaustedError,
    SchemaError,
    UnicodeError,
    ValidationError,
)
from .monitoring import health, metrics, performance, setup_logging
from .pipeline import (
    Pipeline,
    PipelineConfig,
    PipelineMode,
    PipelineStage,
    StageResult,
    StageStatus,
)
from .unicode_handler import (
    UnicodeConfig,
    UnicodeNormalizer,
    generate_name_variants,
    normalize_name,
)

__all__ = [
    # Unicode handling
    "UnicodeNormalizer",
    "UnicodeConfig",
    "normalize_name",
    "generate_name_variants",
    # Pipeline
    "Pipeline",
    "PipelineStage",
    "PipelineConfig",
    "PipelineMode",
    "StageStatus",
    "StageResult",
    # Configuration
    "GMNAPConfig",
    "ConfigurationManager",
    "get_config",
    "set_config_path",
    # Monitoring
    "metrics",
    "health",
    "performance",
    "setup_logging",
    # Errors
    "GMNAPError",
    "ValidationError",
    "SchemaError",
    "UnicodeError",
    "DatabaseError",
    "NetworkError",
    "AuthenticationError",
    "RateLimitError",
    "ConfigurationError",
    "ResourceExhaustedError",
    "ErrorRecovery",
    "CircuitBreaker",
    "ErrorCollector",
]
