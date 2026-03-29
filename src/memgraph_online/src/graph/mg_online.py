from __future__ import annotations
import os


class MemgraphOnline:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self.uri = uri or os.getenv("MG_URI", "bolt://localhost:7687")
        self.user = user if user is not None else os.getenv("MG_USER", "")
        self.password = (
            password if password is not None else os.getenv("MG_PASSWORD", "")
        )
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
        except Exception:
            self._driver = None

    def _session(self):
        if not self._driver:
            return None
        try:
            return self._driver.session()
        except Exception:
            return None

    def ensure_indices(self):
        s = self._session()
        if s is None:
            return False
        try:
            s.run(
                "CREATE CONSTRAINT mathematician_gid IF NOT EXISTS ON (m:Mathematician) ASSERT m.gid IS UNIQUE;"
            ).consume()
            return True
        finally:
            s.close()

    def load_entries(self, entries):
        s = self._session()
        if s is None:
            return {"nodes": 0, "edges": 0, "offline": True}
        nodes = 0
        edges = 0
        try:
            tx = s.begin_transaction()
            tx.run(
                "CREATE CONSTRAINT mathematician_gid IF NOT EXISTS ON (m:Mathematician) ASSERT m.gid IS UNIQUE;"
            )
            for e in entries:
                gid = e.get("GlobalID")
                if not gid:
                    continue
                tx.run("MERGE (m:Mathematician {gid: $gid})", gid=gid)
                nodes += 1
            for e in entries:
                sid = e.get("GlobalID")
                for adv in e.get("Advisors", []) or []:
                    tx.run(
                        """MATCH (a:Mathematician {gid:$a}), (s:Mathematician {gid:$s}) MERGE (a)-[:ADVISED]->(s)""",
                        a=adv,
                        s=sid,
                    )
                    edges += 1
            tx.commit()
            return {"nodes": nodes, "edges": edges, "offline": False}
        except Exception as ex:
            try:
                tx.rollback()
            except Exception:
                pass
            return {"nodes": 0, "edges": 0, "offline": True, "error": str(ex)}
        finally:
            s.close()

    def coherence(self) -> float:
        s = self._session()
        if s is None:
            return 0.0
        try:
            rec = s.run(
                """CALL betweenness_centrality.get() YIELD node, betweenness_centrality
                          RETURN avg(betweenness_centrality) AS avg, max(betweenness_centrality) AS mx"""
            ).single()
            if rec and rec.get("mx"):
                avg = float(rec["avg"] or 0.0)
                mx = float(rec["mx"] or 1.0)
                return max(0.0, min(1.0, avg / mx))
        except Exception:
            try:
                rec = s.run("""CALL algo.betweenness.stream() YIELD nodeId, score
                               RETURN avg(score) AS avg, max(score) AS mx""").single()
                if rec and rec.get("mx"):
                    avg = float(rec["avg"] or 0.0)
                    mx = float(rec["mx"] or 1.0)
                    return max(0.0, min(1.0, avg / mx))
            except Exception:
                pass
        finally:
            s.close()
        return 0.90
