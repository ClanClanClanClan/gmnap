"""End-to-end integration tests against a live Memgraph 2.12.

These tests:

1. validate that ``tools/load_memgraph_from_enrichment.py`` writes the
   schema (constraint on :Person.key, indexes on :Person.global_id and
   :Person.name) that ``src/genealogy/query.py`` reads back;
2. spawn a real ``uvicorn`` instance pointed at the loaded Memgraph
   and confirm ``/api/v1/lineage/name:Euler,%20Leonhard`` returns
   edges *from the graph* — not from the YAML or curated-JSON fallback;
3. confirm ``/readyz`` returns 200 against the live Memgraph and 503
   against a dead bolt port.

When ``MEMGRAPH_BOLT`` is unset (the default for most CI runs / dev
laptops without docker), every test in this module skips. The
dedicated ``memgraph-test`` CI job sets the env var via a
``services:`` block; the regular ``test`` job collects + skips so a
broken integration surface still shows up as "skipped" rather than
silently disappearing.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

import pytest

REPO = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.skipif(
    not os.getenv("MEMGRAPH_BOLT"),
    reason="MEMGRAPH_BOLT not set — skipping live integration tests",
)


# ─── Shared fixtures ────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def loaded_memgraph() -> Generator[str, None, None]:
    """Run the loader against the live Memgraph once per module.

    Idempotent: if the loader has already populated the graph, the
    MERGE statements update-in-place. We also do a sanity check on
    person count; if zero, the fixture fails loud.
    """
    bolt = os.environ["MEMGRAPH_BOLT"]
    user = os.environ.get("MEMGRAPH_USER", "")
    password = os.environ.get("MEMGRAPH_PASSWORD", "")

    # Run the loader as a subprocess so we exercise the same entry
    # point CI does. Cap at 2 minutes — the 20 k-entry load runs in
    # well under a minute on Memgraph 2.12.
    cmd = [
        sys.executable,
        "tools/load_memgraph_from_enrichment.py",
        "--bolt",
        bolt,
        "--user",
        user,
        "--password",
        password,
    ]
    # Loader does ~60 k MERGEs (~39 k :Person + ~21 k advisor edges
    # after round-23's partition-harvest expansion). On GitHub
    # Actions runners with cold Memgraph caches this takes
    # ≈ 4-8 min; cap at 15 minutes to stay below the job's 30-minute
    # overall budget. Round-26 caught a 300 s timeout when the
    # round-23 harvest doubled the dataset.
    proc = subprocess.run(
        cmd,
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, (
        f"loader failed (rc={proc.returncode}):\n"
        f"stdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}"
    )

    # Sanity: we expect ≥ 35 000 :Person nodes (round-23 enrichment
    # contains 39,497; load is idempotent so re-runs land at the same
    # count). Lower bound 35 000 leaves margin for partial-load
    # tolerance without dropping below the previous ~27k floor.
    from neo4j import GraphDatabase  # type: ignore

    auth = (user, password) if user else None
    drv = GraphDatabase.driver(bolt, auth=auth, connection_timeout=5)
    drv.verify_connectivity()
    try:
        with drv.session() as s:
            count = s.run("MATCH (p:Person) RETURN count(p) AS n").single()["n"]
        assert count > 35000, f"expected > 35 000 :Person nodes, got {count}"
    finally:
        drv.close()
    yield bolt


# ─── 1. Loader → schema → query.py round-trip ──────────────────────────


def test_loader_creates_person_nodes(loaded_memgraph):
    """The loader's :Person nodes must be readable by query.py."""
    from src.genealogy.query import query_lineage

    r = query_lineage("name:Euler, Leonhard", depth=3, bolt_uri=loaded_memgraph)
    assert r is not None, "query_lineage returned None — driver issue?"
    assert r.get("root_name") == "Euler, Leonhard"
    edges = r.get("edges") or []
    assert edges, "expected ≥ 1 advisor edge for Euler"
    # First hop must be Bernoulli, Johann
    assert edges[0]["from"] == "Euler, Leonhard"
    assert edges[0]["to"] == "Bernoulli, Johann"
    assert edges[0]["relation"] == "doctoralAdvisor"


# ─── 2. Lineage endpoint actually serves graph data ────────────────────


def _hashcash(bits: int = 18) -> str:
    """Generate a fresh 18-bit hashcash stamp the server will accept."""
    date = datetime.now(timezone.utc).strftime("%y%m%d")
    rand = "intg"
    counter = 0
    while True:
        stamp = f"1:{bits}:{date}:gmnap-api::{rand}:{counter:x}"
        h = hashlib.sha256(stamp.encode()).digest()
        zeros = 0
        for b in h:
            if b == 0:
                zeros += 8
                continue
            t = b
            while (t & 0x80) == 0:
                zeros += 1
                t <<= 1
            break
        if zeros >= bits:
            return stamp
        counter += 1


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_uvicorn(port: int, bolt: str) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO)
    env["MEMGRAPH_BOLT"] = bolt
    # Allow rapid-fire test traffic
    env["GMNAP_FREE_RPM"] = "10000"
    env["GMNAP_LOG_LEVEL"] = "WARNING"
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(REPO),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_readyz(port: int, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/readyz", timeout=1.0
            ) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, socket.error):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"uvicorn not ready on port {port}")


def _http_get_json(url: str) -> tuple[int, Optional[dict]]:
    req = urllib.request.Request(url, headers={"X-Hashcash": _hashcash(18)})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            return resp.status, body
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            body = None
        return e.code, body


def test_lineage_endpoint_returns_real_graph_data(loaded_memgraph):
    """The /api/v1/lineage handler must use the live Memgraph branch
    when the graph is up — not silently fall through to YAML/JSON."""
    port = _free_port()
    proc = _start_uvicorn(port, loaded_memgraph)
    try:
        _wait_for_readyz(port)

        status, body = _http_get_json(
            f"http://127.0.0.1:{port}/api/v1/lineage/" f"name:Euler,%20Leonhard?depth=3"
        )
        assert status == 200, f"got {status}: {body}"
        assert body and body.get("edges"), f"no edges: {body}"
        # Root name comes from query.py's resolution path (not from
        # the curated JSON which doesn't set this field).
        assert body.get("root_name") == "Euler, Leonhard", (
            "missing root_name — endpoint fell through to JSON fallback "
            "instead of using Memgraph"
        )
        pairs = {(e["from"], e["to"]) for e in body["edges"]}
        assert ("Euler, Leonhard", "Bernoulli, Johann") in pairs
    finally:
        proc.send_signal(2)  # SIGINT
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


# ─── 3. /readyz distinguishes alive-and-well vs alive-but-broken ───────


def test_readyz_passes_when_memgraph_up(loaded_memgraph):
    port = _free_port()
    proc = _start_uvicorn(port, loaded_memgraph)
    try:
        _wait_for_readyz(port)
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/readyz", timeout=5
        ) as resp:
            assert resp.status == 200
    finally:
        proc.send_signal(2)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_readyz_returns_503_when_memgraph_unreachable(loaded_memgraph):
    """Point the server at a closed port — must return 503, not 200."""
    port = _free_port()
    bad_bolt = "bolt://127.0.0.1:1"  # port 1 is reserved/closed
    proc = _start_uvicorn(port, bad_bolt)
    try:
        # Don't use _wait_for_readyz: it'd loop forever waiting for 200.
        # Instead poll /healthz which doesn't depend on Memgraph.
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/healthz", timeout=1.0
                ) as r:
                    if r.status == 200:
                        break
            except Exception:
                pass
            time.sleep(0.3)

        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/readyz", timeout=5
            ) as resp:
                # Should not happen
                pytest.fail(f"expected 503, got {resp.status}")
        except urllib.error.HTTPError as e:
            assert e.code == 503, f"expected 503, got {e.code}"
    finally:
        proc.send_signal(2)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
