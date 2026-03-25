"""Tests for stage 10 report generation — DOI draft, attribution, markdown report."""

from __future__ import annotations

import json
import os

import pytest


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")


def _sample_batch():
    return [
        {
            "CanonicalLatin": "Euler, Leonhard",
            "DetectedRegion": "A2",
            "_sources": ["OpenAlex", "Crossref"],
            "GlobalID": "EULER_TEST",
        },
        {
            "CanonicalLatin": "Gauss, Carl",
            "DetectedRegion": "A2",
            "_sources": ["Crossref"],
            "GlobalID": "GAUSS_TEST",
        },
    ]


class TestReportGeneration:
    def test_generate_report_creates_files(self, tmp_path):
        from src.pipeline.stage10_report import generate_report

        snap_dir = str(tmp_path / "snapshots" / "run-abc123")
        report_dir, payload = generate_report(
            batch=_sample_batch(),
            metrics={"total_entries": 2, "duration_seconds": 0.5},
            snapshot_dir=snap_dir,
            mode="Quick",
        )

        assert os.path.isdir(report_dir)
        assert os.path.isfile(os.path.join(report_dir, "report.md"))
        assert os.path.isfile(os.path.join(report_dir, "report.json"))

    def test_doi_draft_has_datacite_fields(self, tmp_path):
        from src.pipeline.stage10_report import generate_report

        snap_dir = str(tmp_path / "snapshots" / "run-doi")
        _, payload = generate_report(batch=_sample_batch(), snapshot_dir=snap_dir)

        doi_path = payload.get("doi_draft")
        assert doi_path and os.path.isfile(doi_path)

        with open(doi_path) as f:
            doi = json.load(f)
        assert "doi" in doi
        assert "creators" in doi
        assert "schemaVersion" in doi

    def test_attribution_file_created(self, tmp_path):
        from src.pipeline.stage10_report import generate_report

        snap_dir = str(tmp_path / "snapshots" / "run-attr")
        generate_report(batch=_sample_batch(), snapshot_dir=snap_dir)

        attr_path = os.path.join(snap_dir, "ATTRIBUTION.txt")
        assert os.path.isfile(attr_path)
        text = open(attr_path).read()
        assert "ATTRIBUTION" in text  # Header always present

    def test_markdown_report_contains_regions(self, tmp_path):
        from src.pipeline.stage10_report import generate_report

        snap_dir = str(tmp_path / "snapshots" / "run-md")
        generate_report(batch=_sample_batch(), snapshot_dir=snap_dir)

        md_path = os.path.join(snap_dir, "report.md")
        text = open(md_path).read()
        assert "A2" in text
        assert "Region Distribution" in text

    def test_empty_batch_does_not_crash(self, tmp_path):
        from src.pipeline.stage10_report import generate_report

        snap_dir = str(tmp_path / "snapshots" / "run-empty")
        report_dir, payload = generate_report(batch=[], snapshot_dir=snap_dir)
        assert os.path.isdir(report_dir)
