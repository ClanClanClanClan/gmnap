"""Build-vs-runtime contracts that must never drift silently (R50 §2b.7/.9).

1. The genealogy corpus builder's ``normalize_key`` and the runtime
   ``GenealogyLookup._normalize_key`` must agree byte-for-byte — a drift
   makes freshly-built corpus keys unresolvable at runtime.
2. docker-compose shape: the dev service, healthcheck gating, and the
   graceful-shutdown grace period are beyond-spec keepers that a compose
   refactor could silently drop.
"""

from pathlib import Path

import pytest
import yaml

from src.core.genealogy_lookup import _normalize_key as runtime_key

REPO = Path(__file__).resolve().parents[2]


def _builder_key():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_genealogy_enrichment", REPO / "tools" / "build_genealogy_enrichment.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.normalize_key


@pytest.mark.timeout(30)
def test_normalize_key_build_runtime_parity():
    builder_key = _builder_key()
    cases = [
        "Erdős, Pál",
        "van der Waerden, Bartel",
        "von Neumann, John",
        "O'Connor, Seán",
        "Nguyễn, Văn A",
        "Hilbert, David (David)",
        "  Gauss ,  Carl-Friedrich  ",
        "ÉRDOS, PAL",
        "李, 明",
    ]
    for name in cases:
        assert builder_key(name) == runtime_key(name), name


@pytest.mark.timeout(30)
def test_compose_shape_keeps_beyond_spec_features():
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text())
    services = compose.get("services", {})
    assert "gmnap-dev" in services, "dev service dropped"
    gmnap = services.get("gmnap", {})
    assert gmnap.get("stop_grace_period") == "120s", "graceful shutdown dropped"
    depends = gmnap.get("depends_on", {})
    assert any(
        isinstance(v, dict) and v.get("condition") == "service_healthy"
        for v in (depends.values() if isinstance(depends, dict) else [])
    ), "healthcheck gating dropped"
