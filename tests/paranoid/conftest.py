from pathlib import Path
import os, sys, json, random, pathlib, importlib, time
import pytest

# Deterministic execution
os.environ.setdefault("OFFLINE", "1")
os.environ.setdefault("PYTHONHASHSEED", "0")
random.seed(1337)

# Add user's project root if `src/` exists
CWD = pathlib.Path.cwd()
if (CWD / "src").exists():
    sys.path.insert(0, str(CWD))


# Try locating pipeline entry point
def _fallback_pipeline(batch):
    return batch


@pytest.fixture(scope="session")
def pipeline_process():
    try:
        mod = importlib.import_module("src.core.pipeline_v7")
        if hasattr(mod, "process"):
            return mod.process
        if hasattr(mod, "PipelineV7"):

            def _run(batch):
                p = mod.PipelineV7()
                return p.run(batch)

            return _run
    except Exception:
        pass
    return _fallback_pipeline


@pytest.fixture
def tiny_dataset():
    return [
        {
            "GlobalID": "G-001",
            "CanonicalLatin": "Euler, Leonhard",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "verified",
        },
        {
            "GlobalID": "G-002",
            "CanonicalLatin": "Гаусс, Карл Фридрих",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "verified",
            "Advisors": ["G-001"],
        },
        {
            "GlobalID": "G-003",
            "CanonicalLatin": "李, 华",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "verified",
        },
    ]


@pytest.fixture
def dice():
    def _bigrams(s: str):
        s = s or ""
        return set(s[i : i + 2] for i in range(len(s) - 1)) if len(s) >= 2 else {s}

    def _dice(a: str, b: str) -> float:
        A, B = _bigrams(a.casefold()), _bigrams(b.casefold())
        if not A and not B:
            return 1.0
        return 2 * len(A & B) / (len(A) + len(B))

    return _dice
