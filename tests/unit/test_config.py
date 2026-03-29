"""
Unit tests for configuration management.
"""

import json
import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from src.core.config import (
    APIConfig,
    CacheConfig,
    ConfigurationManager,
    DatabaseConfig,
    Environment,
    GMNAPConfig,
    MonitoringConfig,
    ProcessingConfig,
    SecurityConfig,
    UnicodeConfig,
    ValidationConfig,
    get_config,
    set_config_path,
)


# Test fixtures
@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_config_dict():
    """Sample configuration dictionary."""
    return {
        "environment": "testing",
        "database": {"type": "sqlite", "path": "./test.db"},
        "processing": {"batch_size": 500, "max_workers": 2},
        "unicode": {"handle_ligatures": False},
    }


# GMNAPConfig tests
class TestGMNAPConfig:
    """Test GMNAPConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GMNAPConfig()

        assert config.environment == Environment.DEVELOPMENT
        assert config.database.type == "duckdb"
        assert config.processing.batch_size == 1000
        assert config.unicode.handle_ligatures == True
        assert config.validation.strict_mode == False
        assert config.monitoring.log_level == "INFO"
        assert config.cache.cache_dir == "./cache"
        assert config.security.enable_input_validation == True
        assert config.api.timeout_seconds == 30

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = GMNAPConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["environment"] == Environment.DEVELOPMENT
        assert isinstance(config_dict["database"], dict)
        assert config_dict["database"]["type"] == "duckdb"

    def test_config_from_dict(self, sample_config_dict):
        """Test creating config from dictionary."""
        config = GMNAPConfig.from_dict(sample_config_dict)

        assert config.environment == Environment.TESTING
        assert config.database.type == "sqlite"
        assert config.database.path == "./test.db"
        assert config.processing.batch_size == 500
        assert config.processing.max_workers == 2
        assert config.unicode.handle_ligatures == False

    def test_nested_config_objects(self):
        """Test nested configuration objects."""
        db_config = DatabaseConfig(type="sqlite", path="/tmp/test.db")
        proc_config = ProcessingConfig(batch_size=100)

        config = GMNAPConfig(
            environment=Environment.TESTING, database=db_config, processing=proc_config
        )

        assert config.database.type == "sqlite"
        assert config.database.path == "/tmp/test.db"
        assert config.processing.batch_size == 100


# ConfigurationManager tests
class TestConfigurationManager:
    """Test ConfigurationManager class."""

    def test_manager_creation(self):
        """Test configuration manager creation."""
        manager = ConfigurationManager()
        assert manager.config_path == Path("./config/gmnap.yaml")
        assert manager._config is None
        assert manager._env_prefix == "GMNAP_"

    def test_custom_config_path(self, temp_config_dir):
        """Test manager with custom config path."""
        config_path = temp_config_dir / "custom.yaml"
        manager = ConfigurationManager(config_path)
        assert manager.config_path == config_path

    def test_load_yaml_config(self, temp_config_dir, sample_config_dict):
        """Test loading configuration from YAML file."""
        config_path = temp_config_dir / "test.yaml"

        with open(config_path, "w") as f:
            yaml.safe_dump(sample_config_dict, f)

        manager = ConfigurationManager(config_path)
        config = manager.load()

        assert config.environment == Environment.TESTING
        assert config.database.type == "sqlite"
        assert config.processing.batch_size == 500

    def test_load_json_config(self, temp_config_dir, sample_config_dict):
        """Test loading configuration from JSON file."""
        config_path = temp_config_dir / "test.json"

        with open(config_path, "w") as f:
            json.dump(sample_config_dict, f)

        manager = ConfigurationManager(config_path)
        config = manager.load()

        assert config.environment == Environment.TESTING
        assert config.database.type == "sqlite"

    def test_load_nonexistent_file(self):
        """Test loading with non-existent config file."""
        manager = ConfigurationManager(Path("/nonexistent/config.yaml"))
        config = manager.load()

        # Should return default config
        assert config.environment == Environment.DEVELOPMENT
        assert config.database.type == "duckdb"

    @patch.dict(
        os.environ,
        {
            "GMNAP_ENVIRONMENT": "production",
            "GMNAP_DATABASE_TYPE": "sqlite",
            "GMNAP_DATABASE_PATH": "/prod/db.sqlite",
            "GMNAP_PROCESSING_BATCH_SIZE": "2000",
            "GMNAP_PROCESSING_MAX_WORKERS": "8",
            "GMNAP_UNICODE_HANDLE_LIGATURES": "false",
            "GMNAP_VALIDATION_STRICT_MODE": "true",
            "GMNAP_CACHE_MAX_CACHE_SIZE_MB": "2048",
            "GMNAP_REGIONS_ENABLED": "north_america,europe,asia",
        },
    )
    def test_load_from_environment(self):
        """Test loading configuration from environment variables."""
        manager = ConfigurationManager(Path("/nonexistent/config.yaml"))
        config = manager.load()

        assert config.environment == Environment.PRODUCTION
        assert config.database.type == "sqlite"
        assert config.database.path == "/prod/db.sqlite"
        assert config.processing.batch_size == 2000
        assert config.processing.max_workers == 8
        assert config.unicode.handle_ligatures == False
        assert config.validation.strict_mode == True
        assert config.cache.max_cache_size_mb == 2048
        assert config.regions_enabled == ["north_america", "europe", "asia"]

    def test_parse_env_value(self):
        """Test environment value parsing."""
        manager = ConfigurationManager()

        # Boolean
        assert manager._parse_env_value("true") == True
        assert manager._parse_env_value("false") == False
        assert manager._parse_env_value("True") == True
        assert manager._parse_env_value("FALSE") == False

        # Integer
        assert manager._parse_env_value("123") == 123
        assert manager._parse_env_value("-456") == -456

        # Float
        assert manager._parse_env_value("3.14") == 3.14
        assert manager._parse_env_value("-2.5") == -2.5

        # List
        assert manager._parse_env_value("a,b,c") == ["a", "b", "c"]
        assert manager._parse_env_value("one, two, three") == ["one", "two", "three"]

        # String
        assert manager._parse_env_value("hello") == "hello"
        assert manager._parse_env_value("/path/to/file") == "/path/to/file"

    def test_config_validation(self):
        """Test configuration validation."""
        manager = ConfigurationManager()

        # Valid config
        valid_config = GMNAPConfig(
            processing=ProcessingConfig(batch_size=100, max_workers=4),
            validation=ValidationConfig(
                min_confidence_score=0.1, max_confidence_score=0.9
            ),
        )
        manager._validate_config(valid_config)  # Should not raise

        # Invalid batch size
        with pytest.raises(ValueError, match="Batch size must be positive"):
            invalid_config = GMNAPConfig(processing=ProcessingConfig(batch_size=0))
            manager._validate_config(invalid_config)

        # Invalid confidence scores
        with pytest.raises(
            ValueError, match="Min confidence score must be between 0 and 1"
        ):
            invalid_config = GMNAPConfig(
                validation=ValidationConfig(min_confidence_score=-0.1)
            )
            manager._validate_config(invalid_config)

        # Min > Max confidence
        with pytest.raises(
            ValueError, match="Min confidence score cannot be greater than max"
        ):
            invalid_config = GMNAPConfig(
                validation=ValidationConfig(
                    min_confidence_score=0.8, max_confidence_score=0.2
                )
            )
            manager._validate_config(invalid_config)

    def test_get_config(self):
        """Test getting configuration."""
        manager = ConfigurationManager()

        # First call loads config
        config1 = manager.get()
        assert config1 is not None
        assert manager._config is config1

        # Second call returns cached config
        config2 = manager.get()
        assert config2 is config1

    def test_reload_config(self, temp_config_dir):
        """Test reloading configuration."""
        config_path = temp_config_dir / "test.yaml"

        # Initial config
        initial_config = {"environment": "development"}
        with open(config_path, "w") as f:
            yaml.safe_dump(initial_config, f)

        manager = ConfigurationManager(config_path)
        config1 = manager.load()
        assert config1.environment == Environment.DEVELOPMENT

        # Update config file
        updated_config = {"environment": "production"}
        with open(config_path, "w") as f:
            yaml.safe_dump(updated_config, f)

        # Reload
        config2 = manager.reload()
        assert config2.environment == Environment.PRODUCTION
        assert config2 is not config1

    def test_save_config(self, temp_config_dir):
        """Test saving configuration."""
        config_path = temp_config_dir / "saved.yaml"
        manager = ConfigurationManager(config_path)

        # Load default config
        config = manager.load()
        config.environment = Environment.STAGING
        config.database.type = "sqlite"

        # Save
        manager.save()

        # Verify saved file
        assert config_path.exists()
        with open(config_path, "r") as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["environment"] == "staging"
        assert saved_data["database"]["type"] == "sqlite"

    def test_save_json_config(self, temp_config_dir):
        """Test saving configuration as JSON."""
        config_path = temp_config_dir / "saved.json"
        manager = ConfigurationManager(config_path)

        config = manager.load()
        config.processing.batch_size = 250

        manager.save()

        with open(config_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["processing"]["batch_size"] == 250


# Environment tests
class TestEnvironment:
    """Test Environment enum."""

    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"


# Global functions tests
class TestGlobalFunctions:
    """Test global configuration functions."""

    def test_get_config(self):
        """Test get_config function."""
        with patch("src.core.config._config_manager", None):
            config = get_config()
            assert isinstance(config, GMNAPConfig)

    def test_set_config_path(self, temp_config_dir):
        """Test set_config_path function."""
        config_path = temp_config_dir / "custom.yaml"

        with patch("src.core.config._config_manager", None):
            set_config_path(config_path)

            # Verify the path is used
            from src.core.config import _config_manager

            assert _config_manager is not None
            assert _config_manager.config_path == config_path
