"""Unit tests for ``src.genealogy.query``.

The live-graph branch of ``/api/v1/lineage``. Tests use mocked neo4j
driver so they run without a Memgraph container — real integration is
covered by ``tools/load_memgraph_from_enrichment.py`` on opt-in.

Three concerns this suite pins:

1. **Connection-failure path returns None** (not an exception). The
   endpoint's middleware depends on this to fall through to the YAML
   path + curated JSON.
2. **Normalisation matches the enrichment file**. If a query comes in
   as "Euler, Leonhard" or "name:Euler, Leonhard" or "euler, leonhard",
   all three hit the same ``p.key = 'euler, leonhard'`` lookup.
3. **DOT output** is valid Graphviz (``rankdir=BT``, quoted node
   labels, one edge per hop).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.genealogy.query import (
    _fold_particles,
    _normalize_key,
    lineage_to_dot,
    query_lineage,
)

# --- Normalisation parity ------------------------------------------------


class TestNormalizeKey:
    def test_reorders_first_last(self):
        assert _normalize_key("Leonhard Euler") == "euler, leonhard"

    def test_diacritic_folded(self):
        assert _normalize_key("Poincaré, Henri") == "poincare, henri"

    def test_drops_parenthetical(self):
        assert _normalize_key("G. H. (Godfrey Harold) Hardy") == "hardy, g. h."

    def test_folds_leading_particle(self):
        assert (
            _normalize_key("von Neumann, John")
            == _normalize_key("Neumann, John von")
            == "neumann, john von"
        )

    def test_empty(self):
        assert _normalize_key("") == ""
        assert _normalize_key("   ") == ""

    def test_fold_particles_noop_without_comma(self):
        assert _fold_particles("no comma here") == "no comma here"


# --- Connection-failure path --------------------------------------------


class TestDriverFailurePath:
    def test_returns_none_when_driver_module_missing(self):
        with patch("src.genealogy.query._DRIVER_AVAILABLE", False):
            assert (
                query_lineage("Euler, Leonhard", depth=3, bolt_uri="bolt://x") is None
            )

    def test_returns_none_when_connect_fails(self):
        # _driver swallows ServiceUnavailable / OSError / Neo4jError
        # and returns None.
        with patch("src.genealogy.query.GraphDatabase") as gd:
            gd.driver.side_effect = OSError("connection refused")
            assert (
                query_lineage(
                    "Euler, Leonhard", depth=3, bolt_uri="bolt://localhost:9999"
                )
                is None
            )

    def test_depth_zero_short_circuits_without_driver_touch(self):
        # Guard the hot path: depth<=0 must NOT even try to open a
        # driver session.
        with patch("src.genealogy.query._driver") as d:
            result = query_lineage("Euler, Leonhard", depth=0)
            assert result == {"root": "Euler, Leonhard", "depth": 0, "edges": []}
            d.assert_not_called()


# --- Happy path via mocked driver ---------------------------------------


def _mock_driver_returning(root_name: str, edges: list[tuple[str, str]]):
    """Return a mocked GraphDatabase that serves a root lookup + an
    edge traversal result."""
    session = MagicMock()

    # First .run() call resolves the root
    root_row = {"name": root_name} if root_name else None
    root_single = MagicMock()
    root_single.single.return_value = root_row

    # Second .run() call returns an iterable of rows
    edge_rows = [{"from_name": f, "to_name": t} for f, t in edges]
    traversal_result = MagicMock()
    traversal_result.__iter__.return_value = iter(edge_rows)

    # Sequence: root lookup, traversal
    session.run.side_effect = [root_single, traversal_result]

    ctx = MagicMock()
    ctx.__enter__.return_value = session
    ctx.__exit__.return_value = False

    drv = MagicMock()
    drv.session.return_value = ctx
    drv.verify_connectivity.return_value = None
    drv.close.return_value = None
    return drv, session


class TestQueryLineage:
    def test_returns_shaped_edges(self):
        drv, _ = _mock_driver_returning(
            "Euler, Leonhard",
            [
                ("Euler, Leonhard", "Bernoulli, Johann"),
                ("Bernoulli, Johann", "Bernoulli, Jacob"),
            ],
        )
        with patch("src.genealogy.query._driver", return_value=drv):
            r = query_lineage("name:Euler, Leonhard", depth=3)
        assert r is not None
        assert r["root"] == "name:Euler, Leonhard"
        assert r["root_name"] == "Euler, Leonhard"
        assert len(r["edges"]) == 2
        assert r["edges"][0] == {
            "from": "Euler, Leonhard",
            "to": "Bernoulli, Johann",
            "relation": "doctoralAdvisor",
        }

    def test_returns_empty_edges_when_root_missing(self):
        drv, session = _mock_driver_returning("", [])
        with patch("src.genealogy.query._driver", return_value=drv):
            r = query_lineage("Nobody, Unknown", depth=3)
        assert r == {"root": "Nobody, Unknown", "depth": 3, "edges": []}
        # Verify the root-lookup query actually ran, and no traversal
        # query followed (early-return short-circuit).
        assert (
            session.run.call_count == 1
        ), f"expected single root-lookup, got {session.run.call_count} calls"
        root_cypher = session.run.call_args_list[0].args[0]
        assert "MATCH (p:Person)" in root_cypher
        assert "RETURN p.name" in root_cypher

    def test_depth_clamped_to_10_in_cypher(self):
        # Confirm the depth substitution is CLAMPED to 10 even for a
        # huge depth request — otherwise a `*1..999` pattern would kill
        # the graph server.
        drv, session = _mock_driver_returning("Euler, Leonhard", [])
        with patch("src.genealogy.query._driver", return_value=drv):
            r = query_lineage("Euler, Leonhard", depth=999)
        assert r is not None
        # Two calls: root lookup, then traversal. Inspect traversal.
        assert session.run.call_count == 2
        traversal_cypher = session.run.call_args_list[1].args[0]
        assert (
            "*1..10" in traversal_cypher
        ), f"expected depth clamp to 10, got cypher:\n{traversal_cypher}"
        assert "*1..999" not in traversal_cypher

    def test_depth_one_passes_one_to_cypher(self):
        drv, session = _mock_driver_returning("Euler, Leonhard", [])
        with patch("src.genealogy.query._driver", return_value=drv):
            query_lineage("Euler, Leonhard", depth=1)
        traversal_cypher = session.run.call_args_list[1].args[0]
        assert "*1..1" in traversal_cypher

    def test_skips_rows_missing_fields(self):
        drv, _ = _mock_driver_returning(
            "Euler, Leonhard",
            [("Euler, Leonhard", "Bernoulli, Johann"), ("", "Orphan")],
        )
        with patch("src.genealogy.query._driver", return_value=drv):
            r = query_lineage("Euler, Leonhard", depth=2)
        assert r is not None
        assert len(r["edges"]) == 1


# --- DOT rendering ------------------------------------------------------


class TestLineageToDot:
    def test_bt_rankdir(self):
        r = {
            "root": "Euler, Leonhard",
            "depth": 2,
            "edges": [
                {
                    "from": "Euler, Leonhard",
                    "to": "Bernoulli, Johann",
                    "relation": "doctoralAdvisor",
                }
            ],
        }
        dot = lineage_to_dot(r)
        assert "digraph Lineage" in dot
        assert "rankdir=BT" in dot
        assert '"Euler, Leonhard" -> "Bernoulli, Johann"' in dot

    def test_empty_edges_still_emits_root(self):
        r = {"root": "Solo", "root_name": "Solo, Node", "depth": 1, "edges": []}
        dot = lineage_to_dot(r)
        assert '"Solo, Node"' in dot

    def test_none_input(self):
        # Defensive — docstring says None → empty graph, not exception
        dot = lineage_to_dot({})
        assert "digraph" in dot

    def test_drops_edges_without_both_endpoints(self):
        r = {
            "edges": [
                {"from": "A", "to": "B"},
                {"from": "", "to": "C"},
                {"from": "D", "to": ""},
            ]
        }
        dot = lineage_to_dot(r)
        assert '"A" -> "B"' in dot
        assert '"C"' not in dot
        assert '"D"' not in dot


# --- Import-side-effect test -------------------------------------------


class TestImport:
    def test_module_imports_without_crash(self):
        # Regression guard for the bug the audit caught — server.py
        # tries `from src.genealogy.query import ...` and this used
        # to be ModuleNotFoundError.
        import importlib

        mod = importlib.import_module("src.genealogy.query")
        assert hasattr(mod, "query_lineage")
        assert hasattr(mod, "lineage_to_dot")


# --- /readyz Bolt probe contract ---------------------------------------


class TestReadyzBoltProbe:
    """`/readyz` now uses ``_driver()`` for its Memgraph check.

    Previously it opened a raw TCP socket and treated any handshake
    response as "ready" — passed even when Memgraph was alive but
    auth was broken. These tests pin the new contract:

    - With ``MEMGRAPH_BOLT`` unset → readiness skipped, returns 200.
    - With it set and ``_driver`` returning a driver → 200.
    - With it set and ``_driver`` returning None (driver missing OR
      bolt port closed OR auth failed) → 503.
    """

    def _make_app(self):
        # Local import — avoids module-load cost on tests that don't
        # need the FastAPI factory. Reset the module-level rate limiter
        # state too, otherwise sequential tests in this class share a
        # sliding window and earlier tests' /readyz calls trigger 429
        # for later tests on busy CI.
        from fastapi.testclient import TestClient

        from src.api import server as srv

        srv._rate_limiter._windows.clear()
        return TestClient(srv.create_app())

    def test_passes_when_memgraph_unset(self, monkeypatch):
        monkeypatch.delenv("MEMGRAPH_BOLT", raising=False)
        client = self._make_app()
        r = client.get("/readyz")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"

    def test_503_when_driver_returns_none(self, monkeypatch):
        monkeypatch.setenv("MEMGRAPH_BOLT", "bolt://localhost:7687")
        with patch("src.genealogy.query._driver", return_value=None):
            client = self._make_app()
            r = client.get("/readyz")
        assert r.status_code == 503
        assert r.json()["detail"] == "Graph DB not ready"

    def test_200_when_driver_returns_real(self, monkeypatch):
        monkeypatch.setenv("MEMGRAPH_BOLT", "bolt://localhost:7687")
        fake = MagicMock()
        fake.close.return_value = None
        with patch("src.genealogy.query._driver", return_value=fake):
            client = self._make_app()
            r = client.get("/readyz")
        assert r.status_code == 200
        # Must close the driver to avoid leaking connections
        fake.close.assert_called_once()
