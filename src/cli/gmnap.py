"""GMNAP V7 CLI - Global Mathematician-Name Authority Project."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

# Maximum input file size: 100 MB
_MAX_INPUT_SIZE = 100 * 1024 * 1024


@click.group()
@click.version_option(version="7.0.0", prog_name="gmnap")
def cli():
    """GMNAP V7 - Global Mathematician-Name Authority Project."""
    pass


@cli.command()
@click.argument("name")
@click.option(
    "--mode",
    default="quick",
    type=click.Choice(["quick", "full", "extreme"]),
)
@click.option("--json-output", "as_json", is_flag=True, help="Output raw JSON")
def query(name: str, mode: str, as_json: bool):
    """Query a mathematician name for region detection and processing."""
    if not name or not name.strip():
        click.echo("Error: name must not be empty", err=True)
        sys.exit(1)
    sys.path.insert(0, ".")
    from src.regions.manager_optimized import RegionManager

    mgr = RegionManager()
    entry = {"CanonicalLatin": name, "OriginalScript": name}
    detection = mgr.detect_region(entry)
    region_code = detection.region_code
    confidence = detection.confidence
    processor = mgr.get_region(region_code)

    result = {
        "input": name,
        "region": region_code,
        "confidence": round(confidence, 4),
    }

    if processor:
        import copy

        work = copy.deepcopy(entry)
        work["RegionCode"] = region_code
        if hasattr(processor, "clean"):
            processor.clean(work)
        if hasattr(processor, "augment"):
            processor.augment(work)
        if hasattr(processor, "order_key"):
            ok = processor.order_key(work)
            if ok:
                work["OrderKey"] = ok

        # Parse family/given while preserving the original input case
        # (processor.clean() lowercases work["CanonicalLatin"])
        family = work.get("FamilyName", "")
        given = work.get("GivenName", "")
        if not family and "," in name:
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
        elif not family:
            parts = name.strip().split()
            if len(parts) >= 2:
                family = parts[-1]
                given = " ".join(parts[:-1])

        result["processed"] = {
            "CanonicalLatin": name,
            "FamilyName": family,
            "GivenName": given,
            "OrderKey": work.get("OrderKey", ""),
            "FamilyNameType": work.get("FamilyNameType", "surname"),
        }

    # Curated genealogy enrichment (Advisors/Institution/BirthYear/...)
    try:
        from src.core.genealogy_lookup import GenealogyLookup

        enrichable = {"CanonicalLatin": name}
        GenealogyLookup().enrich(enrichable)
        for field in (
            "BirthYear",
            "DeathYear",
            "Institution",
            "Country",
            "Thesis",
            "ThesisYear",
            "Advisors",
        ):
            if field in enrichable:
                result[field] = enrichable[field]
    except Exception:
        pass

    if as_json:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Name:       {result['input']}")
        click.echo(f"Region:     {result['region']}")
        click.echo(f"Confidence: {result['confidence']}")
        if "processed" in result:
            p = result["processed"]
            click.echo(f"Family:     {p['FamilyName']}")
            click.echo(f"Given:      {p['GivenName']}")
            click.echo(f"OrderKey:   {p['OrderKey']}")
            click.echo(f"Type:       {p['FamilyNameType']}")
        if result.get("BirthYear"):
            click.echo(f"Born:       {result['BirthYear']}")
        if result.get("Institution"):
            click.echo(f"Institution: {result['Institution']}")
        if result.get("Advisors"):
            advisors = result["Advisors"]
            names = [a.get("name", str(a)) for a in advisors]
            click.echo(f"Advisors:   {', '.join(names)}")


@cli.command()
@click.option("--id", "gid", required=True, help="GlobalID of the mathematician")
@click.option("--depth", default=3, type=int, help="Traversal depth")
@click.option(
    "--format",
    "fmt",
    default="json",
    type=click.Choice(["json", "dot", "svg"]),
)
def lineage(gid: str, depth: int, fmt: str):
    """Query academic genealogy lineage for a mathematician."""
    sys.path.insert(0, ".")
    edges = _query_lineage_graph(gid, depth)

    if not edges:
        click.echo(f"No lineage data found for {gid}", err=True)
        sys.exit(1)

    if fmt == "json":
        click.echo(json.dumps({"root": gid, "depth": depth, "edges": edges}, indent=2))
    elif fmt == "dot":
        click.echo(_edges_to_dot(gid, edges))
    elif fmt == "svg":
        dot = _edges_to_dot(gid, edges)
        try:
            import subprocess

            proc = subprocess.run(
                ["dot", "-Tsvg"],
                input=dot,
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                click.echo(proc.stdout)
            else:
                click.echo(
                    "Error: graphviz 'dot' failed. "
                    "Install graphviz or use --format dot",
                    err=True,
                )
                click.echo(dot)
        except FileNotFoundError:
            click.echo(
                "Error: graphviz not installed. "
                "Use --format dot for raw DOT output.",
                err=True,
            )
            click.echo(dot)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--mode",
    default="quick",
    type=click.Choice(["quick", "full", "extreme"]),
)
@click.option("--output", "-o", default="out/", help="Output directory")
@click.option(
    "--drop-personal",
    is_flag=True,
    help="GDPR: replace personal data with ShadowNodes",
)
@click.option(
    "--force-extreme",
    is_flag=True,
    help="Enable tier-3 sources (GoogleScholar). " "Requires YES_I_ACCEPT_GS_TOS=yes",
)
def process(
    input_file: str,
    mode: str,
    output: str,
    drop_personal: bool,
    force_extreme: bool,
):
    """Run V7 pipeline on an input file (JSON or YAML)."""
    import os

    sys.path.insert(0, ".")
    os.environ["PIPELINE_MODE"] = mode
    os.environ["PYTHONPATH"] = "."

    if drop_personal:
        os.environ["GMNAP_DROP_PERSONAL"] = "1"

    if force_extreme:
        if os.environ.get("YES_I_ACCEPT_GS_TOS", "").lower() != "yes":
            click.echo(
                "ERROR: --force-extreme requires YES_I_ACCEPT_GS_TOS=yes\n"
                "Google Scholar scraping may violate their Terms of Service.\n"
                "Set the env var to acknowledge this risk.",
                err=True,
            )
            sys.exit(1)
        os.environ["GMNAP_FORCE_EXTREME"] = "1"

    # Validate output path: must be relative, no traversal
    out_path = Path(output)
    if out_path.is_absolute():
        click.echo("Error: output path must be relative, not absolute", err=True)
        sys.exit(1)
    try:
        resolved = (Path.cwd() / out_path).resolve()
        if not str(resolved).startswith(str(Path.cwd().resolve())):
            click.echo(
                "Error: output path traversal escapes working directory",
                err=True,
            )
            sys.exit(1)
    except Exception:
        click.echo("Error: invalid output path", err=True)
        sys.exit(1)

    data = _load_input(input_file)
    if not data:
        click.echo(f"No entries found in {input_file}", err=True)
        sys.exit(1)

    click.echo(f"Processing {len(data)} entries in {mode} mode...")
    asyncio.run(_run_pipeline(data, mode, output))


@cli.command()
def sources():
    """List configured authority sources by tier."""
    tiers = {
        0: [
            ("OpenAlex", "CC0"),
            ("Crossref", "CC0"),
            ("ORCID", "CC0"),
            ("Crossref_Thesis", "CC0"),
        ],
        1: [
            ("Wikidata_P184", "CC0"),
            ("OAI_University", "CC-BY"),
            ("HAL", "CC-BY"),
            ("GND", "CC0"),
            ("zbMATH_Open", "CC-BY"),
        ],
        2: [
            ("MathSciNet", "Subscription"),
            ("Scopus", "Elsevier"),
            ("Dimensions", "DigitalScience"),
        ],
        3: [("ProQuest", "Commercial"), ("GoogleScholar", "ToS")],
    }
    for tier, srcs in tiers.items():
        click.echo(f"\nTier {tier}:")
        for name, lic in srcs:
            click.echo(f"  {name:20s} [{lic}]")


_REGION_NAMES = {
    "A1": "Anglo-Sphere",
    "A2": "Western Europe",
    "A3": "Nordic-Baltic",
    "A4": "Oceania Pacific",
    "A5": "Caribbean & French Overseas",
    "B1": "Slavic East (Russian)",
    "B2": "Slavic Central (Polish/Czech)",
    "B3": "Hellenic (Greek)",
    "C1": "Turkic",
    "C2": "Persian",
    "C3": "Arabic Levant & Nile",
    "C4": "Arabic Gulf",
    "C5": "Arabic Maghreb",
    "C6": "Hebrew & Diaspora",
    "C7": "Armenian",
    "C8": "Georgian",
    "C9": "Baltic (Lithuanian/Latvian)",
    "D1": "South Asian Hindi Belt",
    "D2": "South Asian Dravidian",
    "D3": "Bengali",
    "D4": "Pakistani",
    "D5": "Sri Lankan",
    "E1": "Chinese (Simplified)",
    "E2": "Chinese (Traditional)",
    "E3": "Japanese",
    "E4": "Korean",
    "E5": "Vietnamese",
    "E6": "Thai & Mainland SEA",
    "E7": "Maritime SEA",
    "F1": "SSA Francophone & Maghreb",
    "F2": "SSA Anglophone",
    "F3": "Horn of Africa",
    "F4": "Southern & Lusophone Africa",
    "G1": "Latin American",
    "H1": "Historical",
    "R0": "Residual / Unknown",
    "Z0": "Quarantine",
}


@cli.command()
def regions():
    """List all supported region codes."""
    sys.path.insert(0, ".")
    from src.regions.manager_optimized import RegionManager

    mgr = RegionManager()
    codes = sorted(mgr.IMPLEMENTED_REGIONS)
    click.echo(f"Supported regions ({len(codes)}):")
    for code in codes:
        name = _REGION_NAMES.get(code, code)
        click.echo(f"  {code}: {name}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--schema-strict",
    default=0,
    type=click.IntRange(0, 2),
    help="Schema strict mode: 0=advisory, 1=quarantine, 2=reject",
)
@click.option("--json-output", "as_json", is_flag=True, help="Output raw JSON")
def validate(input_file: str, schema_strict: int, as_json: bool):
    """Validate an input file against the GMNAP v2.0 schema."""
    import os

    sys.path.insert(0, ".")
    os.environ["GMNAP_SCHEMA_STRICT"] = str(schema_strict)

    data = _load_input(input_file)
    if not data:
        click.echo(f"No entries found in {input_file}", err=True)
        sys.exit(1)

    from src.validation.schema import SchemaValidator

    validator = SchemaValidator()
    total = 0
    errors_found = 0
    all_errors = []

    for i, entry in enumerate(data if isinstance(data, list) else [data]):
        total += 1
        is_valid, errors = validator.validate_entry(entry)
        if not is_valid:
            errors_found += 1
            name = entry.get("CanonicalLatin", f"entry_{i}")
            all_errors.append({"entry": name, "errors": errors})

    if as_json:
        click.echo(
            json.dumps(
                {
                    "total": total,
                    "valid": total - errors_found,
                    "invalid": errors_found,
                    "schema_strict": schema_strict,
                    "errors": all_errors,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        click.echo(f"Validated {total} entries against schema v2.0")
        click.echo(f"  Valid:   {total - errors_found}")
        click.echo(f"  Invalid: {errors_found}")
        if all_errors:
            click.echo(f"\nErrors (schema_strict={schema_strict}):")
            for err in all_errors[:20]:
                click.echo(f"  {err['entry']}:")
                for e in err["errors"][:3]:
                    click.echo(f"    - {e}")
            if len(all_errors) > 20:
                click.echo(f"  ... and {len(all_errors) - 20} more")

    sys.exit(1 if errors_found > 0 and schema_strict >= 1 else 0)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Bind address")
@click.option("--port", default=8080, type=int, help="Port number")
@click.option("--workers", default=1, type=int, help="Number of workers")
def serve(host: str, port: int, workers: int):
    """Start the GMNAP V7 API server."""
    try:
        import uvicorn
    except ImportError:
        click.echo("uvicorn required. Install with: pip install uvicorn", err=True)
        sys.exit(1)

    click.echo(f"Starting GMNAP V7 API on {host}:{port}...")
    uvicorn.run(
        "src.api.server:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
    )


# ── Helpers ──────────────────────────────────────────────────────────


def _load_input(path: str) -> list:
    """Load entries from JSON or YAML file with validation."""
    p = Path(path)

    # File size check
    try:
        size = p.stat().st_size
    except OSError as e:
        click.echo(f"Error: cannot read {path}: {e}", err=True)
        return []
    if size > _MAX_INPUT_SIZE:
        click.echo(
            f"Error: file too large "
            f"({size // (1024 * 1024)}MB, "
            f"max {_MAX_INPUT_SIZE // (1024 * 1024)}MB)",
            err=True,
        )
        return []

    # Binary file detection (check first 8KB for null bytes)
    try:
        with open(p, "rb") as fh:
            chunk = fh.read(8192)
            if b"\x00" in chunk:
                click.echo(
                    "Error: binary file detected, " "expected JSON or YAML text",
                    err=True,
                )
                return []
    except OSError:
        pass

    # Read text
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        click.echo("Error: file is not valid UTF-8 text", err=True)
        return []

    if not text.strip():
        return []

    # Parse
    if p.suffix in (".yaml", ".yml"):
        try:
            import yaml

            return yaml.safe_load(text) or []
        except ImportError:
            click.echo(
                "PyYAML required for YAML input. pip install pyyaml",
                err=True,
            )
            return []
        except Exception as e:
            click.echo(f"Error: invalid YAML: {e}", err=True)
            return []
    else:
        try:
            return json.loads(text) if text.strip() else []
        except json.JSONDecodeError as e:
            click.echo(f"Error: invalid JSON: {e}", err=True)
            return []


async def _run_pipeline(entries: list, mode: str, output_dir: str):
    """Run V7 pipeline."""
    from src.core.pipeline_v7 import PipelineMode, V7Pipeline

    mode_map = {
        "quick": PipelineMode.QUICK,
        "full": PipelineMode.FULL,
        "extreme": PipelineMode.EXTREME,
    }
    pipeline = V7Pipeline(mode=mode_map[mode])
    result = await pipeline.process_batch(entries)
    entry_count = (
        len(result.get("entries", [])) if isinstance(result, dict) else len(result)
    )
    passed = (
        result.get("quality_gates", {}).get("passed", "N/A")
        if isinstance(result, dict)
        else "N/A"
    )
    click.echo(
        f"Processed {entry_count} entries. "
        f"Quality gates: {passed}. Output in {output_dir}/"
    )


def _query_lineage_graph(gid: str, depth: int) -> list:
    """Query lineage from graph DB or local YAML files."""
    out = Path("out/yaml")
    if out.exists():
        edges: list = []
        visited: set = set()
        _traverse_local(gid, depth, out, edges, visited)
        return edges
    return []


def _traverse_local(
    gid: str,
    depth: int,
    out_dir: Path,
    edges: list,
    visited: set,
):
    """Walk advisor edges from local YAML output."""
    if depth <= 0 or gid in visited:
        return
    visited.add(gid)

    for f in out_dir.glob("*.yaml"):
        try:
            import yaml

            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            if data.get("GlobalID") == gid:
                for adv in data.get("Advisors") or []:
                    edge = {
                        "from": gid,
                        "to": adv,
                        "relation": "doctoralAdvisor",
                    }
                    edges.append(edge)
                    _traverse_local(adv, depth - 1, out_dir, edges, visited)
        except Exception:
            continue


def _edges_to_dot(root: str, edges: list) -> str:
    """Convert edge list to Graphviz DOT format."""
    lines = [
        "digraph lineage {",
        "  rankdir=BT;",
        f'  "{root}" [style=filled, fillcolor=lightblue];',
    ]
    for e in edges:
        lines.append(
            f'  "{e["from"]}" -> "{e["to"]}" ' f'[label="{e.get("relation", "")}"];'
        )
    lines.append("}")
    return "\n".join(lines)


if __name__ == "__main__":
    cli()
