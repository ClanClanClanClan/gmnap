from __future__ import annotations
import pathlib
from typing import List
from .metrics import DB_APPLY_QUERIES
from ..core.db_pool import DBPool


def _split_cypher(content: str) -> List[str]:
    # naive split by semicolon; ignore empty/whitespace and comments
    parts = []
    buf = []
    for line in content.splitlines():
        ln = line.strip()
        if not ln or ln.startswith("//"):
            continue
        buf.append(ln)
        if ln.endswith(";"):
            parts.append(" ".join(buf)[:-1].strip())
            buf = []
    if buf:
        parts.append(" ".join(buf).strip())
    return parts


async def apply_changelog(changelog_path: str, pool: DBPool | None = None) -> int:
    p = pathlib.Path(changelog_path)
    content = p.read_text(encoding="utf-8")
    stmts = _split_cypher(content)
    if pool is None:
        pool = await DBPool().start()
    count = 0
    for s in stmts:
        try:
            await pool.execute(s)
            DB_APPLY_QUERIES.inc()
            count += 1
        except Exception:
            # best-effort apply
            pass
    return count


async def apply_latest_changelog(snapshot_dir: str, pool: DBPool | None = None) -> int:
    p = pathlib.Path(snapshot_dir) / "changelog.cypher"
    if not p.exists():
        return 0
    return await apply_changelog(str(p), pool=pool)
