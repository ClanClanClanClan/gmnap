"""
GMNAP v7.0 Pipeline Stage 1: Data Ingestion
Handles data ingestion from various sources and formats.
"""

from typing import Dict, Any, List, Union, Iterator
import json
import logging

logger = logging.getLogger(__name__)

import csv
from pathlib import Path
from ..core.errors import IngestionError
from ..core.security_validator import SecurityValidator
from ..validation.schema import SchemaValidator


class IngestStage:
    """Stage 1: Data ingestion and initial processing"""

    def __init__(self):
        """Initialize ingestion stage"""
        self.security_validator = SecurityValidator()
        self.schema_validator = SchemaValidator()
        self.supported_formats = ["json", "jsonl", "csv", "yaml"]

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest data from specified sources

        Args:
            context: Pipeline execution context with configuration

        Returns:
            Updated context with ingested data
        """
        try:
            config = context.get("config", {})
            pipeline_config = config.get("pipeline", {})

            # Get data sources from configuration
            data_sources = pipeline_config.get("data_sources", [])

            if not data_sources:
                raise IngestionError("No data sources specified in configuration")

            # Ingest data from all sources
            ingested_data = []
            for source in data_sources:
                data = self._ingest_from_source(source)
                ingested_data.extend(data)

            # Validate ingested data
            validated_data = self._validate_ingested_data(ingested_data)

            # Add to context
            context["raw_data"] = validated_data
            context["stage_1_completed"] = True
            context["records_ingested"] = len(validated_data)

            return context

        except Exception as e:
            raise IngestionError(f"Stage 1 data ingestion failed: {str(e)}")

    def _ingest_from_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ingest data from a single source"""
        source_type = source.get("type")
        source_path = source.get("path")

        if not source_type or not source_path:
            raise IngestionError(f"Invalid source configuration: {source}")

        path = Path(source_path)
        if not path.exists():
            raise IngestionError(f"Source file not found: {source_path}")

        # Determine format from file extension or explicit type
        file_format = source.get("format", path.suffix.lower().lstrip("."))

        if file_format not in self.supported_formats:
            raise IngestionError(f"Unsupported file format: {file_format}")

        # Ingest based on format
        if file_format == "json":
            return self._ingest_json(path)
        elif file_format == "jsonl":
            return self._ingest_jsonl(path)
        elif file_format == "csv":
            return self._ingest_csv(path)
        elif file_format == "yaml":
            return self._ingest_yaml(path)
        else:
            raise IngestionError(f"Format {file_format} not implemented")

    def _ingest_json(self, path: Path) -> List[Dict[str, Any]]:
        """Ingest JSON data"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                raise IngestionError(f"Invalid JSON structure in {path}")

        except json.JSONDecodeError as e:
            raise IngestionError(f"Invalid JSON in {path}: {str(e)}")

    def _ingest_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        """Ingest JSONL (JSON Lines) data"""
        data = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            data.append(record)
                        except json.JSONDecodeError as e:
                            raise IngestionError(
                                f"Invalid JSON on line {line_num} in {path}: {str(e)}"
                            )
            return data
        except Exception as e:
            raise IngestionError(f"Error reading JSONL file {path}: {str(e)}")

    def _ingest_csv(self, path: Path) -> List[Dict[str, Any]]:
        """Ingest CSV data"""
        data = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(dict(row))
            return data
        except Exception as e:
            raise IngestionError(f"Error reading CSV file {path}: {str(e)}")

    def _ingest_yaml(self, path: Path) -> List[Dict[str, Any]]:
        """Ingest YAML data"""
        try:
            import yaml

            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                raise IngestionError(f"Invalid YAML structure in {path}")

        except Exception as e:
            raise IngestionError(f"Error reading YAML file {path}: {str(e)}")

    def _validate_ingested_data(
        self, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate ingested data for security and schema compliance"""
        validated_data = []

        for i, record in enumerate(data):
            try:
                # Security validation
                self._validate_record_security(record)

                # Schema validation
                self.schema_validator.validate_record(record)

                validated_data.append(record)

            except Exception as e:
                # Log validation error but continue processing
                logger.warning(f"Skipping record {i} due to validation error: {str(e)}")
                continue

        return validated_data

    def _validate_record_security(self, record: Dict[str, Any]) -> None:
        """Validate a single record for security issues"""
        for key, value in record.items():
            if isinstance(value, str):
                self.security_validator.validate_string(value, context=f"record.{key}")
