"""GMNAP V7 CLI - Global Mathematician-Name Authority Project."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click


@click.group()
@click.version_option(version="7.0.0", prog_name="gmnap")
def cli():
    """GMNAP V7 - Global Mathematician-Name Authority Project."""
    pass


@cli.command()
@click.argument("name")
@click.option("--mode", default="quick", type=click.Choice(["quick", "full", "extreme"]))
@click.option("--json-output", "as_json", is_flag=True, help="Output raw JSON")
def query(name: str, mode: str, as_json: bool):
    """Query a mathematician name for region detection and processing."""
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

        result["processed"] = {
            "CanonicalLatin": work.get("CanonicalLatin", name),
            "FamilyName": work.get("FamilyName", ""),
            "GivenName": work.get("GivenName", ""),
            "OrderKey": work.get("OrderKey", ""),
            "FamilyNameType": work.get("FamilyNameType", "surname"),
        }

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


@cli.command()
@click.option("--id", "gid", required=True, help="GlobalID of the mathematician")
@click.option("--depth", default=3, type=int, help="Traversal depth")
@click.option("--format", "fmt", default="json", type=click.Choice(["json", "dot", "svg"]))
def lineage(gid: str, depth: int, fmt: str):
    """Query academic genealogy lineage for a mathematician."""
    sys.path.insert(0, ".")

    # Try Memgraph/Neo4j first, fall back to local data
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
                ["dot", "-Tsvg"], input=dot, capture_output=True, text=True
            )
            if proc.returncode == 0:
                click.echo(proc.stdout)
            else:
                click.echo("Error: graphviz 'dot' failed. Install graphviz or use --format dot", err=True)
                click.echo(dot)
        except FileNotFoundError:
            click.echo("Error: graphviz not installed. Use --format dot for raw DOT output.", err=True)
            click.echo(dot)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--mode", default="quick", type=click.Choice(["quick", "full", "extreme"]))
@click.option("--output", "-o", default="out/", help="Output directory")
@click.option("--drop-personal", is_flag=True, help="GDPR: replace personal data with ShadowNodes")
def process(input_file: str, mode: str, output: str, drop_personal: bool):
    """Run V7 pipeline on an input file (JSON or YAML)."""
    import os

    sys.path.insert(0, ".")
    os.environ["PIPELINE_MODE"] = mode
    os.environ["PYTHONPATH"] = "."

    if drop_personal:
        os.environ["GMNAP_DROP_PERSONAL"] = "1"

    data = _load_input(input_file)
    if not data:
        click.echo(f"No entries found in {input_file}", err=True)
        sys.exit(1)

    click.echo(f"Processing {len(data)} entries in {mode} mode...")
    asyncio.run(_run_pipeline(data, mode, output))


@cli.command()
def sources():
    """List configured authority sources by tier."""
    sys.path.insert(0, ".")

    tiers = {
        0: [("OpenAlex", "CC0"), ("Crossref", "CC0"), ("ORCID", "CC0"), ("Crossref_Thesis", "CC0")],
        1: [("Wikidata_P184", "CC0"), ("OAI_University", "CC-BY"), ("HAL", "CC-BY"), ("GND", "CC0"), ("zbMATH_Open", "CC-BY")],
        2: [("MathSciNet", "Subscription"), ("Scopus", "Elsevier"), ("Dimensions", "DigitalScience")],
        3: [("ProQuest", "Commercial"), ("GoogleScholar", "ToS")],
    }
    for tier, srcs in tiers.items():
        click.echo(f"\nTier {tier}:")
        for name, lic in srcs:
            click.echo(f"  {name:20s} [{lic}]")


@cli.command()
def regions():
    """List all supported region codes."""
    sys.path.insert(0, ".")
    from src.regions.manager_optimized import RegionManager

    mgr = RegionManager()
    codes = sorted(mgr.IMPLEMENTED_REGIONS)
    click.echo(f"Supported regions ({len(codes)}):")
    for code in codes:
        p = mgr.get_region(code)
        name = getattr(p, "REGION_NAME", code) if p else code
        click.echo(f"  {code}: {name}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--schema-strict", default=0, type=click.IntRange(0, 2),
              help="Schema strict mode: 0=advisory, 1=quarantine, 2=reject")
@click.option("--json-output", "as_json", is_flag=True, help="Output raw JSON")
def validate(input_file: str, schema_strict: int, as_json: bool):
    """Validate an input file against the GMNAP v2.0 schema (no pipeline run)."""
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
        click.echo(json.dumps({
            "total": total,
            "valid": total - errors_found,
            "invalid": errors_found,
            "schema_strict": schema_strict,
            "errors": all_errors,
        }, indent=2, ensure_ascii=False))
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


# ── Helpers ────────────────────────────────────────────────────────────────


def _load_input(path: str) -> list:
    """Load entries from JSON or YAML file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix in (".yaml", ".yml"):
        try:
            import yaml

            return yaml.safe_load(text) or []
        except ImportError:
            click.echo("PyYAML required for YAML input. pip install pyyaml", err=True)
            return []
    else:
        return json.loads(text) if text.strip() else []


async def _run_pipeline(entries: list, mode: str, output_dir: str):
    """Run V7 pipeline."""
    from src.core.pipeline_v7 import V7Pipeline, PipelineMode

    mode_map = {"quick": PipelineMode.QUICK, "full": PipelineMode.FULL, "extreme": PipelineMode.EXTREME}
    pipeline = V7Pipeline(mode=mode_map[mode])
    result = await pipeline.process_batch(entries)
    click.echo(f"Processed {len(result)} entries. Output in {output_dir}/")


def _query_lineage_graph(gid: str, depth: int) -> list:
    """Query lineage from graph DB or local YAML files."""
    # Try local output files
    out = Path("out/yaml")
    if out.exists():
        edges = []
        visited = set()
        _traverse_local(gid, depth, out, edges, visited)
        return edges

    return []


def _traverse_local(gid: str, depth: int, out_dir: Path, edges: list, visited: set):
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
                    edge = {"from": gid, "to": adv, "relation": "doctoralAdvisor"}
                    edges.append(edge)
                    _traverse_local(adv, depth - 1, out_dir, edges, visited)
        except Exception:
            continue


def _edges_to_dot(root: str, edges: list) -> str:
    """Convert edge list to Graphviz DOT format."""
    lines = ["digraph lineage {", '  rankdir=BT;', f'  "{root}" [style=filled, fillcolor=lightblue];']
    for e in edges:
        lines.append(f'  "{e["from"]}" -> "{e["to"]}" [label="{e.get("relation", "")}"];')
    lines.append("}")
    return "\n".join(lines)


if __name__ == "__main__":
    cli()
