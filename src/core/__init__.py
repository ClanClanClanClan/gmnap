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
from .pipeline import (
    Pipeline,
    PipelineConfig,
    PipelineModeBase,
    PipelineStage,
    StageResult,
    StageStatus,
)
from .unicode_handler import (
    UnicodeHandlerConfig,
    UnicodeNormalizer,
    generate_name_variants,
    normalize_name,
)

__all__ = [
    # Unicode handling
    "UnicodeNormalizer",
    "UnicodeHandlerConfig",
    "normalize_name",
    "generate_name_variants",
    # Pipeline
    "Pipeline",
    "PipelineStage",
    "PipelineConfig",
    "PipelineModeBase",
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
