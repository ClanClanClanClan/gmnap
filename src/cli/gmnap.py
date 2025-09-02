import click, json, sys, pathlib
@click.group()
def cli(): pass

@cli.command()
@click.argument("name")
def query(name):
    """Query by name (demo: echo)."""
    print(json.dumps({"query": name, "hits": []}, indent=2))

@cli.command()
@click.option("--id", "gid", required=True)
@click.option("--depth", default=3, type=int)
@click.option("--format", default="svg")
def lineage(gid, depth, format):
    print(json.dumps({"id": gid, "depth": depth, "format": format}, indent=2))

if __name__ == "__main__":
    cli()
