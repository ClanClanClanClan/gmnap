from __future__ import annotations

from fastapi import FastAPI
from neo4j import GraphDatabase

from .schema import LineagePath, LineageResponse

app = FastAPI()


def driver():
    return GraphDatabase.driver("bolt://localhost:7687", auth=None)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/genealogy/lineage/{global_id}", response_model=LineageResponse)
def lineage(global_id: str, max_depth: int = 10):
    with driver().session() as sess:
        recs = sess.run(
            """MATCH (s:Mathematician {global_id:$id})
WITH s
MATCH p=(s)-[:DOCTORAL_ADVISOR*1..$d]->(a)
RETURN length(p) as L, [n IN nodes(p) | n.global_id] as N
            """,
            id=global_id,
            d=max_depth,
        )
        paths = [LineagePath(length=r["L"], nodes=r["N"]) for r in recs]
        return LineageResponse(start=global_id, depth=max_depth, paths=paths)


@app.get("/genealogy/descendants/{global_id}", response_model=LineageResponse)
def descendants(global_id: str, max_depth: int = 10):
    with driver().session() as sess:
        recs = sess.run(
            """MATCH (a:Mathematician {global_id:$id})
WITH a
MATCH p=(s)-[:DOCTORAL_ADVISOR*1..$d]->(a)
RETURN length(p) as L, [n IN nodes(p) | n.global_id] as N
            """,
            id=global_id,
            d=max_depth,
        )
        paths = [LineagePath(length=r["L"], nodes=r["N"]) for r in recs]
        return LineageResponse(start=global_id, depth=max_depth, paths=paths)
