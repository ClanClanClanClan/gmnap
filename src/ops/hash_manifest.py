from __future__ import annotations
import hashlib, os, pathlib, json


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksums_for_dir(dir_path: str, relbase: str | None = None) -> str:
    p = pathlib.Path(dir_path)
    out_lines = []
    for base, _, files in os.walk(p):
        for fn in files:
            fp = pathlib.Path(base) / fn
            rel = fp.relative_to(relbase or p) if relbase else fp.relative_to(p)
            out_lines.append(f"{sha256_file(str(fp))}  {rel.as_posix()}")
    txt = "\n".join(sorted(out_lines)) + "\n"
    out = p / "CHECKSUMS.sha256"
    out.write_text(txt, encoding="utf-8")
    return str(out)


def write_manifest_json(dir_path: str) -> str:
    p = pathlib.Path(dir_path)
    listing = []
    for base, _, files in os.walk(p):
        for fn in files:
            fp = pathlib.Path(base) / fn
            listing.append(fp.relative_to(p).as_posix())
    m = {"dir": str(p), "count": len(listing), "files": sorted(listing)}
    out = p / "MANIFEST.json"
    out.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)
