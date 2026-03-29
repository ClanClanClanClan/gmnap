"""
GMNAP v7.0 Pipeline Stage 0: Configuration Loading
Handles configuration loading and validation for the pipeline.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from ..core.config import ConfigurationManager
from ..core.errors import ConfigurationError


class ConfigStage:
    """Stage 0: Configuration loading and validation"""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration stage"""
        self.config_path = config_path or Path("./config")
        self.config_manager = ConfigurationManager(self.config_path)
        self.config: Dict[str, Any] = {}

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load and validate configuration

        Args:
            context: Pipeline execution context

        Returns:
            Updated context with configuration loaded
        """
        try:
            # Load main configuration
            self.config = self.config_manager.load()

            # Validate required configuration sections
            self._validate_config()

            # Add configuration to context
            context["config"] = self.config
            context["stage_0_completed"] = True

            return context

        except Exception as e:
            raise ConfigurationError(f"Stage 0 configuration loading failed: {str(e)}")

    def _validate_config(self) -> None:
        """Validate that required configuration sections exist"""
        required_sections = [
            "pipeline",
            "regions",
            "authorities",
            "security",
            "monitoring",
        ]

        for section in required_sections:
            if section not in self.config:
                raise ConfigurationError(
                    f"Missing required configuration section: {section}"
                )

        # Validate pipeline configuration
        pipeline_config = self.config.get("pipeline", {})
        if "mode" not in pipeline_config:
            raise ConfigurationError("Pipeline mode not specified in configuration")

        valid_modes = ["quick", "full", "extreme"]
        if pipeline_config["mode"] not in valid_modes:
            raise ConfigurationError(
                f"Invalid pipeline mode: {pipeline_config['mode']}. Must be one of {valid_modes}"
            )
