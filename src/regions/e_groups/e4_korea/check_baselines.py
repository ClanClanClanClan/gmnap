import yaml, pathlib

for tag, file in (
    ("math", "data/korean.yaml"),
    ("diverse", "data/diverse.yaml"),
    ("indep", "data/independent.yaml"),
):
    rows = yaml.safe_load(pathlib.Path(file).read_text())
    print(f"{tag}: {len(rows)} rows")
