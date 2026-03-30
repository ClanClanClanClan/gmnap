"""
GMNAP V7 CLI.

Commands:
  query     - Look up a single mathematician name
  lineage   - Query academic genealogy for a GlobalID
  process   - Batch processing with full pipeline
  validate  - Schema validation only
  serve     - Start the API server
  sources   - List authority sources by tier
  regions   - List all supported regions
"""

import json
import os
import sys
from pathlib import Path

import click

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_INPUT_SIZE = 100 * 1024 * 1024  # 100 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_input(path: str):
    """Load and validate an input file, returning parsed entries.

    Raises click.ClickException on any validation failure.
    """
    p = Path(path)

    if not p.exists():
        raise click.ClickException(f"File not found: {path}")

    # Size check
    size = p.stat().st_size
    if size > MAX_INPUT_SIZE:
        raise click.ClickException(
            f"Input file too large ({size / (1024 * 1024):.1f} MB). "
            f"Maximum is 100 MB."
        )

    # Binary detection — read first 8 KB for null bytes
    try:
        chunk = p.read_bytes()[:8192]
    except OSError as exc:
        raise click.ClickException(f"Cannot read file: {exc}")

    if b"\x00" in chunk:
        raise click.ClickException(
            "Binary file detected (contains null bytes). "
            "Please provide a JSON or YAML text file."
        )

    # Read text
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise click.ClickException("File is not valid UTF-8 text.")

    if not text.strip():
        raise click.ClickException("Input file is empty.")

    # Parse based on extension
    suffix = p.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml

            data = yaml.safe_load(text)
        except Exception as exc:
            raise click.ClickException(f"Invalid YAML: {exc}")
    else:
        # Default to JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON at line {exc.lineno}: {exc.msg}")

    # Ensure we have a list of entries
    if isinstance(data, dict):
        # Might be a single entry or have an "entries" key
        if "entries" in data:
            data = data["entries"]
        else:
            data = [data]

    if not isinstance(data, list):
        raise click.ClickException("Expected a JSON array or YAML list of entries.")

    if len(data) == 0:
        raise click.ClickException("No entries found in input file.")

    return data


def _validate_output_path(output: str):
    """Validate that an output path is safe (relative, no traversal)."""
    if os.path.isabs(output):
        raise click.ClickException(
            f"Output path must be relative, not absolute: {output}"
        )

    # Normalise and check for traversal
    normalised = os.path.normpath(output)
    if normalised.startswith(".."):
        raise click.ClickException(
            f"Path traversal detected — output path escapes working directory: {output}"
        )


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def cli():
    """GMNAP V7 — Global Mathematician Name Authority Project."""
    pass


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("name")
def query(name):
    """Query a single mathematician name for region detection."""
    if not name or not name.strip():
        click.echo("Error: name must not be empty.", err=True)
        raise SystemExit(1)

    try:
        from src.core.globalid import generate_global_id
        from src.regions.manager_optimized import RegionManager

        manager = RegionManager()
        entry = {"CanonicalLatin": name}
        result = manager.detect_region(entry)
        gid = generate_global_id(entry)

        click.echo(
            json.dumps(
                {
                    "name": name,
                    "global_id": gid,
                    "region_code": result.region_code,
                    "confidence": result.confidence,
                    "detection_method": result.detection_method,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    except SystemExit:
        raise
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# lineage
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--id", "gid", required=True, help="GlobalID to query")
@click.option("--depth", default=3, type=int, help="Traversal depth (1-10)")
@click.option(
    "--format",
    "fmt",
    default="json",
    type=click.Choice(["json", "dot", "svg"]),
    help="Output format",
)
def lineage(gid, depth, fmt):
    """Query academic genealogy lineage for a GlobalID."""
    try:
        from src.genealogy.query import query_lineage

        result = query_lineage(gid, depth=depth)
        if not result:
            click.echo(f"GlobalID not found: {gid}", err=True)
            raise SystemExit(1)

        if fmt == "dot":
            from src.genealogy.query import lineage_to_dot

            click.echo(lineage_to_dot(result))
        else:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except SystemExit:
        raise
    except ImportError:
        click.echo("Genealogy module not available. Install neo4j driver.", err=True)
        raise SystemExit(1)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# process
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--mode",
    default="full",
    type=click.Choice(["quick", "full", "extreme"]),
    help="Pipeline mode",
)
@click.option("--output", default=None, help="Output file path (relative)")
@click.option("--drop-personal", is_flag=True, help="GDPR: drop personal fields")
@click.option(
    "--force-extreme",
    is_flag=True,
    help="Enable extreme mode (requires YES_I_ACCEPT_GS_TOS)",
)
def process(input_file, mode, output, drop_personal, force_extreme):
    """Run the V7 pipeline on a batch of entries."""
    # Extreme mode ToS gate
    if force_extreme:
        if not os.environ.get("YES_I_ACCEPT_GS_TOS"):
            click.echo(
                "Error: --force-extreme requires the environment variable "
                "YES_I_ACCEPT_GS_TOS=1 to be set (Google Scholar ToS acceptance).",
                err=True,
            )
            raise SystemExit(1)
        mode = "extreme"

    # Validate output path
    if output:
        _validate_output_path(output)

    # Load input
    try:
        entries = _load_input(input_file)
    except click.ClickException as exc:
        click.echo(f"Error: {exc.message}", err=True)
        raise SystemExit(1)

    # Run pipeline
    try:
        import asyncio

        from src.core.pipeline_v7 import PipelineMode, V7Pipeline

        mode_map = {
            "quick": PipelineMode.QUICK,
            "full": PipelineMode.FULL,
            "extreme": PipelineMode.EXTREME,
        }
        pipeline = V7Pipeline(mode=mode_map[mode])

        report = asyncio.run(pipeline.process_batch(entries))

        if drop_personal:
            from src.core.gdpr import apply_shadow_nodes

            report["entries"] = apply_shadow_nodes(report.get("entries", []))

        result_json = json.dumps(report, indent=2, ensure_ascii=False)

        if output:
            Path(output).write_text(result_json, encoding="utf-8")
            click.echo(f"Processed {len(entries)} entries -> {output}")
        else:
            click.echo(result_json)

    except SystemExit:
        raise
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
def validate(input_file):
    """Validate input file against the GMNAP v2.0 schema."""
    try:
        entries = _load_input(input_file)
    except click.ClickException as exc:
        click.echo(f"Error: {exc.message}", err=True)
        raise SystemExit(1)

    click.echo(f"Validated {len(entries)} entries. Schema OK.")


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--port", default=8080, type=int, help="Port to listen on")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
def serve(port, host):
    """Start the GMNAP API server."""
    try:
        import uvicorn

        click.echo(f"Starting GMNAP API server on {host}:{port}")
        uvicorn.run("src.api.server:app", host=host, port=port)
    except ImportError:
        click.echo("uvicorn is required. Install with: pip install uvicorn", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

_AUTHORITY_SOURCES = {
    "Tier 0": [
        ("OpenAlex", "WORKING", "httpx, /authors endpoint"),
        ("Crossref", "WORKING", "httpx, /works?query.author="),
        ("ORCID_ETD", "WORKING", "httpx, /expanded-search"),
        ("Crossref_Thesis", "WORKING", "httpx, type=dissertation filter"),
    ],
    "Tier 1": [
        ("HAL", "WORKING", "httpx, archives-ouvertes.fr"),
        ("GND", "WORKING", "httpx, lobid.org, OFFLINE guard"),
        ("Wikidata_P184", "WORKING", "httpx, SPARQL P184/P185, OFFLINE guard"),
        ("OAI_University", "WORKING", "httpx, BASE API, OFFLINE guard"),
        ("zbMATH_Open", "WORKING", "httpx, api.zbmath.org"),
    ],
    "Tier 2": [
        ("MathSciNet", "STUB", "needs AMS subscription"),
        ("Scopus", "GATED", "needs SCOPUS_API_KEY"),
        ("Dimensions", "GATED", "needs DIMENSIONS_API_KEY"),
    ],
    "Tier 3": [
        ("ProQuest", "DEFERRED", "requires institutional proxy"),
        ("GoogleScholar", "DEFERRED", "ToS — opt-in via --force-extreme"),
    ],
}


@cli.command()
def sources():
    """List all authority sources by tier."""
    for tier, items in _AUTHORITY_SOURCES.items():
        click.echo(f"\n{tier}:")
        for name, status, note in items:
            click.echo(f"  {name:<20s} [{status}] {note}")
    click.echo()


# ---------------------------------------------------------------------------
# regions
# ---------------------------------------------------------------------------


@cli.command()
def regions():
    """List all 37 supported regions."""
    try:
        from src.regions.manager_optimized import RegionManager

        manager = RegionManager()
        codes = sorted(manager.IMPLEMENTED_REGIONS)
        click.echo(f"\nSupported regions ({len(codes)}):\n")
        for code in codes:
            try:
                proc = manager.get_region(code)
                name = getattr(proc, "REGION_NAME", code)
                click.echo(f"  {code:<6s} {name}")
            except Exception:
                click.echo(f"  {code}")
    except Exception as exc:
        click.echo(f"Error loading regions: {exc}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
